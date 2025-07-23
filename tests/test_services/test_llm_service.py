"""
LLM Service Tests

Tests for the unified LLM service that handles provider switching
and provides a consistent interface for AI completions.
"""

import pytest
import asyncio
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Mock the provider modules before any imports to avoid dependency issues
sys.modules["src.providers.openai_provider"] = MagicMock()
sys.modules["src.providers.claude_provider"] = MagicMock()

from src.services.llm_service import LLMService
from src.interfaces.llm_interface import LLMInterface


@pytest.fixture
def mock_openai_provider():
    """Mock OpenAI provider for testing."""
    provider = Mock(spec=LLMInterface)
    provider.get_provider_name.return_value = "openai"
    provider.get_available_models.return_value = ["gpt-4o", "gpt-4o-mini"]
    provider.get_default_model.return_value = "gpt-4o"
    provider.chat_completion = AsyncMock(
        return_value={
            "choices": [{"message": {"content": "Test response from OpenAI"}}]
        }
    )
    provider.simple_completion = AsyncMock(
        return_value="Simple test response from OpenAI"
    )
    provider.validate_connection = AsyncMock(return_value=True)
    return provider


@pytest.fixture
def mock_claude_provider():
    """Mock Claude provider for testing."""
    provider = Mock(spec=LLMInterface)
    provider.get_provider_name.return_value = "claude"
    provider.get_available_models.return_value = ["claude-3-5-sonnet", "claude-3-haiku"]
    provider.get_default_model.return_value = "claude-3-5-sonnet"
    provider.chat_completion = AsyncMock(
        return_value={
            "choices": [{"message": {"content": "Test response from Claude"}}]
        }
    )
    provider.simple_completion = AsyncMock(
        return_value="Simple test response from Claude"
    )
    provider.validate_connection = AsyncMock(return_value=True)
    return provider


@pytest.fixture
def mock_openai_provider_class():
    """Mock OpenAI provider class for patching."""

    def create_provider():
        provider = Mock(spec=LLMInterface)
        provider.get_provider_name.return_value = "openai"
        provider.get_available_models.return_value = ["gpt-4o", "gpt-4o-mini"]
        provider.get_default_model.return_value = "gpt-4o"
        provider.chat_completion = AsyncMock(
            return_value={
                "choices": [{"message": {"content": "Test response from OpenAI"}}]
            }
        )
        provider.simple_completion = AsyncMock(
            return_value="Simple test response from OpenAI"
        )
        provider.validate_connection = AsyncMock(return_value=True)
        return provider

    return create_provider


@pytest.fixture
def mock_claude_provider_class():
    """Mock Claude provider class for patching."""

    def create_provider():
        provider = Mock(spec=LLMInterface)
        provider.get_provider_name.return_value = "claude"
        provider.get_available_models.return_value = [
            "claude-3-5-sonnet",
            "claude-3-haiku",
        ]
        provider.get_default_model.return_value = "claude-3-5-sonnet"
        provider.chat_completion = AsyncMock(
            return_value={
                "choices": [{"message": {"content": "Test response from Claude"}}]
            }
        )
        provider.simple_completion = AsyncMock(
            return_value="Simple test response from Claude"
        )
        provider.validate_connection = AsyncMock(return_value=True)
        return provider

    return create_provider


@pytest.mark.llm
@pytest.mark.unit
class TestLLMServiceInitialization:
    """Test LLM service initialization and setup."""

    def test_service_initialization_with_providers(
        self, mock_openai_provider_class, mock_claude_provider_class
    ):
        """Test service initializes correctly with available providers."""
        with patch(
            "src.services.llm_service.OpenAIProvider", mock_openai_provider_class
        ):
            with patch(
                "src.services.llm_service.ClaudeProvider", mock_claude_provider_class
            ):
                with patch(
                    "src.services.llm_service.os.getenv",
                    side_effect=lambda key: (
                        "test-key" if key == "CLAUDE_API_KEY" else None
                    ),
                ):
                    with patch(
                        "src.services.llm_service.parse_default_model",
                        return_value=("openai", "gpt-4o"),
                    ):
                        service = LLMService()

        # Verify providers are registered
        assert "openai" in service.providers
        assert "claude" in service.providers
        assert len(service.providers) == 2

        # Verify default provider is set
        assert service.get_current_provider() == "openai"
        assert service.default_provider_name == "openai"
        assert service.default_model_name == "gpt-4o"

    def test_service_initialization_openai_only(self, mock_openai_provider_class):
        """Test service initializes with only OpenAI when Claude API key missing."""
        with patch(
            "src.services.llm_service.OpenAIProvider", mock_openai_provider_class
        ):
            with patch("src.services.llm_service.os.getenv", return_value=None):
                with patch(
                    "src.services.llm_service.parse_default_model",
                    return_value=("openai", "gpt-4o"),
                ):
                    service = LLMService()

        # Verify only OpenAI is registered
        assert "openai" in service.providers
        assert "claude" not in service.providers
        assert len(service.providers) == 1

        # Verify default provider is set
        assert service.get_current_provider() == "openai"

    def test_service_initialization_with_explicit_provider(
        self, mock_openai_provider_class
    ):
        """Test service initialization with explicit default provider."""
        with patch(
            "src.services.llm_service.OpenAIProvider", mock_openai_provider_class
        ):
            with patch(
                "src.services.llm_service.parse_default_model",
                return_value=("claude", "claude-3-5-sonnet"),
            ):
                service = LLMService(default_provider="openai")

        # Should override config default with explicit provider
        assert service.default_provider_name == "openai"
        assert service.get_current_provider() == "openai"


@pytest.mark.llm
@pytest.mark.unit
class TestProviderManagement:
    """Test provider switching and management."""

    def setup_service_with_providers(
        self, mock_openai_provider_class, mock_claude_provider_class
    ):
        """Helper to create service with both providers."""
        with patch(
            "src.services.llm_service.OpenAIProvider", mock_openai_provider_class
        ):
            with patch(
                "src.services.llm_service.ClaudeProvider", mock_claude_provider_class
            ):
                with patch(
                    "src.services.llm_service.os.getenv",
                    side_effect=lambda key: (
                        "test-key" if key == "CLAUDE_API_KEY" else None
                    ),
                ):
                    with patch(
                        "src.services.llm_service.parse_default_model",
                        return_value=("openai", "gpt-4o"),
                    ):
                        return LLMService()

    def test_set_provider_success(
        self, mock_openai_provider_class, mock_claude_provider_class
    ):
        """Test successfully switching providers."""
        service = self.setup_service_with_providers(
            mock_openai_provider_class, mock_claude_provider_class
        )

        # Switch to Claude
        result = service.set_provider("claude")
        assert result is True
        assert service.get_current_provider() == "claude"

        # Switch back to OpenAI
        result = service.set_provider("openai")
        assert result is True
        assert service.get_current_provider() == "openai"

    def test_set_provider_invalid(
        self, mock_openai_provider_class, mock_claude_provider_class
    ):
        """Test switching to invalid provider."""
        service = self.setup_service_with_providers(
            mock_openai_provider_class, mock_claude_provider_class
        )

        # Try to switch to non-existent provider
        result = service.set_provider("grok")
        assert result is False
        assert service.get_current_provider() == "openai"  # Should remain unchanged

    def test_get_available_providers(
        self, mock_openai_provider_class, mock_claude_provider_class
    ):
        """Test getting list of available providers."""
        service = self.setup_service_with_providers(
            mock_openai_provider_class, mock_claude_provider_class
        )

        providers = service.get_available_providers()
        assert isinstance(providers, list)
        assert "openai" in providers
        assert "claude" in providers
        assert len(providers) == 2


@pytest.mark.llm
@pytest.mark.unit
class TestChatCompletion:
    """Test chat completion functionality."""

    def setup_simple_service(self, mock_openai_provider_class):
        """Helper to create service with OpenAI only."""
        with patch(
            "src.services.llm_service.OpenAIProvider", mock_openai_provider_class
        ):
            with patch(
                "src.services.llm_service.parse_default_model",
                return_value=("openai", "gpt-4o"),
            ):
                return LLMService()

    @pytest.mark.asyncio
    async def test_chat_completion_basic(self, mock_openai_provider_class):
        """Test basic chat completion."""
        service = self.setup_simple_service(mock_openai_provider_class)

        messages = [{"role": "user", "content": "Hello"}]
        result = await service.chat_completion(messages)

        # Verify response structure
        assert "choices" in result
        assert len(result["choices"]) > 0
        assert "message" in result["choices"][0]
        assert "content" in result["choices"][0]["message"]

        # Verify provider was called
        openai_provider = service.providers["openai"]
        openai_provider.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_completion_with_parameters(self, mock_openai_provider_class):
        """Test chat completion with all parameters."""
        service = self.setup_simple_service(mock_openai_provider_class)

        messages = [{"role": "user", "content": "Hello"}]
        result = await service.chat_completion(
            messages=messages,
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=100,
            response_format={"type": "json_object"},
        )

        # Verify provider was called with correct parameters
        openai_provider = service.providers["openai"]
        openai_provider.chat_completion.assert_called_once_with(
            messages=messages,
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=100,
            response_format={"type": "json_object"},
        )

    @pytest.mark.asyncio
    async def test_chat_completion_with_provider_override(
        self, mock_openai_provider_class, mock_claude_provider_class
    ):
        """Test chat completion with provider override."""
        # Setup service with both providers
        with patch(
            "src.services.llm_service.OpenAIProvider", mock_openai_provider_class
        ):
            with patch(
                "src.services.llm_service.ClaudeProvider", mock_claude_provider_class
            ):
                with patch(
                    "src.services.llm_service.os.getenv",
                    side_effect=lambda key: (
                        "test-key" if key == "CLAUDE_API_KEY" else None
                    ),
                ):
                    with patch(
                        "src.services.llm_service.parse_default_model",
                        return_value=("openai", "gpt-4o"),
                    ):
                        service = LLMService()

        messages = [{"role": "user", "content": "Hello"}]

        # Call with provider override
        result = await service.chat_completion(messages, provider="claude")

        # Verify Claude provider was called, not OpenAI
        claude_provider = service.providers["claude"]
        openai_provider = service.providers["openai"]
        claude_provider.chat_completion.assert_called_once()
        openai_provider.chat_completion.assert_not_called()

    @pytest.mark.asyncio
    async def test_chat_completion_no_provider(self):
        """Test chat completion when no provider available."""
        # Create service with no providers
        with patch(
            "src.services.llm_service.OpenAIProvider",
            side_effect=Exception("No provider"),
        ):
            with patch(
                "src.services.llm_service.parse_default_model",
                return_value=("openai", "gpt-4o"),
            ):
                service = LLMService()

        messages = [{"role": "user", "content": "Hello"}]

        with pytest.raises(RuntimeError, match="No LLM provider available"):
            await service.chat_completion(messages)


@pytest.mark.llm
@pytest.mark.unit
class TestSimpleCompletion:
    """Test simple completion functionality."""

    def setup_simple_service(self, mock_openai_provider_class):
        """Helper to create service with OpenAI only."""
        with patch(
            "src.services.llm_service.OpenAIProvider", mock_openai_provider_class
        ):
            with patch(
                "src.services.llm_service.parse_default_model",
                return_value=("openai", "gpt-4o"),
            ):
                return LLMService()

    @pytest.mark.asyncio
    async def test_simple_completion_basic(self, mock_openai_provider_class):
        """Test basic simple completion."""
        service = self.setup_simple_service(mock_openai_provider_class)

        result = await service.simple_completion("Hello world")

        # Verify response is a string
        assert isinstance(result, str)
        assert len(result) > 0

        # Verify provider was called
        openai_provider = service.providers["openai"]
        openai_provider.simple_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_simple_completion_with_parameters(self, mock_openai_provider_class):
        """Test simple completion with parameters."""
        service = self.setup_simple_service(mock_openai_provider_class)

        result = await service.simple_completion(
            prompt="Hello world", model="gpt-4o-mini", temperature=0.5, max_tokens=50
        )

        # Verify provider was called with correct parameters
        openai_provider = service.providers["openai"]
        openai_provider.simple_completion.assert_called_once_with(
            prompt="Hello world",
            model="gpt-4o-mini",
            temperature=0.5,
            max_tokens=50,
            response_format=None,
        )


@pytest.mark.llm
@pytest.mark.unit
class TestDefaultModelHandling:
    """Test default model configuration handling."""

    def test_default_model_used_when_none_specified(self, mock_openai_provider_class):
        """Test that default model is used when none specified."""
        with patch(
            "src.services.llm_service.OpenAIProvider", mock_openai_provider_class
        ):
            with patch(
                "src.services.llm_service.parse_default_model",
                return_value=("openai", "gpt-4o"),
            ):
                service = LLMService()

        # Verify default model settings
        assert service.default_provider_name == "openai"
        assert service.default_model_name == "gpt-4o"
        assert service.get_global_default_model() == "openai:gpt-4o"

    def test_default_model_provider_only(self, mock_openai_provider_class):
        """Test default model handling when only provider specified."""
        with patch(
            "src.services.llm_service.OpenAIProvider", mock_openai_provider_class
        ):
            with patch(
                "src.services.llm_service.parse_default_model",
                return_value=("openai", None),
            ):
                service = LLMService()

        # Verify default model settings
        assert service.default_provider_name == "openai"
        assert service.default_model_name is None
        assert service.get_global_default_model() == "openai"


@pytest.mark.llm
@pytest.mark.unit
class TestProviderValidation:
    """Test provider validation and info functionality."""

    def setup_service_with_providers(
        self, mock_openai_provider_class, mock_claude_provider_class
    ):
        """Helper to create service with both providers."""
        with patch(
            "src.services.llm_service.OpenAIProvider", mock_openai_provider_class
        ):
            with patch(
                "src.services.llm_service.ClaudeProvider", mock_claude_provider_class
            ):
                with patch(
                    "src.services.llm_service.os.getenv",
                    side_effect=lambda key: (
                        "test-key" if key == "CLAUDE_API_KEY" else None
                    ),
                ):
                    with patch(
                        "src.services.llm_service.parse_default_model",
                        return_value=("openai", "gpt-4o"),
                    ):
                        return LLMService()

    @pytest.mark.asyncio
    async def test_validate_all_providers(
        self, mock_openai_provider_class, mock_claude_provider_class
    ):
        """Test validation of all providers."""
        service = self.setup_service_with_providers(
            mock_openai_provider_class, mock_claude_provider_class
        )

        results = await service.validate_all_providers()

        # Verify all providers were validated
        assert "openai" in results
        assert "claude" in results
        assert results["openai"] is True
        assert results["claude"] is True

        # Verify validation methods were called
        openai_provider = service.providers["openai"]
        claude_provider = service.providers["claude"]
        openai_provider.validate_connection.assert_called_once()
        claude_provider.validate_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_providers_with_failure(
        self, mock_openai_provider_class, mock_claude_provider_class
    ):
        """Test validation when one provider fails."""

        # Create a failing Claude provider
        def create_failing_claude_provider():
            provider = Mock(spec=LLMInterface)
            provider.get_provider_name.return_value = "claude"
            provider.get_available_models.return_value = [
                "claude-3-5-sonnet",
                "claude-3-haiku",
            ]
            provider.get_default_model.return_value = "claude-3-5-sonnet"
            provider.chat_completion = AsyncMock(
                return_value={
                    "choices": [{"message": {"content": "Test response from Claude"}}]
                }
            )
            provider.simple_completion = AsyncMock(
                return_value="Simple test response from Claude"
            )
            provider.validate_connection = AsyncMock(
                side_effect=Exception("Connection failed")
            )
            return provider

        service = self.setup_service_with_providers(
            mock_openai_provider_class, create_failing_claude_provider
        )

        results = await service.validate_all_providers()

        # Verify results reflect the failure
        assert results["openai"] is True
        assert results["claude"] is False

    def test_get_provider_info(
        self, mock_openai_provider_class, mock_claude_provider_class
    ):
        """Test getting provider information."""
        service = self.setup_service_with_providers(
            mock_openai_provider_class, mock_claude_provider_class
        )

        info = service.get_provider_info()

        # Verify structure
        assert "openai" in info
        assert "claude" in info

        # Verify OpenAI info
        openai_info = info["openai"]
        assert "available_models" in openai_info
        assert "default_model" in openai_info
        assert "provider_name" in openai_info
        assert openai_info["provider_name"] == "openai"

        # Verify Claude info
        claude_info = info["claude"]
        assert "available_models" in claude_info
        assert "default_model" in claude_info
        assert "provider_name" in claude_info
        assert claude_info["provider_name"] == "claude"


@pytest.mark.llm
@pytest.mark.integration
class TestLLMServiceIntegration:
    """Integration tests for LLM service with real-ish scenarios."""

    def test_service_ready_for_use(self, mock_openai_provider_class):
        """Test that service is ready for typical usage patterns."""
        with patch(
            "src.services.llm_service.OpenAIProvider", mock_openai_provider_class
        ):
            with patch(
                "src.services.llm_service.parse_default_model",
                return_value=("openai", "gpt-4o"),
            ):
                service = LLMService()

        # Service should be ready
        assert service.current_provider is not None
        assert service.get_current_provider() == "openai"
        assert len(service.get_available_providers()) > 0

        # Should have provider info available
        info = service.get_provider_info()
        assert len(info) > 0
        assert "openai" in info

    @pytest.mark.asyncio
    async def test_end_to_end_completion_flow(self, mock_openai_provider_class):
        """Test complete flow from initialization to completion."""
        with patch(
            "src.services.llm_service.OpenAIProvider", mock_openai_provider_class
        ):
            with patch(
                "src.services.llm_service.parse_default_model",
                return_value=("openai", "gpt-4o"),
            ):
                service = LLMService()

        # Validate service is working
        validation_results = await service.validate_all_providers()
        assert validation_results["openai"] is True

        # Test chat completion
        chat_result = await service.chat_completion(
            [{"role": "user", "content": "Hello"}]
        )
        assert "choices" in chat_result

        # Test simple completion
        simple_result = await service.simple_completion("Hello")
        assert isinstance(simple_result, str)

        # Both should have called the provider
        openai_provider = service.providers["openai"]
        assert openai_provider.chat_completion.call_count == 1
        assert openai_provider.simple_completion.call_count == 1
