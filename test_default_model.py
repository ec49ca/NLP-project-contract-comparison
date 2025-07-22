"""
Test script to demonstrate the new default model functionality
"""

import asyncio
import os
from src.services.llm_service import llm_service


async def test_default_model():
    """Test the default model functionality"""

    print("🧪 Testing Default Model Configuration")
    print("=" * 50)

    # Show current global default
    print(f"📋 Global default model: {llm_service.get_global_default_model()}")
    print(f"🎯 Current provider: {llm_service.get_current_provider()}")

    # Test 1: Default behavior (should use global default model)
    print(f"\n📝 Test 1: Using global default model...")
    try:
        response1 = await llm_service.simple_completion(
            "Say 'hello' in exactly one word", max_tokens=5
        )
        print(f"✅ Response with default model: {response1}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 2: Override model (should use specified model)
    print(f"\n📝 Test 2: Overriding with specific model...")
    try:
        response2 = await llm_service.simple_completion(
            "Say 'goodbye' in exactly one word",
            model="gpt-4o-mini",  # Override the default
            max_tokens=5,
        )
        print(f"✅ Response with gpt-4o-mini: {response2}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 3: Override provider (should use that provider's default)
    print(f"\n📝 Test 3: Overriding provider...")
    try:
        response3 = await llm_service.simple_completion(
            "Say 'hi' in exactly one word",
            provider="claude",  # Different provider
            max_tokens=5,
        )
        print(f"✅ Response with Claude: {response3}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 4: Override both provider and model
    print(f"\n📝 Test 4: Overriding both provider and model...")
    try:
        response4 = await llm_service.simple_completion(
            "Say 'hey' in exactly one word",
            provider="openai",
            model="gpt-3.5-turbo",  # Specific model
            max_tokens=5,
        )
        print(f"✅ Response with OpenAI gpt-3.5-turbo: {response4}")
    except Exception as e:
        print(f"❌ Error: {e}")


async def demonstrate_configuration():
    """Demonstrate different configuration options"""

    print(f"\n" + "=" * 50)
    print("🔧 Configuration Examples")
    print("=" * 50)

    print("📝 Set in .env file:")
    print("# For OpenAI GPT-4o (default)")
    print("DEFAULT_LLM_MODEL=openai:gpt-4o")
    print()
    print("# For OpenAI GPT-4o-mini")
    print("DEFAULT_LLM_MODEL=openai:gpt-4o-mini")
    print()
    print("# For Claude Sonnet")
    print("DEFAULT_LLM_MODEL=claude:claude-3-5-sonnet")
    print()
    print("# For Claude Opus")
    print("DEFAULT_LLM_MODEL=claude:claude-3-opus")

    print(f"\n📊 Current provider info:")
    info = llm_service.get_provider_info()
    for provider_name, details in info.items():
        print(f"  {provider_name}:")
        print(f"    Default model: {details['default_model']}")
        print(f"    Available models: {details['available_models']}")


if __name__ == "__main__":
    print("🚀 Running Default Model Test...")
    asyncio.run(test_default_model())
    asyncio.run(demonstrate_configuration())
    print("✅ Test complete!")
