"""
Ollama service for making LLM API calls to local Ollama instance.
"""
import os
import httpx
import logging
import json
from typing import Dict, Any, Optional
from .llm_service import LLMService

logger = logging.getLogger(__name__)


class OllamaService(LLMService):
	"""Service for interacting with Ollama API."""
	
	def __init__(self, base_url: Optional[str] = None, default_model: Optional[str] = None):
		"""
		Initialize Ollama service.
		
		Args:
			base_url: Base URL for Ollama API (defaults to http://localhost:11434)
			default_model: Default model to use (defaults to llama3:latest)
		"""
		self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
		self.default_model = default_model or os.getenv("OLLAMA_MODEL", "llama3:latest")
	
	async def generate(self, prompt: str, model: Optional[str] = None, system: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
		"""
		Generate text using Ollama.
		
		Args:
			prompt: User prompt
			model: Model to use (defaults to default_model)
			system: System prompt (optional)
			max_tokens: Maximum tokens to generate (defaults to 1000)
			
		Returns:
			Generated text response
		"""
		model = model or self.default_model
		max_tokens = max_tokens or 1000  # Default limit
		
		messages = []
		if system:
			messages.append({"role": "system", "content": system})
		messages.append({"role": "user", "content": prompt})
		
		payload = {
			"model": model,
			"messages": messages,
			"stream": False,
			"options": {
				"num_predict": max_tokens  # Limit output tokens
			}
		}
		
		logger.info(f"   📡 LLM: Calling {model} API (Ollama)...")
		logger.info(f"      Prompt length: {len(prompt)} chars")
		if system:
			logger.info(f"      System prompt: {len(system)} chars")
		print(f"   📡 LLM: Calling {model} API (Ollama)...")
		print(f"      Prompt length: {len(prompt)} chars")
		if system:
			print(f"      System prompt: {len(system)} chars")
		
		try:
			async with httpx.AsyncClient(timeout=120.0) as client:
				response = await client.post(
					f"{self.base_url}/api/chat",
					json=payload
				)
				response.raise_for_status()
				
				result = response.json()
				content = result.get("message", {}).get("content", "")
				logger.info(f"   ✅ LLM: Received response ({len(content)} chars)\n")
				print(f"   ✅ LLM: Received response ({len(content)} chars)\n")
				return content
		except httpx.RequestError as e:
			error_msg = f"   ❌ LLM ERROR (Ollama): {str(e)}\n"
			logger.error(error_msg)
			print(error_msg)
			raise Exception(f"Failed to generate response from Ollama: {str(e)}")
		except httpx.HTTPStatusError as e:
			error_msg = f"   ❌ LLM HTTP ERROR (Ollama): {e.response.status_code} - {str(e)}\n"
			logger.error(error_msg)
			print(error_msg)
			raise Exception(f"Failed to generate response from Ollama: HTTP {e.response.status_code}")
	
	async def generate_json(self, prompt: str, model: Optional[str] = None, system: Optional[str] = None) -> Dict[str, Any]:
		"""
		Generate JSON response using Ollama.
		
		Args:
			prompt: User prompt
			model: Model to use
			system: System prompt (optional)
			
		Returns:
			Parsed JSON response
		"""
		# Add instruction to return JSON with specific format - keep it concise
		json_prompt = f"""{prompt}

IMPORTANT: Respond with ONLY valid JSON, no other text. Keep queries under 100 words each. Use this exact format:
{{
  "agents_needed": ["agent1", "agent2"],
  "queries": {{
    "agent1": "short query text",
    "agent2": "short query text"
  }},
  "reasoning": "brief one sentence explanation"
}}"""
		
		# Limit JSON responses to 200 tokens (enough for the structure)
		response = await self.generate(json_prompt, model, system, max_tokens=200)
		
		# Try to extract JSON from response
		try:
			# Remove markdown code blocks if present
			if "```json" in response:
				response = response.split("```json")[1].split("```")[0].strip()
			elif "```" in response:
				response = response.split("```")[1].split("```")[0].strip()
			
			# Try to fix common JSON issues
			# Remove any trailing commas before closing braces/brackets
			import re
			response = re.sub(r',(\s*[}\]])', r'\1', response)
			
			# Try to find JSON object in the response if there's extra text
			json_start = response.find('{')
			json_end = response.rfind('}') + 1
			if json_start >= 0 and json_end > json_start:
				response = response[json_start:json_end]
			
			parsed = json.loads(response)
			logger.info("   ✅ LLM: Successfully parsed JSON response")
			print(f"   ✅ LLM: Successfully parsed JSON response")
			return parsed
		except json.JSONDecodeError as e:
			error_msg = f"   ❌ LLM: Failed to parse JSON - {str(e)}\n      Response preview: {response[:300]}..."
			logger.error(error_msg)
			logger.error(f"Full response was: {response}")
			print(error_msg)
			# Try to return a fallback response
			logger.warning("Attempting to use fallback JSON parsing...")
			try:
				# Try to extract agents_needed, queries, and matched_documents if possible
				import re
				agents_match = re.search(r'"agents_needed"\s*:\s*\[(.*?)\]', response)
				if agents_match:
					agents_str = agents_match.group(1)
					agents = [a.strip().strip('"') for a in agents_str.split(',') if a.strip()]
					queries = {}
					for agent in agents:
						query_match = re.search(rf'"{agent}"\s*:\s*"([^"]*)"', response)
						if query_match:
							queries[agent] = query_match.group(1)
					
					# Try to extract matched_documents
					matched_docs = []
					matched_docs_match = re.search(r'"matched_documents"\s*:\s*\[(.*?)\]', response)
					if matched_docs_match:
						docs_str = matched_docs_match.group(1)
						matched_docs = [d.strip().strip('"') for d in docs_str.split(',') if d.strip()]
					
					if agents:
						logger.info("   ✅ LLM: Successfully parsed JSON using fallback method")
						print(f"   ✅ LLM: Successfully parsed JSON using fallback method")
						result = {
							"agents_needed": agents,
							"queries": queries,
							"reasoning": "Parsed using fallback method"
						}
						if matched_docs:
							result["matched_documents"] = matched_docs
						return result
			except Exception as fallback_error:
				logger.error(f"Fallback parsing also failed: {fallback_error}")
			
			raise Exception(f"Failed to parse JSON response: {str(e)}")

