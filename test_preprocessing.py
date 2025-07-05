#!/usr/bin/env python3
"""
Test script for document preprocessing functionality
Tests various document types and OCR capabilities
"""

import requests
import json
import time
from typing import Dict, Any

# Server configuration
SERVER_URL = "http://localhost:8000"
AGENT_NAME = "Knowledge Graph Agent"
CAPABILITY = "preprocess_document"


def test_preprocessing_basic():
    """Test basic preprocessing functionality"""
    print("🧪 Testing Basic Preprocessing...")

    test_cases = [
        {
            "name": "HTML Content",
            "document_content": "<html><body><h1>Test Title</h1><p>This is a <strong>test</strong> paragraph.</p></body></html>",
            "document_type": "html",
            "normalize_text": True,
            "remove_stopwords": False,
        },
        {
            "name": "Markdown Content",
            "document_content": "# Test Header\n\nThis is **bold** text and *italic* text.\n\n- List item 1\n- List item 2",
            "document_type": "markdown",
            "normalize_text": True,
            "remove_stopwords": False,
        },
        {
            "name": "JSON Content",
            "document_content": '{"name": "John", "age": 30, "city": "New York"}',
            "document_type": "json",
            "normalize_text": True,
            "remove_stopwords": False,
        },
        {
            "name": "Structured Document",
            "document_content": "Name: John Doe\nAge: 30\nCity: New York\n\nTable Data:\nCol1 | Col2 | Col3\nVal1 | Val2 | Val3",
            "document_type": "structured",
            "normalize_text": True,
            "remove_stopwords": False,
        },
        {
            "name": "Unstructured Document",
            "document_content": "This is a long paragraph with lots of text that represents typical unstructured document content. It has multiple sentences and should be processed differently than structured content.",
            "document_type": "unstructured",
            "normalize_text": True,
            "remove_stopwords": True,
        },
    ]

    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing: {test_case['name']}")
        print(f"{'='*60}")

        url = f"{SERVER_URL}/execute/{AGENT_NAME}/{CAPABILITY}"

        try:
            response = requests.post(url, json=test_case, timeout=30)

            if response.status_code == 200:
                result = response.json()
                data = result.get("data", {})

                if result.get("status") == "success" and data.get("success"):
                    print("✅ SUCCESS!")
                    print(f"   📄 Document Type: {data.get('document_type')}")
                    print(f"   📏 Original Length: {data.get('original_length')}")
                    print(f"   📐 Processed Length: {data.get('processed_length')}")
                    print(
                        f"   💬 Word Count: {data.get('metadata', {}).get('word_count', 'N/A')}"
                    )
                    print(
                        f"   📊 Compression Ratio: {data.get('metadata', {}).get('compression_ratio', 0):.2f}"
                    )

                    # Show first 200 characters of processed content
                    processed_content = data.get("processed_content", "")
                    if len(processed_content) > 200:
                        preview = processed_content[:200] + "..."
                    else:
                        preview = processed_content
                    print(f"   📝 Processed Content: {preview}")

                    # Show preprocessing applied
                    preprocessing = data.get("preprocessing_applied", {})
                    print(f"   🔧 Preprocessing Applied:")
                    print(
                        f"      - Normalization: {preprocessing.get('normalization', False)}"
                    )
                    print(
                        f"      - Stopword Removal: {preprocessing.get('stopword_removal', False)}"
                    )
                    print(
                        f"      - Type Specific: {preprocessing.get('type_specific', False)}"
                    )

                else:
                    print("❌ TOOL EXECUTION FAILED!")
                    print(f"   Error: {data.get('error', 'Unknown error')}")

            else:
                print(f"❌ HTTP REQUEST FAILED! Status: {response.status_code}")
                print(f"   Response: {response.text}")

        except requests.RequestException as e:
            print(f"❌ REQUEST FAILED: {e}")

        time.sleep(1)


def test_ocr_preprocessing():
    """Test OCR preprocessing with scanned documents"""
    print("\n🖼️ Testing OCR Preprocessing...")

    # Test with a file path (would need actual image file)
    test_case = {
        "name": "Scanned Document OCR",
        "document_type": "scanned",
        "file_path": "/app/sunworld_test_data/sample_image.png",  # Would need actual image
        "normalize_text": True,
        "remove_stopwords": False,
    }

    print(f"\n{'='*60}")
    print(f"Testing: {test_case['name']}")
    print(f"{'='*60}")

    url = f"{SERVER_URL}/execute/{AGENT_NAME}/{CAPABILITY}"

    try:
        response = requests.post(
            url, json=test_case, timeout=60
        )  # Longer timeout for OCR

        if response.status_code == 200:
            result = response.json()
            data = result.get("data", {})

            if result.get("status") == "success" and data.get("success"):
                print("✅ OCR SUCCESS!")
                print(f"   📄 Document Type: {data.get('document_type')}")
                print(f"   📐 Processed Length: {data.get('processed_length')}")
                print(
                    f"   💬 Word Count: {data.get('metadata', {}).get('word_count', 'N/A')}"
                )

                # Show OCR extracted content
                processed_content = data.get("processed_content", "")
                if processed_content:
                    if len(processed_content) > 300:
                        preview = processed_content[:300] + "..."
                    else:
                        preview = processed_content
                    print(f"   📝 OCR Extracted Text: {preview}")
                else:
                    print("   ⚠️  No text extracted from OCR")

            else:
                print("❌ OCR FAILED!")
                print(f"   Error: {data.get('error', 'Unknown error')}")
                print(
                    "   Note: This is expected if no image file exists or OCR libraries aren't installed"
                )

        else:
            print(f"❌ HTTP REQUEST FAILED! Status: {response.status_code}")
            print(f"   Response: {response.text}")

    except requests.RequestException as e:
        print(f"❌ REQUEST FAILED: {e}")


def check_server_health() -> bool:
    """Check if server is running and healthy"""
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Server is healthy!")
            print(f"   - Status: {health_data.get('status')}")
            print(f"   - Agents: {health_data.get('agents_count')}")
            return True
        else:
            print(f"❌ Server unhealthy. Status: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ Cannot reach server: {e}")
        return False


def main():
    """Run preprocessing tests"""
    print("🧪 Document Preprocessing Test Suite")
    print("=" * 70)

    # Check server health
    if not check_server_health():
        print(
            "\n❌ Server is not available. Please ensure Docker container is running:"
        )
        print("   docker-compose down")
        print("   docker-compose up --build")
        return

    # Wait for server to be ready
    print("\n⏳ Waiting for server to be fully ready...")
    time.sleep(2)

    # Test basic preprocessing
    test_preprocessing_basic()

    # Test OCR preprocessing
    test_ocr_preprocessing()

    print(f"\n{'='*70}")
    print("🎉 Preprocessing tests completed!")
    print("Note: OCR tests require image files and OCR libraries to be installed")
    print("Run 'docker-compose up --build' to install dependencies if needed")


if __name__ == "__main__":
    main()
