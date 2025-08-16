import logging
from typing import Dict, List, Any, Optional
from uuid import UUID
import json
import os

from datetime import datetime

from src.services.pgvector_service import PGVectorService

# from ...services.neo4j_service import Neo4jService
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
        # self._graphdb_ = Neo4jService()
        self._db_ = PGVectorService()

        # Add extract_triples tool - if becomes needed
        # self._tools["extract_triples"] = ExtractTriplesTool()

    # TODO: add document based filtering for collection
    # TODO: vector lookup table should have documetn table for semantics for llms if they get a ton of matches
    async def basic_question_answering_retrieval(self, query: str):
        embedding = await llm_service.create_embedding(
            query, model="text-embedding-3-small"
        )
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
        results = await self._db_.vector_similarity_search(embedding_str)

        filtered_results = [
            res["full_triple_text"] for res in results if res["full_triple_text"]
        ]

        return {"success": True, "results": results}

    async def add_embedding_to_vector_db(self, query: str):
        embedding = await llm_service.create_embedding(
            query, model="text-embedding-3-small"
        )
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
        await self._db_.insert_embedding_lookup(
            embedding_str, query, query, "kg_uuid", "document_id"
        )
        return {"success": True, "results": embedding}

    async def test_pg(self):
        results = await self._db_.get_all_embeddings_and_kg_uuids()
        return {"success": True, "results": results}

    async def test_neo(self):
        # test embeddings
        embedding = await llm_service.create_embedding(
            "Sunworld Inc. grants license to PartyX?",
            model="text-embedding-3-small",
        )

        embedding2 = await llm_service.create_embedding(
            "what grants license to party x?",
            model="text-embedding-3-small",
        )

        # Uncomment below to clear the database and vector lookup table
        # await self._graphdb_.clear_database()
        # await self._db_.initialize()
        # await self._db_.clear_kg_vector_lookup_table()

        await self._db_.initialize()
        # results = await self._graphdb_.test_get_data()
        return {"success": True, "results": embedding}

    # TODO: Fix tools setup
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return agent's capabilities."""
        # TODO: find ways to simplify input query to get it into simple qa
        return [
            {
                "name": "basic_question_answering_retrieval",
                "description": "Retrieves information from knowledge graph triples using vector lookup given a simple query that wants to know about a specific entity or relationship (ex: What produces grapes?)",
                "parameters": {
                    "query": "User query to retrieve information (required) - Simple question in question form:\
						- If looking for subject of triple, phrase questions as 'What [verb] [object]?'\
						- If looking for object of triple, phrase questions as 'What does [subject] [verb]?' or '[subject] [verb] what?'\
						- If looking for relationship between two entities, phrase questions as 'What is the relationship between [subject] and [object]?'"
                },
                "returnValues": {
                    "results": "array - List of triples (in full text form: 'Sunworld produces grapes') retrieved from the knowledge graph extraction",
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
        elif command == "test_pg":
            return await self.test_pg()
        elif command == "basic_question_answering_retrieval":
            return await self.basic_question_answering_retrieval(
                request.get("query", "")
            )
        elif command == "add_embedding":
            return await self.add_embedding_to_vector_db(request.get("query", ""))
        else:
            return {
                "error": f"Unknown command: {command}",
                "available_commands": [
                    "basic_question_answering_retrieval",
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
