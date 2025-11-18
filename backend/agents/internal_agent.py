"""
Faux Internal Agent - Simulates internal document processing.
"""
from uuid import UUID
from typing import Dict, Any, List
import logging
from ..interfaces.agent import AgentInterface
from ..services.ollama_service import OllamaService

logger = logging.getLogger(__name__)


class InternalAgent(AgentInterface):
	"""Faux agent for processing internal documents (e.g., Italy contracts)."""
	
	def __init__(self):
		self._uuid: UUID = None
		self._ollama: OllamaService = None
		self._system_prompt = """You are an internal document retrieval agent that searches through an internal document database.

Your database contains:
- Contract documents from various countries (Italy, France, Germany, etc.)
- Legal agreements and terms
- Policy documents
- Compliance documentation
- Setup and implementation guides

CRITICAL: Keep responses under 300 words. Be concise but informative.

When given a query:
1. Act as if you are searching through actual internal documents
2. Reference specific document names, sections, or clauses when relevant
3. Extract and present information as if you found it in a real document
4. Be specific about contract terms, requirements, and procedures
5. If asked about a specific document (e.g., "italy-xxx document"), reference it by name and extract relevant information
6. Keep responses concise - focus on key information only

Example response style (keep it brief):
"According to the Italy-Contract-2024 document, Section 3.2 specifies that... Key requirements: 1) ... 2) ..."

Be factual, concise, and reference document sources in your responses."""
	
	@property
	def name(self) -> str:
		return "Internal Agent"
	
	@property
	def description(self) -> str:
		return "Faux agent for processing internal documents and contracts"
	
	@property
	def agent_id_str(self) -> str:
		return "internal_agent"
	
	@property
	def uuid(self) -> UUID:
		return self._uuid
	
	@uuid.setter
	def uuid(self, value: UUID):
		self._uuid = value
	
	async def initialize(self, config: Dict[str, Any]) -> None:
		"""Initialize the agent."""
		self._ollama = OllamaService(
			base_url=config.get("ollama_base_url"),
			default_model=config.get("ollama_model")
		)
	
	async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
		"""Process a query request."""
		command = request.get("command", "query")
		
		if command == "query":
			query = request.get("query", "")
			if not query:
				return {
					"success": False,
					"error": "Query is required"
				}
			
			logger.info(f"      🔵 INTERNAL AGENT: Processing query...")
			print(f"      🔵 INTERNAL AGENT: Processing query...")
			try:
				# Limit agent responses to 400 tokens (approximately 300 words)
				response = await self._ollama.generate(
					prompt=query,
					system=self._system_prompt,
					max_tokens=400
				)
				
				logger.info(f"      ✅ INTERNAL AGENT: Got response ({len(response)} chars)")
				print(f"      ✅ INTERNAL AGENT: Got response ({len(response)} chars)")
				return {
					"success": True,
					"data": {
						"query": query,
						"response": response,
						"source": "internal_documents"
					}
				}
			except Exception as e:
				error_msg = f"      ❌ INTERNAL AGENT ERROR: {str(e)}"
				logger.error(error_msg)
				print(error_msg)
				return {
					"success": False,
					"error": str(e)
				}
		else:
			return {
				"success": False,
				"error": f"Unknown command: {command}"
			}
	
	async def shutdown(self) -> None:
		"""Cleanup resources."""
		pass
	
	def get_tools(self) -> List[Dict[str, Any]]:
		"""Return available tools."""
		return [
			{
				"name": "query",
				"description": "Query internal documents for contract and legal information",
				"parameters": {
					"query": {
						"type": "string",
						"description": "The query to search internal documents"
					}
				}
			}
		]
	
	def get_status(self) -> Dict[str, Any]:
		"""Return agent status."""
		return {
			"status": "active",
			"type": "internal",
			"ollama_configured": self._ollama is not None
		}

