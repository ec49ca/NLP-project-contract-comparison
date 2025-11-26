from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import Dict, Any, Set, Type, List, Optional
from uuid import UUID
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from ..interfaces.agent import AgentInterface
from ..registry.registry import AgentRegistrySystem
from ..discovery.agent_discovery import AgentDiscovery
from ..orchestrator.orchestrator import Orchestrator
from ..services.llm_factory import create_llm_service
from ..services.document_storage import DocumentStorage

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

# Initialize LLM service (Ollama or OpenAI based on LLM_PROVIDER env var)
llm_service = create_llm_service()
# Initialize document storage
document_storage = DocumentStorage(upload_dir="backend/uploads")

orchestrator = Orchestrator(registry, llm_service, document_storage)

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


@app.get("/api/providers")
async def get_available_providers():
	"""
	Get list of configured LLM providers.
	
	Returns:
		Dict with available_providers list and current_provider
	"""
	available_providers = []
	current_provider = os.getenv("LLM_PROVIDER", "ollama").lower()
	
	# Check which providers are configured
	# Note: Ollama is assumed available if base URL is set (defaults to localhost)
	ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
	if ollama_base_url:
		available_providers.append("ollama")
	
	if os.getenv("OPENAI_API_KEY"):
		available_providers.append("openai")
	
	if os.getenv("ANTHROPIC_API_KEY"):
		available_providers.append("anthropic")
	
	if os.getenv("GOOGLE_API_KEY"):
		available_providers.append("google")
	
	return {
		"current_provider": current_provider,
		"available_providers": available_providers
	}


@app.get("/api/models")
async def get_available_models(provider: Optional[str] = None):
	"""
	Get available models for a specific provider.
	
	Args:
		provider: Provider name (defaults to LLM_PROVIDER env var)
	
	Returns:
		Dict with provider, default_model, and available_models list
	"""
	if not provider:
		provider = os.getenv("LLM_PROVIDER", "ollama").lower()
	
	if provider == "ollama":
		default_model = os.getenv("OLLAMA_MODEL", "llama3:latest")
		models_str = os.getenv("OLLAMA_MODELS", default_model)
		models = [m.strip() for m in models_str.split(",") if m.strip()]
		return {
			"provider": "ollama",
			"default_model": default_model,
			"available_models": models
		}
	elif provider == "openai":
		default_model = os.getenv("OPENAI_MODEL", "gpt-4")
		models_str = os.getenv("OPENAI_MODELS", default_model)
		models = [m.strip() for m in models_str.split(",") if m.strip()]
		return {
			"provider": "openai",
			"default_model": default_model,
			"available_models": models
		}
	elif provider == "anthropic":
		default_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
		models_str = os.getenv("ANTHROPIC_MODELS", default_model)
		models = [m.strip() for m in models_str.split(",") if m.strip()]
		return {
			"provider": "anthropic",
			"default_model": default_model,
			"available_models": models
		}
	elif provider == "google":
		default_model = os.getenv("GOOGLE_MODEL", "gemini-pro")
		models_str = os.getenv("GOOGLE_MODELS", default_model)
		models = [m.strip() for m in models_str.split(",") if m.strip()]
		return {
			"provider": "google",
			"default_model": default_model,
			"available_models": models
		}
	else:
		return {
			"provider": provider,
			"default_model": None,
			"available_models": []
		}


@app.post("/orchestrate")
async def orchestrate_query(request: Dict[str, Any]):
	"""
	Orchestrate a user query across multiple agents.
	
	Args:
		request: Dict with "query" key containing the user's query, optional "selected_documents" list, and optional "model" override
		
	Returns:
		Dict with agents_used, results, comparison, and interpreted_response
	"""
	try:
		query = request.get("query")
		if not query:
			raise HTTPException(status_code=400, detail="Query is required")
		
		selected_documents = request.get("selected_documents", [])
		provider_override = request.get("provider")  # Optional provider override
		model_override = request.get("model")  # Optional model override
		
		# If provider is overridden, create a new LLM service for this request
		# Pass it through the call chain instead of mutating global state (avoids race conditions)
		llm_service_override = None
		if provider_override:
			from ..services.llm_factory import create_llm_service
			try:
				llm_service_override = create_llm_service(provider=provider_override)
				logger.info(f"   🔄 Using provider override: {provider_override}")
				print(f"   🔄 Using provider override: {provider_override}")
			except ValueError as e:
				logger.warning(f"   ⚠️  Provider override failed: {e}, using default provider")
				print(f"   ⚠️  Provider override failed: {e}, using default provider")
		
		logger.info(f"\n🌐 SERVER: Received orchestrate request")
		logger.info(f"   Query: {query}")
		if selected_documents:
			logger.info(f"   Selected documents: {selected_documents}")
		if provider_override:
			logger.info(f"   Provider override: {provider_override}")
		if model_override:
			logger.info(f"   Model override: {model_override}")
		print(f"\n🌐 SERVER: Received orchestrate request")
		print(f"   Query: {query}")
		if selected_documents:
			print(f"   Selected documents: {selected_documents}")
		if provider_override:
			print(f"   Provider override: {provider_override}")
		if model_override:
			print(f"   Model override: {model_override}\n")
		
		result = await orchestrator.process_query(
			query, 
			selected_documents=selected_documents, 
			model_override=model_override,
			llm_service_override=llm_service_override
		)
		
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


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
	"""
	Upload a PDF document.
	
	Args:
		file: PDF file to upload
		
	Returns:
		Dict with document info
	"""
	try:
		# Validate file type
		if not file.filename.endswith('.pdf'):
			raise HTTPException(status_code=400, detail="Only PDF files are supported")
		
		# Read file content
		file_content = await file.read()
		
		# Save document
		doc_info = document_storage.save_document(file.filename, file_content)
		
		logger.info(f"📄 Document uploaded: {doc_info['filename']}")
		print(f"📄 Document uploaded: {doc_info['filename']}")
		
		return {
			"success": True,
			"document": doc_info
		}
	except HTTPException:
		raise
	except Exception as e:
		error_msg = f"Error uploading document: {str(e)}"
		logger.error(error_msg)
		raise HTTPException(status_code=500, detail=error_msg)


@app.get("/api/documents")
async def list_documents():
	"""
	List all uploaded documents.
	
	Returns:
		List of document info dicts
	"""
	try:
		documents = document_storage.get_documents()
		return {
			"success": True,
			"documents": documents
		}
	except Exception as e:
		error_msg = f"Error listing documents: {str(e)}"
		logger.error(error_msg)
		raise HTTPException(status_code=500, detail=error_msg)


@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
	"""
	Delete a document.
	
	Args:
		filename: Document filename to delete
		
	Returns:
		Success status
	"""
	try:
		success = document_storage.delete_document(filename)
		if not success:
			raise HTTPException(status_code=404, detail="Document not found")
		
		logger.info(f"📄 Document deleted: {filename}")
		print(f"📄 Document deleted: {filename}")
		
		return {
			"success": True,
			"message": f"Document {filename} deleted"
		}
	except HTTPException:
		raise
	except Exception as e:
		error_msg = f"Error deleting document: {str(e)}"
		logger.error(error_msg)
		raise HTTPException(status_code=500, detail=error_msg)


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
			# Pass the LLM service instance to agents instead of config
			default_config = {
				"llm_service": llm_service
			}
			
			# Add document storage to config if this is the internal agent
			# Check by creating a temporary instance to get agent_id_str
			try:
				temp_agent = agent_class()
				if hasattr(temp_agent, 'agent_id_str') and temp_agent.agent_id_str == "internal_agent":
					default_config["document_storage"] = document_storage
			except:
				# If we can't check, skip
				pass
			
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
	uvicorn.run("backend.server.mcp_server:app", host="0.0.0.0", port=port, reload=False)
