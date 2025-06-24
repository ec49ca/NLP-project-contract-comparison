from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional, Set, Type
from uuid import UUID
import logging
from contextlib import asynccontextmanager
from ..registry.registry import AgentRegistrySystem
from ..routing.router import AgentRouter
from ..discovery.agent_discovery import AgentDiscovery
from ..interfaces.agent import AgentInterface
from ..registry.registry_models import AgentStatus
# from mcp.server.fastmcp import FastMCP

# Initialize core components
registry = AgentRegistrySystem()
router = AgentRouter(registry)
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

app = FastAPI(title="AgentForge", version="0.1.0", lifespan=lifespan)

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
        "version": "0.1.0"
    }

@app.post("/agents")
async def register_agent(agent_class_name: str, config: Dict[str, Any]):
    """Register a new agent instance."""
    try:
        # Import the agent module and get the agent class
        agent_module = __import__(f"src.agents.{agent_class_name}", fromlist=[agent_class_name])
        agent_class = getattr(agent_module, agent_class_name)

        # Register the agent
        agent_id = await registry.register_agent(agent_class, config)
        return {"agent_id": str(agent_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get information about a specific agent."""
    try:
        agent_uuid = UUID(agent_id)
        agent = await registry.get_agent(agent_uuid)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        return {
            "agent_id": str(agent_uuid),
            "name": agent.name,
            "description": agent.description,
            "status": (await registry.get_registry_state())["agents"][str(agent_uuid)]["status"]
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID")

@app.get("/agents")
async def list_agents():
    """List all registered agents in an MCP-compliant format."""
    registry_state = await registry.get_registry_state()

    # Transform the response to be more MCP-compliant
    agents = []
    for agent_id, agent_info in registry_state.get("agents", {}).items():
        agent = await registry.get_agent(UUID(agent_id))
        if agent:
            agents.append({
                "name": agent.name,
                "description": agent.description,
                "status": agent_info.get("status"),
                "capabilities": list(agent.get_capabilities().keys())
            })

    return {
        "total_agents": registry_state.get("total_agents", 0),
        "active_agents": registry_state.get("active_agents", 0),
        "agents": agents
    }

@app.post("/routes/{primitive_name}")
async def register_route(primitive_name: str, agent_id: str):
    """Register a route for an MCP primitive to an agent."""
    try:
        agent_uuid = UUID(agent_id)
        await router.register_route(primitive_name, agent_uuid)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/routes/{primitive_name}")
async def unregister_route(primitive_name: str):
    """Unregister a route for an MCP primitive."""
    try:
        await router.unregister_route(primitive_name)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/routes")
async def list_routes():
    """List all registered routes."""
    return await router.get_routes()

@app.post("/primitives/{primitive_name}")
async def process_primitive(primitive_name: str, request: Dict[str, Any]):
    """Process an MCP primitive request."""
    try:
        return await router.route_request(primitive_name, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/discover")
async def discover_agents(background_tasks: BackgroundTasks):
    """
    Discover and auto-register all available agents.
    This endpoint can be called to refresh agent registrations.
    """
    background_tasks.add_task(auto_register_agents)
    return {"status": "Agent discovery started"}

@app.get("/mcp/resources")
async def list_mcp_resources():
    """
    List all available MCP resources (agents and their capabilities).
    This endpoint is used by MCP clients to discover available resources.
    Follows the Model Context Protocol standard.
    """
    agents_state = await registry.get_registry_state()
    resources = []

    for agent_id, agent_info in agents_state.get("agents", {}).items():
        agent = await registry.get_agent(UUID(agent_id))
        if agent and agent_info.get("status") == AgentStatus.ACTIVE.value:
            # Add the agent as a resource with its full capabilities
            agent_resource = {
                "name": agent.name,
                "description": agent.description,
                "type": "agent",
                "capabilities": {}
            }

            # Get capabilities - handle both direct capabilities and tools wrapper
            capabilities = agent.get_capabilities()

            # Check if capabilities are wrapped in a "tools" key
            if "tools" in capabilities:
                tools = capabilities["tools"]
            else:
                # Direct capabilities format
                tools = capabilities

            # Add each capability as a property of the agent resource
            for capability_name, capability_info in tools.items():
                # Also add each capability as an individual resource for direct access
                resources.append({
                    "name": f"{agent.name}.{capability_name}",
                    "description": capability_info.get("description", ""),
                    "parameters": capability_info.get("parameters", {}),
                    "type": "capability"
                })

                # Add to the agent's capabilities
                agent_resource["capabilities"][capability_name] = {
                    "description": capability_info.get("description", ""),
                    "parameters": capability_info.get("parameters", {})
                }

            # Add the complete agent resource
            resources.append(agent_resource)

    return {"resources": resources}

async def auto_register_agents():
    """
    Automatically discover and register all available agents.
    This function is called on server startup and when the /discover endpoint is hit.
    """
    logger.info("Starting automatic agent discovery and registration")

    # Discover all available agents
    logger.info("Calling discovery.discover_agents()...")
    agent_classes = await discovery.discover_agents()
    logger.info(f"Discovery returned {len(agent_classes)} agent classes: {list(agent_classes.keys())}")


    # Register each discovered agent
    for module_name, agent_class in agent_classes.items():
        try:
            # Skip already registered agent classes
            if agent_class in registered_agents:
                logger.info(f"Agent {module_name} already registered, skipping")
                continue

            # Create default config - can be customized per agent type if needed
            default_config = {}

            # Register the agent
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

    logger.info(f"Auto-registration complete. {len(registered_agents)} agents registered.")
    logger.info(f"Agent name to ID mapping: {agent_name_to_id}")

@app.post("/execute/{agent_name}/{capability}")
async def execute_agent_capability(agent_name: str, capability: str, parameters: Dict[str, Any]):
    """
    Execute a specific capability of an agent.
    This endpoint allows direct execution of agent capabilities by name.

    Args:
        agent_name: The name of the agent to execute (e.g., 'stock_price')
        capability: The capability to execute (e.g., 'get_current_price')
        parameters: The parameters to pass to the capability

    Returns:
        The result of executing the capability
    """
    try:
        # Find the agent ID by name
        agent_id = None
        registry_state = await registry.get_registry_state()

        # First try the direct mapping
        if agent_name in agent_name_to_id:
            agent_id = agent_name_to_id[agent_name]
        else:
            # Fall back to searching through all agents
            for aid, agent_info in registry_state.get("agents", {}).items():
                agent = await registry.get_agent(UUID(aid))
                if agent and agent.name == agent_name:
                    agent_id = UUID(aid)
                    # Update the mapping for future use
                    agent_name_to_id[agent_name] = agent_id
                    break

        if not agent_id:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

        # Get the agent instance
        agent = await registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent with ID {agent_id} not found")

        # Check if the agent has the requested capability
        capabilities = agent.get_capabilities()

        # Handle both direct capabilities and tools wrapper
        if "tools" in capabilities:
            available_capabilities = list(capabilities["tools"].keys())
        else:
            available_capabilities = list(capabilities.keys())

        if capability not in available_capabilities:
            raise HTTPException(
                status_code=400,
                detail=f"Agent '{agent_name}' does not have capability '{capability}'. " \
                      f"Available capabilities: {available_capabilities}"
            )

        # Execute the capability
        request = {"command": capability, **parameters}
        result = await agent.process_request(request)

        return {
            "success": True,
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing {agent_name}.{capability}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "src.server.mcp_server:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
