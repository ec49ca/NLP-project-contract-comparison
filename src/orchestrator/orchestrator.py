"""
Orchestrator for coordinating multi-agent workflows.
"""
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from ..services.ollama_service import OllamaService
from ..registry.registry import AgentRegistrySystem

logger = logging.getLogger(__name__)


class Orchestrator:
	"""Orchestrates multi-agent workflows."""
	
	def __init__(self, registry: AgentRegistrySystem, ollama_service: OllamaService):
		"""
		Initialize orchestrator.
		
		Args:
			registry: Agent registry system
			ollama_service: Ollama service for LLM calls
		"""
		self.registry = registry
		self.ollama = ollama_service
		
		self._split_prompt = """You are an intelligent query analyzer for a contract and compliance system. Given a user query, determine which agents are needed and generate optimized queries for each.

Available agents:
- internal_agent: Searches internal company documents (contracts, agreements, internal policies, setup guides from various countries like Italy, France, etc.)
- external_agent: Queries external databases (WIPO, regional compliance databases, international regulations, regional setup requirements for Africa, Asia, etc.)

CRITICAL: Keep all queries under 100 words. Be concise and focused.

Analyze the user query and respond with JSON:
{
  "agents_needed": ["internal_agent"] or ["external_agent"] or ["internal_agent", "external_agent"],
  "queries": {
    "internal_agent": "short optimized query" (if needed),
    "external_agent": "short optimized query" (if needed)
  },
  "reasoning": "one sentence explanation"
}

Guidelines:
- If query mentions specific documents (e.g., "italy-xxx document", "from this contract") → use internal_agent
- If query asks about regional compliance, setup in a region (e.g., "in Africa", "for African countries"), or external regulations → use external_agent
- If query asks about adapting/setting up something from one region to another → use BOTH agents
- Keep queries under 100 words each. Be specific and focused.

Examples:
- "from this italy-xxx document, tell me about setting it up in africa" → both agents
  - internal_agent: "Find italy-xxx document terms and setup procedures"
  - external_agent: "Find African compliance standards and regional requirements"
- "What does the italy-contract-2024 say?" → internal_agent only
- "What are the compliance requirements in Africa?" → external_agent only"""
		
		self._compare_prompt = """You are an intelligent result analyzer for contract and compliance queries. You receive results from internal document searches and external compliance databases, and need to synthesize them into a comprehensive but CONCISE answer.

CRITICAL: Keep your response under 500 words. Be clear, structured, and actionable.

Given the user's original query and results from agents, provide:
1. Brief summary of information from internal documents (contract terms, procedures, requirements)
2. Brief summary of information from external databases (regional compliance, international standards)
3. A concise comparison showing how internal requirements relate to external/regional requirements
4. Specific guidance on adapting or setting up (2-3 key steps)
5. Key differences or additional requirements (bullet points)
6. Actionable recommendations (2-3 items)

Format your response as:
- Clear, structured answer that directly addresses the user's question
- Reference both internal document information and external compliance requirements
- Provide specific, actionable guidance
- Highlight any conflicts, gaps, or additional steps needed
- Be practical and focused on implementation
- Keep total response under 500 words

Example structure (keep it concise):
"Based on the internal Italy-XXX document, it specifies [brief requirements]. According to external compliance databases for Africa, the regional requirements include [brief requirements]. To properly set this up in Africa: [2-3 key steps]. Key differences: [brief comparison]. Additional requirements: [brief list]." """
	
	async def process_query(self, user_query: str) -> Dict[str, Any]:
		"""
		Process a user query through the orchestrator.
		
		Args:
			user_query: The user's query
			
		Returns:
			Dict with agents_used, results, comparison, and interpreted_response
		"""
		print(f"\n{'='*60}")
		print(f"🎯 ORCHESTRATOR: Starting to process query")
		print(f"📝 Query: {user_query}")
		print(f"{'='*60}\n")
		logger.info(f"Processing query: {user_query}")
		
		# Step 1: Split query using LLM
		logger.info("🔍 STEP 1: Analyzing query and determining which agents to use...")
		print("🔍 STEP 1: Analyzing query and determining which agents to use...")
		try:
			split_result = await self.ollama.generate_json(
				prompt=f"User query: {user_query}",
				system=self._split_prompt
			)
			
			agents_needed = split_result.get("agents_needed", [])
			queries = split_result.get("queries", {})
			
			logger.info(f"✅ Query analysis complete!")
			logger.info(f"   Agents needed: {agents_needed}")
			logger.info(f"   Generated queries: {queries}\n")
			print(f"✅ Query analysis complete!")
			print(f"   Agents needed: {agents_needed}")
			print(f"   Generated queries: {queries}\n")
			
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
				
				# Execute agent
				agent_result = await agent.process_request({
					"command": "query",
					"query": query
				})
				
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

Results from agents:
{self._format_results_for_comparison(results)}

Please provide a comprehensive answer that compares the information and addresses the user's query."""
			
			# Limit orchestrator comparison to 600 tokens (approximately 500 words)
			interpreted_response = await self.ollama.generate(
				prompt=comparison_prompt,
				system=self._compare_prompt,
				max_tokens=600
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

