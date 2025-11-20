"""
Faux Internal Agent - Simulates internal document processing.
"""
from uuid import UUID
from typing import Dict, Any, List, Optional
import logging
from ..interfaces.agent import AgentInterface
from ..services.llm_service import LLMService
from ..services.document_storage import DocumentStorage

logger = logging.getLogger(__name__)


class InternalAgent(AgentInterface):
	"""Faux agent for processing internal documents (e.g., Italy contracts)."""
	
	def __init__(self):
		self._uuid: UUID = None
		self._ollama: LLMService = None  # Keep variable name for backward compatibility
		self._document_storage: Optional[DocumentStorage] = None
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
		# Accept either llm_service instance or create from config
		if "llm_service" in config:
			self._ollama = config["llm_service"]
		else:
			# Fallback: create from config (backward compatibility)
			from ..services.llm_factory import create_llm_service
			self._ollama = create_llm_service()
	
	def _get_llm_service(self, request: Dict[str, Any]) -> LLMService:
		"""Get LLM service from request override or use default."""
		if "llm_service" in request:
			return request["llm_service"]
		return self._ollama
		# Document storage is passed separately if available
		if "document_storage" in config:
			self._document_storage = config["document_storage"]
	
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
			
			selected_documents = request.get("selected_documents", [])
			
			logger.info(f"      🔵 INTERNAL AGENT: Processing query...")
			if selected_documents:
				logger.info(f"      📄 Using selected documents: {selected_documents}")
			print(f"      🔵 INTERNAL AGENT: Processing query...")
			if selected_documents:
				print(f"      📄 Using selected documents: {selected_documents}")
			
			try:
				# Get model override and LLM service from request if provided
				model_override = request.get("model")
				llm_service_to_use = self._get_llm_service(request)
				
				# Get document context if documents are selected
				document_context = ""
				if selected_documents and self._document_storage:
					document_context = self._document_storage.get_selected_documents_text(selected_documents)
					if document_context:
						# Update prompt to include document context
						enhanced_prompt = f"""User Query: {query}

Available Documents:
{document_context}

Please answer the query based on the information in the provided documents. Reference specific documents and sections when relevant."""
						logger.info(f"      📄 Document context retrieved: {len(document_context)} characters")
						logger.info(f"      📝 Enhanced prompt length: {len(enhanced_prompt)} characters")
						print(f"      📄 Document context retrieved: {len(document_context)} characters")
						print(f"      📝 Enhanced prompt (first 500 chars): {enhanced_prompt[:500]}...")
					else:
						enhanced_prompt = query
						logger.info(f"      ⚠️  No document context found for selected documents")
						print(f"      ⚠️  No document context found for selected documents")
				else:
					enhanced_prompt = query
					logger.info(f"      ℹ️  No documents selected, using original query only")
					print(f"      ℹ️  No documents selected, using original query only")
				
				# Limit agent responses to 400 tokens (approximately 300 words)
				response = await llm_service_to_use.generate(
					prompt=enhanced_prompt,
					system=self._system_prompt,
					max_tokens=400,
					model=model_override
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

