#!/usr/bin/env python3
"""
HTTP API Server for Samvid MCP Server

Provides REST endpoints for the main Samvid application to communicate
with MCP agents running in this standalone server.

## API Endpoints Documentation

### Health Check
- **GET** `/health`
  - Returns server health status and initialization state
  - Response: `{"status": "healthy", "server_initialized": bool, "agents_count": int, "version": str}`

### Agent Management

#### Discover Agents
- **POST** `/agents/discover`
  - Discovers all available agents or filters by category
  - Request Body: `{"filter": {"category": "string"}}` (optional)
  - Response: `{"success": true, "data": [{"id": str, "name": str, "description": str, "category": str, "tools": [...], "status": str}]}`

#### Invoke Agent
- **POST** `/agents/invoke`
  - Executes an agent with input data and optional context
  - Request Body: `{"agent_id": str, "input_data": dict, "session_id": str, "context": dict}`
  - Response: `{"success": true, "data": {"agent_id": str, "result": dict, "session_id": str}}`

### Tool Management

#### Discover Tools
- **POST** `/tools/discover`
  - Discovers available tools, optionally filtered by agent or tool name
  - Request Body: `{"agent_id": str, "filter": {"name": "string"}}` (both optional)
  - Response: `{"success": true, "data": [{"agent_id": str, "name": str, "description": str, "input_schema": dict, "category": str}]}`

#### Invoke Tool
- **POST** `/tools/invoke`
  - Executes a specific tool on an agent
  - Request Body: `{"agent_id": str, "tool_name": str, "arguments": dict, "session_id": str}`
  - Response: `{"success": true, "data": {"agent_id": str, "tool_name": str, "result": dict, "session_id": str}}`

### Session Management

#### Create Session
- **POST** `/sessions/create`
  - Creates a new user session with optional context
  - Request Body: `{"user_id": str, "context": dict}`
  - Response: `{"success": true, "data": {"id": str, "user_id": str, "context": dict, "created_at": float, "updated_at": float}}`

#### Get Session
- **GET** `/sessions/{session_id}`
  - Retrieves session details by ID
  - Response: `{"success": true, "data": {"id": str, "user_id": str, "context": dict, "created_at": float, "updated_at": float}}`

#### Update Session
- **PUT** `/sessions/{session_id}`
  - Updates session context and metadata
  - Request Body: `{"session_id": str, "context": dict, "metadata": dict}`
  - Response: `{"success": true, "data": {"id": str, "user_id": str, "context": dict, "created_at": float, "updated_at": float}}`

#### Terminate Session
- **DELETE** `/sessions/{session_id}`
  - Terminates and removes a session
  - Response: `{"success": true, "message": "Session terminated"}`

## Available Mock Agents

The server includes the following mock agents for testing:
- **meta**: MetaAgent (orchestration category)
- **vector_search**: VectorSearchAgent (search category)
- **knowledge_graph**: KnowledgeGraphAgent (knowledge category)
- **stats**: StatsAgent (analytics category)

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200`: Success
- `404`: Resource not found
- `500`: Internal server error
- `503`: Service unavailable (server not initialized)

Error responses follow the format: `{"detail": "error message"}`
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

from src.agents.kg_agent import KnowledgeGraphAgent

# Import version - handle both module and direct execution
try:
    from version import __version__
except ImportError:
    try:
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from version import __version__
    except ImportError:
        __version__ = "0.1.0"

# Import our modular components
from .util.dependencies import get_initialized_server, set_session_manager, set_agents, get_session_manager, get_agents
from .util.mock_components import MockAgent, SimpleSessionManager
from .routes import agents, tools, sessions

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await initialize_server()
    yield
    # Shutdown
    await cleanup_server()


# Create FastAPI app
app = FastAPI(
    title="Samvid MCP HTTP API",
    version=__version__,
    description="HTTP API for Samvid MCP Server",
    lifespan=lifespan
)

# Add CORS middleware
allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agents.router)
app.include_router(tools.router)
app.include_router(sessions.router)


async def initialize_server():
    """Initialize the MCP server components"""
    try:
        # Initialize session manager
        session_manager = SimpleSessionManager()
        set_session_manager(session_manager)

        # Initialize mock agents for testing
		# TODO: create more robust way of agent testing
        agents_dict = {
			# comment out everything but kg agent for dev -Sohum
            # "meta": MockAgent("MetaAgent", "orchestration"),
            # "vector_search": MockAgent("VectorSearchAgent", "search"),
            # "knowledge_graph": MockAgent("KnowledgeGraphAgent", "knowledge"),
			"knowledge_graph": KnowledgeGraphAgent(),
            # "stats": MockAgent("StatsAgent", "analytics")
        }
        set_agents(agents_dict)

        logger.info("MCP HTTP API server initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize server: {e}")
        raise


async def cleanup_server():
    """Cleanup server resources"""
    try:
        session_manager = get_session_manager()
        if session_manager:
            await session_manager.cleanup()

        logger.info("MCP HTTP API server cleaned up successfully")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    session_manager = get_session_manager()
    agents = get_agents()

    return {
        "status": "healthy",
        "server_initialized": session_manager is not None,
        "agents_count": len(agents),
        "version": __version__
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "src.server:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("NODE_ENV") != "production"
    )