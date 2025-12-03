"""
Integration tests for MCP tools

These tests verify that the tool registration and execution works correctly.
"""
import pytest
from unittest.mock import patch
import requests_mock
import patchworks_client as pw


class TestToolRegistration:
    """Test that tools can be registered with FastMCP"""

    @pytest.mark.integration
    def test_tools_can_be_registered(self, mcp_server):
        """Test that default tools can be registered without errors"""
        from defaults.tools import register_default_tools

        # Should not raise any exceptions
        register_default_tools(mcp_server)

        # Check registry was created
        assert hasattr(mcp_server, '_default_tools_registry')
        assert len(mcp_server._default_tools_registry) > 0

    @pytest.mark.integration
    def test_registry_structure(self, mcp_server_with_tools):
        """Test that the tool registry has the expected structure"""
        assert hasattr(mcp_server_with_tools, '_default_tools_registry')

        for tool_info in mcp_server_with_tools._default_tools_registry:
            assert "name" in tool_info
            assert "description" in tool_info
            assert "category" in tool_info
            assert isinstance(tool_info["name"], str)
            assert isinstance(tool_info["description"], str)
            assert isinstance(tool_info["category"], str)

    @pytest.mark.integration
    def test_expected_tool_categories(self, mcp_server_with_tools):
        """Test that tools are categorized correctly"""
        expected_categories = ["flows", "payloads", "data", "marketplace", "flow-creation"]

        actual_categories = set(
            tool["category"] for tool in mcp_server_with_tools._default_tools_registry
        )

        for expected_cat in expected_categories:
            assert expected_cat in actual_categories, \
                f"Expected category '{expected_cat}' not found in registry"


class TestClientIntegration:
    """Test integration between tool layer and client layer"""

    @pytest.mark.integration
    def test_get_all_flows_integration(self, sample_flow_data):
        """Test get_all_flows works end-to-end"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/flows',
                json=sample_flow_data
            )

            result = pw.get_all_flows(page=1, per_page=50)

            assert result["data"][0]["id"] == "flow-123"
            assert result["data"][0]["attributes"]["name"] == "Test Flow"

    @pytest.mark.integration
    def test_summarise_failed_run_integration(self, sample_log_data):
        """Test summarise_failed_run works end-to-end"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/flow-runs/run-456/flow-run-logs',
                json=sample_log_data
            )

            result = pw.summarise_failed_run("run-456", max_logs=50)

            assert result["run_id"] == "run-456"
            assert result["log_count"] == 3
            assert "ERROR" in result["levels"]
            assert len(result["highlights"]) > 0

    @pytest.mark.integration
    def test_triage_latest_failures_integration(
        self, sample_flow_run_data, sample_log_data
    ):
        """Test triage_latest_failures works end-to-end"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/flow-runs',
                json=sample_flow_run_data
            )
            m.get(
                'https://core.test.example.com/api/v1/flow-runs/run-456/flow-run-logs',
                json=sample_log_data
            )

            result = pw.triage_latest_failures(limit=20, per_run_log_limit=50)

            assert result["count"] == 1
            assert result["items"][0]["run_id"] == "run-456"
            assert "summary" in result["items"][0]


class TestFlowCreationIntegration:
    """Test flow creation tools integration"""

    @pytest.mark.integration
    def test_import_flow_integration(self):
        """Test import_flow works end-to-end"""
        with requests_mock.Mocker() as m:
            m.post(
                'https://core.test.example.com/api/v1/flows/import',
                json={"status": "success", "flow_id": "flow-999"}
            )

            payload = {
                "metadata": {"company_name": "Test Co"},
                "flow": {"name": "Custom Flow", "priority": 5},
                "systems": []
            }

            result = pw.import_flow(payload)

            assert result["status"] == "success"
            assert result["flow_id"] == "flow-999"
            assert m.last_request.json() == payload


class TestPromptToFlowCreation:
    """Test the full prompt-to-flow creation pipeline"""

    @pytest.mark.integration
    def test_prompt_parsing_to_flow_json(self):
        """Test that prompt parsing produces valid flow JSON"""
        from defaults.schemas import _guess_parts_from_prompt, _build_generic_import_json

        # Parse the prompt
        parts = _guess_parts_from_prompt("create a flow for Shopify to NetSuite orders")

        assert parts["source"] == "Shopify"
        assert parts["destination"] == "Netsuite"
        assert parts["entity"] == "orders"

        # Build the flow JSON
        flow_json = _build_generic_import_json(
            parts["source"],
            parts["destination"],
            parts["entity"],
            priority=3,
            schedule_cron="0 * * * *",
            enable=False
        )

        # Verify the structure
        assert "metadata" in flow_json
        assert "flow" in flow_json
        assert "systems" in flow_json

        # Verify flow details
        assert flow_json["flow"]["priority"] == 3
        assert flow_json["flow"]["is_enabled"] is False
        assert len(flow_json["flow"]["versions"][0]["steps"]) == 5

        # Verify systems
        assert len(flow_json["systems"]) == 2
        system_names = [s["system"]["name"] for s in flow_json["systems"]]
        assert "Shopify" in system_names
        assert "Netsuite" in system_names

    @pytest.mark.integration
    def test_prompt_to_import_full_pipeline(self):
        """Test the complete pipeline from prompt to import"""
        from defaults.schemas import _guess_parts_from_prompt, _build_generic_import_json

        with requests_mock.Mocker() as m:
            m.post(
                'https://core.test.example.com/api/v1/flows/import',
                json={"status": "success", "flow_id": "flow-888"}
            )

            # Step 1: Parse prompt
            parts = _guess_parts_from_prompt("for Magento to Shopify products")

            # Step 2: Build flow JSON
            flow_json = _build_generic_import_json(
                parts["source"],
                parts["destination"],
                parts["entity"],
                priority=3,
                schedule_cron=None,
                enable=False
            )

            # Step 3: Import the flow
            result = pw.import_flow(flow_json)

            # Verify success
            assert result["status"] == "success"
            assert result["flow_id"] == "flow-888"

            # Verify the import payload structure
            import_payload = m.last_request.json()
            assert import_payload["systems"][0]["system"]["name"] == "Magento"
            assert import_payload["systems"][1]["system"]["name"] == "Shopify"
            assert "products" in import_payload["flow"]["description"].lower()


class TestErrorHandling:
    """Test error handling across the integration"""

    @pytest.mark.integration
    def test_http_error_propagation(self):
        """Test that HTTP errors propagate correctly through the stack"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/flows',
                status_code=500,
                text="Internal server error"
            )

            with pytest.raises(RuntimeError) as exc_info:
                pw.get_all_flows()

            assert "500" in str(exc_info.value)

    @pytest.mark.integration
    def test_invalid_flow_import_error(self):
        """Test that invalid flow import returns error"""
        with requests_mock.Mocker() as m:
            m.post(
                'https://core.test.example.com/api/v1/flows/import',
                status_code=400,
                text="Invalid flow definition"
            )

            with pytest.raises(RuntimeError) as exc_info:
                pw.import_flow({"invalid": "data"})

            assert "400" in str(exc_info.value)


class TestDataPoolIntegration:
    """Test data pool operations integration"""

    @pytest.mark.integration
    def test_list_and_get_data_pools(self):
        """Test listing data pools and getting deduped data"""
        with requests_mock.Mocker() as m:
            # Mock list data pools
            m.get(
                'https://core.test.example.com/api/v1/data-pool/',
                json={
                    "data": [
                        {"id": "pool-1", "attributes": {"name": "Test Pool"}}
                    ]
                }
            )

            # Mock get deduped data
            m.get(
                'https://core.test.example.com/api/v1/data-pool/pool-1/deduped-data',
                json={
                    "data": [
                        {"id": "row-1", "attributes": {"data": "value"}}
                    ]
                }
            )

            # List pools
            pools = pw.list_data_pools()
            assert len(pools["data"]) == 1
            pool_id = pools["data"][0]["id"]

            # Get deduped data
            data = pw.get_deduped_data(pool_id)
            assert len(data["data"]) == 1
            assert data["data"][0]["id"] == "row-1"


class TestMarketplaceIntegration:
    """Test marketplace operations integration"""

    @pytest.mark.integration
    def test_list_and_get_marketplace_app(self, sample_marketplace_apps):
        """Test listing marketplace apps and getting specific app"""
        with requests_mock.Mocker() as m:
            # Mock list apps
            m.get(
                'https://core.test.example.com/api/v1/patchworks/marketplace-apps',
                json=sample_marketplace_apps
            )

            # Mock get specific app
            m.get(
                'https://core.test.example.com/api/v1/patchworks/marketplace-apps/app-1',
                json={
                    "data": {
                        "id": "app-1",
                        "attributes": {"name": "Shopify", "version": "1.0"}
                    }
                }
            )

            # List apps
            apps = pw.get_marketplace_apps()
            assert len(apps["data"]) == 2
            app_id = apps["data"][0]["id"]

            # Get specific app
            app = pw.get_marketplace_app(app_id)
            assert app["data"]["id"] == "app-1"
            assert app["data"]["attributes"]["name"] == "Shopify"
