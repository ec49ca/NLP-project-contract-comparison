from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from uuid import UUID


class AgentInterface(ABC):
    """Standardized interface for all MCP agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent's unique identifier."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Brief description of the agent's purpose."""
        pass

    @property
    @abstractmethod
    def agent_id_str(self) -> str:
        """Stable string identifier for the agent type (e.g., 'knowledge_graph')."""
        pass

    @property
    @abstractmethod
    def uuid(self) -> UUID:
        """The unique, immutable UUID for this agent instance."""
        pass

    @uuid.setter
    @abstractmethod
    def uuid(self, value: UUID):
        """Set the UUID for this agent instance (should only be set once)."""
        pass

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the agent with configuration."""
        pass

    @abstractmethod
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests through the agent."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Clean up resources when shutting down."""
        pass

    @abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Return agent's capabilities as a list of objects, each with 'name', 'description', and 'parameters' fields.
        Example:
        [
          {
            "name": "capability_name",
            "description": "Description of the capability",
            "parameters": { ... }
          },
          ...
        ]
        """
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return agent's current status."""
        pass
