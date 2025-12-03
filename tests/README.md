# Tests for patchworks-mcp

This directory contains the test suite for the patchworks-mcp project.

## Setup

Install the test dependencies:

```bash
# Using pip
pip install -e ".[dev]"

# Using uv
uv pip install -e ".[dev]"
```

## Running Tests

Run all tests:

```bash
pytest
```

Run tests with verbose output:

```bash
pytest -v
```

Run specific test files:

```bash
pytest tests/test_schemas.py
pytest tests/test_patchworks_client.py
pytest tests/test_tools_integration.py
```

Run tests by marker:

```bash
# Run only unit tests
pytest -m unit

# Run only client tests
pytest -m client

# Run only integration tests
pytest -m integration
```

Run a specific test:

```bash
pytest tests/test_schemas.py::TestPromptParsing::test_basic_pattern_with_entity
```

## Test Structure

### `test_schemas.py`
Tests for schema validation and helper functions:
- `_guess_parts_from_prompt()` - Natural language prompt parsing
- `_build_generic_import_json()` - Flow JSON generation
- Pydantic schema validation

### `test_patchworks_client.py`
Tests for the patchworks_client module:
- HTTP client functions (mocked with requests-mock)
- API calls to Core and Start APIs
- Error handling and response parsing
- Helper functions

### `test_tools_integration.py`
Integration tests for MCP tools:
- Tool registration and discovery
- End-to-end tool execution
- Tool argument handling
- Error handling in tools

### `conftest.py`
Shared pytest fixtures:
- `mock_session` - Mocked requests session
- `mcp_server` - Fresh FastMCP instance
- `mcp_server_with_tools` - MCP with registered tools
- Sample data fixtures (flows, runs, logs, etc.)

## Test Markers

Tests are marked with the following markers (defined in `pytest.ini`):

- `@pytest.mark.unit` - Unit tests that don't require external dependencies
- `@pytest.mark.client` - Tests for the patchworks_client module
- `@pytest.mark.integration` - Integration tests for multiple components

## Environment Variables

Test environment variables are configured in `pytest.ini`:

- `PATCHWORKS_CORE_API` - Core API URL (set to test URL)
- `PATCHWORKS_START_API` - Start API URL (set to test URL)
- `PATCHWORKS_TOKEN` - Auth token (set to test token)

These are automatically set when running tests and won't affect your real environment.

## Writing New Tests

When adding new tests:

1. Place them in the appropriate test file based on what you're testing
2. Add appropriate markers (`@pytest.mark.unit`, etc.)
3. Use fixtures from `conftest.py` where possible
4. Mock HTTP calls using `requests_mock`
5. Follow the existing test naming conventions

Example:

```python
import pytest
import requests_mock

@pytest.mark.client
def test_my_new_function(self, sample_flow_data):
    """Test description"""
    with requests_mock.Mocker() as m:
        m.get('https://api.example.com/endpoint', json=sample_flow_data)

        # Your test code here
        result = my_function()

        assert result["expected_key"] == "expected_value"
```
