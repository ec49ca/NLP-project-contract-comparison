"""
Agents package for MCP Server.

To add a new agent:
1. Create your agent class implementing AgentInterface
2. Add it to __all__ below
3. Import it here

Example:
    from .my_agent import MyAgent
    __all__ = ["MyAgent"]
"""

from .internal_agent import InternalAgent
from .external_agent import ExternalAgent

# Export all agent classes here
# Agents are automatically discovered and registered on server startup
__all__ = ["InternalAgent", "ExternalAgent"]
