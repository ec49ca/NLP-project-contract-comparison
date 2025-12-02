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
		self._system_prompt = """You are a contract analysis agent that extracts structured information from contract documents.

Your job is to:
1. Read the ENTIRE contract document provided
2. Extract actual quoted text (not summaries) for 9 key topics
3. Identify country-specific references
4. Return structured, factual information

CRITICAL: Extract ACTUAL WORDS from the document. Quote the exact clause text. Do NOT summarize, abbreviate, or interpret.

Extract information for these 9 topics (if present in the document):
1. Territory - actual text about geographic scope
2. Governing Law - actual text about which laws apply
3. Jurisdiction/Dispute Resolution - actual text about courts/arbitration
4. Currency & Payment - actual text about payment terms and currency
5. Taxes/VAT - actual text about tax obligations
6. Intellectual Property & Licensing - actual text about IP rights
7. Exclusivity - actual text about exclusive rights/territories
8. Regulatory/Compliance - actual text about regulatory obligations
9. Term & Termination - actual text about contract duration and termination

For each topic found:
- Quote the EXACT clause text from the document
- Include the section reference (e.g., "Section 2.1", "Article 5", "Clause 3.2")
- Do NOT summarize or abbreviate

Also identify country-specific references:
- References to specific countries (e.g., "Italian law", "French courts", "German VAT")
- References to regional entities (e.g., "EU regulations", "European Union")
- Currency references (e.g., "Euro", "EUR", "USD")
- Geographic references (e.g., "Italy", "Rome", "Milan")

Output format:
CONTRACT: [filename]
SOURCE COUNTRY: [extracted from filename or document]

KEY TERMS BY TOPIC:
- [Topic Name]: "[EXACT QUOTED TEXT FROM DOCUMENT]" ([Section Reference])
- [Topic Name]: "[EXACT QUOTED TEXT FROM DOCUMENT]" ([Section Reference])
...

COUNTRY-SPECIFIC REFERENCES FOUND:
- "[exact quote mentioning country/region]" ([Section Reference])
- "[exact quote mentioning country/region]" ([Section Reference])
...

IMPORTANT:
- Use actual quotes from the document, not your interpretation
- Include section references when available
- If a topic is not in the document, omit it
- Be thorough - extract all relevant clauses for each topic"""
	
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
		
		# Document storage is passed separately if available
		if "document_storage" in config:
			self._document_storage = config["document_storage"]
	
	def _get_llm_service(self, request: Dict[str, Any]) -> LLMService:
		"""Get LLM service from request override or use default."""
		if "llm_service" in request:
			return request["llm_service"]
		return self._ollama
	
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
						# Extract contract ID and source country from filename
						contract_id = selected_documents[0].replace(".pdf", "") if selected_documents else "unknown"
						source_country = self._extract_country_from_filename(selected_documents[0]) if selected_documents else "unknown"
						
						# Build prompt for structured extraction
						enhanced_prompt = f"""Analyze the following contract document(s) and extract structured information.

Document(s) to analyze:
{document_context}

Extract:
1. All key terms organized by the 9 topics (Territory, Governing Law, Jurisdiction, Currency, Taxes, IP, Exclusivity, Regulatory, Term & Termination)
2. All country-specific references (Italian law, EU regulations, specific countries, currencies, etc.)

For each topic, quote the EXACT text from the document with section references.
Do NOT summarize or interpret - use the actual words from the document."""
						
						logger.info(f"      📄 Document context retrieved: {len(document_context)} characters")
						logger.info(f"      📝 Enhanced prompt length: {len(enhanced_prompt)} characters")
						print(f"      📄 Document context retrieved: {len(document_context)} characters")
						print(f"      📝 Analyzing contract: {contract_id}")
					else:
						enhanced_prompt = query
						logger.info(f"      ⚠️  No document context found for selected documents")
						print(f"      ⚠️  No document context found for selected documents")
				else:
					enhanced_prompt = query
					logger.info(f"      ℹ️  No documents selected, using original query only")
					print(f"      ℹ️  No documents selected, using original query only")
				
				# Increase token limit for thorough extraction (up to 2000 tokens for detailed extraction)
				response = await llm_service_to_use.generate(
					prompt=enhanced_prompt,
					system=self._system_prompt,
					max_tokens=2000,
					model=model_override
				)
				
				logger.info(f"      ✅ INTERNAL AGENT: Got response ({len(response)} chars)")
				print(f"      ✅ INTERNAL AGENT: Got response ({len(response)} chars)")
				
				# Log the actual response content (first 2000 chars for visibility)
				response_preview = response[:2000] if len(response) > 2000 else response
				logger.info(f"      📄 Response content:\n{response_preview}")
				print(f"      📄 Response content:\n{response_preview}")
				if len(response) > 2000:
					logger.info(f"      ... (truncated, total {len(response)} chars)")
					print(f"      ... (truncated, total {len(response)} chars)")
				
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
	
	def _extract_country_from_filename(self, filename: str) -> str:
		"""Extract source country from filename (e.g., 'Italy-111.pdf' -> 'Italy')."""
		# Remove .pdf extension
		name = filename.replace(".pdf", "").replace(".PDF", "")
		
		# Common country patterns
		countries = ["Italy", "Italy", "Japan", "Japan", "France", "Germany", "Spain", 
		            "Australia", "United States", "UK", "United Kingdom", "Canada",
		            "Brazil", "China", "India", "South Korea", "Netherlands", "Belgium",
		            "Switzerland", "Austria", "Sweden", "Norway", "Denmark", "Finland"]
		
		for country in countries:
			if country.lower() in name.lower():
				return country
		
		# If no match, try to extract first word before dash/underscore
		parts = name.replace("_", "-").split("-")
		if parts:
			return parts[0].title()
		
		return "unknown"
	
	def get_status(self) -> Dict[str, Any]:
		"""Return agent status."""
		return {
			"status": "active",
			"type": "internal",
			"ollama_configured": self._ollama is not None
		}

