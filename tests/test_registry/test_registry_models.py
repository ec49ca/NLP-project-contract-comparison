"""
Registry Models Unit Tests

Simple tests for registry data models and enums.
"""

import pytest
from datetime import datetime
from uuid import uuid4, UUID
from src.registry.registry_models import AgentStatus, AgentInfo, AgentRegistry


@pytest.mark.unit
class TestAgentStatus:
    """Test AgentStatus enum."""

    def test_agent_status_values(self):
        """Test agent status enum values."""
        assert AgentStatus.ACTIVE.value == "active"
        assert AgentStatus.INACTIVE.value == "inactive"
        assert AgentStatus.ERROR.value == "error"
        assert AgentStatus.SHUTTING_DOWN.value == "shutting_down"

    def test_agent_status_comparison(self):
        """Test agent status comparison."""
        assert AgentStatus.ACTIVE == AgentStatus.ACTIVE
        assert AgentStatus.ACTIVE != AgentStatus.INACTIVE

    def test_agent_status_string_representation(self):
        """Test agent status string representation."""
        status = AgentStatus.ACTIVE
        assert str(status) == "AgentStatus.ACTIVE"


@pytest.mark.unit
class TestAgentInfo:
    """Test AgentInfo data model."""

    def test_agent_info_creation(self):
        """Test basic agent info creation."""
        agent_id = uuid4()
        name = "Test Agent"
        description = "A test agent"

        info = AgentInfo(agent_id, name, description)

        assert info.agent_id == agent_id
        assert info.name == name
        assert info.description == description
        assert info.status == AgentStatus.INACTIVE  # Default status
        assert isinstance(info.last_seen, datetime)

    def test_agent_info_with_custom_status(self):
        """Test agent info creation with custom status."""
        agent_id = uuid4()
        name = "Active Agent"
        description = "An active test agent"

        info = AgentInfo(agent_id, name, description, AgentStatus.ACTIVE)

        assert info.status == AgentStatus.ACTIVE

    def test_agent_info_last_seen_timestamp(self):
        """Test that last_seen is set to current time."""
        info = AgentInfo(uuid4(), "Test", "Description")

        # last_seen should be recent (within last few seconds)
        time_diff = datetime.utcnow() - info.last_seen
        assert time_diff.total_seconds() < 5  # Within 5 seconds


@pytest.mark.unit
class TestAgentRegistry:
    """Test AgentRegistry functionality."""

    def test_registry_creation(self):
        """Test basic registry creation."""
        registry = AgentRegistry()

        assert isinstance(registry._agents, dict)
        assert isinstance(registry._agent_names, dict)
        assert isinstance(registry._active_agents, set)
        assert len(registry._agents) == 0

    def test_add_agent(self):
        """Test adding an agent to registry."""
        registry = AgentRegistry()
        agent_id = uuid4()
        name = "Test Agent"
        description = "Test Description"

        registry.add_agent(agent_id, name, description, AgentStatus.ACTIVE)

        assert agent_id in registry._agents
        assert name in registry._agent_names
        assert registry._agent_names[name] == agent_id
        assert agent_id in registry._active_agents

    def test_add_multiple_agents(self):
        """Test adding multiple agents."""
        registry = AgentRegistry()

        agent1_id = uuid4()
        agent2_id = uuid4()

        registry.add_agent(agent1_id, "Agent 1", "Description 1", AgentStatus.ACTIVE)
        registry.add_agent(agent2_id, "Agent 2", "Description 2", AgentStatus.INACTIVE)

        assert len(registry._agents) == 2
        assert len(registry._agent_names) == 2
        assert agent1_id in registry._active_agents
        assert agent2_id not in registry._active_agents  # INACTIVE status

    def test_agent_info_stored_correctly(self):
        """Test that agent info is stored with correct data."""
        registry = AgentRegistry()
        agent_id = uuid4()
        name = "Test Agent"
        description = "Test Description"

        registry.add_agent(agent_id, name, description, AgentStatus.ACTIVE)

        stored_info = registry._agents[agent_id]
        assert isinstance(stored_info, AgentInfo)
        assert stored_info.agent_id == agent_id
        assert stored_info.name == name
        assert stored_info.description == description
        assert stored_info.status == AgentStatus.ACTIVE


@pytest.mark.unit
class TestAgentRegistryEdgeCases:
    """Test edge cases for agent registry."""

    def test_empty_registry_state(self):
        """Test empty registry initial state."""
        registry = AgentRegistry()

        assert len(registry._agents) == 0
        assert len(registry._agent_names) == 0
        assert len(registry._active_agents) == 0

    def test_agent_name_mapping(self):
        """Test agent name to ID mapping."""
        registry = AgentRegistry()
        agent_id = uuid4()
        name = "Unique Agent Name"

        registry.add_agent(agent_id, name, "Description", AgentStatus.ACTIVE)

        assert registry._agent_names[name] == agent_id

    def test_different_status_types(self):
        """Test adding agents with different status types."""
        registry = AgentRegistry()

        active_id = uuid4()
        inactive_id = uuid4()
        error_id = uuid4()

        registry.add_agent(active_id, "Active", "Desc", AgentStatus.ACTIVE)
        registry.add_agent(inactive_id, "Inactive", "Desc", AgentStatus.INACTIVE)
        registry.add_agent(error_id, "Error", "Desc", AgentStatus.ERROR)

        assert active_id in registry._active_agents
        assert inactive_id not in registry._active_agents
        assert error_id not in registry._active_agents

        assert len(registry._agents) == 3
        assert len(registry._active_agents) == 1
