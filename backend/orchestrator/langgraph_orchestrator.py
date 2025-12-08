"""
LangGraph-based orchestrator for parallel agent execution with one agent call per document.
"""
import logging
from typing import Dict, Any, List, Optional, TypedDict
from uuid import UUID
import asyncio

logger = logging.getLogger(__name__)

try:
	from langgraph.graph import StateGraph, END
	LANGGRAPH_IMPORTED = True
except ImportError:
	LANGGRAPH_IMPORTED = False
	logger.warning("LangGraph not installed. Install with: pip install langgraph langchain-core")

from ..services.llm_service import LLMService
from ..registry.registry import AgentRegistrySystem
from ..services.document_storage import DocumentStorage


class OrchestratorState(TypedDict):
	"""State schema for LangGraph orchestrator."""
	# Input
	user_query: str
	selected_documents: List[str]  # Manually selected documents
	available_documents: List[str]  # All available documents
	model_override: Optional[str]
	llm_service_override: Optional[LLMService]

	# Analysis (internal state between nodes)
	_analysis: Dict[str, Any]  # Analysis results: needs_internal, needs_external, matched_documents

	# Planning
	agent_call_plan: List[Dict[str, Any]]  # List of agent call tasks
	# Format: [{"agent_type": "internal_agent", "document": "file.pdf", "query": "...", "task_id": "..."}, ...]

	# Execution
	agent_results: Dict[str, Dict[str, Any]]  # Results by task_id
	# Format: {"task_1": {"success": True, "data": {...}}, ...}

	# Output
	final_response: Optional[str]
	agents_used: List[str]
	internal_results: List[Dict[str, Any]]  # List of results from internal agents (one per document)
	external_results: Optional[Dict[str, Any]]
	structured_quotes: List[Dict[str, Any]]  # Structured quotes extracted from internal agents for UI
	structured_chunks: List[Dict[str, Any]]  # Structured chunks extracted from external agent for UI
	error: Optional[str]


if not LANGGRAPH_IMPORTED:
	# Create a dummy class if LangGraph is not available
	class LangGraphOrchestrator:
		def __init__(self, *args, **kwargs):
			raise ImportError("LangGraph is not installed. Install with: pip install langgraph langchain-core")
else:
	class LangGraphOrchestrator:
		"""LangGraph-based orchestrator with parallel agent execution - one agent call per document."""

		def __init__(self, registry: AgentRegistrySystem, llm_service: LLMService, document_storage: Optional[DocumentStorage] = None):
			"""
			Initialize LangGraph orchestrator.

			Args:
				registry: Agent registry system
				llm_service: LLM service for making LLM calls
				document_storage: Optional document storage service
			"""
			self.registry = registry
			self.llm_service = llm_service
			self.document_storage = document_storage

			# Store for use in nodes
			self._registry = registry
			self._document_storage = document_storage

			# Prompts (define before building graph)
			self._analysis_prompt = """You are an intelligent query analyzer for a contract and compliance system. Given a user query and available documents, determine which agents are needed and which documents to process.

Available agents:
- internal_agent: Analyzes internal documents (contracts, agreements, policies from various countries). Use this if the query mentions documents, compares documents, asks about contract terms, or analyzes agreements.
- external_agent: Queries external databases (WIPO, regional compliance databases, international regulations). Use this if the query asks about external regulations, compliance standards, or regional requirements not in the documents.

{manual_selection_info}

Available Documents:
{document_list}

Analyze the user query and respond with JSON:
{{
  "needs_internal_agent": true/false,
  "needs_external_agent": true/false,
  "matched_documents": ["filename1.pdf", "filename2.pdf"] or [] (list of document filenames that match what the user mentioned),
  "reasoning": "one sentence explanation"
}}

CRITICAL RULES:
- If the user has manually selected documents → ALWAYS set needs_internal_agent to true
- If the query mentions comparing documents, analyzing documents, or asking about document content → ALWAYS set needs_internal_agent to true
- If the query mentions specific document names (e.g., "japan-111", "italy document") → match them to available documents in the list above
- Match document names flexibly: "japan-111" should match "japan-111.pdf", "japan-111-contract.pdf", etc.
- If query asks about regional compliance or external regulations (not in documents) → needs external_agent
- If query asks about adapting/setting up something from one region to another → needs BOTH agents

Examples:
- "compare this document to japan-111" → needs_internal_agent: true, matched_documents: [manually selected doc] + ["japan-111.pdf"]
- "tell me about this document" (with manual selection) → needs_internal_agent: true, matched_documents: [manually selected doc]
- "what are compliance requirements in Africa?" → needs_external_agent: true"""

			# Synthesis prompts for different scenarios
			# Scenario 1: Internal-only (1+ internal agent outputs)
			self._synthesis_prompt_internal_only = """You are a paralegal analyst reviewing contract documents. Your job is to provide a comprehensive, detailed analysis report formatted for easy scanning and readability.

You receive structured contract analysis data from internal agent calls (one per document, with actual quoted clauses organized by topic). Your task is to analyze, interpret, and report on these findings like a paralegal would.

CRITICAL FORMATTING REQUIREMENTS:
- Use Markdown formatting throughout
- Use **bold** for emphasis on key terms, document names, and important findings
- Use bullet points with `-` (dash) for lists
- Use ## for main section headers, ### for subsections
- Keep paragraphs short (2-3 sentences max)
- Use > blockquotes for actual quoted text from documents
- Use tables for side-by-side comparisons when helpful

Given the user's original query and structured results from internal agents, provide:

## Executive Summary

**Documents Analyzed:** [List all documents analyzed]

**Key Findings:**
- [Bullet point 1]
- [Bullet point 2]
- [Bullet point 3]

**Main Areas of Concern:**
- [Bullet point 1]
- [Bullet point 2]

## Topic-by-Topic Analysis

For each topic found (Territory, Governing Law, Jurisdiction, Currency, Taxes, IP, Exclusivity, Regulatory, Term & Termination, Product/Manufacturing):

### [Topic Name]

**{{Document Name 1}}:**
> "[actual quoted text]" (Section X.X)

{{If multiple documents, add:}}

**{{Document Name 2}}:**
> "[actual quoted text]" (Section Y.Y)

**Key Differences:** {{if multiple documents}}
- [Difference 1 with implications]
- [Difference 2 with implications]

**Impact:**
- [How this affects operations]
- [What needs attention]

## Country-Specific Elements

For each document:

### [Document Name]

**Country-Specific References:**
- **Element 1:** "[quote]" (Section X.X) - [Why it's country-specific]
- **Element 2:** "[quote]" (Section Y.Y) - [Why it's country-specific]

## Recommendations

**Action Items:**
- **Priority 1:** [Specific action] - [Why it matters]
- **Priority 2:** [Specific action] - [Why it matters]

**Risk Areas:**
- [Risk 1] - [Mitigation]
- [Risk 2] - [Mitigation]

CRITICAL: 
- Use ONLY information from the agent results provided
- Quote actual text from documents, do NOT make up quotes
- If only one document, focus on describing that document in detail
- If multiple documents, compare them side-by-side

Original User Query: {user_query}

Agent Results:
{agent_results}"""

			# Scenario 2: External-only (1+ external agent outputs)
			self._synthesis_prompt_external_only = """You are a compliance and regulatory analyst. Your job is to provide clear, actionable compliance and regulatory information based on external database searches (WIPO, regional compliance databases, international regulations).

You receive information from external agent searches that query WIPO documents, regional compliance databases, and international regulations. Your task is to synthesize this information into a clear, useful response.

CRITICAL FORMATTING REQUIREMENTS:
- Use Markdown formatting throughout
- Use **bold** for emphasis on key terms, regulations, and important findings
- Use bullet points with `-` (dash) for lists
- Use ## for main section headers, ### for subsections
- Keep paragraphs short (2-3 sentences max)
- Use > blockquotes for actual quoted text from sources
- Cite sources when available (file names, chunk IDs)

Given the user's original query and results from external agent searches, provide:

## Executive Summary

**Query:** [User's question]

**Key Findings:**
- [Bullet point 1 - main compliance requirement or regulation found]
- [Bullet point 2 - regional variation or important detail]
- [Bullet point 3 - actionable insight]

## Compliance Requirements

### [Main Topic/Region]

**Requirements:**
- [Requirement 1 with details]
- [Requirement 2 with details]

**Regulatory Bodies:**
- [Relevant regulatory body or standard]
- [Additional bodies if mentioned]

**Legal Framework:**
- [Key legal framework or standard]
- [Additional frameworks if relevant]

## Regional Variations

{{If multiple regions or countries are mentioned:}}

### [Region/Country 1]
- [Specific requirement or variation]

### [Region/Country 2]
- [Specific requirement or variation]

## Sources

**Information Sources:**
- [Source 1 - file name and chunk if available]
- [Source 2 - file name and chunk if available]

## Recommendations

**Action Items:**
- **Priority 1:** [Specific action based on compliance requirements]
- **Priority 2:** [Additional action if needed]

**Important Considerations:**
- [Consideration 1]
- [Consideration 2]

CRITICAL: 
- Use ONLY information from the external agent results provided
- Do NOT make up regulations or requirements
- If sources are cited in the agent results, include them
- Focus on answering the user's specific query

Original User Query: {user_query}

Agent Results:
{agent_results}"""

			# Scenario 3: Both internal and external (internal as base, external to help answer)
			self._synthesis_prompt_both = """You are a paralegal analyst reviewing contract documents with external compliance context. Your job is to provide a comprehensive analysis that combines internal contract information with external compliance requirements.

You receive:
1. **Internal Agent Results**: Structured contract analysis from actual contract documents (e.g., japan-111.pdf, Italy-111.pdf). These are REAL CONTRACTS with actual clauses.
2. **External Agent Results**: Compliance and regulatory information from WIPO/external databases. These are REFERENCE SOURCES (e.g., wipo_pub_903.pdf is a WIPO publication, NOT a contract).

CRITICAL DISTINCTION:
- Internal agent results = ACTUAL CONTRACT DOCUMENTS (contracts, agreements)
- External agent results = COMPLIANCE/REGULATORY INFORMATION from WIPO databases (NOT contracts)
- WIPO document names (like wipo_pub_903.pdf) are REFERENCE SOURCES, NOT contracts to compare
- Do NOT treat WIPO documents as "Contract B" or compare them as contracts
- WIPO documents provide compliance requirements and standards, not contract clauses

Your task is to analyze the ACTUAL CONTRACTS in the context of external compliance requirements and provide actionable insights.

CRITICAL FORMATTING REQUIREMENTS:
- Use Markdown formatting throughout
- Use **bold** for emphasis on key terms, document names, and important findings
- Use bullet points with `-` (dash) for lists
- Use ## for main section headers, ### for subsections
- Keep paragraphs short (2-3 sentences max)
- Use > blockquotes for actual quoted text from contracts
- Use tables for side-by-side comparisons when helpful

Given the user's original query and results from both internal and external agents, provide:

## Executive Summary

**Contract Documents Analyzed:** [List ONLY the actual contract documents from internal agent, e.g., japan-111.pdf]

**Compliance Context:** [Brief summary of external compliance/regulatory information found from WIPO/external databases]

**Key Findings:**
- [Bullet point 1 - contract finding]
- [Bullet point 2 - compliance alignment or gap]
- [Bullet point 3 - actionable insight]

**Main Areas of Concern:**
- [Compliance gap or risk area]
- [Additional concern]

## Contract Analysis with Compliance Context

For each relevant topic (Territory, Governing Law, Jurisdiction, Currency, Taxes, IP, Exclusivity, Regulatory, Term & Termination):

### [Topic Name]

**Contract Provisions:**
{{For each ACTUAL CONTRACT document from internal agent:}}

**{{Contract Document Name}} (e.g., japan-111.pdf):**
> "[actual quoted text from contract]" (Section X.X)

**Compliance Requirements (from WIPO/external sources):**
- [External compliance requirement relevant to this topic - from external agent results]
- [Regulatory standard or requirement]

**Compliance Analysis:**
- [Whether contract provisions meet compliance requirements]
- [Gaps or areas where contract differs from compliance standards]
- [What needs to be addressed]

**Impact:**
- [How this affects operations]
- [What needs attention]

## Compliance Alignment Assessment

### Areas of Alignment
- [Contract clause/topic] - [How it aligns with external compliance requirements]

### Areas Requiring Attention
- [Contract clause/topic] - [Gap or non-compliance issue] - [What needs to change to meet compliance]

## Recommendations

**Action Items:**
- **Priority 1:** [Specific action to address compliance] - [Why it matters]
- **Priority 2:** [Additional action] - [Why it matters]

**Risk Areas:**
- [Compliance risk] - [Mitigation strategy]

**Compliance Considerations:**
- [Consideration 1 based on external requirements]
- [Consideration 2]

CRITICAL RULES: 
- Use internal agent results as the BASE (actual contract content from real contract documents)
- Use external agent results to PROVIDE COMPLIANCE CONTEXT (regulations, standards, requirements)
- Do NOT make up contract quotes - use only what's in internal agent results
- Do NOT make up compliance requirements - use only what's in external agent results
- Do NOT treat WIPO document names (wipo_pub_*.pdf) as contracts - they are reference sources
- Do NOT create "Contract A vs Contract B" comparisons using WIPO documents
- Focus on how the ACTUAL CONTRACTS relate to external compliance standards

Original User Query: {user_query}

Agent Results:
{agent_results}"""

			self._query_generation_prompt = """You are an intelligent query optimizer for contract analysis. Given a user's original query and a specific document, generate an optimized extraction query for that SINGLE document.

Original User Query: {user_query}
Document to analyze: {document}

CRITICAL: This agent call will ONLY have access to {document}. It cannot compare to other documents or access other files.

Your task is to intelligently parse the user query and determine what information to extract from {document}:

1. **Parse the user query to identify document-specific requests:**
   - Look for phrases that reference specific documents (e.g., "this document", "italy document", "japan document", document names)
   - If the query has multiple parts for different documents, identify which part applies to {document}
   - If the query mentions "{document}" or references that match {document}, use that specific part
   - If the query says "this document" and {document} is the manually selected document, use the part about "this document"
   - If the query asks for the same thing from all documents, use that for {document}

2. **Generate a focused extraction query that:**
   - Extracts ONLY the information requested for {document} based on the parsed query
   - If the query asks about "transportation" for {document}, extract ONLY transportation/delivery/territory information
   - If the query asks about "product" for {document}, extract ONLY product-related information
   - If the query asks about "payment" for {document}, extract ONLY payment/currency information
   - If the query is general or asks to compare, extract all relevant key terms organized by topic (Territory, Governing Law, Jurisdiction, Currency, Taxes, IP, Exclusivity, Regulatory, Term & Termination)
   - Do NOT extract information that wasn't requested for {document}

IMPORTANT: 
- Parse the user query carefully to identify which part applies to {document}
- Extract ONLY what the user asked for regarding {document}
- Do NOT extract all topics if the query asks for specific information
- Do NOT ask to compare or reference other documents - this agent only sees {document}

Examples:
- User: "tell me about this document's transportation agreement, and tell me about japan document's actual product", Document: Italy-111.pdf (manually selected) → "Extract transportation and delivery terms from Italy-111.pdf"
- User: "tell me about this document's transportation agreement, and tell me about japan document's actual product", Document: japan-111.pdf → "Extract product information and manufacturing details from japan-111.pdf"
- User: "Give me compliance for Italy and delivery for Japan", Document: Italy-111.pdf → "Extract compliance and regulatory terms from Italy-111.pdf"
- User: "Give me compliance for Italy and delivery for Japan", Document: japan-111.pdf → "Extract delivery and territory terms from japan-111.pdf"
- User: "What are the payment terms in both documents?", Document: Italy-111.pdf → "Extract payment and currency terms from Italy-111.pdf"
- User: "Compare Italy and Japan", Document: Italy-111.pdf → "Extract all key terms and country-specific references from Italy-111.pdf organized by topic"

Respond with ONLY the optimized query text, no JSON, no explanation."""

			self._synthesis_prompt = """You are a paralegal analyst reviewing contract documents and compliance requirements. Your job is to provide a comprehensive, detailed analysis report formatted for easy scanning and readability.

You receive structured contract analysis data from multiple internal agent calls (one per document, with actual quoted clauses organized by topic) and external compliance information. Your task is to analyze, interpret, and report on these findings like a paralegal would.

CRITICAL FORMATTING REQUIREMENTS:
- Use Markdown formatting throughout
- Use **bold** for emphasis on key terms, document names, and important findings
- Use bullet points (•) instead of long paragraphs wherever possible
- Use ## for main section headers, ### for subsections
- Keep paragraphs short (2-3 sentences max)
- Use > blockquotes for actual quoted text from documents
- Use tables for side-by-side comparisons when helpful

Given the user's original query and structured results from agents, provide:

## Executive Summary

**Documents Analyzed:** [List documents]

**Key Findings:**
- [Bullet point 1]
- [Bullet point 2]
- [Bullet point 3]

**Main Areas of Concern:**
- [Bullet point 1]
- [Bullet point 2]

## Topic-by-Topic Analysis

For each topic found (Territory, Governing Law, Jurisdiction, Currency, Taxes, IP, Exclusivity, Regulatory, Term & Termination):

### [Topic Name]

**Contract A ([document name]):**
> "[actual quoted text]" (Section X.X)

**Contract B ([document name]):**
> "[actual quoted text]" (Section Y.Y)

**Key Differences:**
- [Difference 1 with implications]
- [Difference 2 with implications]

**Impact:**
- [How this affects operations]
- [What needs attention]

## Country-Specific Elements

### [Document Name]

**Country-Specific References:**
- **Element 1:** "[quote]" (Section X.X) - [Why it's country-specific]
- **Element 2:** "[quote]" (Section Y.Y) - [Why it's country-specific]

**Adaptation Requirements:**
- [What needs to change]
- [Specific modifications needed]

## Recommendations

**Action Items:**
- **Priority 1:** [Specific action] - [Why it matters]
- **Priority 2:** [Specific action] - [Why it matters]

**Risk Areas:**
- [Risk 1] - [Mitigation]
- [Risk 2] - [Mitigation]

**Compliance Considerations:**
- [Consideration 1]
- [Consideration 2]

CRITICAL FORMATTING: 
- Use markdown list syntax with `-` (dash) for ALL bullet points, NOT the bullet character (•)
- Keep paragraphs SHORT (2-3 sentences max)
- Use **bold** for emphasis on key terms, document names, and priorities
- Use > blockquotes for all quoted text from documents
- Use proper markdown: `-` for lists, `**text**` for bold, `##` for headers
- Be specific and actionable

Original User Query: {user_query}

Agent Results:
{agent_results}"""

			# Build the graph
			self.graph = self._build_graph()

		def _build_graph(self) -> StateGraph:
			"""Build the LangGraph state graph."""
			graph = StateGraph(OrchestratorState)

			# Add nodes
			graph.add_node("analyze_query", self._analyze_query_node)
			graph.add_node("plan_agent_calls", self._plan_agent_calls_node)
			graph.add_node("execute_agents", self._execute_agents_node)
			graph.add_node("synthesize_results", self._synthesize_results_node)

			# Define edges
			graph.set_entry_point("analyze_query")
			graph.add_edge("analyze_query", "plan_agent_calls")
			graph.add_edge("plan_agent_calls", "execute_agents")
			graph.add_edge("execute_agents", "synthesize_results")
			graph.add_edge("synthesize_results", END)

			return graph.compile()

		async def _analyze_query_node(self, state: OrchestratorState) -> Dict[str, Any]:
			"""Analyze the query and determine which agents are needed and which documents to process."""
			user_query = state["user_query"]
			selected_documents = state.get("selected_documents", [])
			available_documents = state.get("available_documents", [])
			llm_service = state.get("llm_service_override") or self.llm_service
			model = state.get("model_override")

			logger.info("🔍 STEP 1: Analyzing query and determining which agents to use...")
			print("🔍 STEP 1: Analyzing query and determining which agents to use...")

			# Build document list string
			if available_documents:
				document_list_str = "\n".join([f"- {doc}" for doc in available_documents])
			else:
				document_list_str = "No documents available"

			# Build manual selection info
			if selected_documents:
				manual_selection_str = f"Manually Selected Documents: {selected_documents}\n\nIMPORTANT: The user has already selected these documents. Use them as the PRIMARY documents. Only auto-detect ADDITIONAL documents if the query explicitly mentions other documents by name."
			else:
				manual_selection_str = "Manually Selected Documents: None\n\nThe user has not manually selected any documents. Auto-detect documents from the query if mentioned."

			# Build prompt
			prompt = self._analysis_prompt.format(
				manual_selection_info=manual_selection_str,
				document_list=document_list_str
			)

			try:
				analysis_result = await llm_service.generate_json(
					prompt=f"User query: {user_query}",
					system=prompt,
					model=model
				)

				needs_internal = analysis_result.get("needs_internal_agent", False)
				needs_external = analysis_result.get("needs_external_agent", False)
				matched_documents = analysis_result.get("matched_documents", [])

				# Log what LLM returned
				logger.info(f"   🤖 LLM returned matched_documents: {matched_documents}")
				print(f"   🤖 LLM returned matched_documents: {matched_documents}")

				# CRITICAL: If user manually selected documents, we ALWAYS need internal agent
				if selected_documents and not needs_internal:
					logger.info(f"   ⚠️  LLM said no internal agent, but documents are manually selected. Overriding to True.")
					print(f"   ⚠️  LLM said no internal agent, but documents are manually selected. Overriding to True.")
					needs_internal = True

				# CRITICAL: If query mentions "documents" (plural) or "both documents", we need internal agent
				query_lower = user_query.lower()
				if not needs_internal and ("documents" in query_lower or "document" in query_lower):
					# Check if it's a document-related query (not just a generic mention)
					document_keywords = ["both documents", "all documents", "these documents", "the documents", 
										"document", "contract", "agreement", "pdf", "file"]
					if any(keyword in query_lower for keyword in document_keywords):
						logger.info(f"   ⚠️  Query mentions documents but LLM said no internal agent. Overriding to True.")
						print(f"   ⚠️  Query mentions documents but LLM said no internal agent. Overriding to True.")
						needs_internal = True

				# Only use fallback matching if LLM didn't return any matches AND we need internal agent
				# Handle three scenarios:
				# 1. Manual selection + query mentions other docs → use selected + detect additional from query
				# 2. Manual selection + query doesn't mention others → use only selected (no fallback)
				# 3. No manual selection → use fallback matching to detect from query
				if needs_internal and not matched_documents:
					if selected_documents:
						# Scenario 1 or 2: Documents manually selected
						# Try to find additional documents explicitly mentioned in query (e.g., "japan document")
						# But don't match ALL documents if query just says "documents"
						logger.info(f"   📋 Documents manually selected: {selected_documents}")
						print(f"   📋 Documents manually selected: {selected_documents}")
						
						# Try to match specific documents mentioned in query (by country name or filename)
						for doc in available_documents:
							# Skip if already manually selected
							if doc in selected_documents:
								continue
							
							# Extract key parts of document name for matching
							doc_name_lower = doc.lower().replace(".pdf", "").replace("-", " ").replace("_", " ")
							# Only match on country names (words longer than 4 chars), not numbers
							doc_keywords = [kw for kw in doc_name_lower.split() if len(kw) > 4]
							
							# Check if country name or document name appears in query
							if any(keyword in query_lower for keyword in doc_keywords):
								matched_documents.append(doc)
								logger.info(f"   🔍 Fallback matching: '{doc}' matched from query (country name: {doc_keywords})")
								print(f"   🔍 Fallback matching: '{doc}' matched from query (country name: {doc_keywords})")
						
						# Don't match ALL documents if query just says "documents" when documents are manually selected
						# This prevents adding unwanted documents in scenario 2
					else:
						# Scenario 3: No manual selection - use full fallback matching
						logger.info(f"   🔍 LLM didn't match any documents, using fallback matching...")
						print(f"   🔍 LLM didn't match any documents, using fallback matching...")
						
						# Special case: if query says "both documents" and we have exactly 2 documents, match both
						if "both documents" in query_lower and len(available_documents) == 2:
							matched_documents = available_documents.copy()
							logger.info(f"   🔍 Fallback matching: 'both documents' detected, matching all 2 available documents")
							print(f"   🔍 Fallback matching: 'both documents' detected, matching all 2 available documents")
						else:
							# Try to match by country name or document name
							for doc in available_documents:
								# Extract key parts of document name for matching
								doc_name_lower = doc.lower().replace(".pdf", "").replace("-", " ").replace("_", " ")
								# Only match on country names (words longer than 4 chars), not numbers
								doc_keywords = [kw for kw in doc_name_lower.split() if len(kw) > 4]
								
								# Check if country name appears in query
								if any(keyword in query_lower for keyword in doc_keywords):
									matched_documents.append(doc)
									logger.info(f"   🔍 Fallback matching: '{doc}' matched from query (country name: {doc_keywords})")
									print(f"   🔍 Fallback matching: '{doc}' matched from query (country name: {doc_keywords})")
						
						# If still no matches and query mentions "documents" (plural), match all available documents
						# ONLY if no documents were manually selected
						if not matched_documents and ("documents" in query_lower or "both documents" in query_lower):
							if len(available_documents) > 0:
								matched_documents = available_documents.copy()
								logger.info(f"   🔍 Fallback matching: Query mentions 'documents' but no specific match, using all available documents: {matched_documents}")
								print(f"   🔍 Fallback matching: Query mentions 'documents' but no specific match, using all available documents: {matched_documents}")

				# Combine manual + auto-detected documents
				final_documents = list(set(selected_documents or []))
				if matched_documents:
					valid_matched = [doc for doc in matched_documents if doc in available_documents]
					new_docs = [doc for doc in valid_matched if doc not in final_documents]
					final_documents.extend(new_docs)
					final_documents = list(set(final_documents))

					if new_docs:
						logger.info(f"   📄 Auto-detected additional documents: {new_docs}")
						print(f"   📄 Auto-detected additional documents: {new_docs}")

				logger.info(f"✅ Query analysis complete!")
				logger.info(f"   Needs internal agent: {needs_internal}")
				logger.info(f"   Needs external agent: {needs_external}")
				logger.info(f"   Final documents: {final_documents}")
				print(f"✅ Query analysis complete!")
				print(f"   Needs internal agent: {needs_internal}")
				print(f"   Needs external agent: {needs_external}")
				print(f"   Final documents: {final_documents}\n")

				return {
					"selected_documents": final_documents,
					"agent_call_plan": [],  # Will be filled in next node
					"_analysis": {
						"needs_internal": needs_internal,
						"needs_external": needs_external,
						"matched_documents": final_documents
					}
				}

			except Exception as e:
				import traceback
				error_msg = f"❌ ERROR in query analysis: {str(e)}\n{traceback.format_exc()}"
				logger.error(error_msg)
				print(error_msg)
				return {"error": f"Failed to analyze query: {str(e)}"}

		async def _plan_agent_calls_node(self, state: OrchestratorState) -> Dict[str, Any]:
			"""Plan agent calls - create ONE agent call per document (not one call with multiple documents)."""
			user_query = state["user_query"]
			selected_documents = state.get("selected_documents", [])
			analysis = state.get("_analysis", {})
			llm_service = state.get("llm_service_override") or self.llm_service
			model = state.get("model_override")

			logger.info("📋 STEP 2: Planning agent calls (one call per document)...")
			print("📋 STEP 2: Planning agent calls (one call per document)...")

			agent_call_plan = []
			task_id_counter = 1

			# Get documents from analysis (which includes manually selected + auto-detected)
			documents_to_process = analysis.get("matched_documents", selected_documents)
			if not documents_to_process:
				documents_to_process = selected_documents

			# Debug logging
			logger.info(f"   🔍 Debug: analysis = {analysis}")
			logger.info(f"   🔍 Debug: needs_internal = {analysis.get('needs_internal')}")
			logger.info(f"   🔍 Debug: documents_to_process = {documents_to_process}")
			logger.info(f"   🔍 Debug: selected_documents (from state) = {selected_documents}")
			print(f"   🔍 Debug: analysis = {analysis}")
			print(f"   🔍 Debug: needs_internal = {analysis.get('needs_internal')}")
			print(f"   🔍 Debug: documents_to_process = {documents_to_process}")
			print(f"   🔍 Debug: selected_documents (from state) = {selected_documents}")

			# Create ONE internal agent call PER document (not one call with all documents)
			if analysis.get("needs_internal") and documents_to_process:
				for doc in documents_to_process:
					# Generate document-specific query for this single document
					try:
						query_prompt = self._query_generation_prompt.format(
							user_query=user_query,
							document=doc
						)

						doc_specific_query = await llm_service.generate(
							prompt=query_prompt,
							max_tokens=150,
							model=model
						)

						# Clean up query (remove quotes, extra text)
						doc_specific_query = doc_specific_query.strip().strip('"').strip("'")

						task_id = f"internal_{task_id_counter}"
						agent_call_plan.append({
							"task_id": task_id,
							"agent_type": "internal_agent",
							"document": doc,  # Single document per call
							"query": doc_specific_query
						})
						task_id_counter += 1

						logger.info(f"   📄 Planned internal agent call for {doc}")
						logger.info(f"      Generated Query (FULL): {doc_specific_query}")
						print(f"   📄 Planned internal agent call for {doc}")
						print(f"      Generated Query (FULL): {doc_specific_query}")

					except Exception as e:
						logger.warning(f"   ⚠️  Failed to generate query for {doc}: {e}")
						print(f"   ⚠️  Failed to generate query for {doc}: {e}")
						# Fallback to original query
						task_id = f"internal_{task_id_counter}"
						agent_call_plan.append({
							"task_id": task_id,
							"agent_type": "internal_agent",
							"document": doc,
							"query": user_query
						})
						task_id_counter += 1

			# Create external agent call if needed
			if analysis.get("needs_external"):
				# Generate external agent query
				try:
					external_query_prompt = f"""Given the user query: "{user_query}"

Generate a focused query (under 100 words) for the external agent to find practical drafting guidance, best practices, or helpful recommendations from WIPO documents.

Focus on practical advice and improvements, not complex legal theory. Frame it as "how to improve" or "best practices for" rather than "compliance requirements."

Respond with ONLY the query text, no JSON, no explanation."""

					external_query = await llm_service.generate(
						prompt=external_query_prompt,
						max_tokens=150,
						model=model
					)
					external_query = external_query.strip().strip('"').strip("'")

				except Exception as e:
					logger.warning(f"   ⚠️  Failed to generate external query: {e}")
					external_query = user_query

				task_id = f"external_{task_id_counter}"
				agent_call_plan.append({
					"task_id": task_id,
					"agent_type": "external_agent",
					"document": None,  # External agent doesn't use documents
					"query": external_query
				})

				logger.info(f"   🌐 Planned external agent call")
				logger.info(f"      Generated Query (FULL): {external_query}")
				print(f"   🌐 Planned external agent call")
				print(f"      Generated Query (FULL): {external_query}")

			logger.info(f"✅ Agent call planning complete! {len(agent_call_plan)} tasks planned\n")
			print(f"✅ Agent call planning complete! {len(agent_call_plan)} tasks planned\n")

			return {"agent_call_plan": agent_call_plan, "agent_results": {}}

		async def _execute_agents_node(self, state: OrchestratorState) -> Dict[str, Any]:
			"""Execute all agent calls in parallel - each internal agent processes ONE document."""
			agent_call_plan = state.get("agent_call_plan", [])
			model_override = state.get("model_override")
			llm_service_override = state.get("llm_service_override")

			if not agent_call_plan:
				logger.warning("   ⚠️  No agent calls planned")
				print("   ⚠️  No agent calls planned")
				return {"agent_results": {}}

			logger.info(f"🤖 STEP 3: Executing {len(agent_call_plan)} agent call(s) in parallel...")
			print(f"🤖 STEP 3: Executing {len(agent_call_plan)} agent call(s) in parallel...")

			async def execute_single_agent(task: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
				"""Execute a single agent call."""
				task_id = task["task_id"]
				agent_type = task["agent_type"]
				query = task["query"]
				document = task.get("document")  # Single document per call

				try:
					logger.info(f"   → Executing {task_id} ({agent_type})...")
					print(f"   → Executing {task_id} ({agent_type})...")

					# Find agent
					agent = await self._find_agent_by_name(agent_type)
					if not agent:
						return task_id, {"success": False, "error": f"Agent {agent_type} not found"}

					# Prepare request - ONE document per call
					request_data = {
						"command": "query",
						"query": query
					}

					if agent_type == "internal_agent" and document:
						# Send only ONE document per call
						request_data["selected_documents"] = [document]
						logger.info(f"      📄 Document: {document}")
						print(f"      📄 Document: {document}")

					if model_override:
						request_data["model"] = model_override
					if llm_service_override:
						request_data["llm_service"] = llm_service_override

					# Log full request data being sent to agent
					logger.info(f"      📤 Sending to {agent_type}:")
					logger.info(f"         Request Data: {request_data}")
					print(f"      📤 Sending to {agent_type}:")
					print(f"         Request Data: {request_data}")

					# Execute agent
					result = await agent.process_request(request_data)

					if result.get("success"):
						logger.info(f"   ✅ {task_id} completed successfully")
						print(f"   ✅ {task_id} completed successfully")
					else:
						logger.warning(f"   ⚠️  {task_id} failed: {result.get('error')}")
						print(f"   ⚠️  {task_id} failed: {result.get('error')}")

					return task_id, result

				except Exception as e:
					error_msg = f"   ❌ ERROR executing {task_id}: {str(e)}"
					logger.error(error_msg)
					print(error_msg)
					return task_id, {"success": False, "error": str(e)}

			# Execute all agents in parallel
			results = await asyncio.gather(*[execute_single_agent(task) for task in agent_call_plan])

			# Convert to dict
			agent_results = {task_id: result for task_id, result in results}

			logger.info(f"✅ All agent calls completed! {len(agent_results)} results\n")
			print(f"✅ All agent calls completed! {len(agent_results)} results\n")

			return {"agent_results": agent_results}

		async def _synthesize_results_node(self, state: OrchestratorState) -> Dict[str, Any]:
			"""Synthesize all agent results into final paralegal analysis report."""
			user_query = state["user_query"]
			agent_results = state.get("agent_results", {})
			agent_call_plan = state.get("agent_call_plan", [])
			llm_service = state.get("llm_service_override") or self.llm_service
			model = state.get("model_override")

			logger.info("🔄 STEP 4: Synthesizing results into paralegal analysis report...")
			print("🔄 STEP 4: Synthesizing results into paralegal analysis report...")

			# Format agent results for synthesis
			formatted_results = []
			agents_used = []
			internal_results_list = []
			external_results = None
			structured_quotes = []  # Collect structured quotes from all internal agents
			structured_chunks = []  # Collect structured chunks from external agent
			internal_agent_counter = 0  # Track which internal agent call this is

			for task in agent_call_plan:
				task_id = task["task_id"]
				agent_type = task["agent_type"]
				result = agent_results.get(task_id, {})

				if result.get("success"):
					data = result.get("data", {})
					response = data.get("response", "No response")

					# Format based on agent type
					if agent_type == "internal_agent":
						doc = task.get("document", "unknown")
						formatted_results.append(f"Internal Agent ({doc}):\n{response}")
						internal_results_list.append(result)
						
						# Extract structured_quotes from internal agent response
						agent_quotes = data.get("structured_quotes", [])
						if agent_quotes:
							# Increment counter for each internal agent call
							internal_agent_counter += 1
							agent_id = f"internal_{internal_agent_counter}"
							# Add agent_id to each quote for UI grouping
							for quote in agent_quotes:
								quote["agent_id"] = agent_id
							structured_quotes.extend(agent_quotes)
							logger.info(f"      📋 Collected {len(agent_quotes)} structured quotes from {agent_type} (agent_id: {agent_id})")
							print(f"      📋 Collected {len(agent_quotes)} structured quotes from {agent_type} (agent_id: {agent_id})")
					elif agent_type == "external_agent":
						# Format external agent results with clear labeling that these are compliance sources, not contracts
						formatted_results.append(f"=== EXTERNAL COMPLIANCE INFORMATION (WIPO/Regulatory Sources) ===\n{response}\n\nNOTE: Any document names mentioned above (e.g., wipo_pub_*.pdf) are REFERENCE SOURCES for compliance information, NOT contract documents.")
						if not external_results:
							external_results = result
						
						# Extract structured chunks from external agent response
						source_chunks = data.get("source", [])
						logger.info(f"      🔍 Debug: external agent data keys: {list(data.keys())}")
						logger.info(f"      🔍 Debug: source_chunks found: {len(source_chunks) if source_chunks else 0}")
						print(f"      🔍 Debug: external agent data keys: {list(data.keys())}")
						print(f"      🔍 Debug: source_chunks found: {len(source_chunks) if source_chunks else 0}")
						if source_chunks:
							for chunk in source_chunks:
								structured_chunks.append({
									"file_name": chunk.get("file_name", "unknown"),
									"chunk_id": chunk.get("chunk_id", "unknown"),
									"score": chunk.get("score", 0.0),
									"text": chunk.get("text", ""),
									"agent_id": "external_1"  # External agent is typically single call
								})
							logger.info(f"      📋 Collected {len(source_chunks)} structured chunks from {agent_type}")
							print(f"      📋 Collected {len(source_chunks)} structured chunks from {agent_type}")
						else:
							logger.warning(f"      ⚠️  No source chunks found in external agent response")
							print(f"      ⚠️  No source chunks found in external agent response")

					agents_used.append(agent_type)

			agents_used = list(set(agents_used))  # Unique list

			if not formatted_results:
				error_msg = "I couldn't process your query because no documents were found or selected. Please:\n1. Select documents from the sidebar, or\n2. Mention specific document names in your query (e.g., 'Italy-111.pdf', 'japan-111.pdf')"
				logger.warning("   ⚠️  No agent results to synthesize - returning error message")
				print("   ⚠️  No agent results to synthesize - returning error message")
				return {
					"final_response": error_msg,
					"agents_used": agents_used,
					"internal_results": internal_results_list,
					"external_results": external_results,
					"structured_quotes": structured_quotes,
					"structured_chunks": structured_chunks
				}

			# Determine which synthesis prompt to use based on agent types
			has_internal = "internal_agent" in agents_used
			has_external = "external_agent" in agents_used
			
			if has_internal and has_external:
				# Scenario 3: Both internal and external
				synthesis_template = self._synthesis_prompt_both
				logger.info("   📋 Using synthesis prompt: BOTH (internal + external)")
				print("   📋 Using synthesis prompt: BOTH (internal + external)")
			elif has_internal:
				# Scenario 1: Internal-only
				synthesis_template = self._synthesis_prompt_internal_only
				logger.info("   📋 Using synthesis prompt: INTERNAL-ONLY")
				print("   📋 Using synthesis prompt: INTERNAL-ONLY")
			elif has_external:
				# Scenario 2: External-only
				synthesis_template = self._synthesis_prompt_external_only
				logger.info("   📋 Using synthesis prompt: EXTERNAL-ONLY")
				print("   📋 Using synthesis prompt: EXTERNAL-ONLY")
			else:
				# Fallback to old prompt (shouldn't happen)
				synthesis_template = self._synthesis_prompt
				logger.warning("   ⚠️  Unknown agent combination, using default synthesis prompt")

			# Build synthesis prompt
			results_text = "\n\n".join(formatted_results)
			synthesis_prompt = synthesis_template.format(
				user_query=user_query,
				agent_results=results_text
			)

			try:
				final_response = await llm_service.generate(
					prompt=synthesis_prompt,
					max_tokens=3000,
					model=model
				)

				logger.info("✅ Result synthesis complete!\n")
				print("✅ Result synthesis complete!\n")

				return {
					"final_response": final_response,
					"agents_used": agents_used,
					"internal_results": internal_results_list,
					"external_results": external_results,
					"structured_quotes": structured_quotes,  # Pass through structured quotes for UI
					"structured_chunks": structured_chunks  # Pass through structured chunks for UI
				}

			except Exception as e:
				error_msg = f"❌ ERROR in synthesis: {str(e)}"
				logger.error(error_msg)
				print(error_msg)
				return {
					"final_response": f"I received results from the agents but had trouble synthesizing them: {str(e)}",
					"agents_used": agents_used,
					"internal_results": internal_results_list,
					"external_results": external_results,
					"structured_quotes": structured_quotes,  # Pass through structured quotes for UI
					"structured_chunks": structured_chunks  # Pass through structured chunks for UI
				}

		async def _find_agent_by_name(self, agent_name: str):
			"""Find an agent by its name or agent_id_str."""
			registry_state = await self._registry.get_registry_state()

			for agent_id_str, agent_info in registry_state.get("agents", {}).items():
				agent = await self._registry.get_agent(UUID(agent_id_str))
				if agent and (agent.name == agent_name or agent.agent_id_str == agent_name):
					return agent

			return None

		async def process_query(self, user_query: str, selected_documents: Optional[List[str]] = None, model_override: Optional[str] = None, llm_service_override: Optional[LLMService] = None) -> Dict[str, Any]:
			"""
			Process a user query through the LangGraph orchestrator.

			Args:
				user_query: The user's query
				selected_documents: Optional list of selected document filenames
				model_override: Optional model override
				llm_service_override: Optional LLM service override

			Returns:
				Dict with agents_used, results, and interpreted_response
			"""
			# Get available documents
			available_documents = []
			if self._document_storage:
				doc_list = self._document_storage.get_documents()
				available_documents = [doc["filename"] for doc in doc_list]

			print(f"\n{'='*60}")
			print(f"🎯 LANGGRAPH ORCHESTRATOR: Starting to process query")
			print(f"📝 Query: {user_query}")
			if selected_documents:
				print(f"📄 Manually selected documents: {selected_documents}")
			print(f"{'='*60}\n")

			logger.info(f"Processing query: {user_query}")
			if selected_documents:
				logger.info(f"Manually selected documents: {selected_documents}")

			# Initialize state
			initial_state: OrchestratorState = {
				"user_query": user_query,
				"selected_documents": selected_documents or [],
				"available_documents": available_documents,
				"model_override": model_override,
				"llm_service_override": llm_service_override,
				"_analysis": {},  # Initialize analysis dict
				"agent_call_plan": [],
				"agent_results": {},
				"final_response": None,
				"agents_used": [],
				"internal_results": [],
				"external_results": None,
				"structured_quotes": [],  # Initialize structured quotes
				"structured_chunks": [],  # Initialize structured chunks
				"error": None
			}

			# Run the graph
			try:
				final_state = await self.graph.ainvoke(initial_state)

				# Check for errors
				if final_state.get("error"):
					return {
						"success": False,
						"error": final_state["error"],
						"agents_used": [],
						"interpreted_response": f"I'm sorry, I had trouble processing your query. Error: {final_state['error']}"
					}

				print(f"{'='*60}")
				print(f"✅ LANGGRAPH ORCHESTRATOR: Query processing complete!")
				print(f"{'='*60}\n")

				return {
					"success": True,
					"agents_used": final_state.get("agents_used", []),
					"internal_results": final_state.get("internal_results", []),
					"external_results": final_state.get("external_results"),
					"comparison": final_state.get("final_response"),
					"interpreted_response": final_state.get("final_response", "No response generated"),
					"structured_quotes": final_state.get("structured_quotes", []),  # Pass through structured quotes for UI
					"structured_chunks": final_state.get("structured_chunks", [])  # Pass through structured chunks for UI
				}

			except Exception as e:
				import traceback
				error_msg = f"❌ LANGGRAPH ORCHESTRATOR ERROR: {str(e)}\n{traceback.format_exc()}"
				logger.error(error_msg)
				print(error_msg)
				return {
					"success": False,
					"error": str(e),
					"agents_used": [],
					"interpreted_response": f"I'm sorry, I encountered an error processing your query: {str(e)}"
				}

		async def process_query_stream(self, user_query: str, selected_documents: Optional[List[str]] = None, model_override: Optional[str] = None, llm_service_override: Optional[LLMService] = None):
			"""
			Process a user query with streaming progress updates and streaming final response.
			
			Yields:
				Dict events with type: "status", "progress", "content", or "complete"
			"""
			# Get available documents
			available_documents = []
			if self._document_storage:
				doc_list = self._document_storage.get_documents()
				available_documents = [doc["filename"] for doc in doc_list]

			# STEP 1: Analyze query
			yield {
				"type": "status",
				"step": "analyzing",
				"message": "Analyzing query and determining which agents to use...",
				"progress": 10
			}

			# Initialize state
			initial_state: OrchestratorState = {
				"user_query": user_query,
				"selected_documents": selected_documents or [],
				"available_documents": available_documents,
				"model_override": model_override,
				"llm_service_override": llm_service_override,
				"_analysis": {},
				"agent_call_plan": [],
				"agent_results": {},
				"final_response": None,
				"agents_used": [],
				"internal_results": [],
				"external_results": None,
				"structured_quotes": [],
				"structured_chunks": [],
				"error": None
			}

			try:
				# Run analyze_query node
				analysis_state = await self._analyze_query_node(initial_state)
				initial_state.update(analysis_state)
				
				analysis = initial_state.get("_analysis", {})
				needs_internal = analysis.get("needs_internal", False)
				needs_external = analysis.get("needs_external", False)
				documents = initial_state.get("selected_documents", [])
				
				yield {
					"type": "status",
					"step": "analyzing",
					"message": f"Query analyzed: {len(documents)} document(s) identified, {'internal' if needs_internal else ''} {'external' if needs_external else ''} agent(s) needed",
					"progress": 20,
					"documents": documents,
					"agents": [a for a in ["internal_agent", "external_agent"] if (a == "internal_agent" and needs_internal) or (a == "external_agent" and needs_external)]
				}

				# STEP 2: Plan agent calls
				yield {
					"type": "status",
					"step": "planning",
					"message": "Planning agent calls...",
					"progress": 30
				}

				plan_state = await self._plan_agent_calls_node(initial_state)
				initial_state.update(plan_state)
				
				agent_calls = initial_state.get("agent_call_plan", [])
				yield {
					"type": "status",
					"step": "planning",
					"message": f"Planned {len(agent_calls)} agent call(s)",
					"progress": 40,
					"agent_calls": len(agent_calls)
				}

				# STEP 3: Execute agents
				# Send agent task list
				agent_tasks = [
					{
						"task_id": task.get("task_id"),
						"agent_type": task.get("agent_type"),
						"document": task.get("document"),
						"status": "pending"
					}
					for task in agent_calls
				]
				
				yield {
					"type": "status",
					"step": "executing",
					"message": f"Executing {len(agent_calls)} agent call(s) in parallel...",
					"progress": 50,
					"agent_tasks": agent_tasks
				}
				
				# Send "starting" updates for each agent
				for task in agent_calls:
					task_id = task["task_id"]
					agent_type = task["agent_type"]
					document = task.get("document")
					agent_name = agent_type.replace("_", " ").title()
					
					yield {
						"type": "agent_status",
						"task_id": task_id,
						"agent_type": agent_type,
						"document": document,
						"status": "running",
						"message": f"{agent_name} processing {document}" if document else f"{agent_name} processing query"
					}
				
				# Execute all agents
				execute_state = await self._execute_agents_node(initial_state)
				initial_state.update(execute_state)
				
				agent_results = initial_state.get("agent_results", {})
				completed = 0
				
				# Send completion updates for each agent
				for task in agent_calls:
					task_id = task["task_id"]
					agent_type = task["agent_type"]
					document = task.get("document")
					agent_name = agent_type.replace("_", " ").title()
					result = agent_results.get(task_id, {})
					
					if result.get("success"):
						completed += 1
						yield {
							"type": "agent_status",
							"task_id": task_id,
							"agent_type": agent_type,
							"document": document,
							"status": "completed",
							"message": f"{agent_name} completed {document}" if document else f"{agent_name} completed"
						}
						# Small delay to ensure UI updates are visible
						await asyncio.sleep(0.2)
				
				# Final status update for executing step
				yield {
					"type": "status",
					"step": "executing",
					"message": f"All {completed} agent call(s) completed successfully",
					"progress": 80,
					"completed": completed,
					"total": len(agent_calls)
				}
				
				# Brief pause to show completion before moving to synthesis
				await asyncio.sleep(0.3)

				# STEP 4: Synthesize results (with streaming)
				yield {
					"type": "status",
					"step": "synthesizing",
					"message": "Synthesizing results into final report...",
					"progress": 90
				}

				# Get the synthesis prompt
				user_query = initial_state["user_query"]
				agent_results_dict = initial_state.get("agent_results", {})
				agent_call_plan = initial_state.get("agent_call_plan", [])
				agents_used = initial_state.get("agents_used", [])
				internal_results_list = initial_state.get("internal_results", [])
				external_results = initial_state.get("external_results")
				structured_quotes = []  # Collect structured quotes from agent results
				structured_chunks = []  # Collect structured chunks from external agent

				# Format agent results for synthesis and collect structured quotes
				formatted_results = []
				internal_agent_counter = 0
				for task in agent_calls:
					task_id = task["task_id"]
					agent_type = task["agent_type"]
					result_data = agent_results_dict.get(task_id, {})
					
					if result_data.get("success"):
						data = result_data.get("data", {})
						response = data.get("response", "")
						
						# Format based on agent type (matching non-streaming version)
						if agent_type == "internal_agent":
							doc = task.get("document", "unknown")
							formatted_results.append(f"Internal Agent ({doc}):\n{response}")
							internal_results_list.append(result_data)
							
							# Collect structured quotes from internal agents
							agent_quotes = data.get("structured_quotes", [])
							if agent_quotes:
								internal_agent_counter += 1
								agent_id = f"internal_{internal_agent_counter}"
								# Add agent_id and document to each quote
								for quote in agent_quotes:
									quote["agent_id"] = agent_id
									if "document" not in quote:
										quote["document"] = task.get("document", "unknown")
								structured_quotes.extend(agent_quotes)
								logger.info(f"      📋 Collected {len(agent_quotes)} structured quotes from {agent_type} (agent_id: {agent_id})")
								print(f"      📋 Collected {len(agent_quotes)} structured quotes from {agent_type} (agent_id: {agent_id})")
						elif agent_type == "external_agent":
							# Format external agent results with clear labeling that these are compliance sources, not contracts
							formatted_results.append(f"=== EXTERNAL COMPLIANCE INFORMATION (WIPO/Regulatory Sources) ===\n{response}\n\nNOTE: Any document names mentioned above (e.g., wipo_pub_*.pdf) are REFERENCE SOURCES for compliance information, NOT contract documents.")
							if not external_results:
								external_results = result_data
							
							# Extract structured chunks from external agent response
							source_chunks = data.get("source", [])
							logger.info(f"      🔍 Debug: external agent data keys: {list(data.keys())}")
							logger.info(f"      🔍 Debug: source_chunks found: {len(source_chunks) if source_chunks else 0}")
							print(f"      🔍 Debug: external agent data keys: {list(data.keys())}")
							print(f"      🔍 Debug: source_chunks found: {len(source_chunks) if source_chunks else 0}")
							if source_chunks:
								for chunk in source_chunks:
									structured_chunks.append({
										"file_name": chunk.get("file_name", "unknown"),
										"chunk_id": chunk.get("chunk_id", "unknown"),
										"score": chunk.get("score", 0.0),
										"text": chunk.get("text", ""),
										"agent_id": "external_1"  # External agent is typically single call
									})
								logger.info(f"      📋 Collected {len(source_chunks)} structured chunks from {agent_type}")
								print(f"      📋 Collected {len(source_chunks)} structured chunks from {agent_type}")
							else:
								logger.warning(f"      ⚠️  No source chunks found in external agent response")
								print(f"      ⚠️  No source chunks found in external agent response")
						
						if agent_type not in agents_used:
							agents_used.append(agent_type)

				# CRITICAL: Check if we have any agent results before synthesizing
				if not formatted_results:
					error_msg = "I couldn't process your query because no documents were found or selected. Please:\n1. Select documents from the sidebar, or\n2. Mention specific document names in your query (e.g., 'Italy-111.pdf', 'japan-111.pdf')"
					yield {
						"type": "status",
						"step": "error",
						"message": "No documents found to process",
						"progress": 100
					}
					yield {
						"type": "content",
						"chunk": error_msg
					}
					yield {
						"type": "complete",
						"data": {
							"success": False,
							"interpreted_response": error_msg,
							"structured_quotes": [],
							"structured_chunks": [],
							"agents_used": [],
							"internal_results": [],
							"external_results": None
						},
						"progress": 100
					}
					return
				
				results_text = "\n\n".join(formatted_results)
				
				# Determine which synthesis prompt to use based on agent types (matching non-streaming version)
				has_internal = "internal_agent" in agents_used
				has_external = "external_agent" in agents_used
				
				if has_internal and has_external:
					# Scenario 3: Both internal and external
					synthesis_template = self._synthesis_prompt_both
					logger.info("   📋 Using synthesis prompt: BOTH (internal + external)")
					print("   📋 Using synthesis prompt: BOTH (internal + external)")
				elif has_internal:
					# Scenario 1: Internal-only
					synthesis_template = self._synthesis_prompt_internal_only
					logger.info("   📋 Using synthesis prompt: INTERNAL-ONLY")
					print("   📋 Using synthesis prompt: INTERNAL-ONLY")
				elif has_external:
					# Scenario 2: External-only
					synthesis_template = self._synthesis_prompt_external_only
					logger.info("   📋 Using synthesis prompt: EXTERNAL-ONLY")
					print("   📋 Using synthesis prompt: EXTERNAL-ONLY")
				else:
					# Fallback to old prompt (shouldn't happen)
					synthesis_template = self._synthesis_prompt
					logger.warning("   ⚠️  Unknown agent combination, using default synthesis prompt")
				
				synthesis_prompt = synthesis_template.format(
					user_query=user_query,
					agent_results=results_text
				)

				llm_service = initial_state.get("llm_service_override") or self.llm_service
				model = initial_state.get("model_override")

				# Mark synthesis as complete before streaming starts
				yield {
					"type": "status",
					"step": "synthesizing",
					"message": "Ready to generate final report...",
					"progress": 100
				}

				# Stream the final response
				final_response = ""
				if hasattr(llm_service, 'generate_stream'):
					# Use streaming if available
					
					async for chunk in llm_service.generate_stream(
						prompt=synthesis_prompt,
						max_tokens=3000,
						model=model
					):
						final_response += chunk
						yield {
							"type": "content",
							"chunk": chunk
						}
				else:
					# Fallback to non-streaming
					final_response = await llm_service.generate(
						prompt=synthesis_prompt,
						max_tokens=3000,
						model=model
					)
					yield {
						"type": "content",
						"chunk": final_response
					}

				# Send completion
				yield {
					"type": "complete",
					"data": {
						"success": True,
						"agents_used": agents_used,
						"internal_results": internal_results_list,
						"external_results": external_results,
						"comparison": final_response,
						"interpreted_response": final_response,
						"structured_quotes": structured_quotes,
						"structured_chunks": structured_chunks
					},
					"progress": 100
				}

			except Exception as e:
				import traceback
				error_msg = f"Error in streaming query: {str(e)}"
				logger.error(f"{error_msg}\n{traceback.format_exc()}")
				yield {
					"type": "error",
					"message": error_msg
				}

