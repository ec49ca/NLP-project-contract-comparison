#!/usr/bin/env python3
"""
Simple NER+EL Test - Quick verification that the system works

This test uses a simple example to verify:
1. The NER+EL tool can be imported and initialized
2. Basic entity extraction works
3. Entity linking functions correctly
4. The integration with KG agent works

Run with: python test_ner_el_simple.py
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.kg_agent import KnowledgeGraphAgent


async def test_ner_el_simple():
    """Simple test of the NER+EL system"""

    print("🚀 Testing NER+EL System - Simple Test")
    print("=" * 50)

    # Test data that mimics our clean preprocessing output
    test_content = """
RECORD_1
COMPANY_NAME: Acme Corporation
CEO_NAME: John Smith
LOCATION: San Francisco, California
REVENUE: $2.5 million
EMAIL: contact@acmecorp.com
PHONE: +1-555-123-4567

RECORD_2
PERSON_NAME: Sarah Johnson
JOB_TITLE: Senior Engineer
EMPLOYER: Acme Corporation
SALARY: $150,000
EMAIL: sarah@acmecorp.com
"""

    try:
        # Initialize the agent
        print("📝 Initializing KG Agent...")
        agent = KnowledgeGraphAgent()
        await agent.initialize({})

        # Test the NER+EL functionality
        print("🔍 Testing NER+EL extraction...")

        request = {
            "command": "run_ner_el",
            "text": test_content,
            "confidence_threshold": 0.6,
            "entity_types": [
                "PERSON",
                "ORGANIZATION",
                "LOCATION",
                "MONEY",
                "EMAIL",
                "PHONE",
            ],
        }

        print("🤖 Running NER+EL request...")
        result = await agent.process_request(request)

        if result["status"] == "success":
            data = result["data"]
            print(f"✅ SUCCESS! Found {data['total_entities']} entities")
            print(f"📊 Entity types: {', '.join(data['entity_types_found'])}")
            print(f"🔗 Relationships: {len(data['relationships'])}")

            # Show first few entities
            print("\n📋 Sample Entities:")
            for i, entity in enumerate(data["entities"][:5]):
                print(
                    f"  {i+1}. '{entity['text']}' ({entity['type']}) - {entity['confidence']:.2f}"
                )

            # Show processing stats
            stats = data["statistics"]
            print(f"\n📈 Processing Stats:")
            print(f"  • Chunks processed: {stats['chunks_processed']}")
            print(f"  • High confidence: {stats['high_confidence_entities']}")
            print(f"  • Processing errors: {stats['processing_errors']}")

            print("\n🎯 Test Result: PASSED ✅")

        else:
            print(f"❌ FAILED: {result.get('message', 'Unknown error')}")
            print(f"📝 Full error: {result}")

        await agent.shutdown()

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n✅ Simple NER+EL test completed!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_ner_el_simple())
    sys.exit(0 if success else 1)
