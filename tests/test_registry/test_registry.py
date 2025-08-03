"""
Agent Registry System Unit Tests

Simple tests for agent registration and management.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4, UUID
from src.registry.registry import AgentRegistrySystem
from src.registry.registry_models import AgentStatus
from src.interfaces.agent import AgentInterface


class MockAgent(AgentInterface):
    """Mock agent for testing."""

    def __init__(self, agent_id_str="test_agent", name="Test Agent"):
        self._agent_id_str = agent_id_str
        self._name = name
        self._description = "A test agent"
        self._uuid = None
        self._initialized = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def agent_id_str(self) -> str:
        return self._agent_id_str

    @agent_id_str.setter
    def agent_id_str(self, value: str):
        self._agent_id_str = value

    @property
    def uuid(self):
        return self._uuid

    @uuid.setter
    def uuid(self, value):
        self._uuid = value

    async def initialize(self, config):
        self._initialized = True

    async def process_request(self, request):
        return {"result": "test"}

    async def shutdown(self):
        self._initialized = False

    def get_tools(self):
        return [{"name": "test", "description": "test capability"}]

    def get_status(self):
        return {"initialized": self._initialized}


@pytest.mark.unit
class TestAgentRegistrySystem:
    """Test basic agent registry system functionality."""

    @pytest.mark.asyncio
    async def test_registry_creation(self):
        """Test basic registry system creation."""
        registry = AgentRegistrySystem()

        assert hasattr(registry, "_registry")
        assert hasattr(registry, "_agents")
        assert len(registry._agents) == 0

    @pytest.mark.asyncio
    async def test_register_single_agent(self):
        """Test registering a single agent."""
        registry = AgentRegistrySystem()

        # Create mock agent class
        def mock_agent_class():
            return MockAgent("test_agent", "Test Agent")

        config = {"test": "config"}

        with patch("src.constants.SAMVID_AGENT_NAMESPACE", uuid4()):
            agent_id = await registry.register_agent(mock_agent_class, config)

        assert isinstance(agent_id, UUID)
        assert agent_id in registry._agents

        # Check agent was initialized
        agent = registry._agents[agent_id]
        assert agent._initialized is True
        assert agent.uuid == agent_id

    @pytest.mark.asyncio
    async def test_register_multiple_agents(self):
        """Test registering multiple agents."""
        registry = AgentRegistrySystem()

        def mock_agent_class_1():
            return MockAgent("agent_1", "Agent 1")

        def mock_agent_class_2():
            return MockAgent("agent_2", "Agent 2")

        config = {}

        with patch("src.constants.SAMVID_AGENT_NAMESPACE", uuid4()):
            agent_id_1 = await registry.register_agent(mock_agent_class_1, config)
            agent_id_2 = await registry.register_agent(mock_agent_class_2, config)

        assert len(registry._agents) == 2
        assert agent_id_1 != agent_id_2
        assert agent_id_1 in registry._agents
        assert agent_id_2 in registry._agents

    @pytest.mark.asyncio
    async def test_deterministic_uuid_generation(self):
        """Test that same agent_id_str generates same UUID."""
        registry1 = AgentRegistrySystem()
        registry2 = AgentRegistrySystem()

        def mock_agent_class():
            return MockAgent("same_agent_id", "Same Agent")

        config = {}
        namespace = uuid4()

        with patch("src.constants.SAMVID_AGENT_NAMESPACE", namespace):
            agent_id_1 = await registry1.register_agent(mock_agent_class, config)

        with patch("src.constants.SAMVID_AGENT_NAMESPACE", namespace):
            agent_id_2 = await registry2.register_agent(mock_agent_class, config)

        # Same agent_id_str with same namespace should generate same UUID
        assert agent_id_1 == agent_id_2


@pytest.mark.unit
class TestAgentRegistrySystemEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_agent_initialization_called(self):
        """Test that agent initialization is called during registration."""
        registry = AgentRegistrySystem()

        # Create mock with spy on initialize
        mock_agent = MockAgent()
        mock_agent.initialize = AsyncMock()

        def mock_agent_class():
            return mock_agent

        config = {"test_config": "value"}

        with patch("src.constants.SAMVID_AGENT_NAMESPACE", uuid4()):
            await registry.register_agent(mock_agent_class, config)

        # Verify initialize was called with config
        mock_agent.initialize.assert_called_once_with(config)

    @pytest.mark.asyncio
    async def test_agent_uuid_assignment(self):
        """Test that agent UUID is properly assigned."""
        registry = AgentRegistrySystem()

        def mock_agent_class():
            agent = MockAgent()
            assert agent.uuid is None  # Should start as None
            return agent

        config = {}

        with patch("src.constants.SAMVID_AGENT_NAMESPACE", uuid4()):
            agent_id = await registry.register_agent(mock_agent_class, config)

        # Agent should have UUID assigned
        agent = registry._agents[agent_id]
        assert agent.uuid == agent_id
        assert agent.uuid is not None

    @pytest.mark.asyncio
    async def test_registry_internal_consistency(self):
        """Test internal registry state consistency."""
        registry = AgentRegistrySystem()

        def mock_agent_class():
            return MockAgent("consistency_test", "Consistency Agent")

        config = {}

        with patch("src.constants.SAMVID_AGENT_NAMESPACE", uuid4()):
            agent_id = await registry.register_agent(mock_agent_class, config)

        # Check that both internal registries are consistent
        assert agent_id in registry._agents

        # Registry should contain the agent
        agent_info = registry._registry._agents.get(agent_id)
        assert agent_info is not None
        assert agent_info.agent_id == agent_id
        assert agent_info.status == AgentStatus.ACTIVE


@pytest.mark.unit
class TestAgentRegistrySystemIntegration:
    """Test registry system integration points."""

    @pytest.mark.asyncio
    async def test_agent_class_instantiation(self):
        """Test that agent classes are properly instantiated."""
        registry = AgentRegistrySystem()

        # Track instantiation
        instantiated = []

        def mock_agent_class():
            agent = MockAgent()
            instantiated.append(agent)
            return agent

        config = {}

        with patch("src.constants.SAMVID_AGENT_NAMESPACE", uuid4()):
            await registry.register_agent(mock_agent_class, config)

        assert len(instantiated) == 1
        assert isinstance(instantiated[0], MockAgent)

    @pytest.mark.asyncio
    async def test_config_passing(self):
        """Test that configuration is properly passed to agents."""
        registry = AgentRegistrySystem()

        received_config = None

        class ConfigTestAgent(MockAgent):
            async def initialize(self, config):
                nonlocal received_config
                received_config = config
                await super().initialize(config)

        def mock_agent_class():
            return ConfigTestAgent()

        test_config = {"api_key": "test123", "debug": True}

        with patch("src.constants.SAMVID_AGENT_NAMESPACE", uuid4()):
            await registry.register_agent(mock_agent_class, test_config)

        assert received_config == test_config

    @pytest.mark.asyncio
    async def test_registry_state_after_registration(self):
        """Test registry state after successful registration."""
        registry = AgentRegistrySystem()

        def mock_agent_class():
            return MockAgent("state_test", "State Test Agent")

        config = {}

        with patch("src.constants.SAMVID_AGENT_NAMESPACE", uuid4()):
            agent_id = await registry.register_agent(mock_agent_class, config)

        # Registry should have proper state
        assert len(registry._agents) == 1

        # Agent should be retrievable
        agent = registry._agents[agent_id]
        assert agent is not None
        assert agent.name == "State Test Agent"
        assert agent.agent_id_str == "state_test"
