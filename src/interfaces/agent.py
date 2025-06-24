from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

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
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent's capabilities."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return agent's current status."""
        pass
