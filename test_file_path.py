#!/usr/bin/env python3
"""
Test script for document detection using file paths
Tests the actual .docx files in sunworld_test_data directory
"""

import requests
import json
import time
from typing import Dict, Any, List, Optional

# Server configuration
SERVER_URL = "http://localhost:8000"
AGENT_NAME = "Knowledge Graph Agent"
CAPABILITY = "detect_document_type"

# Test files in the mounted directory
TEST_FILES = [
    "/app/sunworld_test_data/structured_doc_1.docx",
    "/app/sunworld_test_data/semi_structured_doc_1.docx",
    "/app/sunworld_test_data/semi_structured_doc_2.docx",
    "/app/sunworld_test_data/semi_structured_doc_3.docx",
    "/app/sunworld_test_data/semi_structured_doc_4.docx",
    "/app/sunworld_test_data/semi_structured_doc_5.docx",
    "/app/sunworld_test_data/unstructured_doc_1.docx",
    "/app/sunworld_test_data/unstructured_doc_2.docx",
    "/app/sunworld_test_data/unstructured_doc_3.docx",
    "/app/sunworld_test_data/unstructured_doc_4.docx",
    "/app/sunworld_test_data/unstructured_doc_5.docx",
]


def test_file_detection(file_path: str) -> None:
    """Test document detection with a specific file path"""
    filename = file_path.split("/")[-1]  # Extract filename from path

    print(f"\n{'='*60}")
    print(f"Testing: {filename}")
    print(f"Path: {file_path}")
    print(f"{'='*60}")

    url = f"{SERVER_URL}/execute/{AGENT_NAME}/{CAPABILITY}"

    params = {
        "file_path": file_path,
        "filename": filename,
        "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    try:
        response = requests.post(url, json=params, timeout=30)

        if response.status_code == 200:
            result = response.json()
            data = result.get("data", {})

            if result.get("success"):
                print("✅ SUCCESS!")
                print(f"   📄 Document Type: {data.get('document_type', 'unknown')}")
                print(f"   🏗️  Structure Type: {data.get('structure_type', 'unknown')}")
                print(f"   ⭐ Structure Rating: {data.get('structure_rating', '0/7')}")
                print(f"   📊 Confidence: {data.get('confidence', 0):.2f}")
                print(f"   🖼️  Is Scanned: {data.get('is_scanned', False)}")

                # Show metadata if available
                metadata = data.get("metadata", {})
                if metadata:
                    print(f"   📋 Metadata:")
                    for key, value in metadata.items():
                        if key not in ["filename", "file_path"]:  # Skip redundant info
                            print(f"      - {key}: {value}")

                # Validate expected structure for known file types
                expected_structure = get_expected_structure(filename)
                actual_structure = data.get("structure_type", "unknown")

                if expected_structure and not is_classification_compatible(
                    expected_structure, actual_structure
                ):
                    print(
                        f"   ⚠️  Expected '{expected_structure}' family but got '{actual_structure}'"
                    )
                elif expected_structure:
                    print(
                        f"   ✅ Structure classification '{actual_structure}' is compatible with expected '{expected_structure}' family!"
                    )

            else:
                print("❌ TOOL EXECUTION FAILED!")
                print(f"   Error: {data.get('error', 'Unknown error')}")

        else:
            print(f"❌ HTTP REQUEST FAILED! Status: {response.status_code}")
            print(f"   Response: {response.text}")

    except requests.RequestException as e:
        print(f"❌ REQUEST FAILED: {e}")


def get_expected_structure(filename: str) -> Optional[str]:
    """Get expected structure type based on filename"""
    if "structured_doc" in filename:
        return "structured"  # Could be structured or highly_structured
    elif "semi_structured_doc" in filename:
        return "semi_structured"  # Could be lightly_structured, semi_structured, or moderately_structured
    elif "unstructured_doc" in filename:
        return "unstructured"  # Could be unstructured or highly_unstructured
    else:
        return None


def is_classification_compatible(expected: str, actual: str) -> bool:
    """Check if the actual classification is compatible with expected"""
    # Define compatible classifications
    compatible_groups = {
        "structured": ["highly_structured", "structured", "moderately_structured"],
        "semi_structured": [
            "moderately_structured",
            "semi_structured",
            "lightly_structured",
        ],
        "unstructured": ["lightly_structured", "unstructured", "highly_unstructured"],
    }

    return actual in compatible_groups.get(expected, [expected])


def check_server_health() -> bool:
    """Check if server is running and healthy"""
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Server is healthy!")
            print(f"   - Status: {health_data.get('status')}")
            print(f"   - Agents: {health_data.get('agents_count')}")
            print(f"   - Active: {health_data.get('active_agents')}")
            return True
        else:
            print(f"❌ Server unhealthy. Status: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ Cannot reach server: {e}")
        return False


def test_directory_mount() -> bool:
    """Test if the directory is properly mounted by trying to access a file"""
    print("\n🔍 Testing directory mount...")

    # Test with a simple file path check
    test_params = {
        "file_path": "/app/sunworld_test_data/structured_doc_1.docx",
        "filename": "structured_doc_1.docx",
    }

    url = f"{SERVER_URL}/execute/{AGENT_NAME}/{CAPABILITY}"

    try:
        response = requests.post(url, json=test_params, timeout=10)
        result = response.json()

        if response.status_code == 200 and result.get("success"):
            print("✅ Directory mount successful!")
            return True
        else:
            error_msg = result.get("data", {}).get("error", "Unknown error")
            if "file_path" in error_msg.lower() or "not found" in error_msg.lower():
                print("❌ Directory not mounted or files not accessible!")
                print(
                    "   Make sure you've updated docker-compose.yml and restarted the container"
                )
                return False
            else:
                print("✅ Directory mount appears to be working")
                return True

    except Exception as e:
        print(f"❌ Mount test failed: {e}")
        return False


def main():
    """Run file path tests for all documents"""
    print("🧪 Document Detection Test Suite - File Path Method")
    print("=" * 70)

    # Check server health
    if not check_server_health():
        print(
            "\n❌ Server is not available. Please ensure Docker container is running:"
        )
        print("   docker-compose down")
        print("   docker-compose up --build")
        return

    # Test directory mount
    if not test_directory_mount():
        return

    # Wait for server to be ready
    print("\n⏳ Waiting for server to be fully ready...")
    time.sleep(2)

    # Track results
    results = {
        "total": len(TEST_FILES),
        "success": 0,
        "failed": 0,
        "structure_matches": 0,
    }

    print(f"\n📂 Testing {len(TEST_FILES)} documents...")

    # Test each file
    for i, file_path in enumerate(TEST_FILES, 1):
        print(f"\n[{i}/{len(TEST_FILES)}]", end="")

        try:
            test_file_detection(file_path)
            results["success"] += 1
            time.sleep(1)  # Brief pause between tests
        except Exception as e:
            print(f"❌ Test failed for {file_path}: {e}")
            results["failed"] += 1

    # Summary
    print(f"\n{'='*70}")
    print("📊 TEST SUMMARY")
    print(f"{'='*70}")
    print(f"Total files tested: {results['total']}")
    print(f"Successful detections: {results['success']}")
    print(f"Failed detections: {results['failed']}")
    print(f"Success rate: {(results['success']/results['total']*100):.1f}%")

    if results["success"] == results["total"]:
        print("\n🎉 All tests passed!")
    elif results["success"] > 0:
        print(
            f"\n⚠️  {results['failed']} tests failed, but {results['success']} succeeded"
        )
    else:
        print("\n❌ All tests failed - check server and directory mount")


if __name__ == "__main__":
    main()
