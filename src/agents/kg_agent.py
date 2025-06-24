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
from ..services.neo4j_service import Neo4jService

logger = logging.getLogger(__name__)

class KnowledgeGraphAgent(AgentInterface):
	"""Knowledge graph agent for triple extraction and graph operations"""

	def __init__(self):
		self._name = "Knowledge Graph Agent"
		self._description = "Extract triples from data and perform graph operations"
		self._initialized = False
		self._tools = {}
		self._graphdb_= Neo4jService()

		# Add extract_triples tool
		self._tools["extract_triples"] = ExtractTriplesTool()

	@property
	def name(self) -> str:
		"""Agent's unique identifier."""
		return self._name

	@property
	def description(self) -> str:
		"""Brief description of the agent's purpose."""
		return self._description

	async def initialize(self, config: Dict[str, Any]) -> None:
		"""Initialize the agent with configuration."""
		# Initialize tools if needed
		for tool_name, tool in self._tools.items():
			if hasattr(tool, 'initialize'):
				await tool.initialize(config)

		self._initialized = True
		logger.info("KnowledgeGraphAgent initialized successfully")

	async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""Process incoming requests through the agent."""
		if not self._initialized:
			return {"error": "Agent not initialized"}

		command = request.get("command", "")

		if command == "extract_triples":
			return await self._extract_triples(request)
		elif command == "find_relationships":
			return await self._find_relationships(request)
		elif command == "traverse_graph":
			return await self._traverse_graph(request)
		else:
			return {
				"error": f"Unknown command: {command}",
				"available_commands": ["extract_triples", "find_relationships", "traverse_graph"]
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
			result = await self._tools["extract_triples"].execute_tool({
				"text": text,
				"confidence_threshold": confidence_threshold,
				"max_triples": max_triples
			})

			# Insert triples into Neo4j if extraction was successful
			triples = result.get("triples", [])
			if triples:
				self._graphdb_.insert_triples(triples)

			return {
				"status": "success",
				"data": result
			}

		except Exception as e:
			logger.error(f"Error extracting triples: {str(e)}")
			return {
				"status": "error",
				"message": f"Error extracting triples: {str(e)}"
			}

	async def _find_relationships(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""Find relationships between entities."""
		try:
			entity = request.get("entity", "")
			relationship_type = request.get("relationship_type", "any")
			depth = request.get("depth", 2)

			if not entity:
				return {"error": "Missing entity parameter"}

			# Placeholder implementation
			return {
				"status": "success",
				"data": {
					"entity": entity,
					"relationships": [
						{
							"type": "related_to",
							"target": f"Related Entity 1 to {entity}",
							"strength": 0.9
						},
						{
							"type": "part_of",
							"target": f"Parent Entity of {entity}",
							"strength": 0.8
						}
					],
					"depth_searched": depth
				}
			}

		except Exception as e:
			logger.error(f"Error finding relationships: {str(e)}")
			return {
				"status": "error",
				"message": f"Error finding relationships: {str(e)}"
			}

	async def _traverse_graph(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""Traverse knowledge graph from starting point."""
		try:
			start_entity = request.get("start_entity", "")
			end_entity = request.get("end_entity", "")
			max_hops = request.get("max_hops", 3)

			if not start_entity or not end_entity:
				return {"error": "Missing start_entity or end_entity parameter"}

			# Placeholder implementation
			return {
				"status": "success",
				"data": {
					"path": [
						{"entity": start_entity, "hop": 0},
						{"entity": f"Intermediate Entity", "hop": 1},
						{"entity": end_entity, "hop": 2}
					],
					"path_length": 2,
					"confidence": 0.85
				}
			}

		except Exception as e:
			logger.error(f"Error traversing graph: {str(e)}")
			return {
				"status": "error",
				"message": f"Error traversing graph: {str(e)}"
			}

	async def shutdown(self) -> None:
		"""Clean up resources when shutting down."""
		self._initialized = False
		logger.info("KnowledgeGraphAgent shutdown complete")

	def get_capabilities(self) -> Dict[str, Any]:
		"""Return agent's capabilities."""
		return {
			"extract_triples": {
				"description": "Extract triples (subject-predicate-object relationships) from unstructured text",
				"parameters": {
					"text": "Text to extract triples from (required)",
					"confidence_threshold": "Minimum confidence score for triples (0.0-1.0, default: 0.7)",
					"max_triples": "Maximum number of triples to extract (default: 100)"
				}
			},
			"find_relationships": {
				"description": "Find relationships between entities in the knowledge graph",
				"parameters": {
					"entity": "Entity to find relationships for (required)",
					"relationship_type": "Type of relationship to find (default: 'any')",
					"depth": "Search depth in the graph (default: 2)"
				}
			},
			"traverse_graph": {
				"description": "Traverse knowledge graph from starting point to target entity",
				"parameters": {
					"start_entity": "Starting entity (required)",
					"end_entity": "Target entity (required)",
					"max_hops": "Maximum number of hops allowed (default: 3)"
				}
			}
		}

	def get_status(self) -> Dict[str, Any]:
		"""Return agent's current status."""
		return {
			"initialized": self._initialized,
			"healthy": self._initialized,
			"tools_available": list(self._tools.keys()),
			"capabilities": list(self.get_capabilities().keys())
		}