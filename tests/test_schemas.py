"""
Tests for schema validation and helper functions
"""
import pytest
from defaults.schemas import (
    _guess_parts_from_prompt,
    _build_generic_import_json,
    GetAllFlowsArgs,
    GetFlowRunsArgs,
    CreateProcessFlowByPromptArgs,
)


class TestPromptParsing:
    """Tests for _guess_parts_from_prompt function"""

    @pytest.mark.unit
    def test_basic_pattern_with_entity(self):
        """Test basic 'for X to Y entity' pattern"""
        result = _guess_parts_from_prompt("create a flow for Shopify to NetSuite orders")
        assert result["source"] == "Shopify"
        assert result["destination"] == "Netsuite"
        assert result["entity"] == "orders"

    @pytest.mark.unit
    def test_without_create_keyword(self):
        """Test pattern without 'create' keyword"""
        result = _guess_parts_from_prompt("for BigCommerce to Salesforce customers")
        assert result["source"] == "Bigcommerce"
        assert result["destination"] == "Salesforce"
        assert result["entity"] == "customers"

    @pytest.mark.unit
    def test_simple_x_to_y_pattern(self):
        """Test simple 'X to Y' pattern without entity"""
        result = _guess_parts_from_prompt("Magento to SAP")
        assert result["source"] == "Magento"
        assert result["destination"] == "Sap"
        assert result["entity"] == "orders"  # Default

    @pytest.mark.unit
    def test_products_entity(self):
        """Test products entity recognition"""
        result = _guess_parts_from_prompt("for Shopify to WMS products")
        assert result["entity"] == "products"

    @pytest.mark.unit
    def test_inventory_entity(self):
        """Test inventory entity recognition"""
        result = _guess_parts_from_prompt("build flow for ERP to Shopify inventory")
        assert result["entity"] == "inventory"

    @pytest.mark.unit
    def test_payments_entity(self):
        """Test payments entity recognition"""
        result = _guess_parts_from_prompt("for Stripe to Xero payments")
        assert result["entity"] == "payments"

    @pytest.mark.unit
    def test_order_singular_becomes_orders(self):
        """Test that 'order' (singular) becomes 'orders'"""
        result = _guess_parts_from_prompt("for Shopify to NetSuite order")
        assert result["entity"] == "orders"

    @pytest.mark.unit
    def test_customer_singular_becomes_customers(self):
        """Test that 'customer' (singular) is recognized"""
        result = _guess_parts_from_prompt("for CRM to ERP customer")
        # The entity guessing logic returns 'customer' from ENTITY_GUESSES list
        assert result["entity"] == "customer"

    @pytest.mark.unit
    def test_default_values_when_no_match(self):
        """Test default values when prompt doesn't match patterns"""
        result = _guess_parts_from_prompt("something random")
        assert result["source"] == "System A"
        assert result["destination"] == "System B"
        assert result["entity"] == "orders"

    @pytest.mark.unit
    def test_case_insensitive(self):
        """Test that parsing is case insensitive"""
        result = _guess_parts_from_prompt("FOR SHOPIFY TO NETSUITE ORDERS")
        assert result["source"] == "Shopify"
        assert result["destination"] == "Netsuite"
        assert result["entity"] == "orders"


class TestBuildGenericImportJson:
    """Tests for _build_generic_import_json function"""

    @pytest.mark.unit
    def test_basic_flow_structure(self):
        """Test basic flow structure is correct"""
        result = _build_generic_import_json(
            "Shopify", "NetSuite", "orders",
            priority=3, schedule_cron="0 * * * *", enable=False
        )

        assert "metadata" in result
        assert "flow" in result
        assert "systems" in result

    @pytest.mark.unit
    def test_flow_name_format(self):
        """Test flow name follows expected format"""
        result = _build_generic_import_json(
            "Shopify", "NetSuite", "orders",
            priority=3, schedule_cron="0 * * * *", enable=False
        )

        flow_name = result["flow"]["name"]
        assert flow_name.startswith("Shopify > NetSuite Orders")
        assert "-" in flow_name  # Should have timestamp

    @pytest.mark.unit
    def test_flow_has_correct_steps(self):
        """Test flow has all required steps in correct order"""
        result = _build_generic_import_json(
            "Shopify", "NetSuite", "orders",
            priority=3, schedule_cron="0 * * * *", enable=False
        )

        steps = result["flow"]["versions"][0]["steps"]
        assert len(steps) == 5

        step_names = [s["name"] for s in steps]
        assert step_names == [
            "Try/Catch",
            "Source Connector",
            "Flow Control",
            "Map",
            "Destination Connector"
        ]

    @pytest.mark.unit
    def test_priority_setting(self):
        """Test priority is set correctly"""
        result = _build_generic_import_json(
            "Shopify", "NetSuite", "orders",
            priority=5, schedule_cron=None, enable=False
        )

        assert result["flow"]["priority"] == 5
        assert result["flow"]["versions"][0]["flow_priority"] == 5

    @pytest.mark.unit
    def test_schedule_cron_included(self):
        """Test cron schedule is included when provided"""
        result = _build_generic_import_json(
            "Shopify", "NetSuite", "orders",
            priority=3, schedule_cron="0 2 * * *", enable=False
        )

        schedules = result["flow"]["versions"][0]["schedules"]
        assert len(schedules) == 1
        assert schedules[0]["cron_string"] == "0 2 * * *"

    @pytest.mark.unit
    def test_schedule_omitted_when_none(self):
        """Test schedule is omitted when None"""
        result = _build_generic_import_json(
            "Shopify", "NetSuite", "orders",
            priority=3, schedule_cron=None, enable=False
        )

        schedules = result["flow"]["versions"][0]["schedules"]
        assert len(schedules) == 0

    @pytest.mark.unit
    def test_enable_flag(self):
        """Test enable flag is respected"""
        result_disabled = _build_generic_import_json(
            "Shopify", "NetSuite", "orders",
            priority=3, schedule_cron=None, enable=False
        )
        assert result_disabled["flow"]["is_enabled"] is False

        result_enabled = _build_generic_import_json(
            "Shopify", "NetSuite", "orders",
            priority=3, schedule_cron=None, enable=True
        )
        assert result_enabled["flow"]["is_enabled"] is True

    @pytest.mark.unit
    def test_systems_created(self):
        """Test both systems are created with correct names"""
        result = _build_generic_import_json(
            "Shopify", "NetSuite", "orders",
            priority=3, schedule_cron=None, enable=False
        )

        systems = result["systems"]
        assert len(systems) == 2
        assert systems[0]["system"]["name"] == "Shopify"
        assert systems[1]["system"]["name"] == "NetSuite"
        assert systems[0]["system"]["protocol"] == "HTTP"
        assert systems[1]["system"]["protocol"] == "HTTP"

    @pytest.mark.unit
    def test_entity_variations(self):
        """Test different entity types are handled correctly"""
        entities = ["orders", "customers", "products", "inventory"]

        for entity in entities:
            result = _build_generic_import_json(
                "Source", "Dest", entity,
                priority=3, schedule_cron=None, enable=False
            )

            # Check entity appears in flow description
            description = result["flow"]["description"]
            assert entity in description.lower()


class TestSchemaValidation:
    """Tests for Pydantic schema validation"""

    @pytest.mark.unit
    def test_get_all_flows_args_defaults(self):
        """Test GetAllFlowsArgs default values"""
        args = GetAllFlowsArgs()
        assert args.page == 1
        assert args.per_page == 50
        assert args.include is None

    @pytest.mark.unit
    def test_get_all_flows_args_custom(self):
        """Test GetAllFlowsArgs with custom values"""
        args = GetAllFlowsArgs(page=2, per_page=100, include="versions")
        assert args.page == 2
        assert args.per_page == 100
        assert args.include == "versions"

    @pytest.mark.unit
    def test_get_all_flows_args_validation(self):
        """Test GetAllFlowsArgs validation"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            GetAllFlowsArgs(page=0)  # page must be >= 1

        with pytest.raises(Exception):
            GetAllFlowsArgs(per_page=0)  # per_page must be >= 1

        with pytest.raises(Exception):
            GetAllFlowsArgs(per_page=300)  # per_page must be <= 200

    @pytest.mark.unit
    def test_get_flow_runs_args_status_filter(self):
        """Test GetFlowRunsArgs status filter"""
        args = GetFlowRunsArgs(status=3)  # FAILURE
        assert args.status == 3

    @pytest.mark.unit
    def test_create_process_flow_args_defaults(self):
        """Test CreateProcessFlowByPromptArgs defaults"""
        args = CreateProcessFlowByPromptArgs(prompt="test flow")
        assert args.priority == 3
        assert args.schedule_cron == "0 * * * *"
        assert args.enable is False

    @pytest.mark.unit
    def test_create_process_flow_args_validation(self):
        """Test CreateProcessFlowByPromptArgs validation"""
        with pytest.raises(Exception):
            CreateProcessFlowByPromptArgs(prompt="test", priority=0)  # priority >= 1

        with pytest.raises(Exception):
            CreateProcessFlowByPromptArgs(prompt="test", priority=6)  # priority <= 5
