import datetime
import re
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------------------

class GetAllFlowsArgs(BaseModel):
    page: int = Field(1, ge=1)
    per_page: int = Field(50, ge=1, le=200)
    include: Optional[str] = Field(None, description="Comma-separated includes (optional)")

class GetFlowRunsArgs(BaseModel):
    status: Optional[int] = Field(None, description="1=STARTED, 2=SUCCESS, 3=FAILURE, 4=STOPPED, 5=PARTIAL_SUCCESS")
    started_after: Optional[str] = Field(None, description="Timestamp or epoch-ms as string")
    page: int = Field(1, ge=1)
    per_page: int = Field(50, ge=1, le=200)
    sort: Optional[str] = Field("-started_at")
    include: Optional[str] = Field(None)

class GetFlowRunLogsArgs(BaseModel):
    run_id: str
    per_page: int = Field(10, ge=1, le=200)
    page: int = Field(1, ge=1)
    sort: str = Field("id")
    include: str = Field("flowRunLogMetadata")
    fields_flowStep: str = Field("id,name")
    load_payload_ids: bool = Field(True)

class SummariseFailedRunArgs(BaseModel):
    run_id: str
    max_logs: int = Field(50, ge=1, le=500)

class DownloadPayloadArgs(BaseModel):
    payload_metadata_id: str

class StartFlowArgs(BaseModel):
    flow_id: str
    payload: Optional[Dict[str, Any]] = Field(None, description="Optional JSON payload")

class TriageLatestFailuresArgs(BaseModel):
    started_after: Optional[str] = Field(None, description="Timestamp/epoch-ms (string) to filter newer runs")
    limit: int = Field(20, ge=1, le=200, description="How many failed runs to summarise")
    per_run_log_limit: int = Field(50, ge=1, le=500, description="Log entries per run to fetch")

class ListDataPoolsArgs(BaseModel):
    page: int = Field(1, ge=1)
    per_page: int = Field(50, ge=1, le=200)

class GetDedupedDataArgs(BaseModel):
    pool_id: str
    page: int = Field(1, ge=1)
    per_page: int = Field(50, ge=1, le=200)

class GetMarketplaceAppsArgs(BaseModel):
    page: int = Field(1, ge=1)
    per_page: int = Field(50, ge=1, le=200)
    include: Optional[str] = Field(None, description="Comma-separated includes (e.g., 'flowTemplates,systemTemplates')")
    filter_name: Optional[str] = Field(None, description="Filter by app name")
    filter_allowed: Optional[bool] = Field(None, description="Filter by allowed status")
    filter_private: Optional[bool] = Field(None, description="Filter by private status")
    sort: Optional[str] = Field(None, description="Sort field (e.g., 'name', '-created_at')")

class GetMarketplaceAppArgs(BaseModel):
    marketplace_app_id: str = Field(..., description="The ID of the marketplace app to retrieve")
    include: Optional[str] = Field(None, description="Comma-separated includes (e.g., 'flowTemplates,systemTemplates')")

class CreateProcessFlowByPromptArgs(BaseModel):
    prompt: str = Field(..., description="e.g. 'create a process flow for Shopify to NetSuite orders'")
    priority: int = Field(3, ge=1, le=5, description="Flow priority (1 highest)")
    schedule_cron: Optional[str] = Field("0 * * * *", description="Cron schedule; set None to omit")
    enable: bool = Field(False, description="Whether to enable on import")

class CreateProcessFlowFromJsonArgs(BaseModel):
    body: Dict[str, Any] = Field(..., description="Complete /flows/import JSON to send as-is")


ENTITY_GUESSES = [
    "orders","order","customers","customer","products","inventory","shipments","invoices","payments"
]

def _guess_parts_from_prompt(prompt: str) -> Dict[str, str]:
    p = prompt.strip().lower()
    m = re.search(r"for\s+(.+?)\s+to\s+(.+?)\s+([a-zA-Z\-_/ ]+)$", p) or         re.search(r"(?:create|build).*\bflow\b.*?for\s+(.+?)\s+to\s+(.+?)\s+([a-zA-Z\-_/ ]+)$", p)
    src = dst = ent = None
    if m:
        src, dst, ent = [x.strip() for x in m.groups()]
    else:
        m2 = re.search(r"for\s+(.+?)\s+to\s+(.+?)$", p) or re.search(r"(.+?)\s+to\s+(.+?)$", p)
        if m2:
            src, dst = [x.strip() for x in m2.groups()]
    def nice(s): return (s or "").strip().title()
    src, dst = nice(src), nice(dst)
    ent = (ent or "").strip().lower()
    for guess in ENTITY_GUESSES:
        if guess in ent:
            ent = "orders" if "order" in guess else guess
            break
    ent = ent or "orders"
    return {"source": src or "System A", "destination": dst or "System B", "entity": ent}

def _build_generic_import_json(src: str, dst: str, entity: str, *, priority: int, schedule_cron: str | None, enable: bool) -> Dict[str, Any]:
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    flow_name = f"{src} > {dst} {entity.title()} - {now}"
    steps = [
        {
            "name": "Try/Catch",
            "microservice": "try-catch",
            "config": {"action": "partial_success"},
            "routes": [
                {"name": "Try", "first_step": "Source Connector"},
                {"name": "Catch"}
            ]
        },
        {
            "name": "Source Connector",
            "microservice": "connector",
            "config": {
                "timeout": 30,
                "wrapping_behaviour": "Raw",
                "allow_unsuccessful_statuses": False
            },
            "endpoint": {
                "name": f"{src} - Retrieve {entity}",
                "direction": "Receive",
                "http_method": "GET",
                "data_type": "json"
            }
        },
        {
            "name": "Flow Control",
            "microservice": "batch",
            "config": {"path": "*", "size": 1}
        },
        {
            "name": "Map",
            "microservice": "map",
            "config": {}
        },
        {
            "name": "Destination Connector",
            "microservice": "connector",
            "config": {
                "timeout": 30,
                "wrapping_behaviour": "First",
                "allow_unsuccessful_statuses": True
            },
            "endpoint": {
                "name": f"{dst} - Upsert {entity}",
                "direction": "Send",
                "http_method": "POST",
                "data_type": "json"
            }
        }
    ]

    schedules = []
    if schedule_cron:
        schedules.append({"cron_string": schedule_cron})

    flow = {
        "name": flow_name,
        "description": f"{src} → {dst} {entity} (generated)",
        "is_enabled": bool(enable),
        "priority": priority,
        "versions": [
            {
                "flow_name": flow_name,
                "flow_priority": priority,
                "status": "Draft",
                "is_deployed": False,
                "steps": steps,
                "schedules": schedules
            }
        ]
    }

    systems = [
        {
            "system": {
                "name": src,
                "label": f"{src} (placeholder)",
                "protocol": "HTTP"
            }
        },
        {
            "system": {
                "name": dst,
                "label": f"{dst} (placeholder)",
                "protocol": "HTTP"
            }
        }
    ]

    return {
        "metadata": {
            "company_name": "Generated by MCP",
            "flow_name": flow_name,
            "exported_at": now
        },
        "flow": flow,
        "systems": systems
    }
