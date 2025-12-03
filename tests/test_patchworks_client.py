"""
Tests for patchworks_client module
"""
import pytest
import requests_mock
import requests
from unittest.mock import patch, MagicMock
import patchworks_client as pw


class TestHelperFunctions:
    """Tests for helper functions"""

    @pytest.mark.unit
    def test_url_construction(self):
        """Test _url helper constructs URLs correctly"""
        result = pw._url("https://api.example.com", "/flows")
        assert result == "https://api.example.com/flows"

    @pytest.mark.unit
    def test_url_with_leading_slash(self):
        """Test _url with leading slash in path"""
        result = pw._url("https://api.example.com", "/flows")
        assert result == "https://api.example.com/flows"

    @pytest.mark.unit
    def test_url_without_leading_slash(self):
        """Test _url without leading slash in path"""
        result = pw._url("https://api.example.com", "flows")
        assert result == "https://api.example.com/flows"


class TestGetAllFlows:
    """Tests for get_all_flows function"""

    @pytest.mark.client
    def test_get_all_flows_success(self, sample_flow_data):
        """Test successful get_all_flows call"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/flows',
                json=sample_flow_data
            )

            result = pw.get_all_flows(page=1, per_page=50)

            assert result["data"][0]["id"] == "flow-123"
            assert result["data"][0]["attributes"]["name"] == "Test Flow"
            assert result["meta"]["total"] == 1

    @pytest.mark.client
    def test_get_all_flows_with_include(self):
        """Test get_all_flows with include parameter"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/flows',
                json={"data": []}
            )

            pw.get_all_flows(page=1, per_page=50, include="versions,systems")

            # Check the request was made with correct params
            assert m.last_request.qs["include"] == ["versions,systems"]

    @pytest.mark.client
    def test_get_all_flows_pagination(self):
        """Test get_all_flows pagination parameters"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/flows',
                json={"data": []}
            )

            pw.get_all_flows(page=3, per_page=25)

            assert m.last_request.qs["page"] == ["3"]
            assert m.last_request.qs["per_page"] == ["25"]

    @pytest.mark.client
    def test_get_all_flows_http_error(self):
        """Test get_all_flows handles HTTP errors"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/flows',
                status_code=401,
                text="Unauthorized"
            )

            with pytest.raises(RuntimeError) as exc_info:
                pw.get_all_flows()

            assert "401" in str(exc_info.value)


class TestGetFlowRuns:
    """Tests for get_flow_runs function"""

    @pytest.mark.client
    def test_get_flow_runs_with_status_filter(self, sample_flow_run_data):
        """Test get_flow_runs with status filter"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/flow-runs',
                json=sample_flow_run_data
            )

            result = pw.get_flow_runs(status=3)  # FAILURE

            assert m.last_request.qs["filter[status]"] == ["3"]
            assert result["data"][0]["attributes"]["status"] == 3

    @pytest.mark.client
    def test_get_flow_runs_with_started_after(self):
        """Test get_flow_runs with started_after filter"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/flow-runs',
                json={"data": []}
            )

            pw.get_flow_runs(started_after="2025-12-01T00:00:00Z")

            # requests-mock lowercases query string keys
            assert "filter[started_after]" in str(m.last_request.qs) or \
                   "filter%5Bstarted_after%5D" in m.last_request.query

    @pytest.mark.client
    def test_get_flow_runs_with_sort(self):
        """Test get_flow_runs with sort parameter"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/flow-runs',
                json={"data": []}
            )

            pw.get_flow_runs(sort="-started_at")

            assert m.last_request.qs["sort"] == ["-started_at"]


class TestGetFlowRunLogs:
    """Tests for get_flow_run_logs function"""

    @pytest.mark.client
    def test_get_flow_run_logs_success(self, sample_log_data):
        """Test successful get_flow_run_logs call"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/flow-runs/run-456/flow-run-logs',
                json=sample_log_data
            )

            result = pw.get_flow_run_logs("run-456")

            assert len(result["data"]) == 3
            assert result["data"][1]["attributes"]["log_level"] == "ERROR"

    @pytest.mark.client
    def test_get_flow_run_logs_with_params(self):
        """Test get_flow_run_logs with custom parameters"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/flow-runs/run-456/flow-run-logs',
                json={"data": []}
            )

            pw.get_flow_run_logs(
                "run-456",
                per_page=20,
                page=2,
                sort="created_at",
                load_payload_ids=False
            )

            assert m.last_request.qs["per_page"] == ["20"]
            assert m.last_request.qs["page"] == ["2"]
            assert m.last_request.qs["sort"] == ["created_at"]
            assert m.last_request.qs["load_payload_ids"] == ["false"]


class TestDownloadPayload:
    """Tests for download_payload function"""

    @pytest.mark.client
    def test_download_payload_success(self):
        """Test successful payload download"""
        with requests_mock.Mocker() as m:
            test_content = b"test payload content"
            m.get(
                'https://core.test.example.com/api/v1/payload-metadata/payload-123/download',
                content=test_content,
                headers={"Content-Type": "application/json"}
            )

            content_type, raw_bytes = pw.download_payload("payload-123")

            assert content_type == "application/json"
            assert raw_bytes == test_content

    @pytest.mark.client
    def test_download_payload_default_content_type(self):
        """Test payload download with default content type"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/payload-metadata/payload-123/download',
                content=b"test"
            )

            content_type, _ = pw.download_payload("payload-123")

            assert content_type == "application/octet-stream"

    @pytest.mark.client
    def test_download_payload_error(self):
        """Test payload download error handling"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/payload-metadata/payload-123/download',
                status_code=404,
                text="Not found"
            )

            with pytest.raises(RuntimeError) as exc_info:
                pw.download_payload("payload-123")

            assert "404" in str(exc_info.value)


class TestStartFlow:
    """Tests for start_flow function"""

    @pytest.mark.client
    def test_start_flow_success(self):
        """Test successful flow start"""
        with requests_mock.Mocker() as m:
            m.post(
                'https://start.test.example.com/api/v1/flows/flow-123/start',
                json={"status": "started", "run_id": "run-789"}
            )

            result = pw.start_flow("flow-123", payload={"data": "test"})

            assert result["status"] == "started"
            assert result["run_id"] == "run-789"

    @pytest.mark.client
    def test_start_flow_without_payload(self):
        """Test flow start without payload"""
        with requests_mock.Mocker() as m:
            m.post(
                'https://start.test.example.com/api/v1/flows/flow-123/start',
                json={"status": "started"}
            )

            result = pw.start_flow("flow-123")

            assert result["status"] == "started"
            # Check empty dict was sent
            assert m.last_request.json() == {}


class TestDataPools:
    """Tests for data pool functions"""

    @pytest.mark.client
    def test_list_data_pools(self):
        """Test list_data_pools function"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/data-pool/',
                json={"data": [{"id": "pool-1", "attributes": {"name": "Test Pool"}}]}
            )

            result = pw.list_data_pools(page=1, per_page=50)

            assert result["data"][0]["id"] == "pool-1"
            assert result["data"][0]["attributes"]["name"] == "Test Pool"

    @pytest.mark.client
    def test_get_deduped_data(self):
        """Test get_deduped_data function"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/data-pool/pool-1/deduped-data',
                json={"data": [{"id": "row-1", "attributes": {"data": "value"}}]}
            )

            result = pw.get_deduped_data("pool-1", page=1, per_page=50)

            assert result["data"][0]["id"] == "row-1"


class TestMarketplace:
    """Tests for marketplace functions"""

    @pytest.mark.client
    def test_get_marketplace_apps(self, sample_marketplace_apps):
        """Test get_marketplace_apps function"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/patchworks/marketplace-apps',
                json=sample_marketplace_apps
            )

            result = pw.get_marketplace_apps()

            assert len(result["data"]) == 2
            assert result["data"][0]["attributes"]["name"] == "Shopify"

    @pytest.mark.client
    def test_get_marketplace_apps_with_filters(self):
        """Test get_marketplace_apps with filters"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/patchworks/marketplace-apps',
                json={"data": []}
            )

            pw.get_marketplace_apps(
                filter_name="Shopify",
                filter_allowed=True,
                filter_private=False,
                sort="name"
            )

            # Check the request was made with correct parameters (case-insensitive)
            query = m.last_request.query.lower()
            assert "shopify" in query
            assert "filter" in query

    @pytest.mark.client
    def test_get_marketplace_app(self):
        """Test get_marketplace_app function"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/patchworks/marketplace-apps/app-1',
                json={"data": {"id": "app-1", "attributes": {"name": "Shopify"}}}
            )

            result = pw.get_marketplace_app("app-1", include="flowTemplates")

            assert result["data"]["id"] == "app-1"
            # Check include param was passed (case-insensitive)
            assert "include" in m.last_request.query.lower()


class TestSummariseFailedRun:
    """Tests for summarise_failed_run function"""

    @pytest.mark.client
    def test_summarise_failed_run_success(self, sample_log_data):
        """Test summarise_failed_run with error logs"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/flow-runs/run-456/flow-run-logs',
                json=sample_log_data
            )

            result = pw.summarise_failed_run("run-456", max_logs=50)

            assert result["run_id"] == "run-456"
            assert result["log_count"] == 3
            assert result["levels"]["INFO"] == 1
            assert result["levels"]["ERROR"] == 1
            assert result["levels"]["FATAL"] == 1
            assert len(result["highlights"]) >= 1
            assert "Connection timeout" in result["highlights"][0]

    @pytest.mark.client
    def test_summarise_failed_run_no_errors(self):
        """Test summarise_failed_run with no error logs"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/flow-runs/run-456/flow-run-logs',
                json={
                    "data": [
                        {
                            "id": "log-1",
                            "attributes": {
                                "log_level": "INFO",
                                "log_message": "All good",
                                "created_at": "2025-12-03T10:00:00Z"
                            }
                        }
                    ]
                }
            )

            result = pw.summarise_failed_run("run-456")

            assert result["log_count"] == 1
            assert "ERROR" not in result["levels"]
            assert len(result["highlights"]) == 1
            assert "All good" in result["highlights"][0]


class TestTriageLatestFailures:
    """Tests for triage_latest_failures function"""

    @pytest.mark.client
    def test_triage_latest_failures(self, sample_flow_run_data, sample_log_data):
        """Test triage_latest_failures function"""
        with requests_mock.Mocker() as m:
            # Mock get_flow_runs
            m.get(
                'https://core.test.example.com/api/v1/flow-runs',
                json=sample_flow_run_data
            )
            # Mock get_flow_run_logs
            m.get(
                'https://core.test.example.com/api/v1/flow-runs/run-456/flow-run-logs',
                json=sample_log_data
            )

            result = pw.triage_latest_failures(limit=20, per_run_log_limit=50)

            assert result["count"] == 1
            assert result["items"][0]["run_id"] == "run-456"
            assert result["items"][0]["status"] == 3
            assert "summary" in result["items"][0]
            assert result["items"][0]["summary"]["log_count"] == 3

    @pytest.mark.client
    def test_triage_latest_failures_with_started_after(self):
        """Test triage_latest_failures with started_after filter"""
        with requests_mock.Mocker() as m:
            m.get(
                'https://core.test.example.com/api/v1/flow-runs',
                json={"data": []}
            )

            result = pw.triage_latest_failures(
                started_after="2025-12-01T00:00:00Z",
                limit=10
            )

            assert result["started_after"] == "2025-12-01T00:00:00Z"
            assert result["count"] == 0


class TestImportFlow:
    """Tests for import_flow function"""

    @pytest.mark.client
    def test_import_flow_success(self):
        """Test successful flow import"""
        with requests_mock.Mocker() as m:
            m.post(
                'https://core.test.example.com/api/v1/flows/import',
                json={"status": "success", "flow_id": "flow-999"}
            )

            payload = {
                "metadata": {"company_name": "Test"},
                "flow": {"name": "Test Flow"},
                "systems": []
            }

            result = pw.import_flow(payload)

            assert result["status"] == "success"
            assert result["flow_id"] == "flow-999"
            assert m.last_request.json() == payload

    @pytest.mark.client
    def test_import_flow_error(self):
        """Test flow import error handling"""
        with requests_mock.Mocker() as m:
            m.post(
                'https://core.test.example.com/api/v1/flows/import',
                status_code=400,
                text="Invalid flow definition"
            )

            with pytest.raises(RuntimeError) as exc_info:
                pw.import_flow({"invalid": "data"})

            assert "400" in str(exc_info.value)
