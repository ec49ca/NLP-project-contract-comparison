import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

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
    logger.info(f"\n{'='*50}")
    logger.info(f"Running: {description}")
    logger.info(f"Command: {command}")
    print(f"{'='*50}")

    result = subprocess.run(command, shell=True, capture_output=False)

    if result.returncode == 0:
        logger.info(f"✅ {description} - PASSED")
    else:
        logger.error(f"❌ {description} - FAILED")

    return result.returncode == 0


def main():
    """Main test runner function."""
    logger.info("🧪 Test Suite Runner")
    logger.info("===================")

    # Check if we're in the right directory
    if not os.path.exists("src") or not os.path.exists("tests"):
        logger.error("Error: Please run this script from the project root directory")
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
    logger.info(f"\n{'='*50}")
    logger.info("📊 TEST SUMMARY")
    print(f"{'='*50}")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{description}: {status}")

    logger.info(f"
Overall: {passed}/{total} test categories passed")

    if passed == total:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
