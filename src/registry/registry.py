from typing import Dict, Type, Any, Optional
from uuid import UUID
from datetime import datetime
from .registry_models import AgentRegistry, AgentStatus
from ..interfaces.agent import AgentInterface

class AgentRegistrySystem:
    """Manages the lifecycle and state of all registered agents."""

    def __init__(self):
        self._registry = AgentRegistry()
        self._agents: Dict[UUID, AgentInterface] = {}

    async def register_agent(self, agent_class: Type[AgentInterface], config: Dict[str, Any]) -> UUID:
        """Register a new agent instance."""
        agent = agent_class()
        await agent.initialize(config)

		# TODO:
		# create more robust way of generating agent ids
		# so that they don't change over time based on
		# how agents are initialized on different runs
        agent_id = UUID(int=len(self._agents) + 1)
        self._agents[agent_id] = agent

        self._registry.add_agent(
            agent_id=agent_id,
            name=agent.name,
            description=agent.description,
            status=AgentStatus.ACTIVE
        )

        return agent_id

    async def get_agent(self, agent_id: UUID) -> Optional[AgentInterface]:
        """Retrieve an agent by its ID."""
        return self._agents.get(agent_id)

    async def get_all_agents(self) -> Dict[UUID, AgentInterface]:
        """Get all registered agents."""
        return self._agents

    async def update_agent_status(self, agent_id: UUID, status: AgentStatus) -> None:
        """Update an agent's status."""
        if agent_id in self._agents:
            self._registry.update_agent_status(agent_id, status)

    async def shutdown_agent(self, agent_id: UUID) -> None:
        """Shutdown and remove an agent."""
        if agent_id in self._agents:
            agent = self._agents[agent_id]
            await agent.shutdown()
            del self._agents[agent_id]
            self._registry.remove_agent(agent_id)

    async def get_registry_state(self) -> Dict[str, Any]:
        """Get the current state of the registry."""
        return {
            "total_agents": len(self._agents),
            "active_agents": len([a for a in self._agents.values()
                               if self._registry.get_agent_status(a.name) == AgentStatus.ACTIVE]),
            "agents": {
                str(agent_id): {
                    "name": agent.name,
                    "status": self._registry.get_agent_status(agent.name).value,
                    "last_seen": self._registry.get_agent_last_seen(agent.name)
                }
                for agent_id, agent in self._agents.items()
            }
        }
