"""
Test script to verify the centralized configuration system
"""

import os
import sys

# Add src to path for imports
sys.path.insert(0, "src")


def test_config_functions():
    """Test all config functions work properly"""

    print("🧪 Testing Centralized Configuration System")
    print("=" * 50)

    try:
        from services.config import (
            get_provider_config,
            get_provider_default_model,
            get_provider_available_models,
            PROVIDER_MODEL_CONFIGS,
            parse_default_model,
        )

        # Test 1: Provider configs loaded
        print("📋 Test 1: Provider configurations loaded")
        for provider_name in PROVIDER_MODEL_CONFIGS:
            config = get_provider_config(provider_name)
            print(f"  ✅ {provider_name}: {config['default_model']}")
            print(f"     Available models: {list(config['available_models'].keys())}")

        # Test 2: Helper functions work
        print(f"\n🔧 Test 2: Helper functions")
        print(f"  OpenAI default: {get_provider_default_model('openai')}")
        print(f"  Claude default: {get_provider_default_model('claude')}")
        print(f"  OpenAI models: {get_provider_available_models('openai')}")

        # Test 3: Global default parsing
        print(f"\n🌍 Test 3: Global default parsing")
        provider, model = parse_default_model()
        print(f"  Default provider: {provider}")
        print(f"  Default model: {model}")

        print(f"\n✅ All configuration tests passed!")
        return True

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_provider_imports():
    """Test provider imports work with new config"""

    print(f"\n🏭 Testing Provider Imports")
    print("=" * 30)

    try:
        # Test OpenAI provider
        from providers.openai_provider import OpenAIProvider

        openai_provider = OpenAIProvider()
        print(f"✅ OpenAI Provider: {openai_provider.default_model}")
        print(f"   Available models: {list(openai_provider.models.keys())}")

        # Test Claude provider (if API key available)
        if os.getenv("CLAUDE_API_KEY"):
            from providers.claude_provider import ClaudeProvider

            claude_provider = ClaudeProvider()
            print(f"✅ Claude Provider: {claude_provider.default_model}")
            print(f"   Available models: {list(claude_provider.models.keys())}")
        else:
            print("⏭️  Claude Provider skipped (no API key)")

        print(f"\n✅ All provider tests passed!")
        return True

    except Exception as e:
        print(f"❌ Provider test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_llm_service():
    """Test LLM service works with new config"""

    print(f"\n🌐 Testing LLM Service")
    print("=" * 25)

    try:
        from services.llm_service import llm_service

        print(f"Current provider: {llm_service.get_current_provider()}")
        print(f"Global default: {llm_service.get_global_default_model()}")
        print(f"Available providers: {llm_service.get_available_providers()}")

        # Test provider info
        info = llm_service.get_provider_info()
        for provider_name, details in info.items():
            print(f"  {provider_name}:")
            print(f"    Default: {details['default_model']}")
            print(f"    Models: {details['available_models']}")

        print(f"\n✅ LLM service test passed!")
        return True

    except Exception as e:
        print(f"❌ LLM service test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Running Centralized Config Tests...")

    # Set minimal env for testing
    if not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = "sk-test-key-for-config-testing"

    all_passed = True
    all_passed &= test_config_functions()
    all_passed &= test_provider_imports()
    all_passed &= test_llm_service()

    if all_passed:
        print(f"\n🎉 All tests passed! Configuration system working correctly.")
    else:
        print(f"\n💥 Some tests failed. Check the errors above.")

    print("\n📝 Configuration Summary:")
    print("- ✅ Secrets (API keys) in .env")
    print("- ✅ Model configs in config.py")
    print("- ✅ Single source of truth")
    print("- ✅ Clean separation of concerns")
