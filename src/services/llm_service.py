"""
Main LLM Service - Factory and Hotswap Manager

This service provides easy switching between different LLM providers
while maintaining a consistent interface for the rest of the application.
"""

import logging
import os
from typing import Dict, List, Any, Optional, Type
from ..providers.openai_provider import OpenAIProvider
from ..providers.claude_provider import ClaudeProvider
from ..interfaces.llm_interface import LLMInterface, LLMProvider
from ..services.config import parse_default_model

logger = logging.getLogger(__name__)


class LLMService:
    """Main LLM service with provider hotswapping capabilities"""

    def __init__(self, default_provider: str = None):
        self.providers: Dict[str, LLMInterface] = {}

        # Parse global default model configuration
        self.default_provider_name, self.default_model_name = parse_default_model()

        # Override with explicit provider if provided
        if default_provider:
            self.default_provider_name = default_provider

        self.current_provider: Optional[LLMInterface] = None

        # Register available providers
        self._register_providers()

        # Set initial provider
        self.set_provider(self.default_provider_name)

    def _register_providers(self):
        """Register all available LLM providers"""
        try:
            # Register OpenAI (always available)
            self.providers["openai"] = OpenAIProvider()
            logger.info("✅ OpenAI provider registered")
        except Exception as e:
            logger.warning(f"⚠️  OpenAI provider registration failed: {e}")

        try:
            # Register Claude (if API key available)
            if os.getenv("CLAUDE_API_KEY"):
                self.providers["claude"] = ClaudeProvider()
                logger.info("✅ Claude provider registered")
            else:
                logger.info("⏭️  Claude provider skipped (no API key)")
        except Exception as e:
            logger.warning(f"⚠️  Claude provider registration failed: {e}")

        # TODO: Add Grok provider when available
        # try:
        #     if os.getenv("GROK_API_KEY"):
        #         self.providers["grok"] = GrokProvider()
        #         logger.info("✅ Grok provider registered")
        # except Exception as e:
        #     logger.warning(f"⚠️  Grok provider registration failed: {e}")

        if len(list(self.providers.keys())) == 0:
            logger.error("⚠️ No LLM providers registered")
        logger.info(f"📝 Available providers: {list(self.providers.keys())}")

    def set_provider(self, provider_name: str) -> bool:
        """Switch to a different LLM provider"""
        if provider_name not in self.providers:
            logger.error(
                f"❌ Provider '{provider_name}' not available. Available: {list(self.providers.keys())}"
            )
            return False

        self.current_provider = self.providers[provider_name]
        logger.info(f"🔄 Switched to LLM provider: {provider_name}")
        return True

    def get_current_provider(self) -> str:
        """Get name of current provider"""
        return (
            self.current_provider.get_provider_name()
            if self.current_provider
            else "none"
        )

    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return list(self.providers.keys())

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Chat completion with optional provider override

        Args:
                messages: Chat messages
                model: Model to use (provider-specific)
                temperature: Sampling temperature
                max_tokens: Max response tokens
                response_format: Response format constraints
                provider: Override current provider for this call
                **kwargs: Provider-specific parameters
        """
        # Use specified provider or current default
        if provider and provider in self.providers:
            llm_provider = self.providers[provider]
        elif self.current_provider:
            llm_provider = self.current_provider
        else:
            raise RuntimeError("No LLM provider available")

        # Use global default model if no model specified and we're using the default provider
        effective_model = model
        if (
            not model
            and llm_provider.get_provider_name() == self.default_provider_name
            and self.default_model_name
        ):
            effective_model = self.default_model_name

        return await llm_provider.chat_completion(
            messages=messages,
            model=effective_model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            **kwargs,
        )

    async def simple_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Simple completion with optional provider override
        """
        # Use specified provider or current default
        if provider and provider in self.providers:
            llm_provider = self.providers[provider]
        elif self.current_provider:
            llm_provider = self.current_provider
        else:
            raise RuntimeError("No LLM provider available")

        # Use global default model if no model specified and we're using the default provider
        effective_model = model
        if (
            not model
            and llm_provider.get_provider_name() == self.default_provider_name
            and self.default_model_name
        ):
            effective_model = self.default_model_name

        return await llm_provider.simple_completion(
            prompt=prompt,
            model=effective_model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            **kwargs,
        )

    async def create_embedding(
        self,
        text: str,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs,
    ) -> List[float]:
        """
        Create text embeddings with optional provider override

        Args:
            text: Text to create embeddings for
            model: Specific embedding model to use
            provider: Override current provider for this call
            **kwargs: Provider-specific parameters

        Returns:
            List[float]: Embedding vector
        """
        # Use specified provider or current default
        if provider and provider in self.providers:
            llm_provider = self.providers[provider]
        elif self.current_provider:
            llm_provider = self.current_provider
        else:
            raise RuntimeError("No LLM provider available")

        return await llm_provider.create_embedding(
            text=text,
            model=model,
            **kwargs,
        )

    async def validate_all_providers(self) -> Dict[str, bool]:
        """Test all registered providers"""
        results = {}
        for name, provider in self.providers.items():
            try:
                results[name] = await provider.validate_connection()
            except Exception as e:
                logger.error(f"Provider {name} validation failed: {e}")
                results[name] = False
        return results

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about all providers"""
        info = {}
        for name, provider in self.providers.items():
            info[name] = {
                "available_models": provider.get_available_models(),
                "default_model": provider.get_default_model(),
                "provider_name": provider.get_provider_name(),
            }
        return info

    def get_global_default_model(self) -> str:
        """Get the global default model setting"""
        return (
            f"{self.default_provider_name}:{self.default_model_name}"
            if self.default_model_name
            else self.default_provider_name
        )


# Global LLM service instance
llm_service = LLMService()
