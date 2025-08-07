from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional, Set, Type
from uuid import UUID
import logging
from contextlib import asynccontextmanager
from ..registry.registry import AgentRegistrySystem
from ..discovery.agent_discovery import AgentDiscovery
from ..interfaces.agent import AgentInterface
from ..registry.registry_models import AgentStatus
from ..services.llm_service import llm_service

from ..meta.meta_agent import MetaAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# TODO: add image based processing to ocr -> create vectors based on multimodal
# TODO: create streaming for final ai call and general reasoning


meta_agent = MetaAgent()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # global meta_agent
    # meta_agent = await MetaAgent()

    await auto_register_agents()
    yield

    # Shutdown
    logger.info("Shutting down MCP server")


app = FastAPI(title="Samvid MCP", version="0.1.0", lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    registry_state = await meta_agent.agent_registry.get_registry_state()
    return {
        "status": "healthy",
        "server_initialized": True,
        "agents_count": registry_state.get("total_agents", 0),
        "active_agents": registry_state.get("active_agents", 0),
        "version": "0.1.0",
    }

    # @app.get("/mcp/{agent_id}/tools")
    # async def list_tools(agent_id: str):
    """List all tools for a specific agent in an MCP-compliant format."""
    try:
        tools = await meta_agent.get_tools_for_agent(agent_id)
        return tools

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID")
    except Exception as e:
        logger.error(f"Error listing tools for agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp/agents")
async def list_agents():
    """List all registered agents in an MCP-compliant format."""
    return await meta_agent.get_agents()


"""
/execute/{agent_id}/{tool_id} should return:
{
	"success": true,
	"error": "string (optional)",
	"metadata": {
		"executionTime": "number",
		"toolVersion": "string ('1.0' if not defined)"
	},
	"data": {
		[same values returned from tool, specified in each of the return values of get_tools()'s returnValues field]
	}
}
"""


@app.post("/mcp/execute/{agent_id}")
async def execute_agent(agent_id: str, request: Dict[str, Any]):
    try:
        if not request.get("query"):
            return HTTPException(status_code=400, detail="Query is required")

        return await meta_agent.handle_execute_tool_via_agent_request(
            agent_id, request.get("query")
        )
    except Exception as e:
        logger.error(f"Error executing agent {agent_id}: {str(e)}")
        return HTTPException(status_code=500, detail=str(e))


# TODO: UUID hash for tools
@app.post("/execute/{agent_id}/{tool_id}")
async def execute_agent_capability(
    agent_id: str, tool_id: str, parameters: Dict[str, Any]
):
    """
    Execute a specific tool of an agent.
    This endpoint allows direct execution of agent tools by ID.

    Args:
                                                                    agent_id: The UUID of the agent to execute
                                                                    tool_id: The ID/name of the tool to execute
                                                                    parameters: The parameters to pass to the tool (in request body)

    Returns:
                                                                    Structured response with success status, metadata, and tool result data
    """
    print(f"Executing {agent_id}.{tool_id} with parameters {parameters}")
    import time

    start_time = time.time()

    try:
        # Get the agent instance
        agent_uuid = UUID(agent_id)
        agent = await meta_agent.agent_registry.get_agent(agent_uuid)

        if not agent:
            return {
                "success": False,
                "error": f"Agent with ID {agent_id} not found",
                "metadata": {
                    "executionTime": (time.time() - start_time) * 1000,
                    "toolVersion": "1.0",
                },
                "data": {},
            }

        # Check if the agent has the requested tool
        tools_list = agent.get_tools()
        available_tools = [tool.get("name", "") for tool in tools_list]

        # Find the specific tool to get its version
        tool_version = "1.0"  # default
        tool_found = False
        for tool in tools_list:
            if tool.get("name", "") == tool_id:
                tool_found = True
                # Check if tool has version info in metadata or other fields
                tool_version = tool.get("version", tool.get("toolVersion", "1.0"))
                break

        if not tool_found:
            return {
                "success": False,
                "error": f"Tool '{tool_id}' not found in agent '{agent_id}'. Available tools: {available_tools}",
                "metadata": {
                    "executionTime": (time.time() - start_time) * 1000,
                    "toolVersion": tool_version,
                },
                "data": {},
            }

        # Execute the tool
        request = {"command": tool_id, **parameters}
        result = await agent.process_request(request)

        execution_time = (time.time() - start_time) * 1000

        return {
            "success": True,
            "metadata": {"executionTime": execution_time, "toolVersion": tool_version},
            "data": result,
        }

    except ValueError as e:
        execution_time = (time.time() - start_time) * 1000
        return {
            "success": False,
            "error": f"Invalid agent ID: {str(e)}",
            "metadata": {"executionTime": execution_time, "toolVersion": "1.0"},
            "data": {},
        }
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(f"Error executing {agent_id}.{tool_id}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "metadata": {"executionTime": execution_time, "toolVersion": "1.0"},
            "data": {},
        }


async def auto_register_agents():
    """
    Automatically discover and register all available agents.
    This function is called on server startup and when the /discover endpoint is hit.
    """
    # Keep track of registered agent classes to avoid duplicates
    registered_agents: Set[Type[AgentInterface]] = set()

    # Dictionary to map agent names to their IDs for easier lookup
    agent_name_to_id = {}

    logger.info("Starting automatic agent discovery and registration")

    # Discover all available agents
    logger.info("Calling discovery.discover_agents()...")
    agent_classes = await meta_agent.discovery.discover_agents()
    logger.info(
        f"Discovery returned {len(agent_classes)} agent classes: {list(agent_classes.keys())}"
    )

    # Register each discovered agent
    for module_name, agent_class in agent_classes.items():
        try:
            # Skip already registered agent classes
            if agent_class in registered_agents:
                logger.info(f"Agent {module_name} already registered, skipping")
                continue

            # Create default config - can be customized per agent type if needed
            default_config = {}

            # Register the agent and use the deterministic agent_id
            logger.info(f"Registering agent {module_name}...")
            agent_id = await meta_agent.agent_registry.register_agent(
                agent_class, default_config
            )
            registered_agents.add(agent_class)

            # Get the agent instance to access its name
            agent = await meta_agent.agent_registry.get_agent(agent_id)
            if agent:
                # Store the mapping from agent name to ID for easier lookup
                agent_name_to_id[agent.name] = agent_id
                logger.info(f"Mapped agent name '{agent.name}' to ID {agent_id}")

            logger.info(f"Auto-registered agent {module_name} with ID {agent_id}")
        except Exception as e:
            logger.error(f"Error auto-registering agent {module_name}: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")

    logger.info(
        f"Auto-registration complete. {len(registered_agents)} agents registered."
    )
    logger.info(f"Agent name to ID mapping: {agent_name_to_id}")


# @app.post("/tool-generator/execute")
# async def execute_tool_generator(request: Dict[str, Any]):
#     """
#     Convenience endpoint for the tool generator.
#     Accepts a query and data, then generates and executes a dynamic tool.
#     """
#     try:
#         query = request.get("query", "")
#         data = request.get("data", [])

#         if not query:
#             raise HTTPException(status_code=400, detail="Query is required")
#         if not data:
#             raise HTTPException(status_code=400, detail="Data is required")

#         # Find the tool generator agent
#         agent_id = agent_name_to_id.get("Tool Generator Agent")
#         if not agent_id:
#             raise HTTPException(
#                 status_code=404, detail="Tool Generator Agent not found"
#             )

#         # Get the agent instance
#         agent = await registry.get_agent(agent_id)
#         if not agent:
#             raise HTTPException(
#                 status_code=404, detail="Tool Generator Agent not available"
#             )

#         # Execute the tool generation
#         result = await agent.process_request(
#             {"command": "generate_and_execute", "query": query, "data": data}
#         )

#         return result

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error in tool generator: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))


# @app.post("/llm/completion")
# async def llm_completion(request: Dict[str, Any]):
#     """
#     Simple LLM completion endpoint that proxies to llm_service.simple_completion.

#     Expected request format:
#     {
#         "prompt": "Your prompt here",
#         "model": "optional-model-name",
#         "temperature": 0.7,
#         "max_tokens": 1000,
#         "provider": "openai",
#         "response_format": {"type": "json_object"}
#     }

#     Returns:
#     {
#         "completion": "LLM response text",
#         "provider": "provider_name",
#         "model": "model_used"
#     }
#     """
#     try:
#         # Extract required and optional parameters
#         prompt = request.get("prompt")
#         if not prompt:
#             raise HTTPException(status_code=400, detail="Prompt is required")

#         # Call the LLM service
#         completion = await llm_service.simple_completion(prompt)

#         return {
#             "completion": completion,
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error in LLM completion: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("src.server.mcp_server:app", host="0.0.0.0", port=port, reload=False)
