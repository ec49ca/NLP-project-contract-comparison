"""
Orchestrator for coordinating multi-agent workflows.
"""
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from ..services.llm_service import LLMService
from ..registry.registry import AgentRegistrySystem
from ..services.document_storage import DocumentStorage

logger = logging.getLogger(__name__)


class Orchestrator:
	"""Orchestrates multi-agent workflows."""
	
	def __init__(self, registry: AgentRegistrySystem, llm_service: LLMService, document_storage: Optional[DocumentStorage] = None):
		"""
		Initialize orchestrator.
		
		Args:
			registry: Agent registry system
			llm_service: LLM service for making LLM calls (Ollama, OpenAI, etc.)
			document_storage: Optional document storage service
		"""
		self.registry = registry
		self.ollama = llm_service  # Keep variable name for backward compatibility
		self.document_storage = document_storage
		
		self._split_prompt_template = """You are an intelligent query analyzer for a contract and compliance system. Given a user query and available documents, determine which agents are needed, match any mentioned documents, and generate optimized queries for each.

Available agents:
- internal_agent: Searches internal documents (contracts, agreements, policies, setup guides from various countries like Italy, France, etc.)
- external_agent: Queries external databases (WIPO, regional compliance databases, international regulations, regional setup requirements for Africa, Asia, etc.)

{manual_selection_info}

Available Documents:
{document_list}

CRITICAL: Keep all queries under 100 words. Be concise and focused.

Analyze the user query and respond with JSON:
{{
  "agents_needed": ["internal_agent"] or ["external_agent"] or ["internal_agent", "external_agent"],
  "matched_documents": ["filename1.pdf", "filename2.pdf"] or [] (list of document filenames that match what the user mentioned in their query),
  "queries": {{
    "internal_agent": "short optimized query with specific instructions about what to extract from the documents" (if needed),
    "external_agent": "short optimized query" (if needed)
  }},
  "reasoning": "one sentence explanation"
}}

Guidelines:
- IMPORTANT: If the user has manually selected documents, use those as the PRIMARY documents. Only auto-detect ADDITIONAL documents if the query explicitly mentions them by name (e.g., "japan document", "compare to france-456").
- If the user manually selected documents and the query is ambiguous (e.g., "tell me about this document", "what does this say"), ONLY use the manually selected documents. Do NOT auto-detect additional documents.
- If query mentions specific documents by name (e.g., "italy-123123 document", "japan-xxx", "from this contract") → match to available documents and use internal_agent
- Match document names flexibly: "italy-123123" should match "italy-123123.pdf" or "italy-123123-contract.pdf"
- If documents are matched, generate a detailed query for internal_agent like: "Look at [document name] and provide all important quoted annexes, codes, terms, and requirements that are relevant for comparison"
- If query asks about regional compliance, setup in a region (e.g., "in Africa", "for Australian countries"), or external regulations → use external_agent
- If query asks about adapting/setting up something from one region to another → use BOTH agents
- Keep queries under 100 words each. Be specific and focused.

Examples:
- User manually selected: ["Italy-111.pdf"], Query: "tell me about this document" → ONLY use ["Italy-111.pdf"], do NOT auto-detect other documents
- User manually selected: ["Italy-111.pdf"], Query: "compare this to my japan document" → use ["Italy-111.pdf"] (manual) + auto-detect ["japan-111.pdf"] from query
- "can you tell me how italy-123123 document will work in australia" → both agents
  - matched_documents: ["italy-123123.pdf"]
  - internal_agent: "Look at italy-123123 document and provide all important quoted annexes, codes, terms, and requirements that need to be compared for Australia"
  - external_agent: "Find Australian compliance standards and regional requirements"
- "What does the italy-contract-2024 say?" → internal_agent only
  - matched_documents: ["italy-contract-2024.pdf"]
  - internal_agent: "Extract and summarize key terms, requirements, and important sections from italy-contract-2024"
- "What are the compliance requirements in Africa?" → external_agent only
  - matched_documents: []
- If no documents match, return empty array for matched_documents"""
		
		self._compare_prompt = """You are a paralegal analyst reviewing contract documents and compliance requirements. Your job is to provide a comprehensive, detailed analysis report - NOT a summary.

You receive structured contract analysis data from internal agents (with actual quoted clauses organized by topic) and external compliance information. Your task is to analyze, interpret, and report on these findings like a paralegal would.

CRITICAL: This is an ANALYSIS REPORT, not a summary. Be thorough, detailed, and include actual quotes.

Given the user's original query and structured results from agents, provide:

1. EXECUTIVE SUMMARY (2-3 paragraphs)
   - Overview of what documents were analyzed
   - Key findings at a high level
   - Main areas of difference or concern

2. DETAILED TOPIC-BY-TOPIC ANALYSIS
   For each topic found in the contracts (Territory, Governing Law, Jurisdiction, Currency, Taxes, IP, Exclusivity, Regulatory, Term & Termination):
   - Compare what each contract says (include actual quoted text)
   - Identify differences, similarities, and variations
   - Explain the implications of each difference
   - Note any country-specific elements that require attention
   - Provide examples of how these differences might impact operations

3. COUNTRY-SPECIFIC ELEMENTS ANALYSIS
   - List all country-specific references found in each contract
   - Explain why each is country-specific
   - Identify which elements would need to change for adaptation
   - Provide specific examples of what would need to be modified

4. COMPREHENSIVE COMPARISON
   - Side-by-side comparison of key terms
   - Highlight conflicts or incompatibilities
   - Identify gaps or missing elements
   - Note any regulatory or compliance differences

5. DETAILED RECOMMENDATIONS
   - Specific, actionable steps for adaptation (if applicable)
   - Risk areas that need attention
   - Compliance considerations
   - Best practices based on the analysis

Format your response as:
- A professional paralegal report with clear sections
- Include actual quoted text from documents (with section references)
- Provide detailed analysis, not brief summaries
- Use examples to illustrate points
- Be comprehensive and thorough
- Structure it like a legal analysis document

Example structure:
"EXECUTIVE SUMMARY
[Detailed overview with actual findings]

TERRITORY ANALYSIS
Contract A (Italy-111.pdf) specifies: '[actual quote]' (Section X.X)
Contract B (japan-111.pdf) specifies: '[actual quote]' (Section Y.Y)
Analysis: [Detailed comparison and implications]...

GOVERNING LAW ANALYSIS
[Similar detailed analysis with quotes]...

[Continue for all topics found]

COUNTRY-SPECIFIC ELEMENTS
[Detailed analysis of each country-specific reference]...

RECOMMENDATIONS
[Comprehensive, actionable recommendations with examples]..." """
	
	async def process_query(self, user_query: str, selected_documents: Optional[List[str]] = None, model_override: Optional[str] = None, llm_service_override: Optional[LLMService] = None) -> Dict[str, Any]:
		"""
		Process a user query through the orchestrator.
		
		Args:
			user_query: The user's query
			selected_documents: Optional list of selected document filenames
			model_override: Optional model override
			llm_service_override: Optional LLM service override (for provider switching)
			
		Returns:
			Dict with agents_used, results, comparison, and interpreted_response
		"""
		# Use the LLM service override if provided, otherwise use default
		llm_service_to_use = llm_service_override or self.ollama
		model_name = model_override
		print(f"\n{'='*60}")
		print(f"🎯 ORCHESTRATOR: Starting to process query")
		print(f"📝 Query: {user_query}")
		if selected_documents:
			print(f"📄 Manually selected documents: {selected_documents}")
		print(f"{'='*60}\n")
		logger.info(f"Processing query: {user_query}")
		if selected_documents:
			logger.info(f"Manually selected documents: {selected_documents}")
		
		# Step 1: Get available documents and analyze query using LLM
		logger.info("🔍 STEP 1: Analyzing query and determining which agents to use...")
		print("🔍 STEP 1: Analyzing query and determining which agents to use...")
		
		# Get list of available documents
		available_documents = []
		if self.document_storage:
			doc_list = self.document_storage.get_documents()
			available_documents = [doc["filename"] for doc in doc_list]
		
		# Log available documents
		if available_documents:
			logger.info(f"   📚 Available documents: {available_documents}")
			print(f"   📚 Available documents: {available_documents}")
		else:
			logger.info(f"   📚 No documents available")
			print(f"   📚 No documents available")
		
		# Build document list string for prompt
		if available_documents:
			document_list_str = "\n".join([f"- {doc}" for doc in available_documents])
		else:
			document_list_str = "No documents available"
		
		# Build manual selection info string for prompt
		if selected_documents:
			manual_selection_str = f"Manually Selected Documents: {selected_documents}\n\nIMPORTANT: The user has already selected these documents. Use them as the PRIMARY documents. Only auto-detect ADDITIONAL documents if the query explicitly mentions other documents by name."
		else:
			manual_selection_str = "Manually Selected Documents: None\n\nThe user has not manually selected any documents. Auto-detect documents from the query if mentioned."
		
		# Build split prompt with document list and manual selection info
		split_prompt = self._split_prompt_template.format(
			manual_selection_info=manual_selection_str,
			document_list=document_list_str
		)
		
		try:
			split_result = await llm_service_to_use.generate_json(
				prompt=f"User query: {user_query}",
				system=split_prompt,
				model=model_name
			)
			
			agents_needed = split_result.get("agents_needed", [])
			queries = split_result.get("queries", {})
			matched_documents = split_result.get("matched_documents", [])
			
			# Fallback: If LLM didn't match documents but we have documents and query mentions them, do simple matching
			if not matched_documents and available_documents and "internal_agent" in agents_needed:
				# Simple string matching: check if query mentions any document name (case-insensitive)
				query_lower = user_query.lower()
				for doc in available_documents:
					doc_name_lower = doc.lower().replace(".pdf", "").replace("-", " ").replace("_", " ")
					# Check if query contains key parts of document name
					doc_keywords = doc_name_lower.split()
					if any(keyword in query_lower for keyword in doc_keywords if len(keyword) > 3):
						matched_documents.append(doc)
						logger.info(f"   🔍 Fallback matching: '{doc}' matched from query")
						print(f"   🔍 Fallback matching: '{doc}' matched from query")
			
			# Combine manually selected documents with auto-detected documents
			# Start with manually selected documents as the base
			final_selected_documents = list(set(selected_documents or []))
			
			# Add auto-detected documents (LLM should only detect additional ones if query mentions them)
			if matched_documents:
				# Validate matched documents exist
				valid_matched = [doc for doc in matched_documents if doc in available_documents]
				
				# Only add documents that aren't already in manual selection
				# This handles the case where LLM might re-detect manually selected docs
				new_docs = [doc for doc in valid_matched if doc not in final_selected_documents]
				final_selected_documents.extend(new_docs)
				final_selected_documents = list(set(final_selected_documents))  # Remove duplicates
				
				if new_docs:
					logger.info(f"   📄 Auto-detected additional documents: {new_docs}")
					print(f"   📄 Auto-detected additional documents: {new_docs}")
				elif valid_matched:
					logger.info(f"   📄 Auto-detected documents (already in manual selection): {valid_matched}")
					print(f"   📄 Auto-detected documents (already in manual selection): {valid_matched}")
				
				if matched_documents != valid_matched:
					invalid = [doc for doc in matched_documents if doc not in available_documents]
					logger.warning(f"   ⚠️  LLM matched non-existent documents: {invalid}")
					print(f"   ⚠️  LLM matched non-existent documents: {invalid}")
			
			# Update selected_documents with combined list
			selected_documents = final_selected_documents if final_selected_documents else None
			
			logger.info(f"✅ Query analysis complete!")
			logger.info(f"   Agents needed: {agents_needed}")
			logger.info(f"   Generated queries: {queries}")
			if selected_documents:
				logger.info(f"   Final selected documents: {selected_documents}\n")
			print(f"✅ Query analysis complete!")
			print(f"   Agents needed: {agents_needed}")
			print(f"   Generated queries: {queries}")
			if selected_documents:
				print(f"   Final selected documents: {selected_documents}\n")
			
		except Exception as e:
			import traceback
			error_msg = f"❌ ERROR in query analysis: {str(e)}\n   Error type: {type(e).__name__}\n   Traceback: {traceback.format_exc()}\n"
			logger.error(error_msg)
			print(error_msg)
			return {
				"success": False,
				"error": f"Failed to analyze query: {str(e)}",
				"agents_used": [],
				"interpreted_response": f"I'm sorry, I had trouble analyzing your query. Error: {str(e)}. Please try again."
			}
		
		# Step 2: Execute agents in parallel
		logger.info(f"🤖 STEP 2: Executing {len(agents_needed)} agent(s)...")
		print(f"🤖 STEP 2: Executing {len(agents_needed)} agent(s)...")
		results = {}
		internal_results = None
		external_results = None
		
		for agent_name in agents_needed:
			try:
				logger.info(f"   → Executing {agent_name}...")
				print(f"   → Executing {agent_name}...")
				# Find agent by name
				agent = await self._find_agent_by_name(agent_name)
				if not agent:
					logger.warning(f"   ❌ Agent {agent_name} not found!")
					print(f"   ❌ Agent {agent_name} not found!")
					continue
				
				query = queries.get(agent_name, user_query)
				query_preview = query[:100] + "..." if len(query) > 100 else query
				logger.info(f"      Query: {query_preview}")
				print(f"      Query: {query_preview}")
				
				# Log full query for agents
				logger.info(f"      📋 Full query for {agent_name}: {query}")
				print(f"      📋 Full query for {agent_name}: {query}")
				
				# Execute agent with selected documents if internal agent
				request_data = {
					"command": "query",
					"query": query
				}
				if agent_name == "internal_agent" and selected_documents:
					request_data["selected_documents"] = selected_documents
					logger.info(f"      📄 Documents being sent to {agent_name}: {selected_documents}")
					print(f"      📄 Documents being sent to {agent_name}: {selected_documents}")
				
				# Pass model override and LLM service to agents if provided
				if model_override:
					request_data["model"] = model_override
				if llm_service_override:
					request_data["llm_service"] = llm_service_override
				
				agent_result = await agent.process_request(request_data)
				
				results[agent_name] = agent_result
				
				if agent_name == "internal_agent":
					internal_results = agent_result
				elif agent_name == "external_agent":
					external_results = agent_result
				
				if agent_result.get("success"):
					logger.info(f"   ✅ {agent_name} completed successfully\n")
					print(f"   ✅ {agent_name} completed successfully\n")
				else:
					error_msg = f"   ❌ {agent_name} failed: {agent_result.get('error', 'Unknown error')}\n"
					logger.error(error_msg)
					print(error_msg)
				
			except Exception as e:
				error_msg = f"   ❌ ERROR executing {agent_name}: {str(e)}\n"
				logger.error(error_msg)
				print(error_msg)
				results[agent_name] = {
					"success": False,
					"error": str(e)
				}
		
		# Step 3: Compare and synthesize results
		logger.info("🔄 STEP 3: Comparing and synthesizing results...")
		print("🔄 STEP 3: Comparing and synthesizing results...")
		try:
			comparison_prompt = f"""Original user query: {user_query}

Structured contract analysis results from agents:
{self._format_results_for_comparison(results)}

Analyze these results as a paralegal would. The internal agent has provided structured contract analysis with actual quoted clauses organized by topic (Territory, Governing Law, Jurisdiction, Currency, Taxes, IP, Exclusivity, Regulatory, Term & Termination) and country-specific references.

Provide a comprehensive paralegal analysis report that:
- Analyzes each topic in detail with actual quotes
- Compares contracts side-by-side
- Identifies differences and their implications
- Explains country-specific elements
- Provides detailed recommendations with examples

Include actual quoted text from the documents in your analysis."""
			
			# Increase token limit for comprehensive analysis (up to 3000 tokens for detailed paralegal report)
			interpreted_response = await llm_service_to_use.generate(
				prompt=comparison_prompt,
				system=self._compare_prompt,
				max_tokens=3000,
				model=model_name
			)
			
			logger.info("✅ Result synthesis complete!\n")
			print("✅ Result synthesis complete!\n")
			
		except Exception as e:
			error_msg = f"❌ ERROR in result synthesis: {str(e)}\n"
			logger.error(error_msg)
			print(error_msg)
			interpreted_response = f"I received results from the agents but had trouble synthesizing them: {str(e)}"
		
		logger.info(f"{'='*60}")
		logger.info(f"✅ ORCHESTRATOR: Query processing complete!")
		logger.info(f"{'='*60}\n")
		print(f"{'='*60}")
		print(f"✅ ORCHESTRATOR: Query processing complete!")
		print(f"{'='*60}\n")
		
		return {
			"success": True,
			"agents_used": agents_needed,
			"internal_results": internal_results,
			"external_results": external_results,
			"comparison": interpreted_response,
			"interpreted_response": interpreted_response
		}
	
	async def _find_agent_by_name(self, agent_name: str):
		"""Find an agent by its name or agent_id_str."""
		registry_state = await self.registry.get_registry_state()
		
		for agent_id_str, agent_info in registry_state.get("agents", {}).items():
			agent = await self.registry.get_agent(UUID(agent_id_str))
			if agent and (agent.name == agent_name or agent.agent_id_str == agent_name):
				return agent
		
		return None
	
	def _format_results_for_comparison(self, results: Dict[str, Any]) -> str:
		"""Format agent results for comparison prompt."""
		formatted = []
		for agent_name, result in results.items():
			if result.get("success"):
				data = result.get("data", {})
				formatted.append(f"{agent_name}: {data.get('response', 'No response')}")
			else:
				formatted.append(f"{agent_name}: Error - {result.get('error', 'Unknown error')}")
		
		return "\n".join(formatted)

