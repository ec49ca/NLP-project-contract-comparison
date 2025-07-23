#!/usr/bin/env python3
"""
Simple test runner to verify our test setup works.

This script provides convenient commands for running different types of tests.
"""

import subprocess
import sys
import os


def run_command(command, description):
    """Run a command and print the result."""
    print(f"\n{'='*50}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*50}")

    result = subprocess.run(command, shell=True, capture_output=False)

    if result.returncode == 0:
        print(f"✅ {description} - PASSED")
    else:
        print(f"❌ {description} - FAILED")

    return result.returncode == 0


def main():
    """Main test runner function."""
    print("🧪 Test Suite Runner")
    print("===================")

    # Check if we're in the right directory
    if not os.path.exists("src") or not os.path.exists("tests"):
        print("❌ Error: Please run this script from the project root directory")
        sys.exit(1)

    # Run different test categories
    test_commands = [
        ("pytest tests/test_config.py -v", "Configuration Tests"),
        ("pytest tests/test_server.py -v", "Server Endpoint Tests"),
        ("pytest -m config -v", "All Configuration Tests"),
        ("pytest -m server -v", "All Server Tests"),
        ("pytest -m unit -v", "All Unit Tests"),
        ("pytest -m integration -v", "All Integration Tests"),
    ]

    results = []

    for command, description in test_commands:
        success = run_command(command, description)
        results.append((description, success))

    # Summary
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print(f"{'='*50}")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{description}: {status}")

    print(f"\nOverall: {passed}/{total} test categories passed")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
