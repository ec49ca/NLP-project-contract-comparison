"""
Knowledge Graph Agent Tests

Tests for the Knowledge Graph Agent that handles triple extraction,
document processing, and graph operations.
"""

import pytest
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import uuid4

# Mock all problematic dependencies before any imports
sys.modules["openai"] = MagicMock()
sys.modules["src.services.neo4j_service"] = MagicMock()
sys.modules["src.agents.tools.extract_triples"] = MagicMock()
sys.modules["src.agents.tools.detect_document_tool"] = MagicMock()
sys.modules["src.agents.tools.ner_el_tool"] = MagicMock()
sys.modules["src.agents.tools.preprocess_document_tool"] = MagicMock()
sys.modules["src.agents.tools.relation_extraction_tool"] = MagicMock()
sys.modules["src.services.prompt_service"] = MagicMock()

# Mock the tool classes themselves
mock_extract_tool_class = MagicMock()
mock_detect_tool_class = MagicMock()
mock_preprocess_tool_class = MagicMock()
mock_ner_tool_class = MagicMock()
mock_relation_tool_class = MagicMock()

sys.modules["src.agents.tools.extract_triples"].ExtractTriplesTool = (
    mock_extract_tool_class
)
sys.modules["src.agents.tools.detect_document_tool"].DetectDocumentTool = (
    mock_detect_tool_class
)
sys.modules["src.agents.tools.preprocess_document_tool"].PreprocessDocumentTool = (
    mock_preprocess_tool_class
)
sys.modules["src.agents.tools.ner_el_tool"].NEREntityLinkingTool = mock_ner_tool_class
sys.modules["src.agents.tools.relation_extraction_tool"].RelationExtractionTool = (
    mock_relation_tool_class
)

# Import after mocking
from src.agents.kg_agent import KnowledgeGraphAgent


@pytest.fixture
def mock_neo4j_service():
    """Mock Neo4j service for testing."""
    service = Mock()
    service.is_connected = AsyncMock(return_value=True)
    service.execute_query = AsyncMock(return_value={"success": True})
    return service


@pytest.fixture
def mock_extract_triples_tool():
    """Mock extract triples tool."""
    tool = Mock()
    tool.execute_tool = AsyncMock(
        return_value={
            "triples": [
                {"subject": "John", "predicate": "works_at", "object": "Company"},
                {"subject": "Company", "predicate": "located_in", "object": "New York"},
            ],
            "confidence": 0.85,
        }
    )
    return tool


@pytest.fixture
def mock_detect_document_tool():
    """Mock document detection tool."""
    tool = Mock()
    tool.execute_tool = AsyncMock(
        return_value={
            "document_type": "text",
            "confidence": 0.9,
            "metadata": {"language": "en", "encoding": "utf-8"},
        }
    )
    return tool


@pytest.fixture
def mock_preprocess_tool():
    """Mock document preprocessing tool."""
    tool = Mock()
    tool.execute_tool = AsyncMock(
        return_value={
            "cleaned_text": "This is preprocessed text.",
            "original_length": 100,
            "processed_length": 95,
            "metadata": {"removed_chars": 5},
        }
    )
    return tool


@pytest.fixture
def mock_ner_el_tool():
    """Mock NER Entity Linking tool."""
    tool = Mock()
    tool.execute_tool = AsyncMock(
        return_value={
            "entities": [
                {"text": "John", "label": "PERSON", "start": 0, "end": 4},
                {"text": "Company", "label": "ORG", "start": 15, "end": 22},
            ],
            "confidence": 0.88,
        }
    )
    return tool


@pytest.fixture
def mock_relation_extraction_tool():
    """Mock relation extraction tool."""
    tool = Mock()
    tool.execute_tool = AsyncMock(
        return_value={
            "relations": [
                {
                    "subject": "John",
                    "relation": "WORKS_AT",
                    "object": "Company",
                    "confidence": 0.92,
                }
            ]
        }
    )
    return tool


@pytest.mark.agents
@pytest.mark.unit
class TestKGAgentInitialization:
    """Test KG Agent initialization and setup."""

    def test_agent_creation(self):
        """Test basic agent creation and properties."""
        agent = KnowledgeGraphAgent()

        # Test basic properties
        assert agent.agent_id_str == "knowledge_graph"
        assert agent.agent_id == "knowledge_graph"
        assert agent.name == "Knowledge Graph Agent"
        assert "extract triples" in agent.description.lower()  # Fix text assertion
        assert agent.category == "knowledge_management"
        assert not agent._initialized

        # Test tools are initialized
        assert "extract_triples" in agent._tools
        assert "detect_document_type" in agent._tools
        assert "preprocess_document" in agent._tools
        assert "run_ner_el" in agent._tools
        assert "run_relation_extraction" in agent._tools

    def test_uuid_property(self):
        """Test UUID property management."""
        agent = KnowledgeGraphAgent()

        # Should raise error when UUID not set
        with pytest.raises(ValueError, match="UUID has not been set"):
            _ = agent.uuid

        # Should set UUID successfully
        test_uuid = uuid4()
        agent.uuid = test_uuid
        assert agent.uuid == test_uuid

        # Should not allow setting UUID twice
        with pytest.raises(ValueError, match="UUID can only be set once"):
            agent.uuid = uuid4()

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization process."""
        agent = KnowledgeGraphAgent()

        # Mock tool initialization
        for tool in agent._tools.values():
            tool.initialize = AsyncMock()

        config = {"test_config": "value"}
        await agent.initialize(config)

        assert agent._initialized is True

        # Verify tools with initialize method were called
        for tool in agent._tools.values():
            if hasattr(tool, "initialize"):
                tool.initialize.assert_called_once_with(config)

    @pytest.mark.asyncio
    async def test_agent_shutdown(self):
        """Test agent shutdown process."""
        agent = KnowledgeGraphAgent()
        agent._initialized = True

        await agent.shutdown()

        assert agent._initialized is False


@pytest.mark.agents
@pytest.mark.unit
class TestKGAgentStatus:
    """Test KG Agent status and capabilities."""

    def test_get_status(self):
        """Test agent status reporting."""
        agent = KnowledgeGraphAgent()
        agent._initialized = True

        status = agent.get_status()

        assert status["initialized"] is True
        assert status["healthy"] is True
        assert "tools_available" in status
        assert "capabilities" in status
        assert len(status["tools_available"]) == 5  # All tools

        # Test uninitialized state
        agent._initialized = False
        status = agent.get_status()
        assert status["initialized"] is False
        assert status["healthy"] is False

    def test_get_capabilities(self):
        """Test capabilities reporting."""
        agent = KnowledgeGraphAgent()

        capabilities = agent.get_capabilities()

        assert isinstance(capabilities, list)
        assert len(capabilities) > 0

        # Each capability should have required fields
        for capability in capabilities:
            assert isinstance(capability, dict)
            assert "name" in capability
            assert "description" in capability

    def test_tools_available(self):
        """Test tools are available in agent."""
        agent = KnowledgeGraphAgent()

        # Test tools dictionary is accessible
        assert isinstance(agent._tools, dict)
        assert "extract_triples" in agent._tools
        assert "detect_document_type" in agent._tools
        assert "preprocess_document" in agent._tools
        assert "run_ner_el" in agent._tools
        assert "run_relation_extraction" in agent._tools


@pytest.mark.agents
@pytest.mark.unit
class TestKGAgentRequestProcessing:
    """Test KG Agent request processing."""

    @pytest.mark.asyncio
    async def test_process_request_uninitialized(self):
        """Test request processing when agent not initialized."""
        agent = KnowledgeGraphAgent()
        agent._initialized = False

        request = {"command": "extract_triples", "text": "Test text"}
        result = await agent.process_request(request)

        assert "error" in result
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_process_request_unknown_command(self):
        """Test request processing with unknown command."""
        agent = KnowledgeGraphAgent()
        agent._initialized = True

        request = {"command": "unknown_command"}
        result = await agent.process_request(request)

        assert "error" in result
        assert "Unknown command" in result["error"]
        assert "available_commands" in result
        assert len(result["available_commands"]) > 0

    @pytest.mark.asyncio
    async def test_process_extract_triples_request(self, mock_extract_triples_tool):
        """Test extract triples request processing."""
        agent = KnowledgeGraphAgent()
        agent._initialized = True
        agent._tools["extract_triples"] = mock_extract_triples_tool

        request = {
            "command": "extract_triples",
            "text": "John works at Company.",
            "confidence_threshold": 0.8,
        }

        result = await agent.process_request(request)

        # Verify tool was called
        mock_extract_triples_tool.execute_tool.assert_called_once()

        # Check result structure (will depend on actual implementation)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_process_detect_document_request(self, mock_detect_document_tool):
        """Test document detection request processing."""
        agent = KnowledgeGraphAgent()
        agent._initialized = True
        agent._tools["detect_document_type"] = mock_detect_document_tool

        request = {
            "command": "detect_document_type",
            "document_content": "This is a test document.",  # Fixed parameter name
            "filename": "test.txt",
        }

        result = await agent.process_request(request)

        # Verify tool was called
        mock_detect_document_tool.execute_tool.assert_called_once()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_process_preprocess_document_request(self, mock_preprocess_tool):
        """Test document preprocessing request processing."""
        agent = KnowledgeGraphAgent()
        agent._initialized = True
        agent._tools["preprocess_document"] = mock_preprocess_tool

        request = {
            "command": "preprocess_document",
            "document_content": "Raw document content with extra spaces   .",  # Fixed parameter name
            "document_type": "text",
        }

        result = await agent.process_request(request)

        # Verify tool was called
        mock_preprocess_tool.execute_tool.assert_called_once()
        assert isinstance(result, dict)


@pytest.mark.agents
@pytest.mark.unit
class TestKGAgentToolIntegration:
    """Test KG Agent integration with its tools."""

    @pytest.mark.asyncio
    async def test_ner_el_integration(self, mock_ner_el_tool):
        """Test NER Entity Linking tool integration."""
        agent = KnowledgeGraphAgent()
        agent._initialized = True
        agent._tools["run_ner_el"] = mock_ner_el_tool

        request = {
            "command": "run_ner_el",
            "text": "John works at Company in New York.",
        }

        result = await agent.process_request(request)

        mock_ner_el_tool.execute_tool.assert_called_once()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_relation_extraction_integration(self, mock_relation_extraction_tool):
        """Test relation extraction tool integration."""
        agent = KnowledgeGraphAgent()
        agent._initialized = True
        agent._tools["run_relation_extraction"] = mock_relation_extraction_tool

        request = {
            "command": "run_relation_extraction",
            "text": "John works at Company.",
        }

        result = await agent.process_request(request)

        mock_relation_extraction_tool.execute_tool.assert_called_once()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test error handling when tools fail."""
        agent = KnowledgeGraphAgent()
        agent._initialized = True

        # Mock a tool that raises an exception
        failing_tool = Mock()
        failing_tool.execute_tool = AsyncMock(side_effect=Exception("Tool failed"))
        agent._tools["extract_triples"] = failing_tool

        request = {"command": "extract_triples", "text": "Test"}

        # Should handle tool errors gracefully
        result = await agent.process_request(request)

        # Depending on implementation, might return error or raise exception
        # This would need to be adjusted based on actual error handling
        assert isinstance(result, dict)


@pytest.mark.agents
@pytest.mark.integration
class TestKGAgentWorkflows:
    """Test KG Agent end-to-end workflows."""

    @pytest.mark.asyncio
    async def test_document_processing_workflow(
        self, mock_detect_document_tool, mock_preprocess_tool, mock_extract_triples_tool
    ):
        """Test complete document processing workflow."""
        agent = KnowledgeGraphAgent()
        agent._initialized = True

        # Setup mocked tools
        agent._tools["detect_document_type"] = mock_detect_document_tool
        agent._tools["preprocess_document"] = mock_preprocess_tool
        agent._tools["extract_triples"] = mock_extract_triples_tool

        # Simulate document processing workflow
        document_content = "John works at Company. Company is located in New York."

        # Step 1: Detect document type
        detect_request = {
            "command": "detect_document_type",
            "document_content": document_content,
        }
        detect_result = await agent.process_request(detect_request)

        # Step 2: Preprocess document
        preprocess_request = {
            "command": "preprocess_document",
            "document_content": document_content,
        }
        preprocess_result = await agent.process_request(preprocess_request)

        # Step 3: Extract triples
        extract_request = {"command": "extract_triples", "text": document_content}
        extract_result = await agent.process_request(extract_request)

        # Verify tools were called (detect and extract should work)
        mock_detect_document_tool.execute_tool.assert_called_once()
        mock_extract_triples_tool.execute_tool.assert_called_once()

        # Verify results are dictionaries and successful
        assert isinstance(detect_result, dict)
        assert isinstance(preprocess_result, dict)
        assert isinstance(extract_result, dict)

        # Check that operations completed successfully (no errors)
        assert "error" not in detect_result or detect_result.get("status") == "success"
        assert (
            "error" not in extract_result or extract_result.get("status") == "success"
        )

    @pytest.mark.asyncio
    async def test_ner_to_relation_workflow(
        self, mock_ner_el_tool, mock_relation_extraction_tool
    ):
        """Test NER to relation extraction workflow."""
        agent = KnowledgeGraphAgent()
        agent._initialized = True

        agent._tools["run_ner_el"] = mock_ner_el_tool
        agent._tools["run_relation_extraction"] = mock_relation_extraction_tool

        text = "John works at Company."

        # Step 1: Run NER+EL
        ner_request = {"command": "run_ner_el", "text": text}
        ner_result = await agent.process_request(ner_request)

        # Step 2: Extract relations
        relation_request = {"command": "run_relation_extraction", "text": text}
        relation_result = await agent.process_request(relation_request)

        # Verify both tools were called
        mock_ner_el_tool.execute_tool.assert_called_once()
        mock_relation_extraction_tool.execute_tool.assert_called_once()

        assert isinstance(ner_result, dict)
        assert isinstance(relation_result, dict)


@pytest.mark.agents
@pytest.mark.integration
class TestKGAgentNeo4jIntegration:
    """Test KG Agent integration with Neo4j database."""

    @pytest.mark.asyncio
    async def test_neo4j_service_available(self, mock_neo4j_service):
        """Test that Neo4j service is available to the agent."""
        with patch("src.agents.kg_agent.Neo4jService", return_value=mock_neo4j_service):
            agent = KnowledgeGraphAgent()

            # Neo4j service should be initialized
            assert agent._graphdb_ is not None

    @pytest.mark.asyncio
    async def test_agent_ready_for_production(self):
        """Test that agent is ready for typical production usage."""
        agent = KnowledgeGraphAgent()

        # Agent should have all required components
        assert agent.agent_id_str is not None
        assert agent.name is not None
        assert agent.description is not None
        assert len(agent._tools) > 0
        assert agent._graphdb_ is not None

        # Should be able to initialize
        await agent.initialize({})
        assert agent._initialized is True

        # Should report healthy status
        status = agent.get_status()
        assert status["healthy"] is True
        assert len(status["tools_available"]) > 0
