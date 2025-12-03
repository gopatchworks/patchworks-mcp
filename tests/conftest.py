"""
Shared pytest fixtures for patchworks-mcp tests
"""
import pytest
from unittest.mock import MagicMock
from mcp.server.fastmcp import FastMCP


@pytest.fixture
def mock_session(mocker):
    """Mock requests session for testing HTTP calls"""
    mock = mocker.patch('patchworks_client.session')
    return mock


@pytest.fixture
def mcp_server():
    """Create a fresh FastMCP server instance for testing"""
    return FastMCP("test-patchworks")


@pytest.fixture
def mcp_server_with_tools(mcp_server):
    """Create a FastMCP server with default tools registered"""
    from defaults.tools import register_default_tools
    register_default_tools(mcp_server)
    return mcp_server


@pytest.fixture
def sample_flow_data():
    """Sample flow data for testing"""
    return {
        "data": [
            {
                "id": "flow-123",
                "type": "flows",
                "attributes": {
                    "name": "Test Flow",
                    "description": "A test flow",
                    "is_enabled": True,
                    "priority": 3
                }
            }
        ],
        "meta": {
            "page": 1,
            "per_page": 50,
            "total": 1
        }
    }


@pytest.fixture
def sample_flow_run_data():
    """Sample flow run data for testing"""
    return {
        "data": [
            {
                "id": "run-456",
                "type": "flow-runs",
                "attributes": {
                    "status": 3,  # FAILURE
                    "started_at": "2025-12-03T10:00:00Z",
                    "finished_at": "2025-12-03T10:05:00Z",
                    "flow_id": "flow-123",
                    "flow_version_id": "version-789"
                }
            }
        ]
    }


@pytest.fixture
def sample_log_data():
    """Sample log data for testing"""
    return {
        "data": [
            {
                "id": "log-1",
                "type": "flow-run-logs",
                "attributes": {
                    "log_level": "INFO",
                    "log_message": "Flow started successfully",
                    "created_at": "2025-12-03T10:00:00Z",
                    "flow_step_id": "step-1"
                }
            },
            {
                "id": "log-2",
                "type": "flow-run-logs",
                "attributes": {
                    "log_level": "ERROR",
                    "log_message": "Connection timeout to external API",
                    "created_at": "2025-12-03T10:02:00Z",
                    "flow_step_id": "step-2",
                    "payload_metadata_id": "payload-123"
                }
            },
            {
                "id": "log-3",
                "type": "flow-run-logs",
                "attributes": {
                    "log_level": "FATAL",
                    "log_message": "Flow execution failed",
                    "created_at": "2025-12-03T10:05:00Z",
                    "flow_step_id": "step-3"
                }
            }
        ]
    }


@pytest.fixture
def sample_marketplace_apps():
    """Sample marketplace apps data"""
    return {
        "data": [
            {
                "id": "app-1",
                "type": "marketplace-apps",
                "attributes": {
                    "name": "Shopify",
                    "allowed": True,
                    "private": False
                }
            },
            {
                "id": "app-2",
                "type": "marketplace-apps",
                "attributes": {
                    "name": "NetSuite",
                    "allowed": True,
                    "private": False
                }
            }
        ]
    }