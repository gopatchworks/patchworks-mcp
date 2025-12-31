from __future__ import annotations
import os, json, sys, logging, base64
from typing import Any, List, Optional, Dict
from typing_extensions import Annotated
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP
import re

import patchworks_client as pw
from datetime import datetime

# Log to STDERR only (stdio transport cannot receive stdout noise)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger("patchworks-mcp")

mcp = FastMCP("patchworks")


# Regex patterns derived from your JSON Schema
# Note: JSON double backslashes (\\) are converted to single backslashes (\) for Python raw strings.
DATE_PATTERN = r"^(?:(?:(?:(?:(?:[13579][26]|[2468][048])00)|(?:[0-9]{2}(?:(?:[13579][26])|(?:[2468][048]|0[48]))))(?:-)(?:02)(?:-)(?:29))|(?:(?:[0-9]{4})(?:-)(?:(?:(?:0[13578]|1[02])(?:-)(?:31))|(?:(?:0[1,3-9]|1[0-2])(?:-)(?:29|30))|(?:(?:0[1-9])|(?:1[0-2]))(?:-)(?:0[1-9]|1[0-9]|2[0-8]))))(?:T)(?:[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?)(?:Z)$"
# The provided regex in the prompt was slightly complex; this is the cleaned raw string version of the ISO8601 pattern provided.
# If you prefer the exact raw pattern from the prompt:
PROMPT_DATE_PATTERN = r"^(?:(?:\d\d[2468][048]|\d\d[13579][26]|\d\d0[48]|[02468][048]00|[13579][26]00)-02-29|\d{4}-(?:(?:0[13578]|1[02])-(?:0[1-9]|[12]\d|3[01])|(?:0[469]|11)-(?:0[1-9]|[12]\d|30)|(?:02)-(?:0[1-9]|1\d|2[0-8])))T(?:(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d+)?)?(?:Z))$"

EMAIL_PATTERN = r"^(?!\.)(?!.*\.\.)([A-Za-z0-9_'+\-\.]*)[A-Za-z0-9_+-]@([A-Za-z0-9][A-Za-z0-9\-]*\.)+[A-Za-z]{2,}$"

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
            ent = "orders" if "order" in guess else guess.rstrip("s")+"s"
            break
    ent = ent or "orders"
    return {"source": src or "System A", "destination": dst or "System B", "entity": ent}

def _build_generic_import_json(src: str, dst: str, entity: str, *, priority: int, schedule_cron: str | None, enable: bool) -> Dict[str, Any]:
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
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

# ------------------------------------------------------------------------------
# Patchworks Tools
# ------------------------------------------------------------------------------

@mcp.tool()
def get_all_flows(args: GetAllFlowsArgs) -> Any:
    """List flows from the Core API."""
    return pw.get_all_flows(page=args.page, per_page=args.per_page, include=args.include)

@mcp.tool()
def get_flow_runs(args: GetFlowRunsArgs) -> Any:
    """Query flow runs (filter by status, started_after; sort; includes)."""
    return pw.get_flow_runs(
        status=args.status,
        started_after=args.started_after,
        page=args.page,
        per_page=args.per_page,
        sort=args.sort,
        include=args.include,
    )

@mcp.tool()
def get_flow_run_logs(args: GetFlowRunLogsArgs) -> Any:
    """Retrieve logs for a specific flow run (optionally with payload IDs)."""
    return pw.get_flow_run_logs(
        run_id=args.run_id,
        per_page=args.per_page,
        page=args.page,
        sort=args.sort,
        include=args.include,
        fields_flowStep=args.fields_flowStep,
        load_payload_ids=args.load_payload_ids,
    )


@mcp.tool()
def summarise_failed_run(args: SummariseFailedRunArgs) -> Any:
    """Summarise what went wrong in a failed run by inspecting log levels/messages."""
    return pw.summarise_failed_run(run_id=args.run_id, max_logs=args.max_logs)

@mcp.tool()
def triage_latest_failures(args: TriageLatestFailuresArgs) -> Any:
    """Fetch recent failed runs and return a compact summary for each."""
    return pw.triage_latest_failures(
        started_after=args.started_after,
        limit=args.limit,
        per_run_log_limit=args.per_run_log_limit,
    )

@mcp.tool()
def download_payload(args: DownloadPayloadArgs) -> Any:
    """Download payload bytes for a given payload metadata ID (returned as base64)."""
    ctype, raw = pw.download_payload(args.payload_metadata_id)
    return {"content_type": ctype, "bytes_base64": base64.b64encode(raw).decode("ascii")}

@mcp.tool()
def start_flow(args: StartFlowArgs) -> Any:
    """Trigger a flow run via the Start service (/flows/{id}/start)."""
    return pw.start_flow(flow_id=args.flow_id, payload=args.payload)

@mcp.tool()
def list_data_pools(args: ListDataPoolsArgs) -> Any:
    """List all data/dedupe pools."""
    return pw.list_data_pools(page=args.page, per_page=args.per_page)

@mcp.tool()
def get_deduped_data(args: GetDedupedDataArgs) -> Any:
    """Retrieve deduplicated data for a specific pool."""
    return pw.get_deduped_data(pool_id=args.pool_id, page=args.page, per_page=args.per_page)

@mcp.tool()
def create_process_flow_from_prompt(args: CreateProcessFlowByPromptArgs) -> Any:
    """
    Build a generic flow from a natural-language prompt and import it.
    Produces a Try/Catch → Source Connector → Batch → Map → Destination Connector skeleton.
    """
    parts = _guess_parts_from_prompt(args.prompt)
    body = _build_generic_import_json(
        parts["source"], parts["destination"], parts["entity"],
        priority=args.priority,
        schedule_cron=args.schedule_cron,
        enable=args.enable
    )
    return pw.import_flow(body)

@mcp.tool()
def create_process_flow_from_json(args: CreateProcessFlowFromJsonArgs) -> Any:
    """
    Import a flow with the exact JSON body provided.
    Useful when you want to post a full export unchanged.
    """
    return pw.import_flow(args.body)

# ------------------------------------------------------------------------------
# Commerce Foundation Operation Query Tools
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# Tool get-customers Commerce Foundation Operation Query Tools
# ------------------------------------------------------------------------------
class GetCustomersArgs(BaseModel):
    # Enforce "additionalProperties": false
    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')

    updatedAtMin: Optional[str] = Field(
        default=None, 
        description="Minimum updated at date (inclusive)",
        pattern=PROMPT_DATE_PATTERN,
        json_schema_extra={"format": "date-time"}
    )
    
    updatedAtMax: Optional[str] = Field(
        default=None, 
        description="Maximum updated at date (inclusive)",
        pattern=PROMPT_DATE_PATTERN,
        json_schema_extra={"format": "date-time"}
    )
    
    createdAtMin: Optional[str] = Field(
        default=None, 
        description="Minimum created at date (inclusive)",
        pattern=PROMPT_DATE_PATTERN,
        json_schema_extra={"format": "date-time"}
    )
    
    createdAtMax: Optional[str] = Field(
        default=None, 
        description="Maximum created at date (inclusive)",
        pattern=PROMPT_DATE_PATTERN,
        json_schema_extra={"format": "date-time"}
    )
    
    pageSize: Optional[int] = Field(
        default=10, 
        description="Number of results to return per page. Use with skip to paginate through results.",
        gt=0, # exclusiveMinimum: 0
        le=9007199254740991 # maximum safe integer
    )
    
    skip: Optional[int] = Field(
        default=0, 
        description="Number of results to skip. To navigate to the next page, increment skip by pageSize (e.g., skip=0 for first page, skip=100 for second page when pageSize=100).",
        ge=0, # minimum: 0
        le=9007199254740991 # maximum safe integer
    )
    
    ids: Optional[List[str]] = Field(
        default=None, 
        description="Unique customer ID in the Fulfillment System"
    )
    
    # We use Annotated to apply the regex pattern to the items *inside* the list
    emails: Optional[List[Annotated[str, Field(pattern=EMAIL_PATTERN, json_schema_extra={"format": "email"})]]] = Field(
        default=None, 
        description="Customer email address"
    )
    
@mcp.tool()    
def get_customers(args: Optional[GetCustomersArgs] = None) -> Any:
    """Get customers as per JSON args in the input schema. If no args is provided, get all customers."""
 
    # 1. Convert the Pydantic model to a clean dictionary
    # exclude_none=True ensures we don't send "locationIds": null if it wasn't provided
    query_data = args.model_dump(exclude_none=True)
    
    # 2. Serialize that dictionary into a JSON string
    json_string_payload = json.dumps(query_data)
    
    # 3. Pass the JSON string to your service method
    return pw.get_customers(inputSchema=json_string_payload)

# ------------------------------------------------------------------------------
# Tool get-products Commerce Foundation Operation Query Tools
# ------------------------------------------------------------------------------

class GetProductsArgs(BaseModel):
    # Allows additionalProperties: false
    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')
    ids: Optional[List[str]] = Field(
        default=None,
        description="Unique product ID in the Fulfillment System"
    )
    skus: Optional[List[str]] = Field(
        default=None,
        description="Product SKU (Stock Keeping Unit)"
    )
    updatedAtMin: Optional[str] = Field(
        default=None,
        description="Minimum updated at date (inclusive)",
        pattern=DATE_PATTERN
    )
    updatedAtMax: Optional[str] = Field(
        default=None,
        description="Maximum updated at date (inclusive)",
        pattern=DATE_PATTERN
    )
    createdAtMin: Optional[str] = Field(
        default=None,
        description="Minimum created at date (inclusive)",
        pattern=DATE_PATTERN
    )
    createdAtMax: Optional[str] = Field(
        default=None,
        description="Maximum created at date (inclusive)",
        pattern=DATE_PATTERN
    )
    pageSize: int = Field(
        default=10,
        gt=0, # exclusiveMinimum: 0
        le=9007199254740991, # maximum
        description="Number of results to return per page. Use with skip to paginate through results."
    )
    skip: int = Field(
        default=0,
        ge=0, # minimum: 0
        le=9007199254740991, # maximum
        description="Number of results to skip. To navigate to the next page, increment skip by pageSize (e.g., skip=0 for first page, skip=100 for second page when pageSize=100)."
    )

@mcp.tool()    
def get_products(args: Optional[GetProductsArgs] = None) -> Any:
    """Get products as per JSON args in the input schema. If no args is provided, get all products."""
    
    # 1. Convert the Pydantic model to a clean dictionary
    # exclude_none=True ensures we don't send "locationIds": null if it wasn't provided
    query_data = args.model_dump(exclude_none=True)
    
    # 2. Serialize that dictionary into a JSON string
    json_string_payload = json.dumps(query_data)
    
    # 3. Pass the JSON string to your service method
    return pw.get_products(inputSchema=json_string_payload)
# ------------------------------------------------------------------------------
# Tool get-product-variants Commerce Foundation Operation Query Tools
# ------------------------------------------------------------------------------

class GetProductVariantsArgs(BaseModel):
    # Allows additionalProperties: false
    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')

    ids: Optional[List[str]] = Field(
        default=None,
        description="Unique variant IDs in the fulfillment system"
    )
    
    skus: Optional[List[str]] = Field(
        default=None,
        description="Variant SKUs (Stock Keeping Units)"
    )
    
    productIds: Optional[List[str]] = Field(
        default=None,
        description="Parent product IDs; returns all variants"
    )
    
    updatedAtMin: Optional[str] = Field(
        default=None,
        description="Minimum updated at date (inclusive)",
        pattern=DATE_PATTERN
    )
    
    updatedAtMax: Optional[str] = Field(
        default=None,
        description="Maximum updated at date (inclusive)",
        pattern=DATE_PATTERN
    )
    
    createdAtMin: Optional[str] = Field(
        default=None,
        description="Minimum created at date (inclusive)",
        pattern=DATE_PATTERN
    )
    
    createdAtMax: Optional[str] = Field(
        default=None,
        description="Maximum created at date (inclusive)",
        pattern=DATE_PATTERN
    )
    
    pageSize: int = Field(
        default=10,
        gt=0, # exclusiveMinimum: 0
        le=9007199254740991, # maximum
        description="Number of results to return per page. Use with skip to paginate through results."
    )
    
    skip: int = Field(
        default=0,
        ge=0, # minimum: 0
        le=9007199254740991, # maximum
        description="Number of results to skip. To navigate to the next page, increment skip by pageSize (e.g., skip=0 for first page, skip=100 for second page when pageSize=100)."
    )


@mcp.tool()    
def get_product_variants(args: GetProductVariantsArgs) -> Any:
    """Get product variants as per JSON args in the input schema. If no args is provided, get all variants."""
    
    # 1. Convert the Pydantic model to a clean dictionary
    # exclude_none=True ensures we don't send "locationIds": null if it wasn't provided
    query_data = args.model_dump(exclude_none=True)
    
    # 2. Serialize that dictionary into a JSON string
    json_string_payload = json.dumps(query_data)
    
    # 3. Pass the JSON string to your service method
    return pw.get_product_variants(inputSchema=json_string_payload)

# ------------------------------------------------------------------------------
# Tool get-inventory Commerce Foundation Operation Query Tools
# ------------------------------------------------------------------------------

class GetInventoryArgs(BaseModel):
    skus: Optional[List[str]] = Field(
        default=None, 
        description="Product SKU to get inventory for (required)"
    )
    locationIds: Optional[List[str]] = Field(
        None, 
        description="Specific warehouse/location ID (optional - if not provided, returns aggregated inventory)"
    )

@mcp.tool()
def get_inventory(args: Optional[GetInventoryArgs] = None) -> Any:
    """Input schema for querying inventory. Returns inventory data for specific SKUs."""
    
    # 1. Convert the Pydantic model to a clean dictionary
    # exclude_none=True ensures we don't send "locationIds": null if it wasn't provided
    query_data = args.model_dump(exclude_none=True)
    
    # 2. Serialize that dictionary into a JSON string
    json_string_payload = json.dumps(query_data)
    
    # 3. Pass the JSON string to your service method
    return pw.get_inventory(inputSchema=json_string_payload)


# ------------------------------------------------------------------------------
# Tool get-returns Commerce Foundation Operation Query Tools
# ------------------------------------------------------------------------------
 
class GetReturnsArgs(BaseModel):
    ids: Optional[List[str]] = Field(
        default=None, 
        description="Internal return IDs"
    )
    orderIds: Optional[List[str]] = Field(
        default=None, 
        description="Order IDs to find returns for"
    )
    returnNumbers: Optional[List[str]] = Field(
        default=None, 
        description="Return numbers (customer-facing identifiers)"
    )
    statuses: Optional[List[str]] = Field(
        default=None, 
        description="Return statuses"
    )
    outcomes: Optional[List[str]] = Field(
        default=None, 
        description="Return outcomes (refund/exchange)"
    )
 
@mcp.tool()
def get_returns(args: Optional[GetReturnsArgs] = None) -> Any:
    """Get inventory as per JSON args in the input schema. If no args is provided, get all inventory."""
    
    # 1. Convert the Pydantic model to a clean dictionary
    # exclude_none=True ensures we don't send "locationIds": null if it wasn't provided
    query_data = args.model_dump(exclude_none=True)
    
    # 2. Serialize that dictionary into a JSON string
    json_string_payload = json.dumps(query_data)
    
    # 3. Pass the JSON string to your service method
    return pw.get_returns(inputSchema=json_string_payload)

# ------------------------------------------------------------------------------
# Tool get-fulfillments Commerce Foundation Operation Query Tools
# ------------------------------------------------------------------------------

class GetFulfillmentArgs(BaseModel):
    model_config = ConfigDict(regex_engine='python-re')
    ids: Optional[List[str]] = Field(
        default=None,
        description="Unique shipment ID in the Fulfillment System"
    )
    orderIds: Optional[List[str]] = Field(
        default=None,
        description="Order ID associated with the shipment"
    )
    updatedAtMin: Optional[str] = Field(
        default=None,
        description="Minimum updated at date (inclusive)",
        pattern=DATE_PATTERN
    )
    updatedAtMax: Optional[str] = Field(
        default=None,
        description="Maximum updated at date (inclusive)",
        pattern=DATE_PATTERN
    )
    createdAtMin: Optional[str] = Field(
        default=None,
        description="Minimum created at date (inclusive)",
        pattern=DATE_PATTERN
    )
    createdAtMax: Optional[str] = Field(
        default=None,
        description="Maximum created at date (inclusive)",
        pattern=DATE_PATTERN
    )
    pageSize: int = Field(
        default=10,
        description="Number of results to return per page. Use with skip to paginate through results.",
        gt=0,  # Exclusive minimum 0
        le=9007199254740991 # Maximum safety limit
    )
    skip: int = Field(
        default=0,
        description="Number of results to skip. To navigate to the next page, increment skip by pageSize (e.g., skip=0 for first page, skip=100 for second page when pageSize=100).",
        ge=0,  # Minimum 0
        le=9007199254740991
    )

    # This enforces "additionalProperties": false
    model_config = ConfigDict(extra="forbid")

@mcp.tool()
def get_fulfillments(args: Optional[GetFulfillmentArgs] = None) -> Any:
    """Get inventory as per JSON args in the input schema. If no args is provided, get all inventory."""
    
    # 1. Convert the Pydantic model to a clean dictionary
    # exclude_none=True ensures we don't send "locationIds": null if it wasn't provided
    query_data = args.model_dump(exclude_none=True)
    
    # 2. Serialize that dictionary into a JSON string
    json_string_payload = json.dumps(query_data)
    
    # 3. Pass the JSON string to your service method
    return pw.get_fulfillments(inputSchema=json_string_payload)

class GetOrdersArgs(BaseModel):
    ids: Optional[List[str]] = Field(
        None, 
        description="Internal order ID, could be a comma separated list"
    )
    externalIds: Optional[List[str]] = Field(
        None, 
        description="External order ID from source system, could be a comma separated list"
    )
    statuses: Optional[List[str]] = Field(
        None, 
        description="Order status"
    )
    names: Optional[List[str]] = Field(
        None, 
        description="Friendly Order identifier"
    )
    includeLineItems: bool = Field(
        True, 
        description="Whether to include detailed line item information in the returned orders"
    )
    updatedAtMin: Optional[str] = Field(
        None, 
        description="Minimum updated at date (inclusive). Format: ISO 8601 (YYYY-MM-DDThh:mm:ssZ)"
    )
    updatedAtMax: Optional[str] = Field(
        None, 
        description="Maximum updated at date (inclusive). Format: ISO 8601 (YYYY-MM-DDThh:mm:ssZ)"
    )
    createdAtMin: Optional[str] = Field(
        None, 
        description="Minimum created at date (inclusive). Format: ISO 8601 (YYYY-MM-DDThh:mm:ssZ)"
    )
    createdAtMax: Optional[str] = Field(
        None, 
        description="Maximum created at date (inclusive). Format: ISO 8601 (YYYY-MM-DDThh:mm:ssZ)"
    )
    pageSize: int = Field(
        10, 
        description="Number of results to return per page. Use with skip to paginate through results.",
        ge=0,
        le=9007199254740991
    )
    skip: int = Field(
        0, 
        description="Number of results to skip. To navigate to the next page, increment skip by pageSize.",
        ge=0,
        le=9007199254740991
    )

@mcp.tool()
def get_orders(args: Optional[GetOrdersArgs] = None) -> Any:
    """Get orders as per JSON args in the input schema. If no args is provided, get all orders."""
    
    # 1. Convert the Pydantic model to a clean dictionary
    # exclude_none=True ensures we don't send "locationIds": null if it wasn't provided
    query_data = args.model_dump(exclude_none=True)
    
    # 2. Serialize that dictionary into a JSON string
    json_string_payload = json.dumps(query_data)
    
    # 3. Pass the JSON string to your service method
    return pw.get_orders(inputSchema=json_string_payload)


# ------------------------------------------------------------------------------
# Commerce Foundation Operation Action Tools
# ------------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Shared / Sub-Models
# -----------------------------------------------------------------------------

class CustomField(BaseModel):
    name: str
    value: str
    model_config = ConfigDict(regex_engine='python-re')
    model_config = ConfigDict(extra='forbid')

class Address(BaseModel):
    model_config = ConfigDict(regex_engine='python-re')
    address1: Optional[str] = Field(None, description='Primary street address (e.g., "123 Main Street")')
    address2: Optional[str] = Field(None, description='Secondary address information such as apartment, suite, or unit number (e.g., "Apt 4B")')
    city: Optional[str] = Field(None, description="City or town name")
    company: Optional[str] = Field(None, description="Company or organization name associated with this address")
    country: Optional[str] = Field(None, description='Country code in ISO 3166-1 alpha-2 format (2 letters, e.g., "US", "CA", "GB")')
    email: Optional[str] = Field(Field(pattern=EMAIL_PATTERN, json_schema_extra={"format": "email"}))
    firstName: Optional[str] = Field(None, description="First name of the person at this address")
    lastName: Optional[str] = Field(None, description="Last name of the person at this address")
    phone: Optional[str] = Field(None, description='Phone number including country code if applicable (e.g., "+1-555-123-4567")')
    stateOrProvince: Optional[str] = Field(None, description='State or province. For US addresses, use 2-letter state code (e.g., "CA", "NY"). For other countries, use full province name or local standard.')
    zipCodeOrPostalCode: Optional[str] = Field(None, description="ZIP code (US) or postal code (international) for the address")

    model_config = ConfigDict(extra='forbid')

class CustomerAddressEntry(BaseModel):
    """Wrapper for addresses inside the Customer object"""
    name: Optional[str] = Field(None, description="Description of the address e.g. home, work, billing, shipping, etc")
    address: Address

    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')

class Customer(BaseModel):
    id: str = Field(..., description="Unique system-generated identifier for this entity (read-only)")
    externalId: Optional[str] = Field(None, description="ID of the entity in the client's system. Must be unique within the tenant.")
    createdAt: str = Field(
        ..., 
        description="ISO 8601 timestamp when the entity was created (read-only)",
        pattern=r"^(?:(?:\\d\\d[2468][048]|\\d\\d[13579][26]|\\d\\d0[48]|[02468][048]00|[13579][26]00)-02-29|\\d{4}-(?:(?:0[13578]|1[02])-(?:0[1-9]|[12]\\d|3[01])|(?:0[469]|11)-(?:0[1-9]|[12]\\d|30)|(?:02)-(?:0[1-9]|1\\d|2[0-8])))T(?:(?:[01]\\d|2[0-3]):[0-5]\\d(?::[0-5]\\d(?:\\.\\d+)?)?(?:Z))$"
    )
    updatedAt: str = Field(
        ..., 
        description="ISO 8601 timestamp when the entity was last updated (read-only)",
        pattern=r"^(?:(?:\\d\\d[2468][048]|\\d\\d[13579][26]|\\d\\d0[48]|[02468][048]00|[13579][26]00)-02-29|\\d{4}-(?:(?:0[13578]|1[02])-(?:0[1-9]|[12]\\d|3[01])|(?:0[469]|11)-(?:0[1-9]|[12]\\d|30)|(?:02)-(?:0[1-9]|1\\d|2[0-8])))T(?:(?:[01]\\d|2[0-3]):[0-5]\\d(?::[0-5]\\d(?:\\.\\d+)?)?(?:Z))$"
    )
    tenantId: str = Field(..., description="Unique identifier for the tenant that owns this entity (read-only)")
    addresses: Optional[List[CustomerAddressEntry]] = Field(None, description="List of addresses associated with the customer (e.g., shipping, billing, home, work)")
    email: Optional[str] = Field(Field(pattern=EMAIL_PATTERN, json_schema_extra={"format": "email"}))
    firstName: Optional[str] = Field(None, description="Customer's first name")
    lastName: Optional[str] = Field(None, description="Customer's last name")
    notes: Optional[str] = Field(None, description="Internal notes about the customer for reference (not visible to the customer)")
    phone: Optional[str] = Field(None, description='Primary phone number including country code if applicable (e.g., "+1-555-123-4567")')
    status: Optional[str] = Field(None, description='Customer account status (e.g., "active", "inactive", "suspended")')
    type: Optional[str] = Field(None, description='Customer type (e.g., "individual" for personal customers or "company" for business customers)')
    customFields: Optional[List[CustomField]] = Field(None, description="Custom Fields - allows for arbitrary key-value pairs to be added to an entity.")
    tags: Optional[List[str]] = Field(None, description='Tags for categorization and filtering.')

    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')

class LineItem(BaseModel):
    id: Optional[str] = Field(None, description="Unique identifier for this line item within the order")
    sku: str = Field(..., min_length=1, description="Product Variant SKU")
    quantity: float = Field(..., minimum=1, description="Quantity ordered")
    unitPrice: Optional[float] = Field(None, minimum=0, description="Price per unit")
    unitDiscount: Optional[float] = Field(None, minimum=0, description="Discount per unit")
    totalPrice: Optional[float] = Field(None, minimum=0, description="Total price for the line item. Calculated as (unitPrice - unitDiscount) * quantity")
    name: Optional[str] = Field(None, description="Product name for display")
    customFields: Optional[List[CustomField]] = Field(None, description="Custom Fields")

    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')

class Order(BaseModel):
    externalId: Optional[str] = Field(None, description="ID of the entity in the client's system. Must be unique within the tenant.")
    name: Optional[str] = Field(None, description="Order name")
    status: Optional[str] = Field(None, description="Order status")
    billingAddress: Optional[Address] = Field(None, description="Billing address")
    currency: Optional[str] = Field(None, description="Order currency code")
    customFields: Optional[List[CustomField]] = Field(None, description="Custom Fields")
    customer: Optional[Customer] = Field(None, description="Order customer information")
    discounts: Optional[List[Dict[str, Any]]] = Field(None, description="Discounts")
    lineItems: List[LineItem]
    orderDiscount: Optional[float] = Field(None, description="Order Discount")
    orderNote: Optional[str] = Field(None, description="Order Notes")
    orderSource: Optional[str] = Field(None, description="The original order platform, walmart, etsy, etc")
    orderTax: Optional[float] = Field(None, description="Order Tax")
    paymentStatus: Optional[str] = Field(None, description="status of the payment")
    payments: Optional[List[Dict[str, Any]]] = Field(None, description="Payments")
    refunds: Optional[List[Dict[str, Any]]] = Field(None, description="Refunds")
    subTotalPrice: Optional[float] = Field(None, description="Sub Total Price")
    tags: Optional[List[str]] = Field(None, description='Tags for categorization and filtering.')
    totalPrice: Optional[float] = Field(None, description="Total Price")
    shippingAddress: Optional[Address] = Field(None, description="Shipping address")
    shippingCarrier: Optional[str] = Field(None, description="Shipping carrier name eg. UPS, FedEx, USPS")
    shippingClass: Optional[str] = Field(None, description="Service level e.g. Next Day, Express, Ground")
    shippingCode: Optional[str] = None
    shippingNote: Optional[str] = Field(None, description="Additional shipping notes")
    shippingPrice: Optional[float] = Field(None, description="Shipping cost")
    giftNote: Optional[str] = None
    incoterms: Optional[str] = None

    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')

# -----------------------------------------------------------------------------
# Commerce Operations Foundation - Create Sales Order
# -----------------------------------------------------------------------------

class CreateSalesOrderArgs(BaseModel):
    """
    Input schema for creating a sales order.
    Matches the schema title 'create-sales-order'.
    """
    order: Order
    
    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')

@mcp.tool()
def create_sales_order(args: CreateSalesOrderArgs) -> Any:
    """Create Sales Order as per JSON args in the input schema https://raw.githubusercontent.com/commerce-operations-foundation/mcp-reference-server/refs/heads/develop/schemas/tool-inputs/create-sales-order.json. If no args is provided, error"""
    # 1. Convert the Pydantic model to a clean dictionary
    # exclude_none=True ensures we don't send "locationIds": null if it wasn't provided
    query_data = args.model_dump(exclude_none=True)
    
    # 2. Serialize that dictionary into a JSON string
    json_string_payload = json.dumps(query_data)
    
    # 3. Pass the JSON string to your service method
    return pw.create_sales_order(inputSchema=json_string_payload)


# -----------------------------------------------------------------------------
# Commerce Operations Foundation - Update Sales Order
# -----------------------------------------------------------------------------


# We assume Address, Customer, and CustomField are imported or available 
# from the previous definition.

class UpdateOrderLineItem(BaseModel):
    """
    Specific LineItem definition for updates.
    Differs from the create schema by requiring 'unitPrice'.
    """
    id: Optional[str] = Field(None, description="Unique identifier for this line item within the order")
    sku: str = Field(..., min_length=1, description="Product Variant SKU")
    quantity: float = Field(..., minimum=1, description="Quantity ordered")
    unitPrice: float = Field(..., minimum=0, description="Price per unit") # Required in this schema
    unitDiscount: Optional[float] = Field(None, minimum=0, description="Discount per unit")
    totalPrice: Optional[float] = Field(None, minimum=0, description="Total price for the line item. Calculated as (unitPrice - unitDiscount) * quantity")
    name: Optional[str] = Field(None, description="Product name for display")
    customFields: Optional[List[CustomField]] = Field(None, description="Custom Fields")

    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')

class OrderUpdates(BaseModel):
    """
    Fields allowed to be updated on an order.
    """
    externalId: Optional[str] = Field(None, description="ID of the entity in the client's system. Must be unique within the tenant.")
    tenantId: Optional[str] = Field(None, description="Unique identifier for the tenant that owns this entity (read-only)")
    name: Optional[str] = Field(None, description="Order name")
    status: Optional[str] = Field(None, description="Order status")
    billingAddress: Optional[Address] = Field(None, description="Billing address")
    currency: Optional[str] = Field(None, description="Order currency code")
    customFields: Optional[List[CustomField]] = Field(None, description="Custom Fields")
    customer: Optional[Customer] = Field(None, description="Order customer information")
    discounts: Optional[List[Dict[str, Any]]] = Field(None, description="Discounts")
    lineItems: Optional[List[UpdateOrderLineItem]] = Field(None, description="List of line items to update")
    orderDiscount: Optional[float] = Field(None, description="Order Discount")
    orderNote: Optional[str] = Field(None, description="Order Notes")
    orderSource: Optional[str] = Field(None, description="The original order platform, walmart, etsy, etc")
    orderTax: Optional[float] = Field(None, description="Order Tax")
    paymentStatus: Optional[str] = Field(None, description="status of the payment")
    payments: Optional[List[Dict[str, Any]]] = Field(None, description="Payments")
    refunds: Optional[List[Dict[str, Any]]] = Field(None, description="Refunds")
    subTotalPrice: Optional[float] = Field(None, description="Sub Total Price")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization and filtering.")
    totalPrice: Optional[float] = Field(None, description="Total Price")
    shippingAddress: Optional[Address] = Field(None, description="Shipping address")
    shippingCarrier: Optional[str] = Field(None, description="Shipping carrier name eg. UPS, FedEx, USPS")
    shippingClass: Optional[str] = Field(None, description="Service level e.g. Next Day, Express, Ground")
    shippingCode: Optional[str] = None
    shippingNote: Optional[str] = Field(None, description="Additional shipping notes")
    shippingPrice: Optional[float] = Field(None, description="Shipping cost")
    giftNote: Optional[str] = None
    incoterms: Optional[str] = None

    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')

class UpdateSalesOrderArgs(BaseModel):
    """
    Input schema for updating an order.
    Matches the schema title 'update-order'.
    """
    id: str = Field(..., description="Order ID")
    updates: OrderUpdates = Field(..., description="Fields to update")
    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')

@mcp.tool()
def update_order(args: UpdateSalesOrderArgs) -> Any:
    """update Sales Order as per JSON args in the input schema https://raw.githubusercontent.com/commerce-operations-foundation/mcp-reference-server/refs/heads/develop/schemas/tool-inputs/update-order.json. If no args is provided, error"""
    # 1. Convert the Pydantic model to a clean dictionary
    # exclude_none=True ensures we don't send "locationIds": null if it wasn't provided
    query_data = args.model_dump(exclude_none=True)
    
    # 2. Serialize that dictionary into a JSON string
    json_string_payload = json.dumps(query_data)
    
    # 3. Pass the JSON string to your service method
    return pw.update_order(inputSchema=json_string_payload)


# -----------------------------------------------------------------------------
# Commerce Operations Foundation - Cancel Sales Order
# -----------------------------------------------------------------------------

class CancelOrderLineItem(BaseModel):
    """
    Specific line item definition for cancellation requests.
    Includes only the fields necessary to identify the item and quantity to cancel.
    """
    sku: str = Field(..., min_length=1, description="Product Variant SKU")
    quantity: float = Field(..., minimum=1, description="Quantity ordered")
    id: Optional[str] = Field(None, description="Unique identifier for this line item within the order")

    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')

class CancelSalesOrderArgs(BaseModel):
    """
    Input schema for canceling an order.
    Matches the schema title 'cancel-order'.
    """
    orderId: str = Field(..., description="id of the order to cancel")
    reason: Optional[str] = Field(None, description="Reason for cancellation")
    notifyCustomer: Optional[bool] = Field(None, description="Whether to send cancellation notification to customer")
    notes: Optional[str] = Field(None, description="Additional cancellation notes")
    lineItems: Optional[List[CancelOrderLineItem]] = Field(None, description="Specific line items to cancel (omit to cancel entire order)")

    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')
    
@mcp.tool()
def cancel_order(args: CancelSalesOrderArgs) -> Any:
    """Create Sales Order as per JSON args in the input schema https://raw.githubusercontent.com/commerce-operations-foundation/mcp-reference-server/refs/heads/develop/schemas/tool-inputs/cancel-order.json. If no args is provided, error"""
    # 1. Convert the Pydantic model to a clean dictionary
    # exclude_none=True ensures we don't send "locationIds": null if it wasn't provided
    query_data = args.model_dump(exclude_none=True)
    
    # 2. Serialize that dictionary into a JSON string
    json_string_payload = json.dumps(query_data)
    
    # 3. Pass the JSON string to your service method
    return pw.cancel_order(inputSchema=json_string_payload)

# -----------------------------------------------------------------------------
# Commerce Operations Foundation - Fulfill Sales Order
# -----------------------------------------------------------------------------
class FulfillmentLineItem(BaseModel):
    """
    Specific line item definition for fulfillment.
    Matches the schema within 'fulfill-order'.
    """
    id: Optional[str] = Field(None, description="Unique identifier for this line item within the order")
    sku: str = Field(..., min_length=1, description="Product Variant SKU")
    quantity: float = Field(..., minimum=1, description="Quantity ordered")
    unitPrice: Optional[float] = Field(None, minimum=0, description="Price per unit")
    unitDiscount: Optional[float] = Field(None, minimum=0, description="Discount per unit")
    totalPrice: Optional[float] = Field(None, minimum=0, description="Total price for the line item. Calculated as (unitPrice - unitDiscount) * quantity")
    name: Optional[str] = Field(None, description="Product name for display")
    customFields: Optional[List[CustomField]] = Field(None, description="Custom Fields")

    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')

class FulfillOrderArgs(BaseModel):
    """
    Input schema for fulfilling an order.
    Matches the schema title 'fulfill-order'.
    """
    customFields: Optional[List[CustomField]] = Field(None, description="Custom Fields")
    expectedDeliveryDate: Optional[str] = Field(None, description="Expected delivery date", pattern=DATE_PATTERN)
    expectedShipDate: Optional[str] = Field(None, description="Expected date the order will be shipped", pattern=DATE_PATTERN)
    lineItems: List[FulfillmentLineItem] = Field(..., description="Items included in this fulfillment")
    locationId: Optional[str] = None
    orderId: str = Field(..., description="Order ID")
    shipByDate: Optional[str] = Field(None, pattern=DATE_PATTERN)
    status: Optional[str] = None
    tags: Optional[List[str]] = Field(None, description="Tags for categorization and filtering.")
    trackingNumbers: List[str] = Field(..., description="Tracking numbers from carrier")
    shippingAddress: Optional[Address] = Field(None, description="Shipping address")
    shippingCarrier: Optional[str] = Field(None, description="Shipping carrier name eg. UPS, FedEx, USPS")
    shippingClass: Optional[str] = Field(None, description="Service level e.g. Next Day, Express, Ground")
    shippingCode: Optional[str] = None
    shippingNote: Optional[str] = Field(None, description="Additional shipping notes")
    shippingPrice: Optional[float] = Field(None, description="Shipping cost")
    giftNote: Optional[str] = None
    incoterms: Optional[str] = None

    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')
    
@mcp.tool()
def fulfill_order(args: FulfillOrderArgs) -> Any:
    """Create Sales Order as per JSON args in the input schema https://raw.githubusercontent.com/commerce-operations-foundation/mcp-reference-server/refs/heads/develop/schemas/tool-inputs/cancel-order.json. If no args is provided, error"""
    # 1. Convert the Pydantic model to a clean dictionary
    # exclude_none=True ensures we don't send "locationIds": null if it wasn't provided
    query_data = args.model_dump(exclude_none=True)
    
    # 2. Serialize that dictionary into a JSON string
    json_string_payload = json.dumps(query_data)
    
    # 3. Pass the JSON string to your service method
    return pw.fulfill_order(inputSchema=json_string_payload)

# -----------------------------------------------------------------------------
# Commerce Operations Foundation - Create Return
# -----------------------------------------------------------------------------
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

# We assume Address, CustomField, and DATE_PATTERN are available from previous definitions.

class Inspection(BaseModel):
    """
    Item condition grade and disposition details.
    """
    conditionCategory: Optional[str] = Field(None, description="Item condition grade after inspection")
    dispositionOutcome: Optional[str] = Field(None, description="Disposition decision for the returned item")
    warehouseLocationId: Optional[str] = Field(None, description="Warehouse bin/shelf location identifier for restocking")
    note: Optional[str] = Field(None, description="Inspection notes about item condition and disposition")
    inspectedBy: Optional[str] = Field(None, description="Who inspected the item")
    inspectedAt: Optional[str] = Field(None, description="When item was inspected", pattern=DATE_PATTERN)
    images: Optional[List[str]] = Field(None, description="Photos of returned item condition")

    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')

class ReturnLineItem(BaseModel):
    """
    Items being returned.
    """
    id: Optional[str] = Field(None, description="Unique identifier for this return line item")
    orderLineItemId: str = Field(..., description="Reference to the original order line item")
    sku: str = Field(..., description="Product Variant SKU")
    quantityReturned: float = Field(..., minimum=1, description="Quantity being returned")
    returnReason: str = Field(..., description='Primary return reason code (e.g., "defective", "wrong_item", "no_longer_needed", "size_issue", "quality_issue")')
    inspection: Optional[Inspection] = None
    unitPrice: Optional[float] = Field(None, description="Original unit price from order")
    refundAmount: Optional[float] = Field(None, minimum=0, description="Refund amount for this line item")
    restockFee: Optional[float] = Field(None, minimum=0, description="Restocking fee charged for this line item")
    name: Optional[str] = Field(None, description="Product name for display")

    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')

class ExchangeLineItem(BaseModel):
    """
    Items being exchanged.
    """
    id: Optional[str] = Field(None, description="Unique exchange line item identifier")
    exchangeOrderId: Optional[str] = Field(None, description="Order ID created for this exchange")
    exchangeOrderName: Optional[str] = Field(None, description="Order number/name for exchange order")
    sku: str = Field(..., description="Product Variant SKU")
    name: Optional[str] = Field(None, description="Product name")
    quantity: float = Field(..., minimum=1, description="Quantity requested")
    unitPrice: Optional[float] = Field(None, description="Unit price")

    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')

class ReturnMethod(BaseModel):
    """
    Method customer uses to return items.
    """
    provider: Optional[str] = Field(None, description="Return logistics provider")
    methodType: Optional[str] = Field(None, description="Method customer uses to return items")
    address: Optional[Address] = Field(None, description="Address where customer returns items")
    qrCodeUrl: Optional[str] = Field(None, description="QR code URL for label-free return methods")
    updatedAt: Optional[str] = Field(None, pattern=DATE_PATTERN)

    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')

class ReturnLabel(BaseModel):
    """
    Shipping labels for this return.
    """
    status: Optional[str] = Field(None, description="Label lifecycle status")
    carrier: str = Field(..., description="Shipping carrier providing the label")
    trackingNumber: str = Field(..., description="Tracking number for the return shipment")
    url: Optional[str] = Field(None, description="URL to download the shipping label")
    rate: Optional[float] = Field(None, description="Shipping cost for this label")
    createdAt: Optional[str] = Field(None, pattern=DATE_PATTERN)
    updatedAt: Optional[str] = Field(None, pattern=DATE_PATTERN)

    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')

class CreateReturnArgs(BaseModel):
    """
    Input schema for creating a Return.
    Matches the schema title 'Return'.
    """
    id: str = Field(..., description="Unique system-generated identifier for this entity (read-only)")
    externalId: Optional[str] = Field(None, description="ID of the entity in the client's system. Must be unique within the tenant.")
    createdAt: str = Field(..., description="ISO 8601 timestamp when the entity was created (read-only)", pattern=DATE_PATTERN)
    updatedAt: str = Field(..., description="ISO 8601 timestamp when the entity was last updated (read-only)", pattern=DATE_PATTERN)
    tenantId: str = Field(..., description="Unique identifier for the tenant that owns this entity (read-only)")
    returnNumber: Optional[str] = Field(None, description='Customer-facing return identifier used for tracking and reference (e.g., "RET-12345")')
    orderId: str = Field(..., description="ID of the original order being returned")
    status: Optional[str] = Field(None, description="Return processing status in the return lifecycle")
    outcome: str = Field(..., description="What the customer receives for their return")
    returnLineItems: List[ReturnLineItem] = Field(..., description="Items being returned")
    exchangeLineItems: Optional[List[ExchangeLineItem]] = Field(None, description="Items being exchanged")
    totalQuantity: Optional[float] = Field(None, description="Total quantity of items being returned (excludes exchange items)")
    returnMethod: Optional[ReturnMethod] = None
    returnShippingAddress: Optional[Address] = Field(None, description="Address where items should be returned to")
    labels: Optional[List[ReturnLabel]] = Field(None, description="Shipping labels for this return")
    locationId: Optional[str] = Field(None, description="Warehouse facility identifier where return will be received")
    returnTotal: Optional[float] = Field(None, description="Gross merchandise value of returned items before fees")
    exchangeTotal: Optional[float] = Field(None, description="Gross merchandise value of exchange items before any credits applied")
    refundAmount: Optional[float] = Field(None, description="Final refund amount to customer after fees and restocking charges")
    refundMethod: Optional[str] = Field(None, description="Payment method for issuing the refund")
    refundStatus: Optional[str] = Field(None, description="Payment refund processing status (separate from return status)")
    refundTransactionId: Optional[str] = Field(None, description="Transaction ID for the refund")
    shippingRefundAmount: Optional[float] = Field(None, description="Amount of original shipping cost being refunded")
    returnShippingFees: Optional[float] = Field(None, description="Return shipping cost charged to customer (if applicable)")
    restockingFee: Optional[float] = Field(None, description="Total restocking fees charged to customer across all items")
    requestedAt: Optional[str] = Field(None, description="When return was requested", pattern=DATE_PATTERN)
    receivedAt: Optional[str] = Field(None, description="When returned items were received", pattern=DATE_PATTERN)
    completedAt: Optional[str] = Field(None, description="When return was fully processed", pattern=DATE_PATTERN)
    customerNote: Optional[str] = Field(None, description="Customer notes about the return")
    internalNote: Optional[str] = Field(None, description="Internal notes for staff")
    returnInstructions: Optional[str] = Field(None, description="Instructions provided to customer")
    declineReason: Optional[str] = Field(None, description="Reason if return was declined")
    statusPageUrl: Optional[str] = Field(None, description="Customer-facing status tracking page")
    tags: Optional[List[str]] = Field(None, description='Tags for categorization and filtering.')
    customFields: Optional[List[CustomField]] = Field(None, description="Custom Fields")

    model_config = ConfigDict(extra='forbid')
    model_config = ConfigDict(regex_engine='python-re')


@mcp.tool()
def create_return(args: CreateReturnArgs) -> Any:
    """Create Sales Order as per JSON args in the input schema https://raw.githubusercontent.com/commerce-operations-foundation/mcp-reference-server/refs/heads/develop/schemas/tool-inputs/cancel-order.json. If no args is provided, error"""
    # 1. Convert the Pydantic model to a clean dictionary
    # exclude_none=True ensures we don't send "locationIds": null if it wasn't provided
    query_data = args.model_dump(exclude_none=True)
    
    # 2. Serialize that dictionary into a JSON string
    json_string_payload = json.dumps(query_data)
    
    # 3. Pass the JSON string to your service method
    return pw.create_return(inputSchema=json_string_payload)

if __name__ == "__main__":
    mcp.run(transport="stdio")
