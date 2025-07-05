#!/usr/bin/env python3
"""
Test script to demonstrate the new clean preprocessing format.
Shows the old verbose format vs new clean format.
"""

import json
import asyncio
import aiohttp
import sys


async def test_preprocessing_format():
    """Test the new clean preprocessing format"""

    # Test data examples
    test_cases = [
        {
            "name": "CSV Customer Data",
            "document_type": "csv",
            "content": """Customer ID,Name,Email,Registration Date,Subscription Type,Monthly Revenue,Status,Last Login
1001,John Smith,john.smith@email.com,2023-01-15,Premium,99.99,Active,2023-12-01
1002,Sarah Johnson,sarah.j@company.com,2023-02-20,Basic,29.99,Active,2023-11-30
1003,Mike Brown,mike.brown@service.com,2023-03-10,Premium,99.99,Inactive,2023-10-15""",
        },
        {
            "name": "JSON Customer Data",
            "document_type": "json",
            "content": json.dumps(
                {
                    "customers": [
                        {
                            "id": 2001,
                            "name": "Alice Wilson",
                            "email": "alice@example.com",
                            "registration_date": "2023-04-01",
                            "subscription_type": "Enterprise",
                            "monthly_revenue": 199.99,
                            "status": "Active",
                        },
                        {
                            "id": 2002,
                            "name": "Bob Davis",
                            "email": "bob@test.com",
                            "registration_date": "2023-05-15",
                            "subscription_type": "Basic",
                            "monthly_revenue": 29.99,
                            "status": "Active",
                        },
                    ]
                }
            ),
        },
    ]

    print("🧪 Testing New Clean Preprocessing Format\n")
    print("=" * 60)

    for test_case in test_cases:
        print(f"\n📄 Test: {test_case['name']}")
        print("-" * 40)

        # Prepare request
        payload = {
            "content": test_case["content"],
            "document_type": test_case["document_type"],
            "enhance_for_ocr": False,
            "remove_stopwords": False,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8000/mcp/call",
                    json={"method": "preprocess_document", "params": payload},
                ) as response:
                    if response.status == 200:
                        result = await response.json()

                        if result.get("success"):
                            processed_content = result["data"]["processed_content"]

                            print("✅ New Clean Format:")
                            print(processed_content)
                            print()

                            # Show metadata
                            metadata = result["data"]["metadata"]
                            print(
                                f"📊 Compression: {metadata.get('compression_ratio', 'N/A')}"
                            )
                            print(
                                f"📝 Words: {metadata.get('original_word_count', 'N/A')} → {metadata.get('processed_word_count', 'N/A')}"
                            )

                        else:
                            print(f"❌ Error: {result.get('error')}")
                    else:
                        print(f"❌ HTTP Error: {response.status}")

        except Exception as e:
            print(f"❌ Connection Error: {e}")
            print("💡 Make sure the MCP server is running with: docker-compose up")

        print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_preprocessing_format())
