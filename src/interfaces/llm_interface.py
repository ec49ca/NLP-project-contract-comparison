from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers"""

    OPENAI = "openai"
    CLAUDE = "claude"
    GROK = "grok"


class LLMInterface(ABC):
    """Abstract interface for Language Model providers"""

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generic chat completion interface

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Specific model to use (override default)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            response_format: Response format constraints (e.g., {"type": "json_object"})
            **kwargs: Provider-specific parameters

        Returns:
            Dict with 'choices' containing response data
        """
        pass

    @abstractmethod
    async def simple_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Simple text completion interface

        Args:
            prompt: Text prompt
            model: Specific model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            response_format: Response format constraints
            **kwargs: Provider-specific parameters

        Returns:
            str: Response content
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of this LLM provider"""
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models for this provider"""
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model for this provider"""
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Test if the provider connection is working"""
        pass
