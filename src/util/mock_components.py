"""
Mock components for the MCP HTTP API

Contains mock implementations for testing purposes.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class MockAgent:
    """Simple mock agent class for testing"""

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


class SimpleSessionManager:
    """Simple session manager for testing"""

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