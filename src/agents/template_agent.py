"""
Template Agent - Boilerplate for Creating New Agents

This template provides the basic structure for creating a new agent in the system.
Copy this file and customize it for your specific agent needs.

## How to Use This Template:
1. Copy this file to a new file: `your_agent_name_agent.py`
2. Replace all instances of "Template" with your agent name
3. Update the agent_id_str, category, and description
4. Implement your specific functionality in the process_request method
5. Add any additional imports, tools, or attributes as needed
6. Update the capabilities and status methods
7. Add your agent to the __init__.py file

## Required Customizations:
- Agent name and description
- Agent ID and category
- Process request logic
- Capabilities definition
- Any specialized tools or attributes
"""

import logging
from typing import Dict, List, Any, Optional
from ..interfaces.agent import AgentInterface
from uuid import UUID

logger = logging.getLogger(__name__)

class TemplateAgent(AgentInterface):
	"""Template agent for [DESCRIBE YOUR AGENT'S PURPOSE HERE]"""

	def __init__(self):
		# Standard attributes - customize these values
		self._agent_id_str = "template"  # CHANGE THIS: unique identifier for your agent
		self._uuid = None
		self.agent_id = "template"  # CHANGE THIS: should match _agent_id_str
		self._name = "Template Agent"  # CHANGE THIS: human-readable name
		self._description = "A template agent for creating new agents"  # CHANGE THIS: describe what your agent does
		self._initialized = False
		self.category = "template"  # CHANGE THIS: category like "analysis", "search", "financial_modeling", etc.
		self.status = "initialized"
		self._tools = {}  # Add any tools your agent needs

		# ADD ANY ADDITIONAL ATTRIBUTES HERE
		# Examples:
		# self.client = None  # for API clients
		# self.config = {}    # for configuration
		# self.cache = {}     # for caching

	@property
	def agent_id_str(self) -> str:
		return self._agent_id_str

	@property
	def uuid(self) -> UUID:
		if self._uuid is None:
			raise ValueError("UUID has not been set yet.")
		return self._uuid

	@uuid.setter
	def uuid(self, value: UUID):
		if self._uuid is not None:
			raise ValueError("UUID can only be set once.")
		self._uuid = value

	@property
	def name(self) -> str:
		"""Agent's unique identifier."""
		return self._name

	@property
	def description(self) -> str:
		"""Brief description of the agent's purpose."""
		return self._description

	async def initialize(self, config: Dict[str, Any]) -> None:
		"""Initialize the agent with configuration"""
		# ADD YOUR INITIALIZATION LOGIC HERE
		# Examples:
		# - Initialize API clients
		# - Load configuration
		# - Set up databases or connections
		# - Initialize tools

		self.status = "ready"
		self._initialized = True
		logger.info(f"{self._name} initialized successfully")

	async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""Process a request using the template agent"""
		if not self._initialized:
			return {"error": "Agent not initialized"}

		# CUSTOMIZE THIS: Handle different commands/tools for your agent
		command = request.get("command", "")
		tool_name = request.get("tool", "default_tool")

		if command == "your_command" or tool_name == "your_tool":
			return {"response": "Your response here"}
		else:
			return {
				"error": f"Unknown command: {command}",
				"available_commands": ["your_command", "another_command"]  # UPDATE THIS LIST
			}

	async def shutdown(self) -> None:
		"""Shutdown the agent"""
		# ADD YOUR CLEANUP LOGIC HERE
		# Examples:
		# - Close database connections
		# - Clean up temporary files
		# - Save state

		self.status = "shutdown"
		self._initialized = False
		logger.info(f"{self._name} shutdown complete")

	def get_capabilities(self) -> List[Dict[str, Any]]:
		"""Get the capabilities provided by this agent"""
		# CUSTOMIZE THIS: Define what your agent can do
		return [
			{
				"name": "your_tool_name",
				"description": "Description of what this tool does",
				"parameters": {
					"param1": "string - Description of parameter 1",
					"param2": "integer - Description of parameter 2 (optional)"
				}
			},

		]

	def get_status(self) -> Dict[str, Any]:
		"""Get the current status of the agent"""
		return {
			"status": self.status,
			"agent_id": self.agent_id,
			"name": self.name,
			"category": self.category,
			"capabilities": self.get_capabilities(),
			"initialized": self._initialized
		}
