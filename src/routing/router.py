from typing import Dict, Any, Optional
from uuid import UUID
from ..interfaces.agent import AgentInterface
from ..registry.registry import AgentRegistrySystem
# from mcp.server.fastmcp import FastMCP

class AgentRouter:
    """Handles routing of requests to appropriate agents."""

    def __init__(self, registry: AgentRegistrySystem):
        self._registry = registry
        self._routes: Dict[str, UUID] = {}  # primitive_name -> agent_id

    async def register_route(self, primitive_name: str, agent_id: UUID) -> None:
        """Register a route for an MCP primitive to an agent."""
        self._routes[primitive_name] = agent_id

    async def unregister_route(self, primitive_name: str) -> None:
        """Remove a route for an MCP primitive."""
        self._routes.pop(primitive_name, None)

    async def route_request(self, primitive_name: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """Route a request to the appropriate agent."""
        agent_id = self._routes.get(primitive_name)
        if not agent_id:
            raise ValueError(f"No agent registered for primitive: {primitive_name}")

        agent = await self._registry.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        return await agent.process_request(request)

    async def get_routes(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered routes."""
        routes = {}
        for primitive_name, agent_id in self._routes.items():
            agent = await self._registry.get_agent(agent_id)
            if agent:
                routes[primitive_name] = {
                    "agent_id": str(agent_id),
                    "agent_name": agent.name,
                    "agent_status": (await self._registry.get_registry_state())
                    ["agents"][str(agent_id)]["status"]
                }
        return routes

    async def get_agent_routes(self, agent_id: UUID) -> Dict[str, Any]:
        """Get all primitives routed to a specific agent."""
        agent_routes = {}
        for primitive_name, route_agent_id in self._routes.items():
            if route_agent_id == agent_id:
                agent_routes[primitive_name] = {
                    "agent_id": str(agent_id),
                    "primitive": primitive_name
                }
        return agent_routes
