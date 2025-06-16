#!/usr/bin/env python3
"""
HTTP API Server for Samvid MCP Server

Provides REST endpoints for the main Samvid application to communicate
with MCP agents running in this standalone server.
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
import sys
sys.path.append('..')
from version import __version__

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances - simplified for testing
session_manager: Optional[Any] = None
agents: Dict[str, Any] = {}

# Request/Response models
class AgentDiscoveryRequest(BaseModel):
    filter: Optional[Dict[str, Any]] = None

class ToolDiscoveryRequest(BaseModel):
    agent_id: Optional[str] = None
    filter: Optional[Dict[str, Any]] = None

class AgentInvocationRequest(BaseModel):
    agent_id: str
    input_data: Dict[str, Any]
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ToolInvocationRequest(BaseModel):
    agent_id: str
    tool_name: str
    arguments: Dict[str, Any]
    session_id: Optional[str] = None

class SessionCreateRequest(BaseModel):
    user_id: str
    context: Optional[Dict[str, Any]] = None

class SessionUpdateRequest(BaseModel):
    session_id: str
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

# Simple mock agent class for testing
class MockAgent:
    def __init__(self, name: str, category: str = "general"):
        self.name = name
        self.category = category
        self.is_initialized = True
    
    def get_agent_info(self):
        return {
            "name": self.name,
            "description": f"Mock {self.name} agent for testing",
            "category": self.category
        }
    
    async def get_tools(self):
        return [
            {
                "name": f"{self.name}_tool",
                "description": f"Mock tool for {self.name}",
                "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}}
            }
        ]
    
    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]):
        return {
            "agent": self.name,
            "input": input_data,
            "context": context,
            "result": f"Mock result from {self.name}",
            "timestamp": asyncio.get_event_loop().time()
        }
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]):
        return {
            "tool": tool_name,
            "arguments": arguments,
            "result": f"Mock tool result from {tool_name}",
            "timestamp": asyncio.get_event_loop().time()
        }

# Simple session manager for testing
class SimpleSessionManager:
    def __init__(self):
        self.sessions = {}
    
    async def create_session(self, user_id: str, context: Optional[Dict[str, Any]] = None):
        session_id = f"session_{len(self.sessions) + 1}"
        session = {
            "id": session_id,
            "user_id": user_id,
            "context": context or {},
            "created_at": asyncio.get_event_loop().time(),
            "updated_at": asyncio.get_event_loop().time()
        }
        self.sessions[session_id] = session
        return session
    
    async def get_session(self, session_id: str):
        return self.sessions.get(session_id)
    
    async def update_session(self, session_id: str, context: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None):
        if session_id in self.sessions:
            if context:
                self.sessions[session_id]["context"].update(context)
            if metadata:
                self.sessions[session_id]["metadata"] = metadata
            self.sessions[session_id]["updated_at"] = asyncio.get_event_loop().time()
            return self.sessions[session_id]
        return None
    
    async def terminate_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    async def cleanup(self):
        self.sessions.clear()

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

async def initialize_server():
    """Initialize the MCP server components"""
    global session_manager, agents
    
    try:
        # Initialize session manager
        session_manager = SimpleSessionManager()
        
        # Initialize mock agents for testing
        agents = {
            "meta": MockAgent("MetaAgent", "orchestration"),
            "vector_search": MockAgent("VectorSearchAgent", "search"),
            "knowledge_graph": MockAgent("KnowledgeGraphAgent", "knowledge"),
            "stats": MockAgent("StatsAgent", "analytics")
        }
        
        logger.info("MCP HTTP API server initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize server: {e}")
        raise

async def cleanup_server():
    """Cleanup server resources"""
    global session_manager
    
    try:
        if session_manager:
            await session_manager.cleanup()
            
        logger.info("MCP HTTP API server cleaned up successfully")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

# Dependency to ensure server is initialized
async def get_initialized_server():
    if not session_manager:
        raise HTTPException(status_code=503, detail="Server not initialized")
    return True

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "server_initialized": session_manager is not None,
        "agents_count": len(agents),
        "version": __version__
    }

# Agent discovery endpoint
@app.post("/agents/discover")
async def discover_agents(
    request: AgentDiscoveryRequest,
    _: bool = Depends(get_initialized_server)
):
    """Discover available agents"""
    try:
        discovered_agents = []
        
        for agent_id, agent in agents.items():
            if not agent.is_initialized:
                continue
                
            # Apply filter if provided
            if request.filter:
                # Simple filtering logic - can be enhanced
                if 'category' in request.filter:
                    if hasattr(agent, 'category') and agent.category != request.filter['category']:
                        continue
            
            agent_info = agent.get_agent_info()
            tools = await agent.get_tools()
            
            discovered_agents.append({
                "id": agent_id,
                "name": agent_info.get("name", agent_id),
                "description": agent_info.get("description", ""),
                "category": getattr(agent, 'category', 'general'),
                "tools": [
                    {
                        "name": tool["name"],
                        "description": tool["description"],
                        "input_schema": tool["inputSchema"]
                    }
                    for tool in tools
                ],
                "status": "active" if agent.is_initialized else "inactive"
            })
        
        return {"success": True, "data": discovered_agents}
        
    except Exception as e:
        logger.error(f"Error discovering agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Tool discovery endpoint
@app.post("/tools/discover")
async def discover_tools(
    request: ToolDiscoveryRequest,
    _: bool = Depends(get_initialized_server)
):
    """Discover available tools"""
    try:
        discovered_tools = []
        
        # If agent_id is specified, only get tools from that agent
        target_agents = {request.agent_id: agents[request.agent_id]} if request.agent_id and request.agent_id in agents else agents
        
        for agent_id, agent in target_agents.items():
            if not agent.is_initialized:
                continue
                
            tools = await agent.get_tools()
            
            for tool in tools:
                # Apply filter if provided
                if request.filter:
                    # Simple filtering logic - can be enhanced
                    if 'name' in request.filter:
                        if request.filter['name'].lower() not in tool["name"].lower():
                            continue
                
                discovered_tools.append({
                    "agent_id": agent_id,
                    "name": tool["name"],
                    "description": tool["description"],
                    "input_schema": tool["inputSchema"],
                    "category": getattr(agent, 'category', 'general')
                })
        
        return {"success": True, "data": discovered_tools}
        
    except Exception as e:
        logger.error(f"Error discovering tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Agent invocation endpoint
@app.post("/agents/invoke")
async def invoke_agent(
    request: AgentInvocationRequest,
    _: bool = Depends(get_initialized_server)
):
    """Invoke an agent"""
    try:
        if request.agent_id not in agents:
            raise HTTPException(status_code=404, detail=f"Agent {request.agent_id} not found")
        
        agent = agents[request.agent_id]
        if not agent.is_initialized:
            raise HTTPException(status_code=503, detail=f"Agent {request.agent_id} not initialized")
        
        # Execute the agent
        result = await agent.execute(request.input_data, request.context or {})
        
        return {
            "success": True,
            "data": {
                "agent_id": request.agent_id,
                "result": result,
                "session_id": request.session_id
            }
        }
        
    except Exception as e:
        logger.error(f"Error invoking agent {request.agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Tool invocation endpoint
@app.post("/tools/invoke")
async def invoke_tool(
    request: ToolInvocationRequest,
    _: bool = Depends(get_initialized_server)
):
    """Invoke a specific tool"""
    try:
        if request.agent_id not in agents:
            raise HTTPException(status_code=404, detail=f"Agent {request.agent_id} not found")
        
        agent = agents[request.agent_id]
        if not agent.is_initialized:
            raise HTTPException(status_code=503, detail=f"Agent {request.agent_id} not initialized")
        
        # Execute the tool
        result = await agent.execute_tool(request.tool_name, request.arguments)
        
        return {
            "success": True,
            "data": {
                "agent_id": request.agent_id,
                "tool_name": request.tool_name,
                "result": result,
                "session_id": request.session_id
            }
        }
        
    except Exception as e:
        logger.error(f"Error invoking tool {request.tool_name} on agent {request.agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Session management endpoints
@app.post("/sessions/create")
async def create_session(
    request: SessionCreateRequest,
    _: bool = Depends(get_initialized_server)
):
    """Create a new session"""
    try:
        session = await session_manager.create_session(request.user_id, request.context)
        return {"success": True, "data": session}
        
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    _: bool = Depends(get_initialized_server)
):
    """Get session details"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"success": True, "data": session}
        
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/sessions/{session_id}")
async def update_session(
    session_id: str,
    request: SessionUpdateRequest,
    _: bool = Depends(get_initialized_server)
):
    """Update session"""
    try:
        session = await session_manager.update_session(
            session_id, 
            request.context, 
            request.metadata
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"success": True, "data": session}
        
    except Exception as e:
        logger.error(f"Error updating session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sessions/{session_id}")
async def terminate_session(
    session_id: str,
    _: bool = Depends(get_initialized_server)
):
    """Terminate session"""
    try:
        success = await session_manager.terminate_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"success": True, "message": "Session terminated"}
        
    except Exception as e:
        logger.error(f"Error terminating session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "src.http_server:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("NODE_ENV") != "production"
    ) 