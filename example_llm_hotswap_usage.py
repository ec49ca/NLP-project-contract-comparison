"""
Example: LLM Provider Hotswapping

This script demonstrates how to use the new LLM interface to hotswap
between different language model providers (OpenAI, Claude, Grok).
"""

import asyncio
from src.services.llm_service import llm_service


async def main():
    """Demonstrate LLM provider hotswapping"""

    print("🚀 LLM Provider Hotswapping Demo")
    print("=" * 50)

    # Show available providers
    providers = llm_service.get_available_providers()
    current = llm_service.get_current_provider()
    print(f"📋 Available providers: {providers}")
    print(f"🎯 Current provider: {current}")

    # Test with current provider
    print(f"\n🧪 Testing with {current}...")
    response1 = await llm_service.simple_completion(
        prompt="Say hello in exactly 3 words", max_tokens=10
    )
    print(f"✅ Response: {response1}")

    # Switch providers and test
    for provider in providers:
        if provider != current:
            print(f"\n🔄 Switching to {provider}...")

            if llm_service.set_provider(provider):
                try:
                    response = await llm_service.simple_completion(
                        prompt="Say goodbye in exactly 3 words", max_tokens=10
                    )
                    print(f"✅ {provider} response: {response}")
                except Exception as e:
                    print(f"❌ {provider} failed: {e}")
            else:
                print(f"⚠️  Failed to switch to {provider}")

    # Test per-call provider override
    print(f"\n🎭 Testing per-call provider override...")
    try:
        # Use OpenAI for this specific call regardless of current provider
        response = await llm_service.simple_completion(
            prompt="Count to three",
            provider="openai",  # Override provider for this call
            max_tokens=20,
        )
        print(f"✅ OpenAI override: {response}")
    except Exception as e:
        print(f"❌ Override failed: {e}")

    # Test direct LLM service usage
    print(f"\n🔧 Testing direct LLM service usage...")

    # Example of using LLM service for entity extraction
    response = await llm_service.simple_completion(
        prompt="Extract entities from: 'John Smith works at OpenAI in San Francisco.' Return as JSON.",
        provider="openai",  # Optional provider override
        response_format={"type": "json_object"},
    )
    print(f"✅ Entity extraction response: {response[:100]}...")

    # Provider info
    print(f"\n📊 Provider Information:")
    info = llm_service.get_provider_info()
    for provider_name, details in info.items():
        print(f"  {provider_name}:")
        print(f"    Default model: {details['default_model']}")
        print(f"    Available models: {details['available_models']}")


async def test_migration_example():
    """Example of migrating existing code to use new interface"""

    print("\n" + "=" * 50)
    print("🔧 Migration Example")
    print("=" * 50)

    # NEW WAY - direct LLM service usage
    print("🚀 Using unified LLM service...")

    text = "Apple Inc. was founded by Steve Jobs."

    # Extract entities with different providers
    openai_response = await llm_service.simple_completion(
        prompt=f"Extract entities from: '{text}' Return JSON with entities array.",
        provider="openai",
    )
    print(f"📊 OpenAI response: {openai_response[:100]}...")

    # Switch providers and test
    print(f"🔄 Current provider: {llm_service.get_current_provider()}")

    # Test with Claude (if available)
    if "claude" in llm_service.get_available_providers():
        claude_response = await llm_service.simple_completion(
            prompt=f"Extract entities from: '{text}' Return JSON with entities array.",
            provider="claude",
        )
        print(f"📊 Claude response: {claude_response[:50]}...")
    else:
        print("⚠️  Claude not available")


if __name__ == "__main__":
    print("🧪 Running LLM Hotswap Demo...")
    asyncio.run(main())
    asyncio.run(test_migration_example())
    print("✅ Demo complete!")
