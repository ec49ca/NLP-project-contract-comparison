# Test Suite

This directory contains the test suite for the samvid-mcp project.

## Quick Start

To run all tests:
```bash
pytest
```

To run the test runner script:
```bash
python run_tests.py
```

## Test Structure

- **`conftest.py`** - Shared test configuration and fixtures
- **`test_config.py`** - Configuration system tests
- **`test_server.py`** - API endpoint tests

## Test Categories

Tests are organized with markers for easy filtering:

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Integration tests with mocked dependencies
- `@pytest.mark.config` - Configuration-related tests
- `@pytest.mark.server` - Server endpoint tests

## Running Specific Tests

```bash
# Run only configuration tests
pytest -m config

# Run only server tests
pytest -m server

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run a specific test file
pytest tests/test_config.py

# Run with verbose output
pytest -v

# Run a specific test function
pytest tests/test_config.py::TestDefaultModelParsing::test_parse_valid_default_model
```

## Environment

Tests use isolated environment variables and don't affect your actual configuration. The test environment is automatically set up through fixtures in `conftest.py`.

## Adding New Tests

1. Create test files following the `test_*.py` naming convention
2. Use appropriate markers (`@pytest.mark.unit`, `@pytest.mark.integration`, etc.)
3. Add fixtures to `conftest.py` if they'll be reused
4. Follow the existing test structure and naming patterns

## Current Test Coverage

- ✅ Configuration system (basic)
- ✅ Server endpoints (basic)
- 🚧 Agent functionality (planned)
- 🚧 LLM service (planned)
- 🚧 Provider system (planned)