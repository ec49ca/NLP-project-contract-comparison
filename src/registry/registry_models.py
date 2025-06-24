from typing import Dict, Set, Optional
from datetime import datetime
from enum import Enum
from uuid import UUID

class AgentStatus(Enum):
    """Possible states of an agent."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"

class AgentInfo:
    """Information about a registered agent."""

    def __init__(self,
                 agent_id: UUID,
                 name: str,
                 description: str,
                 status: AgentStatus = AgentStatus.INACTIVE):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.status = status
        self.last_seen = datetime.utcnow()

class AgentRegistry:
    """Maintains the state of all registered agents."""

    def __init__(self):
        self._agents: Dict[UUID, AgentInfo] = {}
        self._agent_names: Dict[str, UUID] = {}
        self._active_agents: Set[UUID] = set()

    def add_agent(self,
                 agent_id: UUID,
                 name: str,
                 description: str,
                 status: AgentStatus) -> None:
        """Register a new agent."""
        if name in self._agent_names:
            raise ValueError(f"Agent with name '{name}' already exists")

        agent_info = AgentInfo(agent_id, name, description, status)
        self._agents[agent_id] = agent_info
        self._agent_names[name] = agent_id

        if status == AgentStatus.ACTIVE:
            self._active_agents.add(agent_id)

    def update_agent_status(self, agent_id: UUID, status: AgentStatus) -> None:
        """Update an agent's status."""
        if agent_id in self._agents:
            self._agents[agent_id].status = status
            self._agents[agent_id].last_seen = datetime.utcnow()

            if status == AgentStatus.ACTIVE:
                self._active_agents.add(agent_id)
            else:
                self._active_agents.discard(agent_id)

    def remove_agent(self, agent_id: UUID) -> None:
        """Remove an agent from the registry."""
        if agent_id in self._agents:
            agent_info = self._agents[agent_id]
            del self._agents[agent_id]
            del self._agent_names[agent_info.name]
            self._active_agents.discard(agent_id)

    def get_agent_status(self, name: str) -> AgentStatus:
        """Get an agent's status by name."""
        agent_id = self._agent_names.get(name)
        if agent_id and agent_id in self._agents:
            return self._agents[agent_id].status
        return AgentStatus.INACTIVE

    def get_agent_last_seen(self, name: str) -> datetime:
        """Get when an agent was last seen."""
        agent_id = self._agent_names.get(name)
        if agent_id and agent_id in self._agents:
            return self._agents[agent_id].last_seen
        return datetime.min
