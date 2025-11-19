"""
Basic Test Configuration and Fixtures

This file contains essential pytest fixtures for configuration and server testing.
"""

import pytest
import os
import sys
from typing import Dict, Generator
from fastapi.testclient import TestClient

# Add project root to Python path for imports
project_root = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, project_root)


@pytest.fixture
def test_env() -> Generator[Dict[str, str], None, None]:
    """Set up clean test environment variables."""
    # Store original environment
    original_env = os.environ.copy()

    # Set minimal test environment variables
    test_vars = {
        "LOG_LEVEL": "ERROR",  # Reduce logging noise during tests
		"ALLOWED_ORIGINS": "*",
    }

    # Apply test environment
    for key, value in test_vars.items():
        os.environ[key] = value

    yield test_vars

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def client(test_env) -> TestClient:
    """Create a test client for the FastAPI app."""
    # Import here to ensure test_env is applied first
	from backend.server.mcp_server import app

    return TestClient(app)
