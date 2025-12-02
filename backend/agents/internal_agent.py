"""
Faux Internal Agent - Simulates internal document processing.
"""
from uuid import UUID
from typing import Dict, Any, List, Optional
import logging
import re
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

Output format (CRITICAL - use this exact format for parsing):
CONTRACT: [filename]
SOURCE COUNTRY: [extracted from filename or document]

KEY TERMS BY TOPIC:
[Territory|Section 2.1] "EXACT QUOTED TEXT FROM DOCUMENT"
[Governing Law|Section 5.2] "EXACT QUOTED TEXT FROM DOCUMENT"
[Jurisdiction/Dispute Resolution|Section 3.1] "EXACT QUOTED TEXT FROM DOCUMENT"
[Currency & Payment|Section 4.3] "EXACT QUOTED TEXT FROM DOCUMENT"
[Taxes/VAT|Section 6.1] "EXACT QUOTED TEXT FROM DOCUMENT"
[Intellectual Property & Licensing|Section 7.2] "EXACT QUOTED TEXT FROM DOCUMENT"
[Exclusivity|Section 8.1] "EXACT QUOTED TEXT FROM DOCUMENT"
[Regulatory/Compliance|Section 9.2] "EXACT QUOTED TEXT FROM DOCUMENT"
[Term & Termination|Section 10.1] "EXACT QUOTED TEXT FROM DOCUMENT"

COUNTRY-SPECIFIC REFERENCES FOUND:
[Section 3.4] "exact quote mentioning country/region"
[Section 4.1] "exact quote mentioning country/region"

[Continue with any additional analysis or context here...]

IMPORTANT:
- Use the EXACT format: [Topic|Section X.X] "quote" for KEY TERMS BY TOPIC
- Use the EXACT format: [Section X.X] "quote" for COUNTRY-SPECIFIC REFERENCES
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
				
				# Parse structured quotes from the response
				document_name = selected_documents[0] if selected_documents else None
				structured_quotes = self._parse_structured_quotes(response, document_name)
				
				logger.info(f"      📋 Parsed {len(structured_quotes)} structured quotes")
				print(f"      📋 Parsed {len(structured_quotes)} structured quotes")
				
				return {
					"success": True,
					"data": {
						"query": query,
						"response": response,  # Raw text for orchestrator
						"source": "internal_documents",
						"structured_quotes": structured_quotes  # Parsed JSON for UI
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
	
	def _parse_structured_quotes(self, agent_text: str, document: Optional[str] = None) -> List[Dict[str, Any]]:
		"""
		Parse structured quotes from internal agent text output.
		
		Supports both formats:
		- NEW: [Topic|Section X.X] "quote" (for KEY TERMS BY TOPIC)
		- OLD: - Topic: "quote" (Section X.X) (for backward compatibility)
		- NEW: [Section X.X] "quote" (for COUNTRY-SPECIFIC REFERENCES)
		- OLD: - "quote" (Section X.X) (for backward compatibility)
		
		Args:
			agent_text: The text output from internal agent
			document: Document filename (optional, will try to extract from text)
		
		Returns:
			List of structured quote dictionaries
		"""
		quotes = []
		
		if not agent_text:
			return quotes
		
		# Extract document name if not provided
		if not document:
			doc_match = re.search(r'CONTRACT:\s*(.+)', agent_text)
			if doc_match:
				document = doc_match.group(1).strip()
		
		# NEW format patterns
		topic_pattern_new = r'\[([^\|]+)\|([^\]]+)\]\s*"([^"]+)"'
		country_pattern_new = r'\[([^\]]+)\]\s*"([^"]+)"'
		
		# OLD format patterns (backward compatibility)
		topic_pattern_old = r'-\s*([^:]+):\s*"([^"]+)"\s*\(([^)]+)\)'
		country_pattern_old = r'-\s*"([^"]+)"\s*\(([^)]+)\)'
		
		# Extract KEY TERMS BY TOPIC section
		key_terms_match = re.search(r'KEY TERMS BY TOPIC:(.*?)(?:COUNTRY-SPECIFIC|$)', agent_text, re.DOTALL)
		if key_terms_match:
			key_terms_section = key_terms_match.group(1)
			
			# Try NEW format first
			for match in re.finditer(topic_pattern_new, key_terms_section):
				topic, section, quote = match.groups()
				quotes.append({
					"document": document or "unknown",
					"topic": topic.strip(),
					"section": section.strip(),
					"quote": quote.strip(),
					"type": "key_term"
				})
			
			# Fall back to OLD format if no matches
			if not quotes or all(q.get("type") != "key_term" for q in quotes):
				for match in re.finditer(topic_pattern_old, key_terms_section):
					topic, quote, section = match.groups()
					quotes.append({
						"document": document or "unknown",
						"topic": topic.strip(),
						"section": section.strip(),
						"quote": quote.strip(),
						"type": "key_term"
					})
		
		# Extract COUNTRY-SPECIFIC REFERENCES section
		country_refs_match = re.search(r'COUNTRY-SPECIFIC REFERENCES FOUND:(.*?)(?:\[|NOTE|IMPORTANT|$)', agent_text, re.DOTALL)
		if country_refs_match:
			country_refs_section = country_refs_match.group(1)
			
			# Try NEW format first
			for match in re.finditer(country_pattern_new, country_refs_section):
				section, quote = match.groups()
				quotes.append({
					"document": document or "unknown",
					"topic": "Country-Specific Reference",
					"section": section.strip(),
					"quote": quote.strip(),
					"type": "country_specific"
				})
			
			# Fall back to OLD format
			for match in re.finditer(country_pattern_old, country_refs_section):
				quote, section = match.groups()
				quotes.append({
					"document": document or "unknown",
					"topic": "Country-Specific Reference",
					"section": section.strip(),
					"quote": quote.strip(),
					"type": "country_specific"
				})
		
		return quotes
	
	def get_status(self) -> Dict[str, Any]:
		"""Return agent status."""
		return {
			"status": "active",
			"type": "internal",
			"ollama_configured": self._ollama is not None
		}

