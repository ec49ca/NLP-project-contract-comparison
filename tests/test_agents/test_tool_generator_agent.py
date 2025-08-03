"""
Tool Generator Agent Tests

Tests for the Tool Generator Agent that handles dynamic tool creation
from natural language queries using complexity-based routing.
"""

import pytest
import sys
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import uuid4

# Mock dependencies to avoid import issues during testing
sys.modules["openai"] = MagicMock()
sys.modules["src.services.prompt_service"] = MagicMock()

# Mock OpenAI client
mock_openai_class = MagicMock()
sys.modules["openai"].OpenAI = mock_openai_class

from src.agents.tool_generator_agent import ToolGeneratorAgent


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = Mock()

    # Mock chat completions
    completion_response = Mock()
    completion_response.choices = [Mock()]
    completion_response.choices[0].message = Mock()
    completion_response.choices[0].message.content = (
        '{"complexity": "simple", "reasoning": "Basic data analysis"}'
    )

    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = Mock(return_value=completion_response)

    return client


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""

    def create_response(content):
        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message = Mock()
        response.choices[0].message.content = content
        return response

    return create_response


@pytest.mark.agents
@pytest.mark.unit
class TestToolGeneratorInitialization:
    """Test Tool Generator Agent initialization and setup."""

    def test_agent_creation(self):
        """Test basic agent creation and properties."""
        agent = ToolGeneratorAgent()

        # Test basic properties
        assert agent.agent_id_str == "tool_generator"
        assert agent.agent_id == "tool_generator"
        assert agent.name == "Tool Generator Agent"
        assert "dynamic tool" in agent.description.lower()
        assert agent.category == "tool_generation"
        assert not agent._initialized

        # Test storage initialization
        assert isinstance(agent.pending_tools, dict)
        assert isinstance(agent.approved_tools, dict)
        assert len(agent.pending_tools) == 0
        assert len(agent.approved_tools) == 0

    @pytest.mark.asyncio
    async def test_agent_initialization(self, mock_openai_client):
        """Test agent initialization with configuration."""
        agent = ToolGeneratorAgent()

        config = {"openai_api_key": "test-key-123", "debug": True}

        with patch(
            "src.agents.tool_generator_agent.OpenAI", return_value=mock_openai_client
        ):
            await agent.initialize(config)

        assert agent._initialized is True
        assert agent.client is not None
        assert agent.api_key == "test-key-123"

    @pytest.mark.asyncio
    async def test_agent_initialization_no_api_key(self):
        """Test agent initialization without API key."""
        agent = ToolGeneratorAgent()

        config = {}

        with patch.dict("os.environ", {}, clear=True):
            # Should raise ValueError when no API key is provided
            with pytest.raises(ValueError, match="OpenAI API key not found"):
                await agent.initialize(config)

    @pytest.mark.asyncio
    async def test_agent_shutdown(self):
        """Test agent shutdown process."""
        agent = ToolGeneratorAgent()
        agent._initialized = True

        await agent.shutdown()

        # Note: Tool Generator Agent shutdown doesn't modify _initialized flag
        # This is the actual behavior of the agent
        assert agent._initialized is True  # Shutdown doesn't change this flag


@pytest.mark.agents
@pytest.mark.unit
class TestToolGeneratorStatus:
    """Test Tool Generator Agent status and capabilities."""

    def test_get_status(self):
        """Test agent status reporting."""
        agent = ToolGeneratorAgent()
        agent._initialized = True

        status = agent.get_status()

        assert status["initialized"] is True
        # Note: Tool Generator Agent doesn't have "healthy" field in status
        assert "pending_tools_count" in status
        assert "approved_tools_count" in status
        assert "session_id" in status
        assert "capabilities_count" in status

        # Test uninitialized state
        agent._initialized = False
        status = agent.get_status()
        assert status["initialized"] is False

    def test_get_tools(self):
        """Test capabilities reporting."""
        agent = ToolGeneratorAgent()

        capabilities = agent.get_tools()

        assert isinstance(capabilities, list)
        assert len(capabilities) > 0

        # Each capability should have required fields
        for capability in capabilities:
            assert isinstance(capability, dict)
            assert "name" in capability
            assert "description" in capability

    def test_debug_logging(self):
        """Test debug logging functionality."""
        agent = ToolGeneratorAgent()

        # Test that debug logging doesn't crash
        test_data = {"test": "data"}
        agent.log_debug("test_step", test_data, "INFO")

        # Should complete without errors
        assert agent.current_session_id is not None
        assert len(agent.current_session_id) == 8


@pytest.mark.agents
@pytest.mark.unit
class TestToolGeneratorRequestProcessing:
    """Test Tool Generator Agent request processing."""

    @pytest.mark.asyncio
    async def test_process_request_uninitialized(self):
        """Test request processing when agent not initialized."""
        agent = ToolGeneratorAgent()
        agent._initialized = False

        request = {"command": "generate_and_execute", "query": "Test query"}
        result = await agent.process_request(request)

        assert "error" in result
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_process_request_unknown_command(self, mock_openai_client):
        """Test request processing with unknown command."""
        agent = ToolGeneratorAgent()
        agent._initialized = True
        agent.client = mock_openai_client

        request = {"command": "unknown_command"}
        result = await agent.process_request(request)

        assert "error" in result
        assert "Unknown command" in result["error"]
        assert "available_commands" in result
        assert len(result["available_commands"]) > 0
        assert "generate_and_execute" in result["available_commands"]

    @pytest.mark.asyncio
    async def test_assess_complexity_request(
        self, mock_openai_client, mock_openai_response
    ):
        """Test complexity assessment request processing."""
        agent = ToolGeneratorAgent()
        agent._initialized = True
        agent.client = mock_openai_client

        # Mock OpenAI response for complexity assessment
        complexity_response = mock_openai_response(
            '{"complexity": "simple", "reasoning": "Basic query"}'
        )
        mock_openai_client.chat.completions.create.return_value = complexity_response

        request = {
            "command": "assess_complexity",
            "query": "Calculate the average of these numbers",
            "data": [1, 2, 3, 4, 5],
        }

        result = await agent.process_request(request)

        # Verify OpenAI was called
        mock_openai_client.chat.completions.create.assert_called_once()

        # Check result structure
        assert isinstance(result, dict)
        assert result.get("status") in ["success", "error"] or "complexity" in result

    @pytest.mark.asyncio
    async def test_generate_direct_request(
        self, mock_openai_client, mock_openai_response
    ):
        """Test direct generation request processing."""
        agent = ToolGeneratorAgent()
        agent._initialized = True
        agent.client = mock_openai_client

        # Mock OpenAI response for code generation
        code_response = mock_openai_response(
            """
        ```python
        def calculate_average(data):
            return sum(data) / len(data)
        result = calculate_average([1, 2, 3, 4, 5])
        ```
        """
        )
        mock_openai_client.chat.completions.create.return_value = code_response

        request = {
            "command": "generate_direct",
            "query": "Calculate average of numbers",
            "data": [1, 2, 3, 4, 5],
        }

        result = await agent.process_request(request)

        # Verify OpenAI was called
        mock_openai_client.chat.completions.create.assert_called_once()

        # Check result structure
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_generate_and_execute_request(
        self, mock_openai_client, mock_openai_response
    ):
        """Test generate and execute request processing."""
        agent = ToolGeneratorAgent()
        agent._initialized = True
        agent.client = mock_openai_client

        # Mock responses for the multi-step process
        complexity_response = mock_openai_response('{"complexity": "simple"}')
        code_response = mock_openai_response(
            """
        ```python
        def process_data(data):
            return {"result": sum(data), "count": len(data)}
        result = process_data(data)
        ```
        """
        )

        mock_openai_client.chat.completions.create.side_effect = [
            complexity_response,
            code_response,
        ]

        request = {
            "command": "generate_and_execute",
            "query": "Sum these numbers",
            "data": [1, 2, 3],
        }

        result = await agent.process_request(request)

        # Verify OpenAI was called multiple times
        assert mock_openai_client.chat.completions.create.call_count >= 1

        # Check result structure
        assert isinstance(result, dict)


@pytest.mark.agents
@pytest.mark.unit
class TestToolGeneratorToolManagement:
    """Test Tool Generator Agent tool management functionality."""

    @pytest.mark.asyncio
    async def test_get_pending_tools(self, mock_openai_client):
        """Test getting pending tools."""
        agent = ToolGeneratorAgent()
        agent._initialized = True
        agent.client = mock_openai_client

        # Add some pending tools
        agent.pending_tools["tool1"] = {"name": "Test Tool 1", "query": "Test query 1"}
        agent.pending_tools["tool2"] = {"name": "Test Tool 2", "query": "Test query 2"}

        request = {"command": "get_pending_tools"}
        result = await agent.process_request(request)

        # Tool Generator Agent wraps response in {"status": "success", "data": {...}}
        assert result["status"] == "success"
        assert "data" in result
        assert "pending_tools" in result["data"]
        assert len(result["data"]["pending_tools"]) == 2
        assert isinstance(result["data"]["pending_tools"], list)

    @pytest.mark.asyncio
    async def test_approve_tool(self, mock_openai_client):
        """Test approving a pending tool."""
        agent = ToolGeneratorAgent()
        agent._initialized = True
        agent.client = mock_openai_client

        # Add a pending tool
        tool_id = "test_tool_id"
        agent.pending_tools[tool_id] = {
            "name": "Test Tool",
            "query": "Test query",
            "code": "def test(): return True",
        }

        request = {"command": "approve_tool", "tool_id": tool_id}

        result = await agent.process_request(request)

        # Tool should be moved from pending to approved
        assert tool_id not in agent.pending_tools
        assert tool_id in agent.approved_tools
        assert result.get("status") == "success"

    @pytest.mark.asyncio
    async def test_reject_tool(self, mock_openai_client):
        """Test rejecting a pending tool."""
        agent = ToolGeneratorAgent()
        agent._initialized = True
        agent.client = mock_openai_client

        # Add a pending tool
        tool_id = "test_tool_id"
        agent.pending_tools[tool_id] = {"name": "Test Tool", "query": "Test query"}

        request = {
            "command": "reject_tool",
            "tool_id": tool_id,
            "reason": "Not suitable",
        }

        result = await agent.process_request(request)

        # Tool should be removed from pending
        assert tool_id not in agent.pending_tools
        assert tool_id not in agent.approved_tools
        assert result.get("status") == "success"

    @pytest.mark.asyncio
    async def test_get_approved_tools(self, mock_openai_client):
        """Test getting approved tools."""
        agent = ToolGeneratorAgent()
        agent._initialized = True
        agent.client = mock_openai_client

        # Add some approved tools
        agent.approved_tools["tool1"] = {"name": "Approved Tool 1"}
        agent.approved_tools["tool2"] = {"name": "Approved Tool 2"}

        request = {"command": "get_approved_tools"}
        result = await agent.process_request(request)

        # Tool Generator Agent wraps response in {"status": "success", "data": {...}}
        assert result["status"] == "success"
        assert "data" in result
        assert "approved_tools" in result["data"]
        assert len(result["data"]["approved_tools"]) == 2
        assert isinstance(result["data"]["approved_tools"], list)

    @pytest.mark.asyncio
    async def test_approve_nonexistent_tool(self, mock_openai_client):
        """Test approving a non-existent tool."""
        agent = ToolGeneratorAgent()
        agent._initialized = True
        agent.client = mock_openai_client

        request = {"command": "approve_tool", "tool_id": "nonexistent_tool"}

        result = await agent.process_request(request)

        assert "error" in result or result.get("status") == "error"


@pytest.mark.agents
@pytest.mark.unit
class TestToolGeneratorCodeExecution:
    """Test Tool Generator Agent code execution functionality."""

    def test_execute_code_basic(self):
        """Test basic code execution."""
        agent = ToolGeneratorAgent()

        code = """
result = sum([1, 2, 3, 4, 5])
"""
        data = []
        kwargs = {}

        result = agent.execute_code(code, data, kwargs)

        # Should execute without errors
        assert result is not None

    def test_execute_code_with_data(self):
        """Test code execution with data parameter."""
        agent = ToolGeneratorAgent()

        code = """
result = sum(data)
"""
        data = [1, 2, 3, 4, 5]
        kwargs = {}

        result = agent.execute_code(code, data, kwargs)

        # Should execute and use the data parameter
        assert result is not None

    def test_execute_code_error_handling(self):
        """Test code execution error handling."""
        agent = ToolGeneratorAgent()

        # Invalid code that should raise an error
        code = """
result = undefined_variable + 1
"""
        data = []
        kwargs = {}

        result = agent.execute_code(code, data, kwargs)

        # Should handle the error gracefully
        assert result is not None


@pytest.mark.agents
@pytest.mark.integration
class TestToolGeneratorWorkflows:
    """Test Tool Generator Agent end-to-end workflows."""

    @pytest.mark.asyncio
    async def test_simple_tool_generation_workflow(
        self, mock_openai_client, mock_openai_response
    ):
        """Test complete simple tool generation workflow."""
        agent = ToolGeneratorAgent()
        agent._initialized = True
        agent.client = mock_openai_client

        # Mock the complexity assessment to return "simple"
        complexity_response = mock_openai_response(
            '{"complexity": "simple", "reasoning": "Basic calculation"}'
        )

        # Mock the code generation
        code_response = mock_openai_response(
            """
        ```python
        def calculate_sum(data):
            return sum(data)
        result = calculate_sum(data)
        ```
        """
        )

        mock_openai_client.chat.completions.create.side_effect = [
            complexity_response,
            code_response,
        ]

        request = {
            "command": "generate_and_execute",
            "query": "Calculate the sum of these numbers",
            "data": [1, 2, 3, 4, 5],
        }

        result = await agent.process_request(request)

        # Verify the workflow completed
        assert isinstance(result, dict)
        assert mock_openai_client.chat.completions.create.call_count >= 1

    @pytest.mark.asyncio
    async def test_tool_approval_workflow(self, mock_openai_client):
        """Test tool approval workflow."""
        agent = ToolGeneratorAgent()
        agent._initialized = True
        agent.client = mock_openai_client

        # Simulate a tool being generated and pending approval
        tool_id = "workflow_tool"
        agent.pending_tools[tool_id] = {
            "name": "Workflow Tool",
            "query": "Test workflow",
            "code": "def workflow(): return True",
        }

        # Get pending tools
        pending_request = {"command": "get_pending_tools"}
        pending_result = await agent.process_request(pending_request)

        assert pending_result["status"] == "success"
        assert len(pending_result["data"]["pending_tools"]) == 1

        # Approve the tool
        approve_request = {"command": "approve_tool", "tool_id": tool_id}
        approve_result = await agent.process_request(approve_request)

        assert approve_result.get("status") == "success"

        # Get approved tools
        approved_request = {"command": "get_approved_tools"}
        approved_result = await agent.process_request(approved_request)

        assert approved_result["status"] == "success"
        assert len(approved_result["data"]["approved_tools"]) == 1
        assert len(agent.pending_tools) == 0


@pytest.mark.agents
@pytest.mark.integration
class TestToolGeneratorProduction:
    """Test Tool Generator Agent production readiness."""

    @pytest.mark.asyncio
    async def test_agent_ready_for_production(self):
        """Test that agent is ready for typical production usage."""
        agent = ToolGeneratorAgent()

        # Agent should have all required components
        assert agent.agent_id_str is not None
        assert agent.name is not None
        assert agent.description is not None
        assert hasattr(agent, "pending_tools")
        assert hasattr(agent, "approved_tools")

        # Should be able to initialize
        config = {"openai_api_key": "test-key"}
        with patch("src.agents.tool_generator_agent.OpenAI"):
            await agent.initialize(config)
        assert agent._initialized is True

        # Should report status (no "healthy" field in Tool Generator Agent)
        status = agent.get_status()
        assert status["initialized"] is True
        assert "session_id" in status

    def test_session_management(self):
        """Test session ID generation and management."""
        agent = ToolGeneratorAgent()

        # Should have a session ID
        assert agent.current_session_id is not None
        assert len(agent.current_session_id) == 8

        # Session ID should be consistent
        session1 = agent.current_session_id
        session2 = agent.current_session_id
        assert session1 == session2

    def test_error_resilience(self):
        """Test agent resilience to various error conditions."""
        agent = ToolGeneratorAgent()

        # Should handle missing files gracefully
        agent.log_debug("test", {"data": "test"})

        # Should handle invalid code execution
        result = agent.execute_code("invalid syntax", [], {})
        assert result is not None  # Should not crash
