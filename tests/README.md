# Test Suite Documentation

This directory contains tests for the Contract Comparisons MCP Server project.

## Quick Start

### Run All Tests
```bash
pytest
```

### Run Specific Test Files
```bash
pytest tests/test_registry/test_registry.py -v
pytest tests/test_server.py -v
```

## Test Structure

```
tests/
├── conftest.py              # Test configuration and fixtures
├── test_registry/          # Registry system tests
│   ├── test_registry.py
│   └── test_registry_models.py
└── test_server.py          # Server endpoint tests
```

## Test Coverage

- **Registry System**: Agent registration and management
- **Server Endpoints**: API endpoint functionality
- **Agent Discovery**: Automatic agent discovery

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_server.py -v
```
