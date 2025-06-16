"""
Base Agent Class

This is the abstract base class that all MCP agents inherit from.
It provides common functionality and interface for all agents.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class Tool:
    """Simple tool representation"""
    def __init__(self, name: str, description: str, inputSchema: Dict[str, Any]):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema

class BaseAgent(ABC):
    """
    Abstract base class for all MCP agents.
    
    All agents must implement the get_tools() and execute_tool() methods.
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.name = "Base Agent"
        self.description = "Base agent class"
        self.category = "general"
        self.db_connector = None
        self.api_client = None
        self.is_initialized = False
    
    async def initialize(self, db_connector, api_client):
        """Initialize the agent with database and API connections."""
        self.db_connector = db_connector
        self.api_client = api_client
        self.is_initialized = True
        logger.info(f"Agent {self.agent_id} initialized successfully")
    
    @abstractmethod
    async def get_tools(self) -> List[Tool]:
        """
        Get the tools provided by this agent.
        
        Returns:
            List[Tool]: List of MCP tools this agent provides
        """
        pass
    
    @abstractmethod
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a specific tool with the given arguments.
        
        Args:
            tool_name (str): Name of the tool to execute
            arguments (Dict[str, Any]): Arguments for the tool
            
        Returns:
            Any: Result of the tool execution
        """
        pass
    
    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """
        Execute the agent with input data and context.
        
        Args:
            input_data (Dict[str, Any]): Input data for the agent
            context (Dict[str, Any]): Execution context
            
        Returns:
            Any: Result of the agent execution
        """
        # Default implementation - can be overridden by specific agents
        return {"message": f"Agent {self.agent_id} executed", "input": input_data}
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get basic information about this agent."""
        return {
            "id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "is_initialized": self.is_initialized
        } 