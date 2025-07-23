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
        "OPENAI_API_KEY": "sk-test-key-for-testing",
        "CLAUDE_API_KEY": "sk-ant-test-key",
        "DEFAULT_LLM_MODEL": "openai:gpt-4o-mini",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "test_password",
        "LOG_LEVEL": "ERROR",  # Reduce logging noise during tests
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
    from src.server.mcp_server import app

    return TestClient(app)


@pytest.fixture
def sample_config_data():
    """Sample configuration data for testing."""
    return {
        "valid_provider": "openai",
        "valid_model": "gpt-4o-mini",
        "valid_default_model": "openai:gpt-4o-mini",
        "invalid_provider": "nonexistent",
        "invalid_model_format": "invalid-format",
        "empty_string": "",
    }
