import logging
from typing import Dict, List, Any, Optional
from uuid import UUID
import json
import os

from datetime import datetime

from src.services.pgvector_service import PGVectorService
from ...services.neo4j_service import Neo4jService
from ...interfaces.agent import AgentInterface
from .tools.extract_triples import ExtractTriplesTool
from ...services.llm_service import llm_service
from ...services.prompt_service import prompt_service

logger = logging.getLogger(__name__)


class KnowledgeGraphRetrievalAgent(AgentInterface):
    """Knowledge graph retrieval agent"""

    def __init__(self):
        self._agent_id_str = "knowledge_graph_retrieval"
        self._uuid = None
        self.agent_id = "knowledge_graph_retrieval"
        self._name = "Knowledge Graph Retrieval Agent"
        self._description = "Retrieves data from knowledge graph. QA system over all important documents and user questions. "
        self._initialized = False
        self.category = "knowledge_management"
        self.status = "initialized"
        self._tools = {}
        self._graphdb_ = Neo4jService()
        self._vectordb_ = PGVectorService()

        # Add extract_triples tool - if becomes needed
        # self._tools["extract_triples"] = ExtractTriplesTool()

    """
	TODO:
	- route for queries for QA:
		- embed query (embed everything in questions form:
			- "What produces table grapes?"
			- "What does Sunworld produce?"
			- "What is the relationship between Sunworld and table grapes?"
		)
		- lookup in postgres
		- search in neo4j
		- return results
	"""

    async def test_neo(self):
        embedding = await llm_service.create_embedding(
            "Who produces grapes?",
            model="text-embedding-3-small",
        )
        logger.info(f"Embedding result: {embedding}")
        return {"success": True, "embedding": embedding}

        results = await self._graphdb_.test_get_data()
        logger.info(f"Retrieval result: {results}")

        return {"success": True, "results": results}

    # TODO: Fix tools setup
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return agent's capabilities."""
        return [
            {
                "name": "retrieve",
                "description": "Retrieve information from the knowledge graph based on the user's query",
                "parameters": {
                    "query": "User query to retrieve information (required)",
                    "intent": "Intent of the user query (optional)",
                    "context": "Additional context for the query (optional)",
                },
                "returnValues": {
                    "intent": "string - Classified intent of the user query",
                    "intent_confidence": "number - Confidence score for the intent classification (0.0-1.0)",
                    "extracted_entities": "array - List of entities extracted from the query with text, type, and confidence",
                    "extracted_relationships": "array - List of relationships extracted from the query",
                    # "results": "array - Retrieved information from knowledge graph (future implementation)",
                    # "metadata": "object - Additional execution metadata (future implementation)",
                },
            },
        ]

    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests through the agent."""
        if not self._initialized:
            return {"error": "Agent not initialized"}

        command = request.get("command", "")

        if command == "test_neo":
            return await self.test_neo()
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
                    "process_file_to_ner",
                    "retrieve",
                ],
            }

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the agent with configuration."""
        # Initialize tools if needed
        for tool_name, tool in self._tools.items():
            if hasattr(tool, "initialize"):
                await tool.initialize(config)

        self._initialized = True
        logger.info("KnowledgeGraphExtractionAgent initialized successfully")

    async def shutdown(self) -> None:
        """Clean up resources when shutting down."""
        self._initialized = False
        logger.info("KnowledgeGraphExtractionAgent shutdown complete")

    def get_status(self) -> Dict[str, Any]:
        """Return agent's current status."""
        return {
            "initialized": self._initialized,
            "healthy": self._initialized,
            "tools_available": list(self._tools.keys()),
            "capabilities": self.get_tools(),
        }

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
