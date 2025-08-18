"""
Configuration for external services and LLM providers
"""

import os
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# =============================================================================
# LLM Provider Configuration
# =============================================================================

# Global LLM provider selection
LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "openai")

# Global default model (format: "provider:model" or just "provider")
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "openai:gpt-4o")

# =============================================================================
# Provider Model Configurations (Single Source of Truth)
# =============================================================================

PROVIDER_MODEL_CONFIGS = {
    "openai": {
        "available_models": {
            "gpt-4o": "gpt-4o",
            "gpt-4o-mini": "gpt-4o-mini",
            "gpt-4": "gpt-4",
            "gpt-3.5-turbo": "gpt-3.5-turbo",
        },
        "embedding_models": {
            "text-embedding-3-large": "text-embedding-3-large",
            "text-embedding-3-small": "text-embedding-3-small",
            "text-embedding-ada-002": "text-embedding-ada-002",
        },
        "default_model": "gpt-4o",
        "default_embedding_model": "text-embedding-3-small",
        "default_temperature": 0.1,
        "default_max_tokens": 8000,
    },
    "claude": {
        "available_models": {
            "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
            "claude-3-opus": "claude-3-opus-20240229",
            "claude-3-haiku": "claude-3-haiku-20240307",
        },
        "default_model": "claude-3-5-sonnet",
        "default_temperature": 0.1,
        "default_max_tokens": 4000,
    },
    "grok": {
        "available_models": {"grok-1": "grok-1", "grok-1.5": "grok-1.5"},
        "default_model": "grok-1",
        "default_temperature": 0.1,
        "default_max_tokens": 4000,
    },
}


def get_provider_config(provider_name: str) -> Optional[Dict]:
    """Get model configuration for a specific provider"""
    return PROVIDER_MODEL_CONFIGS.get(provider_name)


def get_provider_default_model(provider_name: str) -> str:
    """Get default model for a specific provider"""
    config = get_provider_config(provider_name)
    return config["default_model"] if config else "gpt-4o"


def get_provider_available_models(provider_name: str) -> List[str]:
    """Get available models for a specific provider"""
    config = get_provider_config(provider_name)
    return list(config["available_models"].keys()) if config else []


def parse_default_model() -> tuple[str, str]:
    """Parse DEFAULT_LLM_MODEL into provider and model"""
    if ":" in DEFAULT_LLM_MODEL:
        provider, model = DEFAULT_LLM_MODEL.split(":", 1)
        return provider.strip(), model.strip()
    else:
        # If no model specified, use provider's default
        return DEFAULT_LLM_MODEL.strip(), None


# =============================================================================
# API Keys Configuration (Only secrets go in .env)
# =============================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
GROK_API_KEY = os.getenv("GROK_API_KEY")


# =============================================================================
# Provider Registry (API Keys + Model Config Combined)
# =============================================================================
def get_provider_registry() -> Dict[str, Dict]:
    """Get combined provider registry with API keys and model configs"""
    registry = {}

    for provider_name, model_config in PROVIDER_MODEL_CONFIGS.items():
        # Get API key based on provider
        api_key = None
        if provider_name == "openai":
            api_key = OPENAI_API_KEY
        elif provider_name == "claude":
            api_key = CLAUDE_API_KEY
        elif provider_name == "grok":
            api_key = GROK_API_KEY

        registry[provider_name] = {
            "api_key": api_key,
            "required": provider_name == "openai",  # Only OpenAI is required
            **model_config,  # Merge in all model config
        }

    return registry


# Legacy compatibility
PROVIDER_CONFIGS = get_provider_registry()

# =============================================================================
# Validation Functions
# =============================================================================


def validate_openai_config() -> bool:
    """Validate OpenAI configuration (backward compatibility)"""
    logger.info("Validating OpenAI configuration...")
    logger.info("OPENAI_API_KEY present", extra={'present': bool(OPENAI_API_KEY)})

    config = get_provider_config("openai")
    if config:
        logger.info("OPENAI_DEFAULT_MODEL", extra={'model': config['default_model']})
        logger.info("OPENAI_MAX_TOKENS", extra={'max_tokens': config['default_max_tokens']})
        logger.info("OPENAI_TEMPERATURE", extra={'temperature': config['default_temperature']})

    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY environment variable is required")
        raise ValueError("OPENAI_API_KEY environment variable is required")

    if not OPENAI_API_KEY.startswith("sk-"):
        logger.warning("OPENAI_API_KEY doesn't start with 'sk-'", extra={'key_preview': OPENAI_API_KEY[:10]})

    logger.info("OpenAI configuration validation successful")
    return True


def validate_claude_config() -> bool:
    """Validate Claude configuration"""
    logger.info("Validating Claude configuration...")
    logger.info("CLAUDE_API_KEY present", extra={'present': bool(CLAUDE_API_KEY)})

    config = get_provider_config("claude")
    if config:
        logger.info("CLAUDE_DEFAULT_MODEL", extra={'model': config['default_model']})
        logger.info("CLAUDE_MAX_TOKENS", extra={'max_tokens': config['default_max_tokens']})
        logger.info("CLAUDE_TEMPERATURE", extra={'temperature': config['default_temperature']})

    if not CLAUDE_API_KEY:
        logger.warning(
            "CLAUDE_API_KEY not provided - Claude provider will be unavailable"
        )
        return False

    logger.info("Claude configuration validation successful")
    return True


def validate_grok_config() -> bool:
    """Validate Grok configuration"""
    logger.info("Validating Grok configuration...")
    logger.info("GROK_API_KEY present", extra={'present': bool(GROK_API_KEY)})

    config = get_provider_config("grok")
    if config:
        logger.info("GROK_DEFAULT_MODEL", extra={'model': config['default_model']})
        logger.info("GROK_MAX_TOKENS", extra={'max_tokens': config['default_max_tokens']})
        logger.info("GROK_TEMPERATURE", extra={'temperature': config['default_temperature']})

    if not GROK_API_KEY:
        logger.warning("GROK_API_KEY not provided - Grok provider will be unavailable")
        return False

    logger.info("Grok configuration validation successful")
    return True


def validate_provider_config(provider_name: str) -> bool:
    """Validate configuration for a specific provider"""
    if provider_name == "openai":
        return validate_openai_config()
    elif provider_name == "claude":
        return validate_claude_config()
    elif provider_name == "grok":
        return validate_grok_config()
    else:
        logger.error("Unknown provider", extra={'provider_name': provider_name})
        return False


def validate_all_provider_configs() -> Dict[str, bool]:
    """Validate all provider configurations"""
    logger.info("Validating all LLM provider configurations...")

    results = {}
    provider_registry = get_provider_registry()

    for provider_name, config in provider_registry.items():
        try:
            is_valid = validate_provider_config(provider_name)
            results[provider_name] = is_valid

            if config["required"] and not is_valid:
                raise ValueError(
                    f"Required provider {provider_name} configuration is invalid"
                )

        except Exception as e:
            logger.error("Error validating provider", extra={'provider_name': provider_name, 'error': str(e)})
            results[provider_name] = False

            if config["required"]:
                raise

    # Validate global provider selection
    if LLM_PROVIDER not in provider_registry:
        logger.error("Invalid LLM_PROVIDER", extra={'invalid_provider': LLM_PROVIDER, 'available_providers': list(provider_registry.keys())})
        raise ValueError(f"Invalid LLM_PROVIDER '{LLM_PROVIDER}'")

    if not results.get(LLM_PROVIDER, False):
        logger.error("Selected LLM_PROVIDER is not properly configured", extra={'selected_provider': LLM_PROVIDER})
        raise ValueError(f"Selected LLM_PROVIDER '{LLM_PROVIDER}' is not available")

    available_providers = [name for name, valid in results.items() if valid]
    logger.info("Provider validation complete", extra={'available_providers': available_providers})
    logger.info("Selected provider", extra={'selected_provider': LLM_PROVIDER})

    return results


def get_available_providers() -> List[str]:
    """Get list of available (properly configured) providers"""
    available = []
    for provider_name in PROVIDER_MODEL_CONFIGS:
        try:
            if validate_provider_config(provider_name):
                available.append(provider_name)
        except Exception:
            continue  # Skip providers with invalid config
    return available


def get_full_provider_config(provider_name: str) -> Optional[Dict]:
    """Get full configuration (API key + models) for a specific provider"""
    return get_provider_registry().get(provider_name)
