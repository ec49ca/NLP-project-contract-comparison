from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import Dict, Any, Set, Type
from uuid import UUID
import logging
from contextlib import asynccontextmanager

from ..interfaces.agent import AgentInterface
from ..registry.registry import AgentRegistrySystem
from ..discovery.agent_discovery import AgentDiscovery
from ..orchestrator.orchestrator import Orchestrator
from ..services.ollama_service import OllamaService

# Configure logging to also output to console with immediate flushing
import sys
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	handlers=[
		logging.StreamHandler(sys.stdout),  # Output to stdout with immediate flush
	],
	force=True  # Force reconfiguration
)
# Ensure immediate flushing
for handler in logging.root.handlers:
	handler.flush = lambda: sys.stdout.flush()
logger = logging.getLogger(__name__)

# Initialize core components
registry = AgentRegistrySystem()
discovery = AgentDiscovery()

# Initialize Ollama service and orchestrator
ollama_service = OllamaService(
	base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
	default_model=os.getenv("OLLAMA_MODEL", "llama3:latest")
)
orchestrator = Orchestrator(registry, ollama_service)

# Keep track of registered agent classes to avoid duplicates
registered_agents: Set[Type[AgentInterface]] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
	# Startup
	await auto_register_agents()
	yield
	# Shutdown
	logger.info("Shutting down MCP server")


app = FastAPI(title="MCP Server", version="0.1.0", lifespan=lifespan)

# Enable CORS
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = (
	[origin.strip() for origin in allowed_origins_str.split(",")]
	if allowed_origins_str and allowed_origins_str != "*"
	else ["*"]
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=allowed_origins,
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


@app.get("/mcp/agents")
async def list_agents():
	"""List all registered agents in an MCP-compliant format."""
	registry_state = await registry.get_registry_state()
	return {
		"agents": [
			{
				"agent_id": str(agent_id),
				"name": info["name"],
				"description": info["description"],
				"status": info["status"],
				"tools": info["tools"],
			}
			for agent_id, info in registry_state.get("agents", {}).items()
		],
		"total_agents": registry_state.get("total_agents", 0),
		"active_agents": registry_state.get("active_agents", 0),
	}


@app.get("/mcp/resources")
async def list_mcp_resources():
	"""
	List all available MCP resources (agents and their tools).
	This endpoint is used by MCP clients to discover available resources.
	Follows the Model Context Protocol standard.
	"""
	registry_state = await registry.get_registry_state()
	resources = []
	
	for agent_id, agent_info in registry_state.get("agents", {}).items():
		if agent_info.get("status") == "active":
			# Add the agent as a resource with its full tools
			agent_resource = {
				"name": agent_info["name"],
				"description": agent_info["description"],
				"type": "agent",
				"agent_id": str(agent_id),
				"tools": agent_info.get("tools", [])
			}
			
			# Add each tool as an individual resource for direct access
			for tool in agent_info.get("tools", []):
				resources.append({
					"name": f"{agent_info['name']}.{tool['name']}",
					"description": tool.get("description", ""),
					"parameters": tool.get("parameters", {}),
					"type": "tool",
					"agent_id": str(agent_id)
				})
			
			# Add the complete agent resource
			resources.append(agent_resource)
	
	return {"resources": resources}


@app.post("/mcp/execute/{agent_id}")
async def execute_agent_by_id(agent_id: str, request: Dict[str, Any]):
	"""Execute a tool on a specific agent."""
	try:
		agent_uuid = UUID(agent_id)
		agent = await registry.get_agent(agent_uuid)
		
		if not agent:
			raise HTTPException(status_code=404, detail=f"Agent with ID {agent_id} not found")
		
		# Get the tool name from the request
		tool_name = request.get("tool")
		if not tool_name:
			raise HTTPException(status_code=400, detail="Tool name is required in request")
		
		# Execute the tool
		request_data = {"command": tool_name, **request.get("parameters", {})}
		result = await agent.process_request(request_data)
		
		return {
			"success": True,
			"data": result
		}
	except ValueError:
		raise HTTPException(status_code=400, detail=f"Invalid agent ID: {agent_id}")
	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"Error executing agent {agent_id}: {str(e)}")
		raise HTTPException(status_code=500, detail=str(e))


@app.post("/orchestrate")
async def orchestrate_query(request: Dict[str, Any]):
	"""
	Orchestrate a user query across multiple agents.
	
	Args:
		request: Dict with "query" key containing the user's query
		
	Returns:
		Dict with agents_used, results, comparison, and interpreted_response
	"""
	try:
		query = request.get("query")
		if not query:
			raise HTTPException(status_code=400, detail="Query is required")
		
		logger.info(f"\n🌐 SERVER: Received orchestrate request")
		logger.info(f"   Query: {query}\n")
		print(f"\n🌐 SERVER: Received orchestrate request")
		print(f"   Query: {query}\n")
		
		result = await orchestrator.process_query(query)
		
		logger.info(f"🌐 SERVER: Returning response to client\n")
		print(f"🌐 SERVER: Returning response to client\n")
		return result
		
	except HTTPException:
		raise
	except Exception as e:
		error_msg = f"🌐 SERVER ERROR: {str(e)}\n"
		logger.error(error_msg)
		print(error_msg)
		raise HTTPException(status_code=500, detail=str(e))


@app.post("/discover")
async def discover_agents():
	"""Trigger agent discovery and registration."""
	await auto_register_agents()
	registry_state = await registry.get_registry_state()
	return {
		"status": "success",
		"agents_registered": registry_state.get("total_agents", 0)
	}


async def auto_register_agents():
	"""
	Automatically discover and register all available agents.
	This function is called on server startup and when the /discover endpoint is hit.
	"""
	logger.info("Starting automatic agent discovery and registration")
	
	# Discover all available agents
	agent_classes = await discovery.discover_agents()
	logger.info(f"Discovered {len(agent_classes)} agent classes")
	
	# Register each discovered agent
	for module_name, agent_class in agent_classes.items():
		try:
			# Skip already registered agent classes
			if agent_class in registered_agents:
				logger.info(f"Agent {module_name} already registered, skipping")
				continue
			
			# Create config with Ollama settings
			default_config = {
				"ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
				"ollama_model": os.getenv("OLLAMA_MODEL", "llama3:latest")
			}
			
			# Register the agent
			agent_id = await registry.register_agent(agent_class, default_config)
			registered_agents.add(agent_class)
			
			logger.info(f"Auto-registered agent {module_name} with ID {agent_id}")
		except Exception as e:
			logger.error(f"Error auto-registering agent {module_name}: {str(e)}")
	
	logger.info(f"Auto-registration complete. {len(registered_agents)} agents registered.")


if __name__ == "__main__":
	import uvicorn
	
	port = int(os.getenv("PORT", 8000))
	uvicorn.run("src.server.mcp_server:app", host="0.0.0.0", port=port, reload=False)
