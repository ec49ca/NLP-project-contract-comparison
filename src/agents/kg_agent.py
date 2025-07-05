"""
Knowledge Graph Agent - Triple Extraction Implementation

This agent provides knowledge graph capabilities starting with triple extraction from client data.
Additional tools to be implemented:

## Core Tools to Implement:

1. **Triple Creation & Management**
   - extract_triples
   - create_triples_from_data - Convert structured data (JSON, CSV) to triples
   - validate_triples - Validate and normalize triples

2. **Graph Traversal & Querying**
   - find_relationships
   - traverse_graph

How tools work:
1. Discovery: client hits /agents/discover to get a list of agents with basic info and tools available
        - agentdiscoveryrequest with filters. each agent returns tools via .get_tools()
2. Tool discovery:
"""

import logging
from typing import Dict, List, Any, Optional
from ..interfaces.agent import AgentInterface
from .tools.extract_triples import ExtractTriplesTool
from .tools.detect_document_tool import DetectDocumentTool
from .tools.preprocess_document_tool import PreprocessDocumentTool
from ..services.neo4j_service import Neo4jService
from uuid import UUID

logger = logging.getLogger(__name__)


class KnowledgeGraphAgent(AgentInterface):
    """Knowledge graph agent for triple extraction and graph operations"""

    def __init__(self):
        self._agent_id_str = "knowledge_graph"
        self._uuid = None
        self.agent_id = "knowledge_graph"
        self._name = "Knowledge Graph Agent"
        self._description = "Extract triples from data and perform graph operations"
        self._initialized = False
        self.category = "knowledge_management"
        self.status = "initialized"
        self._tools = {}
        self._graphdb_ = Neo4jService()

        # Add extract_triples tool
        self._tools["extract_triples"] = ExtractTriplesTool()

        # Add detect_document_type tool
        self._tools["detect_document_type"] = DetectDocumentTool()

        # Add preprocess_document tool
        self._tools["preprocess_document"] = PreprocessDocumentTool()

    @property
    def agent_id_str(self) -> str:
        return self._agent_id_str

    @property
    def uuid(self) -> UUID:
        if self._uuid is None:
            raise ValueError("UUID has not been set yet.")
        return self._uuid

    @uuid.setter
    def uuid(self, value: UUID):
        if self._uuid is not None:
            raise ValueError("UUID can only be set once.")
        self._uuid = value

    @property
    def name(self) -> str:
        """Agent's unique identifier."""
        return self._name

    @property
    def description(self) -> str:
        """KG Agent will extract triples from text data and insert them into the graph database."""
        return self._description

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the agent with configuration."""
        # Initialize tools if needed
        for tool_name, tool in self._tools.items():
            if hasattr(tool, "initialize"):
                await tool.initialize(config)

        self._initialized = True
        logger.info("KnowledgeGraphAgent initialized successfully")

    async def shutdown(self) -> None:
        """Clean up resources when shutting down."""
        self._initialized = False
        logger.info("KnowledgeGraphAgent shutdown complete")

    def get_status(self) -> Dict[str, Any]:
        """Return agent's current status."""
        return {
            "initialized": self._initialized,
            "healthy": self._initialized,
            "tools_available": list(self._tools.keys()),
            "capabilities": self.get_capabilities(),
        }

    def get_capabilities(self) -> List[Dict[str, Any]]:
        """Return agent's capabilities."""
        return [
            {
                "name": "extract_triples",
                "description": "Extract triples (subject-predicate-object relationships) from unstructured text",
                "parameters": {
                    "text": "Text to extract triples from (required)",
                    "confidence_threshold": "Minimum confidence score for triples (0.0-1.0, default: 0.7)",
                    "max_triples": "Maximum number of triples to extract (default: 100)",
                },
            },
            {
                "name": "detect_document_type",
                "description": "Detect document type with 7-point structure classification: highly_structured, structured, moderately_structured, semi_structured, lightly_structured, unstructured, highly_unstructured, plus scanned detection",
                "parameters": {
                    "document_content": "Document content or file path (required)",
                    "content_type": "MIME type hint (optional)",
                    "filename": "Original filename for extension-based detection (optional)",
                    "file_path": "Path to the file for analysis (optional, alternative to document_content)",
                },
            },
            {
                "name": "preprocess_document",
                "description": "Clean and preprocess document content for knowledge extraction with OCR support for scanned documents, type-specific preprocessing, text normalization, and stopword removal",
                "parameters": {
                    "document_content": "Raw document content (required if no file_path)",
                    "document_type": "Document type from detect_document_type (required) - use 'scanned' for OCR processing",
                    "remove_stopwords": "Whether to remove stopwords (default: false)",
                    "normalize_text": "Whether to normalize text (default: true)",
                    "file_path": "Path to file for OCR processing (optional, for scanned documents)",
                },
            },
            {
                "name": "run_ner_el",
                "description": "Perform Named Entity Recognition and Entity Linking on preprocessed text",
                "parameters": {
                    "text": "Preprocessed text content (required)",
                    "entity_types": "List of entity types to extract (optional, default: ['PERSON', 'ORG', 'GPE', 'PRODUCT'])",
                    "confidence_threshold": "Minimum confidence score for entities (0.0-1.0, default: 0.8)",
                    "max_entities": "Maximum number of entities to extract (default: 50)",
                },
            },
            {
                "name": "run_relation_extraction",
                "description": "Extract relationships between entities from preprocessed text",
                "parameters": {
                    "text": "Preprocessed text content (required)",
                    "entities": "List of entities from NER (optional, will auto-detect if not provided)",
                    "relation_types": "List of relation types to extract (optional)",
                    "confidence_threshold": "Minimum confidence score for relations (0.0-1.0, default: 0.7)",
                    "max_relations": "Maximum number of relations to extract (default: 100)",
                },
            },
            {
                "name": "create_quadruples",
                "description": "Create quadruples from relation extraction and NER+EL results",
                "parameters": {
                    "relations": "List of relations from run_relation_extraction (required)",
                    "entities": "List of entities from run_ner_el (required)",
                    "confidence_threshold": "Minimum confidence score for quadruples (0.0-1.0, default: 0.7)",
                    "max_quadruples": "Maximum number of quadruples to create (default: 100)",
                },
            },
        ]

    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests through the agent."""
        if not self._initialized:
            return {"error": "Agent not initialized"}

        command = request.get("command", "")

        if command == "extract_triples":
            return await self._extract_triples(request)
        elif command == "detect_document_type":
            return await self._detect_document_type(request)
        elif command == "preprocess_document":
            return await self._preprocess_document(request)
        elif command == "run_ner_el":
            return await self._run_ner_el(request)
        elif command == "run_relation_extraction":
            return await self._run_relation_extraction(request)
        elif command == "create_quadruples":
            return await self._create_quadruples(request)
        else:
            return {
                "error": f"Unknown command: {command}",
                "available_commands": [
                    "extract_triples",
                    "detect_document_type",
                    "preprocess_document",
                    "run_ner_el",
                    "run_relation_extraction",
                    "create_quadruples",
                ],
            }

    async def _extract_triples(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Extract triples from text data."""
        try:
            text = request.get("text", "")
            confidence_threshold = request.get("confidence_threshold", 0.7)
            max_triples = request.get("max_triples", 100)

            if not text:
                return {"error": "Missing text parameter"}

            # Use the extract_triples tool
            result = await self._tools["extract_triples"].execute_tool(
                {
                    "text": text,
                    "confidence_threshold": confidence_threshold,
                    "max_triples": max_triples,
                }
            )

            # Insert triples into Neo4j if extraction was successful
            triples = result.get("triples", [])
            if triples:
                self._graphdb_.insert_triples(triples)

            return {"status": "success", "data": result}

        except Exception as e:
            logger.error(f"Error extracting triples: {str(e)}")
            return {"status": "error", "message": f"Error extracting triples: {str(e)}"}

    async def _detect_document_type(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Detect document type from content, filename, or MIME type."""
        try:
            document_content = request.get("document_content", "")
            filename = request.get("filename", "")
            content_type = request.get("content_type", "")
            file_path = request.get("file_path", "")

            if not document_content and not file_path:
                return {"error": "Missing document_content or file_path parameter"}

            # Use the detect_document_type tool
            result = await self._tools["detect_document_type"].execute_tool(
                {
                    "document_content": document_content,
                    "filename": filename,
                    "content_type": content_type,
                    "file_path": file_path,
                }
            )

            return {"status": "success", "data": result}

        except Exception as e:
            logger.error(f"Error detecting document type: {str(e)}")
            return {
                "status": "error",
                "message": f"Error detecting document type: {str(e)}",
            }

    async def _preprocess_document(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess document content for knowledge extraction."""
        try:
            document_content = request.get("document_content", "")
            document_type = request.get("document_type", "")
            remove_stopwords = request.get("remove_stopwords", False)
            normalize_text = request.get("normalize_text", True)
            file_path = request.get("file_path", "")

            if not document_content and not file_path:
                return {"error": "Missing document_content or file_path parameter"}

            if not document_type:
                return {"error": "Missing document_type parameter"}

            # Use the preprocess_document tool
            result = await self._tools["preprocess_document"].execute_tool(
                {
                    "document_content": document_content,
                    "document_type": document_type,
                    "remove_stopwords": remove_stopwords,
                    "normalize_text": normalize_text,
                    "file_path": file_path,
                }
            )

            return {"status": "success", "data": result}

        except Exception as e:
            logger.error(f"Error preprocessing document: {str(e)}")
            return {
                "status": "error",
                "message": f"Error preprocessing document: {str(e)}",
            }

    async def _run_ner_el(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Run Named Entity Recognition and Entity Linking on preprocessed text."""
        try:
            text = request.get("text", "")

            if not text:
                return {"error": "Missing text parameter"}

            # Placeholder implementation
            result = {
                "entities": [],
                "total_found": 0,
                "message": "Placeholder implementation",
            }

            return {"status": "success", "data": result}

        except Exception as e:
            logger.error(f"Error running NER+EL: {str(e)}")
            return {"status": "error", "message": f"Error running NER+EL: {str(e)}"}

    async def _run_relation_extraction(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relationships between entities from preprocessed text."""
        try:
            text = request.get("text", "")

            if not text:
                return {"error": "Missing text parameter"}

            # Placeholder implementation
            result = {
                "relations": [],
                "total_found": 0,
                "message": "Placeholder implementation",
            }

            return {"status": "success", "data": result}

        except Exception as e:
            logger.error(f"Error running relation extraction: {str(e)}")
            return {
                "status": "error",
                "message": f"Error running relation extraction: {str(e)}",
            }

    async def _create_quadruples(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create quadruples from relation extraction and NER+EL results."""
        try:
            relations = request.get("relations", [])
            entities = request.get("entities", [])

            if not relations:
                return {"error": "Missing relations parameter"}
            if not entities:
                return {"error": "Missing entities parameter"}

            # Placeholder implementation
            result = {
                "quadruples": [],
                "total_found": 0,
                "message": "Placeholder implementation",
            }

            return {"status": "success", "data": result}

        except Exception as e:
            logger.error(f"Error creating quadruples: {str(e)}")
            return {
                "status": "error",
                "message": f"Error creating quadruples: {str(e)}",
            }
