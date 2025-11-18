"""
Faux External Agent - Simulates external database queries (e.g., WIPO).
"""
from uuid import UUID
from typing import Dict, Any, List
import logging
from ..interfaces.agent import AgentInterface
from ..services.ollama_service import OllamaService

logger = logging.getLogger(__name__)


class ExternalAgent(AgentInterface):
	"""Faux agent for querying external databases (e.g., WIPO)."""
	
	def __init__(self):
		self._uuid: UUID = None
		self._ollama: OllamaService = None
		self._system_prompt = """You are an external database agent that queries international legal and compliance databases.

Your databases include:
- WIPO (World Intellectual Property Organization) database
- Regional compliance databases (African Union, EU regulations, etc.)
- International legal standards and requirements
- Cross-border compliance requirements
- Regional setup and implementation requirements

CRITICAL: Keep responses under 300 words. Be concise but informative.

When given a query:
1. Act as if you are querying real external databases (WIPO, regional compliance systems)
2. Provide information about international regulations, regional requirements, and compliance standards
3. Reference specific regulations, standards, or database entries when relevant
4. Focus on requirements for specific regions (e.g., Africa, Asia, Europe)
5. Provide setup procedures, compliance requirements, and regional variations
6. Keep responses concise - focus on key requirements only

Example response style (keep it brief):
"According to WIPO database entry WIPO-REG-2024-AFR-001, the requirements for setting up in Africa include... The African Union compliance standards specify... Key regional variations: ..."

Be authoritative, reference external sources, and provide specific but concise compliance information."""
	
	@property
	def name(self) -> str:
		return "External Agent"
	
	@property
	def description(self) -> str:
		return "Faux agent for querying external databases (e.g., WIPO)"
	
	@property
	def agent_id_str(self) -> str:
		return "external_agent"
	
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
			
			logger.info(f"      🟢 EXTERNAL AGENT: Processing query...")
			print(f"      🟢 EXTERNAL AGENT: Processing query...")
			try:
				# Limit agent responses to 400 tokens (approximately 300 words)
				response = await self._ollama.generate(
					prompt=query,
					system=self._system_prompt,
					max_tokens=400
				)
				
				logger.info(f"      ✅ EXTERNAL AGENT: Got response ({len(response)} chars)")
				print(f"      ✅ EXTERNAL AGENT: Got response ({len(response)} chars)")
				return {
					"success": True,
					"data": {
						"query": query,
						"response": response,
						"source": "external_database"
					}
				}
			except Exception as e:
				error_msg = f"      ❌ EXTERNAL AGENT ERROR: {str(e)}"
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
				"description": "Query external databases (e.g., WIPO) for legal and compliance information",
				"parameters": {
					"query": {
						"type": "string",
						"description": "The query to search external databases"
					}
				}
			}
		]
	
	def get_status(self) -> Dict[str, Any]:
		"""Return agent status."""
		return {
			"status": "active",
			"type": "external",
			"ollama_configured": self._ollama is not None
		}

