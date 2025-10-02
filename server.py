from __future__ import annotations
import sys, logging, base64
from typing import Any, Optional, Dict
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

import patchworks_client as pw

# Log to STDERR only (stdio transport cannot receive stdout noise)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger("patchworks-mcp")

mcp = FastMCP("patchworks")

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

# ------------------------------------------------------------------------------
# Tools
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

if __name__ == "__main__":
    mcp.run(transport="stdio")