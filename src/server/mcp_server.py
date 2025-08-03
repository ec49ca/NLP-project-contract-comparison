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

# Initialize core components
registry = AgentRegistrySystem()
discovery = AgentDiscovery()

# Keep track of registered agent classes to avoid duplicates
registered_agents: Set[Type[AgentInterface]] = set()

# Dictionary to map agent names to their IDs for easier lookup
agent_name_to_id = {}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
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
    registry_state = await registry.get_registry_state()
    return {
        "status": "healthy",
        "server_initialized": True,
        "agents_count": registry_state.get("total_agents", 0),
        "active_agents": registry_state.get("active_agents", 0),
        "version": "0.1.0",
    }


async def get_agent_tools(agent):
    """Helper function to get tools for an agent in MCP format (for list_agents)."""
    tools = []
    agent_tools = agent.get_tools()

    for tool in agent_tools:
        if isinstance(tool, dict):
            tools.append(
                {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {}),
                }
            )

    return tools


"""
/mcp/{agent_id}/tools should return:
{
	"total_tools": 1,
	"active_tools": 1,
	"tools": [
		{
			"agentId": "Agent1 ID",
			"id": "Tool1",
			"name": "Tool 1",
			"description": "Description of Tool 1",
			"parameters": {
				"parameter1": "description of parameter 1",
				"parameter2": "description of parameter 2"
			},
			"returnValues": {
				"description": "Description of what this tool returns",
				"structure": {
					"field1": "type - description of field1",
					"field2": "type - description of field2"
				}
			}

			OPTIONAL:
			metadata: {
				"metadata1": "description of metadata 1",
			},
			tags: [
				"tag1",
				"tag2"
			],
		}
	]
}
"""


@app.get("/mcp/{agent_id}/tools")
async def list_tools(agent_id: str):
    """List all tools for a specific agent in an MCP-compliant format."""
    try:
        # Get the specific agent
        agent_uuid = UUID(agent_id)
        agent = await registry.get_agent(agent_uuid)

        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Get tools from the agent
        tools = []
        agent_tools = agent.get_tools()

        for tool in agent_tools:
            if isinstance(tool, dict):
                tool_def = {
                    "agentId": str(agent_uuid),
                    "id": tool.get("name", ""),
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {}),
                }

                # Add returnValues if available
                if "returnValues" in tool:
                    tool_def["returnValues"] = tool["returnValues"]

                tools.append(tool_def)

        return {
            "total_tools": len(tools),
            "active_tools": len(tools),
            "tools": tools,
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID")
    except Exception as e:
        logger.error(f"Error listing tools for agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


"""
/mcp/agents should return:
{
	"total_agents": 1,
	"active_agents": 1,
	"agents": [
		{
			"id": "Agent1",
			"name": "Agent 1",
			"description": "Description of Agent 1",

			OPTIONAL:
			"tools": [
				{
					"name": "Tool 1",
					"description": "Description of Tool 1",
					"parameters": {}
				}
			],
			"tags": [
				"tag1",
				"tag2"
			],
			"isActive": true,
			"agentType": "agentType1"
		}
	]
}
"""


@app.get("/mcp/agents")
async def list_agents():
    """List all registered agents in an MCP-compliant format."""
    registry_state = await registry.get_registry_state()

    # Transform the response to be more MCP-compliant
    agents = []
    for agent_id, agent_info in registry_state.get("agents", {}).items():
        agent = await registry.get_agent(UUID(agent_id))
        if agent:
            agents.append(
                {
                    "id": agent.uuid,
                    "name": agent.name,
                    "description": agent.description,
                    "isActive": True,
                    "tools": await get_agent_tools(agent),
                }
            )

    return {
        "total_agents": registry_state.get("total_agents", 0),
        "active_agents": registry_state.get("active_agents", 0),
        "agents": agents,
    }


@app.get("/mcp/resources")
async def list_mcp_resources():
    """
    List all available MCP resources (agents and their capabilities).
    This endpoint is used by MCP clients to discover available resources.
    Follows the Model Context Protocol standard.
    """
    agents_state = await registry.get_registry_state()
    logger.info(
        f"MCP Resources: Got registry state with {len(agents_state.get('agents', {}))} agents"
    )

    resources = []

    for agent_id, agent_info in agents_state.get("agents", {}).items():
        logger.info(
            f"MCP Resources: Processing agent {agent_id} with info {agent_info}"
        )

        agent = await registry.get_agent(UUID(agent_id))
        if agent:
            logger.info(
                f"MCP Resources: Found agent {agent.name} with status {agent_info.get('status')}"
            )

            if agent_info.get("status") == AgentStatus.ACTIVE.value:
                logger.info(
                    f"MCP Resources: Agent {agent.name} is active, adding to resources"
                )

                # Add the agent as a resource with its full capabilities
                agent_resource = {
                    "name": agent.name,
                    "description": agent.description,
                    "type": "agent",
                    "capabilities": agent.get_tools(),
                }

                # Add each capability as a property of the agent resource
                capabilities_list = agent.get_tools()
                for capability_info in capabilities_list:
                    if not isinstance(capability_info, dict):
                        continue
                    capability_name = capability_info.get("name", "")
                    resources.append(
                        {
                            "name": f"{agent.name}.{capability_name}",
                            "description": capability_info.get("description", ""),
                            "parameters": capability_info.get("parameters", {}),
                            "type": "capability",
                        }
                    )

                # Add the complete agent resource
                resources.append(agent_resource)
                logger.info(f"MCP Resources: Added agent resource for {agent.name}")
            else:
                logger.info(
                    f"MCP Resources: Agent {agent.name} is not active (status: {agent_info.get('status')})"
                )
        else:
            logger.warning(f"MCP Resources: Could not find agent with ID {agent_id}")

    logger.info(f"MCP Resources: Returning {len(resources)} resources")
    return {"resources": resources}


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
    import time

    start_time = time.time()

    try:
        # Get the agent instance
        agent_uuid = UUID(agent_id)
        agent = await registry.get_agent(agent_uuid)

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
    logger.info("Starting automatic agent discovery and registration")

    # Discover all available agents
    logger.info("Calling discovery.discover_agents()...")
    agent_classes = await discovery.discover_agents()
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
            agent_id = await registry.register_agent(agent_class, default_config)
            registered_agents.add(agent_class)

            # Get the agent instance to access its name
            agent = await registry.get_agent(agent_id)
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
