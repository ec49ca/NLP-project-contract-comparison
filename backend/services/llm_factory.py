"""
Factory for creating LLM service instances based on configuration.
"""
import os
import logging
from typing import Optional
from .llm_service import LLMService
from .ollama_service import OllamaService
from .openai_service import OpenAIService

logger = logging.getLogger(__name__)


def create_llm_service(
	provider: Optional[str] = None,
	**kwargs
) -> LLMService:
	"""
	Create an LLM service instance based on provider.
	
	Args:
		provider: LLM provider name ("ollama" or "openai"). Defaults to LLM_PROVIDER env var.
		**kwargs: Additional arguments passed to the service constructor
		
	Returns:
		LLMService instance
	"""
	provider = provider or os.getenv("LLM_PROVIDER", "ollama").lower()
	
	if provider == "ollama":
		return OllamaService(
			base_url=kwargs.get("base_url") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
			default_model=kwargs.get("default_model") or os.getenv("OLLAMA_MODEL", "llama3:latest")
		)
	elif provider == "openai":
		api_key = kwargs.get("api_key") or os.getenv("OPENAI_API_KEY")
		if not api_key:
			raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
		return OpenAIService(
			api_key=api_key,
			default_model=kwargs.get("default_model") or os.getenv("OPENAI_MODEL", "gpt-4")
		)
	elif provider in ["anthropic", "google"]:
		# These providers are listed in /api/providers but not yet implemented
		raise ValueError(f"Provider '{provider}' is not yet implemented. Supported providers: ollama, openai")
	else:
		raise ValueError(f"Unsupported LLM provider: {provider}. Supported providers: ollama, openai")

