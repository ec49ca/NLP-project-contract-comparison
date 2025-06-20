"""
Request models for the MCP HTTP API

Contains all Pydantic models for request validation.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel


class AgentDiscoveryRequest(BaseModel):
    """Request model for agent discovery"""
    filter: Optional[Dict[str, Any]] = None


class ToolDiscoveryRequest(BaseModel):
    """Request model for tool discovery"""
    agent_id: Optional[str] = None
    filter: Optional[Dict[str, Any]] = None


class AgentInvocationRequest(BaseModel):
    """Request model for agent invocation"""
    agent_id: str
    input_data: Dict[str, Any]
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ToolInvocationRequest(BaseModel):
    """Request model for tool invocation"""
    agent_id: str
    tool_name: str
    arguments: Dict[str, Any]
    session_id: Optional[str] = None


class SessionCreateRequest(BaseModel):
    """Request model for session creation"""
    user_id: str
    context: Optional[Dict[str, Any]] = None


class SessionUpdateRequest(BaseModel):
    """Request model for session updates"""
    session_id: str
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None