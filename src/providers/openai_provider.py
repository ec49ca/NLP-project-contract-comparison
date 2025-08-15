"""
OpenAI LLM Provider Implementation
Note about langfuse: using drop in replacement for openai via langfuse; wont work with other providers as of time of development
"""

import logging
import os
from typing import Dict, List, Any, Optional
from langfuse.openai import openai

# from openai import OpenAI
from ..services.config import (
    OPENAI_API_KEY,
    validate_openai_config,
    get_provider_config,
    get_provider_default_model,
    get_provider_available_models,
)
from ..interfaces.llm_interface import LLMInterface

# from langfuse import observe

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMInterface):
    """OpenAI implementation of LLM interface"""

    def __init__(self):
        logger.info("Initializing OpenAI Provider")
        validate_openai_config()

        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.provider_name = "openai"

        # Get model configurations from central config
        config = get_provider_config("openai")
        if not config:
            raise ValueError("OpenAI provider configuration not found in config.py")

        self.models = config["available_models"]
        self.embedding_models = config["embedding_models"]
        self.default_model = config["default_model"]
        self.default_embedding_model = config["default_embedding_model"]
        self.default_temperature = config["default_temperature"]
        self.default_max_tokens = config["default_max_tokens"]

        logger.info(
            f"OpenAI Provider initialized with default model: {self.default_model}"
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """OpenAI chat completion implementation"""
        try:
            # Use provided model or default
            actual_model = model or self.default_model

            # Build parameters
            params = {
                "model": actual_model,
                "messages": messages,
                "temperature": temperature or self.default_temperature,
                "max_tokens": max_tokens or self.default_max_tokens,
            }

            # Add response format if specified
            if response_format:
                params["response_format"] = response_format

            # Add any additional OpenAI-specific parameters
            params.update(kwargs)

            logger.info(
                f"Making OpenAI chat completion call with model: {actual_model}"
            )

            response = self.client.chat.completions.create(**params)

            # Convert to standard format
            return {
                "choices": [
                    {
                        "message": {
                            "content": response.choices[0].message.content,
                            "role": response.choices[0].message.role,
                        }
                    }
                ],
                "provider": self.provider_name,
                "model": actual_model,
            }

        except Exception as e:
            logger.error(f"OpenAI chat completion failed: {e}")
            raise

    async def simple_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """OpenAI simple completion implementation"""
        try:
            messages = [{"role": "user", "content": prompt}]

            response = await self.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
                **kwargs,
            )

            return response["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"OpenAI simple completion failed: {e}")
            raise

    def get_provider_name(self) -> str:
        """Get provider name"""
        return self.provider_name

    def get_available_models(self) -> List[str]:
        """Get available OpenAI models"""
        return list(self.models.keys())

    def get_default_model(self) -> str:
        """Get default OpenAI model"""
        return self.default_model

    async def validate_connection(self) -> bool:
        """Test OpenAI connection"""
        try:
            await self.simple_completion(prompt="Hello", max_tokens=5)
            logger.info("OpenAI connection validated successfully")
            return True
        except Exception as e:
            logger.error(f"OpenAI connection validation failed: {e}")
            return False

    async def create_embedding(
        self, text: str, model: Optional[str] = None, **kwargs
    ) -> List[float]:
        """Create text embeddings using OpenAI's embedding models"""
        try:
            # Use provided model or default embedding model
            actual_model = model or self.default_embedding_model

            logger.info(f"Creating embedding with model: {actual_model}")

            response = self.client.embeddings.create(
                input=text, model=actual_model, **kwargs
            )

            # Extract embedding vector from response
            embedding = response.data[0].embedding

            logger.info(
                f"Successfully created embedding with {len(embedding)} dimensions"
            )
            return embedding

        except Exception as e:
            logger.error(f"OpenAI embedding creation failed: {e}")
            raise
