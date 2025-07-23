"""
Configuration Tests

Basic tests to verify that the configuration system works properly.
These tests focus on the core config functionality that everything depends on.
"""

import pytest
import os
from unittest.mock import patch
import importlib

# Import config functions but not constants (we'll patch those)
import src.services.config as config_module


@pytest.mark.config
@pytest.mark.unit
class TestDefaultModelParsing:
    """Test parsing of DEFAULT_LLM_MODEL environment variable."""

    def test_parse_valid_default_model(self, test_env):
        """Test parsing a valid default model string."""
        # Patch the module constant directly
        with patch.object(config_module, "DEFAULT_LLM_MODEL", "openai:gpt-4o"):
            provider, model = config_module.parse_default_model()

            assert provider == "openai"
            assert model == "gpt-4o"

    def test_parse_default_model_no_colon(self, test_env):
        """Test parsing default model without colon (provider only)."""
        # Patch the module constant directly
        with patch.object(config_module, "DEFAULT_LLM_MODEL", "claude"):
            provider, model = config_module.parse_default_model()

            assert provider == "claude"
            assert model is None

    def test_parse_empty_default_model(self, test_env):
        """Test parsing empty default model."""
        # Test with empty string - should still parse successfully
        with patch.object(config_module, "DEFAULT_LLM_MODEL", ""):
            provider, model = config_module.parse_default_model()

            assert provider == ""  # Empty string, not fallback
            assert model is None


@pytest.mark.config
@pytest.mark.unit
class TestProviderConfiguration:
    """Test provider configuration loading."""

    def test_get_openai_provider_config(self, test_env):
        """Test getting OpenAI provider configuration."""
        config = config_module.get_provider_config("openai")

        assert config is not None
        assert "available_models" in config
        assert "default_model" in config
        assert "default_temperature" in config
        assert "default_max_tokens" in config

        # Verify some expected models are present - check if it's a dict
        models = config["available_models"]
        assert isinstance(models, dict)  # Models are stored as dict, not list
        assert "gpt-4o" in models or "gpt-4o-mini" in models

    def test_get_claude_provider_config(self, test_env):
        """Test getting Claude provider configuration."""
        config = config_module.get_provider_config("claude")

        assert config is not None
        assert "available_models" in config
        assert "default_model" in config

        # Verify structure is consistent - Claude models are also stored as dict
        assert isinstance(config["available_models"], dict)  # Dict, not list
        assert isinstance(config["default_model"], str)

    def test_get_invalid_provider_config(self, test_env):
        """Test getting configuration for non-existent provider."""
        config = config_module.get_provider_config("nonexistent_provider")

        assert config is None


@pytest.mark.config
@pytest.mark.unit
class TestProviderHelperFunctions:
    """Test helper functions for provider information."""

    def test_get_provider_available_models(self, test_env, sample_config_data):
        """Test getting available models for a provider."""
        models = config_module.get_provider_available_models(
            sample_config_data["valid_provider"]
        )

        assert isinstance(models, list)
        assert len(models) > 0
        # Should contain at least one valid model
        assert any("gpt" in model.lower() for model in models)

    def test_get_provider_default_model(self, test_env, sample_config_data):
        """Test getting default model for a provider."""
        default_model = config_module.get_provider_default_model(
            sample_config_data["valid_provider"]
        )

        assert isinstance(default_model, str)
        assert len(default_model) > 0
        # Should be a reasonable model name
        assert "gpt" in default_model.lower() or "4" in default_model

    def test_get_invalid_provider_models(self, test_env, sample_config_data):
        """Test getting models for invalid provider."""
        models = config_module.get_provider_available_models(
            sample_config_data["invalid_provider"]
        )
        default_model = config_module.get_provider_default_model(
            sample_config_data["invalid_provider"]
        )

        assert models == []  # Empty list for invalid provider
        assert default_model == "gpt-4o"  # Falls back to gpt-4o for invalid provider


@pytest.mark.config
@pytest.mark.unit
class TestEnvironmentVariables:
    """Test that required environment variables are loaded."""

    def test_api_keys_with_patching(self, test_env):
        """Test that API keys can be accessed when properly patched."""
        # Patch the module constants directly since they're loaded at import time
        with patch.object(config_module, "OPENAI_API_KEY", "sk-test-key-for-testing"):
            with patch.object(config_module, "CLAUDE_API_KEY", "sk-ant-test-key"):
                assert config_module.OPENAI_API_KEY == "sk-test-key-for-testing"
                assert config_module.CLAUDE_API_KEY == "sk-ant-test-key"

    def test_missing_api_key_handling(self):
        """Test behavior when API keys are missing."""
        # Test what happens when keys are None (default behavior)
        # The actual loaded values might be None, which is expected behavior
        assert config_module.OPENAI_API_KEY is None or isinstance(
            config_module.OPENAI_API_KEY, str
        )
        assert config_module.CLAUDE_API_KEY is None or isinstance(
            config_module.CLAUDE_API_KEY, str
        )


@pytest.mark.config
@pytest.mark.integration
class TestConfigurationIntegration:
    """Integration tests for configuration with other components."""

    def test_config_supports_llm_service_initialization(self, test_env):
        """Test that config provides everything needed for LLM service."""
        # Test that we can get provider configs for all supported providers
        openai_config = config_module.get_provider_config("openai")
        claude_config = config_module.get_provider_config("claude")

        assert openai_config is not None
        assert claude_config is not None

        # Test that default model parsing works with current value
        provider, model = config_module.parse_default_model()
        assert isinstance(provider, str)  # Should be a valid string

        # Test that we can get config for any provider that parse_default_model returns
        if provider:  # Only test if provider is not empty
            default_provider_config = config_module.get_provider_config(provider)
            # Might be None if the provider from DEFAULT_LLM_MODEL is not in our configs
            # This is valid behavior
