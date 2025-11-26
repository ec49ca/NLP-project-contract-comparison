"""
Abstract base class for LLM services.
Allows switching between different LLM providers (Ollama, OpenAI, etc.)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class LLMService(ABC):
	"""Abstract base class for LLM services."""
	
	@abstractmethod
	async def generate(self, prompt: str, model: Optional[str] = None, system: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
		"""
		Generate text using the LLM.
		
		Args:
			prompt: User prompt
			model: Model to use (optional, uses default if not provided)
			system: System prompt (optional)
			max_tokens: Maximum tokens to generate (optional)
			
		Returns:
			Generated text response
		"""
		pass
	
	@abstractmethod
	async def generate_json(self, prompt: str, model: Optional[str] = None, system: Optional[str] = None) -> Dict[str, Any]:
		"""
		Generate JSON response using the LLM.
		
		Args:
			prompt: User prompt
			model: Model to use (optional)
			system: System prompt (optional)
			
		Returns:
			Parsed JSON response as dictionary
		"""
		pass

