from __future__ import annotations
import os, json, sys, logging, base64
from typing import Any, List, Optional, Dict
from typing_extensions import Annotated
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP
import re
import asyncio

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

import uvicorn
import socket
import multiprocessing
from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount

import patchworks_client as pw
from docs_search import get_index as _get_docs_index
from datetime import datetime

# Log to STDERR only (stdio transport cannot receive stdout noise)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger("patchworks-mcp")

mcp = FastMCP("patchworks")


# Regex patterns derived from your JSON Schema
DATE_PATTERN = r"^(?:(?:(?:(?:(?:[13579][26]|[2468][048])00)|(?:[0-9]{2}(?:(?:[13579][26])|(?:[2468][048]|0[48]))))(?:-)(?:02)(?:-)(?:29))|(?:(?:[0-9]{4})(?:-)(?:(?:(?:0[13578]|1[02])(?:-)(?:31))|(?:(?:0[1,3-9]|1[0-2])(?:-)(?:29|30))|(?:(?:0[1-9])|(?:1[0-2]))(?:-)(?:0[1-9]|1[0-9]|2[0-8]))))(?:T)(?:[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?)(?:Z)$"
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
    flow_id: Optional[int] = Field(None, description="Filter runs by flow ID")
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

class InvestigateFailureArgs(BaseModel):
    flow_id: Optional[int] = Field(None, description="Numeric flow ID (if known)")
    flow_name: Optional[str] = Field(None, description="Flow name to search for (case-insensitive)")
    run_id: Optional[str] = Field(None, description="Specific flow run ID to investigate")
    include_payload: bool = Field(False, description="Include full payload content in the response. Alert chain following always happens regardless.")
    failed_at: Optional[str] = Field(None, description="Timestamp of the failure from the alert message (e.g. '2026-02-24 13:34:04'). When provided, matches the run closest to this timestamp instead of using the most recent run.")

class GetRunPayloadsArgs(BaseModel):
    run_id: str = Field(..., description="Flow run ID to fetch payloads for")
    step_name: Optional[str] = Field(None, description="Filter payloads by step name (e.g. 'Catch', 'Source Connector')")


ENTITY_GUESSES = [
    "orders","order","customers","customer","products","inventory","shipments","invoices","payments"
]

def _guess_parts_from_prompt(prompt: str) -> Dict[str, str]:
    p = prompt.strip().lower()
    m = re.search(r"for\s+(.+?)\s+to\s+(.+?)\s+([a-zA-Z\-_/ ]+)$", p) or \
        re.search(r"(?:create|build).*\bflow\b.*?for\s+(.+?)\s+to\s+(.+?)\s+([a-zA-Z\-_/ ]+)$", p)
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
            },
            "connector": {
                "name": f"{src} Connector",
                "timezone": "Europe/London"
            },
            "endpoints": [
                {
                    "name": f"{src} - Retrieve {entity}",
                    "endpoint": "https://placeholder.example.com/api",
                    "http_method": "GET",
                    "data_type": "json",
                    "direction": "Receive"
                }
            ]
        },
        {
            "system": {
                "name": dst,
                "label": f"{dst} (placeholder)",
                "protocol": "HTTP"
            },
            "connector": {
                "name": f"{dst} Connector",
                "timezone": "Europe/London"
            },
            "endpoints": [
                {
                    "name": f"{dst} - Upsert {entity}",
                    "endpoint": "https://placeholder.example.com/api",
                    "http_method": "POST",
                    "data_type": "json",
                    "direction": "Send"
                }
            ]
        }
    ]

    return {
        "flow": flow,
        "systems": systems
    }


# --- Tool Registration (MCP) ---
# These are only used when running as an MCP server, not via /chat

@mcp.tool()
def get_all_flows(args: GetAllFlowsArgs) -> Dict[str, Any]:
    """Retrieve all flows (integrations) visible to this user."""
    return pw.get_all_flows(**args.model_dump())

@mcp.tool()
def get_flow_runs(args: GetFlowRunsArgs) -> Dict[str, Any]:
    """Get flow runs with optional filtering by status, date range, etc."""
    return pw.get_flow_runs(**args.model_dump())

@mcp.tool()
def get_flow_run_logs(args: GetFlowRunLogsArgs) -> Dict[str, Any]:
    """Fetch logs for a specific flow run to debug failures or see details."""
    return pw.get_flow_run_logs(**args.model_dump())

@mcp.tool()
def summarise_failed_run(args: SummariseFailedRunArgs) -> Dict[str, Any]:
    """Analyse a failed run and produce a concise summary of what went wrong."""
    return pw.summarise_failed_run(**args.model_dump())

@mcp.tool()
def triage_latest_failures(args: TriageLatestFailuresArgs) -> Dict[str, Any]:
    """
    Triage multiple recent failures at once. Returns a summarised breakdown
    of what failed, when, and why. Good for quickly assessing platform health.
    """
    return pw.triage_latest_failures(**args.model_dump())

@mcp.tool()
def download_payload(args: DownloadPayloadArgs) -> Dict[str, str]:
    """
    Download a payload from a flow run. Returns content_type and base64-encoded bytes.
    """
    ctype, raw = pw.download_payload(args.payload_metadata_id)
    return {
        "content_type": ctype,
        "bytes_base64": base64.b64encode(raw).decode("ascii")
    }

@mcp.tool()
def start_flow(args: StartFlowArgs) -> Dict[str, Any]:
    """Manually trigger a flow run. Optionally pass a JSON payload to inject data."""
    return pw.start_flow(**args.model_dump())

@mcp.tool()
def list_data_pools(args: ListDataPoolsArgs) -> Dict[str, Any]:
    """List all data pools (deduplicated data storage) in the platform."""
    return pw.list_data_pools(**args.model_dump())

@mcp.tool()
def get_deduped_data(args: GetDedupedDataArgs) -> Dict[str, Any]:
    """Retrieve deduped records from a specific pool."""
    return pw.get_deduped_data(**args.model_dump())

@mcp.tool()
def create_process_flow_from_prompt(args: CreateProcessFlowByPromptArgs) -> Dict[str, Any]:
    """
    Create a new flow from a natural language prompt. e.g.:
    "create a process flow for Shopify to NetSuite orders"
    """
    parts = _guess_parts_from_prompt(args.prompt)
    body = _build_generic_import_json(
        parts["source"], parts["destination"], parts["entity"],
        priority=args.priority,
        schedule_cron=args.schedule_cron,
        enable=args.enable,
    )
    return pw.import_flow(body)

@mcp.tool()
def create_process_flow_from_json(args: CreateProcessFlowFromJsonArgs) -> Dict[str, Any]:
    """
    Import a flow from a full JSON structure (as exported from /flows/export).
    Allows advanced users to craft custom flow definitions.
    """
    return pw.import_flow(args.body)

@mcp.tool()
def investigate_failure(args: InvestigateFailureArgs) -> Dict[str, Any]:
    """
    All-in-one failure investigation. Provide a flow name, flow ID, or run ID.
    Resolves the flow, finds the most recent failed run, summarises it, downloads
    payloads (including catch-route payloads), and follows the alert chain to the
    originating failed run if this is an alert/notification flow.
    Returns a complete diagnostic in a single tool call.
    """
    return pw.investigate_failure(**args.model_dump())

@mcp.tool()
def get_run_payloads(args: GetRunPayloadsArgs) -> Dict[str, Any]:
    """
    Retrieve all payloads for a flow run in a single call.
    Optionally filter by step name (e.g. 'Catch', 'Source Connector').
    Downloads and decodes each payload, returning the content inline.
    """
    return pw.get_run_payloads(**args.model_dump())


# ------------------------------------------------------------------------------
# Documentation Knowledge Base
# ------------------------------------------------------------------------------

@mcp.tool()
def search_docs(query: str, max_results: int = 3) -> Any:
    """Search the Patchworks product documentation knowledge base.

    Use this to answer questions about Patchworks concepts, features, and configuration
    that are not specific to a particular account's data. Covers: getting started,
    registration, subscription tiers, company setup, users & roles, marketplace,
    blueprints, connectors & instances, process flows, virtual environments,
    general settings, connector builder, custom scripting, the Patchworks API,
    the Patchworks MCP server, and Stockr.
    """
    idx = _get_docs_index()
    results = idx.search(query, max_results=max_results)
    if not results:
        return {"results": [], "message": "No matching documentation found. Try different keywords."}
    return {"results": results}


# Commerce Foundation Tools
@mcp.tool()
def get_customers(inputSchema: Optional[str] = None) -> Dict[str, Any]:
    """Query customers using the Commerce Foundation."""
    return pw.get_customers(inputSchema=inputSchema)

@mcp.tool()
def get_products(inputSchema: Optional[str] = None) -> Dict[str, Any]:
    """Query products using the Commerce Foundation."""
    return pw.get_products(inputSchema=inputSchema)

@mcp.tool()
def get_product_variants(inputSchema: Optional[str] = None) -> Dict[str, Any]:
    """Query product variants (SKUs) using the Commerce Foundation."""
    return pw.get_product_variants(inputSchema=inputSchema)

@mcp.tool()
def get_inventory(inputSchema: Optional[str] = None) -> Dict[str, Any]:
    """Query inventory levels using the Commerce Foundation."""
    return pw.get_inventory(inputSchema=inputSchema)

@mcp.tool()
def get_returns(inputSchema: Optional[str] = None) -> Dict[str, Any]:
    """Query returns/refunds using the Commerce Foundation."""
    return pw.get_returns(inputSchema=inputSchema)

@mcp.tool()
def get_fulfillments(inputSchema: Optional[str] = None) -> Dict[str, Any]:
    """Query fulfillments/shipments using the Commerce Foundation."""
    return pw.get_fulfillments(inputSchema=inputSchema)

@mcp.tool()
def get_orders(inputSchema: Optional[str] = None) -> Dict[str, Any]:
    """Query orders using the Commerce Foundation."""
    return pw.get_orders(inputSchema=inputSchema)

@mcp.tool()
def create_sales_order(inputSchema: Optional[str] = None) -> Dict[str, Any]:
    """Create a new sales order via the Commerce Foundation."""
    return pw.create_sales_order(inputSchema=inputSchema)

@mcp.tool()
def update_order(inputSchema: Optional[str] = None) -> Dict[str, Any]:
    """Update an existing order via the Commerce Foundation."""
    return pw.update_order(inputSchema=inputSchema)

@mcp.tool()
def cancel_order(inputSchema: Optional[str] = None) -> Dict[str, Any]:
    """Cancel an order via the Commerce Foundation."""
    return pw.cancel_order(inputSchema=inputSchema)

@mcp.tool()
def fulfill_order(inputSchema: Optional[str] = None) -> Dict[str, Any]:
    """Mark an order as fulfilled via the Commerce Foundation."""
    return pw.fulfill_order(inputSchema=inputSchema)

@mcp.tool()
def create_return(inputSchema: Optional[str] = None) -> Dict[str, Any]:
    """Create a return/refund via the Commerce Foundation."""
    return pw.create_return(inputSchema=inputSchema)


# ------------------------------------------------------------------------------
# /chat endpoint — Claude API with agentic tool use
# ------------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a Patchworks integration platform assistant.
You help users monitor and manage their integration flows, investigate failures,
check order/product/inventory data, and perform operations.

**Formatting rules:**
- Use standard Markdown for all responses (headings, **bold**, `code`, ```code blocks```, lists).
- NEVER use Markdown tables. Instead, group data under bold headings with bullet points.
  For example, instead of a table comparing tiers, format as:
  **Trial**
  - Deployed Connectors - 2
  - Active Process Flows - 2

  **Standard**
  - Deployed Connectors - 2
  - Active Process Flows - 10
- Keep responses concise and actionable.
- When listing items, limit to 10 unless asked for more.

**Documentation knowledge base:**
- You have access to a `search_docs` tool that searches the Patchworks product documentation.
- Use `search_docs` FIRST when the user asks about Patchworks concepts, features, setup,
  configuration, pricing tiers, terminology, or how-to questions about the platform.
- Topics covered include: getting started, registration, subscription tiers, quickstart guide,
  company setup, users & roles & permissions, marketplace, blueprints, connectors & instances,
  process flows, virtual environments, general settings, connector builder, custom scripting,
  the Patchworks API, the Patchworks MCP server, and Stockr.
- Do NOT guess at Patchworks-specific answers — always check the docs first.
- Combine documentation results with your general knowledge to give thorough, accurate answers.

**Tool usage optimization:**
- Try to answer questions with a single tool call when possible.
- Call multiple tools in parallel when they are independent. For example, when investigating
  a failure you can call `get_all_flows` and `triage_latest_failures` in the same turn.
- Summarize tool results naturally — don't dump raw JSON.
- When investigating issues, proactively check logs and suggest next steps.
- If a tool returns an error, explain what likely went wrong in plain language.

**Failure investigation — use `investigate_failure` first:**
- When a user asks "why did X fail?", "what went wrong with X?", or similar, call
  `investigate_failure` with the flow name or ID. This single tool call will:
  1. Resolve the flow name to an ID.
  2. Find the run matching the failure timestamp (or the most recent if no timestamp).
  3. Summarise the logs, errors, and highlights.
  4. Return a `run_log_url` dashboard link for the flow run.
- **CRITICAL — Always extract the `failed_at` timestamp:** The conversation history often
  contains a Slack alert with a "Failed At" timestamp (e.g. "2026-02-24 13:34:04"). You
  MUST extract this timestamp and pass it as the `failed_at` parameter to
  `investigate_failure`. This ensures you investigate the EXACT run the alert refers to,
  not just the most recent one (which may be a different run entirely).
- By default, `include_payload` is false to keep response times fast. Only set it to true
  when the user specifically asks about payload content or you need to follow the alert chain.
- If you need payload content separately, call `get_run_payloads` as a follow-up.
- Only fall back to individual tools (`get_flow_runs`, `get_flow_run_logs`, etc.) if
  `investigate_failure` does not return enough detail or the user asks for something specific.
- **ALWAYS** include a dashboard link in your response so the user can view the full logs.
  Format it as a clickable Markdown link.
- When the result contains `originating_run_log_url`, use THAT link (not `run_log_url`) because
  the originating run is where the real failure happened. The `run_log_url` in this case is
  just the alert flow's run, which is less useful.
- When there is NO originating run, use `run_log_url`.

**Alert / notification flow pattern:**
- Flows with Try/Catch often handle errors internally: the connector call fails, the Catch
  branch runs a script and sends a Slack alert, and the overall run finishes as SUCCESS (2)
  or PARTIAL_SUCCESS (5) — NOT FAILURE (3).
- This means the run with the real error logs can have ANY status.  When a `failed_at`
  timestamp is provided, `investigate_failure` searches all statuses (3, 5, 2, 1) and
  timestamp-matches to find the exact run.
- Some flows are separate alert flows triggered by another flow's catch route.  In that case
  `investigate_failure` follows the alert chain automatically via catch-route payloads.
- When the result contains `originating_run_summary` and `originating_run_log_url`, base
  your answer on the ORIGINATING run's errors, not the alert flow's logs.
- Always prefer `originating_run_log_url` over `run_log_url` in your response when both
  are present.  When there is no originating run, use `run_log_url`.

**Payload retrieval:**
- When a user asks "what payload did we send?", "show me the payload", or similar, use
  `get_run_payloads` with the run ID. This fetches all payloads in one call.
- You can filter by step name, e.g. step_name="Catch" for the catch-route payload.
- When `summarise_failed_run` or `investigate_failure` results include `available_payloads`,
  those are payload metadata IDs you can retrieve with `download_payload` or `get_run_payloads`.
- For alert flows, the catch-route payload typically contains the error details and a reference
  to the original failed run.

**Suggesting fixes for failures — NEVER fabricate payloads:**
- When a connector call fails (e.g. HTTP 422, 400, 500), do NOT fabricate example payloads,
  do NOT guess what the correct request body should be, and do NOT invent "corrected" payload
  examples. You WILL get fields wrong and mislead the user. This is a hard rule — no exceptions.
- Instead: clearly explain WHAT failed and WHY (based on the error message and logs), then
  tell the user which external system's documentation they should consult (e.g. "Check the
  Odoo docs for the sale.order `create` method to see the required `vals_list` format").
- You CAN show the payload that was actually sent (from the flow run logs) so the user can
  compare it against the API documentation themselves.
- If the error is clearly a Patchworks configuration issue (e.g. missing mapping, wrong
  endpoint), use `search_docs` to find relevant Patchworks documentation and link to that.

**CRITICAL — Links in responses:**
- The ONLY links you may include in responses are:
  1. `run_log_url` or `originating_run_log_url` values returned by tools (these are verified).
  2. Links returned by `search_docs` from the Patchworks knowledge base (these have real URLs).
- NEVER fabricate or guess URLs for external documentation (Odoo, Shopify, Slack, etc.).
  These URLs are frequently wrong and lead to 404 pages. Instead, tell the user what to
  search for by name (e.g. "search the Odoo docs for sale.order create vals_list").

**Retrying / starting flows with a payload:**
- When the user asks to "retry with this payload" or "start the flow with X data", use
  `start_flow` with the `payload` parameter set to the data the user provided.
- The payload is automatically JSON-stringified before being sent to the Start API, so
  you should pass the raw data object — do NOT stringify or wrap it yourself.
- IMPORTANT: If the previous investigation found an ORIGINATING flow (alert chain), retry
  the ORIGINATING flow, not the alert flow. The `investigate_failure` result will include
  `originating_flow_id` — use THAT as the `flow_id` in `start_flow`. Never use the alert
  flow's ID for retrying.
- The alert flow just sends notifications — the originating flow is the one that does the
  actual work and needs retrying.
- After starting a flow, tell the user the flow was triggered and include both the
  originating flow name/ID and the `originating_run_log_url` so they can monitor it.

**Timestamps and run identification:**
- Always include the `run_started_at` timestamp in your response when discussing a specific
  flow run, so the user can verify which run you're referring to.
- Format timestamps in a human-readable way (e.g. "started at 2026-02-24 14:32:01 UTC").
- This is especially important when the user asks follow-up questions — it prevents confusion
  about which run is being discussed."""

# Load tool definitions from file (Anthropic format — canonical source).
# Other providers convert from this format at runtime via providers/tool_converter.py.
_tools_path = Path(__file__).parent / "anthropic_tools.json"
with open(_tools_path) as _f:
    ANTHROPIC_TOOLS = json.load(_f)
log.info(f"Loaded {len(ANTHROPIC_TOOLS)} tool definitions from {_tools_path}")

# Max agentic iterations — raised from 5 to 10 to support complex
# multi-step investigations (e.g. alert chain follow-through).
MAX_TOOL_ITERATIONS = 10

# Hard cap on the size of a single tool result string (in characters).
# Keeps conversation history from ballooning and hitting token limits on
# follow-up turns.  ~20k chars ≈ ~5k tokens, leaving plenty of headroom.
MAX_TOOL_RESULT_CHARS = 20_000


def _execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool by name using local Python functions. Returns JSON string."""

    # The Anthropic tool schemas wrap args under an "args" key for PW core tools
    args = tool_input.get("args", tool_input)

    try:
        # --- Patchworks Core tools ---
        if tool_name == "get_all_flows":
            result = pw.get_all_flows(**args)
        elif tool_name == "get_flow_runs":
            result = pw.get_flow_runs(**args)
        elif tool_name == "get_flow_run_logs":
            result = pw.get_flow_run_logs(**args)
        elif tool_name == "summarise_failed_run":
            result = pw.summarise_failed_run(**args)
        elif tool_name == "triage_latest_failures":
            result = pw.triage_latest_failures(**args)
        elif tool_name == "download_payload":
            ctype, raw = pw.download_payload(args["payload_metadata_id"])
            result = {"content_type": ctype, "bytes_base64": base64.b64encode(raw).decode("ascii")}
        elif tool_name == "start_flow":
            result = pw.start_flow(**args)
        elif tool_name == "list_data_pools":
            result = pw.list_data_pools(**args)
        elif tool_name == "get_deduped_data":
            result = pw.get_deduped_data(**args)
        elif tool_name == "create_process_flow_from_prompt":
            parts = _guess_parts_from_prompt(args["prompt"])
            body = _build_generic_import_json(
                parts["source"], parts["destination"], parts["entity"],
                priority=args.get("priority", 3),
                schedule_cron=args.get("schedule_cron", "0 * * * *"),
                enable=args.get("enable", False),
            )
            result = pw.import_flow(body)
        elif tool_name == "create_process_flow_from_json":
            result = pw.import_flow(args.get("body", {}))
        elif tool_name == "investigate_failure":
            result = pw.investigate_failure(
                flow_id=args.get("flow_id"),
                flow_name=args.get("flow_name"),
                run_id=args.get("run_id"),
                include_payload=args.get("include_payload", False),
                failed_at=args.get("failed_at"),
            )
        elif tool_name == "get_run_payloads":
            result = pw.get_run_payloads(
                run_id=args["run_id"],
                step_name=args.get("step_name"),
            )

        # --- Documentation search ---
        elif tool_name == "search_docs":
            idx = _get_docs_index()
            q = args.get("query", "")
            mr = args.get("max_results", 3)
            hits = idx.search(q, max_results=mr)
            result = {"results": hits} if hits else {"results": [], "message": "No matching documentation found. Try different keywords."}

        # --- Commerce Foundation tools (pass through as JSON) ---
        elif tool_name in (
            "get_customers", "get_products", "get_product_variants",
            "get_inventory", "get_returns", "get_fulfillments", "get_orders",
            "create_sales_order", "update_order", "cancel_order",
            "fulfill_order", "create_return",
        ):
            cf_fn = getattr(pw, tool_name)
            cf_payload = json.dumps(args) if args else None
            result = cf_fn(inputSchema=cf_payload)

        else:
            result = {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        log.error(f"Tool execution error for {tool_name}: {e}")
        result = {"error": str(e)}

    result_str = json.dumps(result, default=str)

    # Truncate oversized tool results to stay within token budget
    if len(result_str) > MAX_TOOL_RESULT_CHARS:
        log.warning(f"Tool result for {tool_name} truncated from {len(result_str)} to {MAX_TOOL_RESULT_CHARS} chars")
        result_str = result_str[:MAX_TOOL_RESULT_CHARS] + '... [TRUNCATED — result too large. Use more specific queries or ask the user to narrow scope.]'

    return result_str


from providers import get_provider

async def _run_chat(message: str, conversation_history: list[dict] | None = None, provider_name: str | None = None) -> str:
    """Full agentic loop: sends message to LLM provider, executes any tool calls, returns final response."""
    provider = get_provider(provider_name)

    messages = list(conversation_history or [])
    messages.append({"role": "user", "content": message})

    return await provider.run_chat(
        messages=messages,
        system_prompt=SYSTEM_PROMPT,
        tools=ANTHROPIC_TOOLS,
        tool_executor=_execute_tool,
        max_iterations=MAX_TOOL_ITERATIONS,
    )


async def chat_endpoint(request: Request) -> JSONResponse:
    """POST /chat — accepts message + conversation history, returns final response.

    Optional ``provider`` field in the JSON body selects the LLM backend:
    "anthropic" (default), "openai", or "gemini".
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    message = body.get("message", "").strip()
    if not message:
        return JSONResponse({"error": "No message provided"}, status_code=400)

    conversation_history = body.get("conversation_history", [])
    provider_name = body.get("provider")  # None → falls back to env / default

    try:
        response_text = await _run_chat(message, conversation_history, provider_name)
        return JSONResponse({"response": response_text})
    except Exception as e:
        log.error(f"Chat endpoint error: {e}", exc_info=True)
        return JSONResponse(
            {"error": f"Failed to process message: {str(e)}"},
            status_code=500,
        )


# ------------------------------------------------------------------------------
# Server Startup - Dual Mode (stdio for Claude Desktop, HTTP for ngrok/flows)
# ------------------------------------------------------------------------------
# IMPORTANT: is_port_available, HostRewriteMiddleware, and run_server are defined
# at module level (not inside __main__) so that macOS multiprocessing (spawn mode)
# can pickle and locate them in child processes.
# ------------------------------------------------------------------------------

def is_port_available(port: int) -> bool:
    """Check if a port is available for binding."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return True
        except OSError:
            return False


class HostRewriteMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope["headers"])
            scope["headers"] = list(headers.items())
        await self.app(scope, receive, send)


def run_server(port: int):
    """Run uvicorn on the given port. Must be top-level for macOS spawn multiprocessing."""
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app):
        async with mcp_app.router.lifespan_context(app):
            yield

    app = Starlette(
        routes=[
            Route("/chat", chat_endpoint, methods=["POST"]),
            Mount("/", app=mcp_app),
        ],
        lifespan=lifespan,
    )
    app = HostRewriteMiddleware(app)
    log.info(f"Starting HTTP server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    if is_port_available(8000):
        log.info("Port 8000 available - starting HTTP servers on ports 8000 and 8001")
        log.info("Port 8000: For ngrok tunnel and flows")
        log.info("Port 8001: For alternative HTTP access")

        ports = [8000, 8001]
        processes = []

        for port in ports:
            p = multiprocessing.Process(target=run_server, args=(port,))
            p.start()
            processes.append(p)
            log.info(f"✓ Started server process on port {port} (PID: {p.pid})")

        try:
            for p in processes:
                p.join()
        except KeyboardInterrupt:
            log.info("Shutting down HTTP servers...")
            for p in processes:
                p.terminate()
                p.join()
            log.info("All servers stopped")
    else:
        # stdio mode — port 8000 is in use, assume Claude Desktop
        log.info("Port 8000 in use - running in stdio mode for Claude Desktop")
        log.info("HTTP servers will not start (using stdio transport instead)")
        mcp.run()
