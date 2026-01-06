from typing import Any, Dict, Optional
import base64
import re
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP, Context

from defaults.schemas import *
import patchworks_client as pw
from auth_helper import get_token_from_context


def register_default_tools(mcp: FastMCP):
    """Register default tools based on config"""

    # Track default tools for list_tools() function
    if not hasattr(mcp, '_default_tools_registry'):
        mcp._default_tools_registry = []

    # ------------------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------------------

    @mcp.tool()
    def get_all_flows(args: GetAllFlowsArgs, ctx: Optional[Context] = None) -> Any:
        """List flows from the Core API."""
        token = get_token_from_context(ctx)
        return pw.get_all_flows(page=args.page, per_page=args.per_page, include=args.include, token=token)

    mcp._default_tools_registry.append({
        "name": "get_all_flows",
        "description": "List flows from the Core API.",
        "category": "flows"
    })

    @mcp.tool()
    def get_flow_runs(args: GetFlowRunsArgs, ctx: Optional[Context] = None) -> Any:
        """Query flow runs (filter by status, started_after; sort; includes)."""
        token = get_token_from_context(ctx)
        return pw.get_flow_runs(
            status=args.status,
            started_after=args.started_after,
            page=args.page,
            per_page=args.per_page,
            sort=args.sort,
            include=args.include,
            token=token
        )

    mcp._default_tools_registry.append({
        "name": "get_flow_runs",
        "description": "Query flow runs (filter by status, started_after; sort; includes).",
        "category": "flows"
    })

    @mcp.tool()
    def get_flow_run_logs(args: GetFlowRunLogsArgs, ctx: Optional[Context] = None) -> Any:
        """Retrieve logs for a specific flow run (optionally with payload IDs)."""
        token = get_token_from_context(ctx)
        return pw.get_flow_run_logs(
            run_id=args.run_id,
            per_page=args.per_page,
            page=args.page,
            sort=args.sort,
            include=args.include,
            fields_flowStep=args.fields_flowStep,
            load_payload_ids=args.load_payload_ids,
            token=token
        )

    mcp._default_tools_registry.append({
        "name": "get_flow_run_logs",
        "description": "Retrieve logs for a specific flow run (optionally with payload IDs).",
        "category": "flows"
    })

    @mcp.tool()
    def summarise_failed_run(args: SummariseFailedRunArgs, ctx: Optional[Context] = None) -> Any:
        """Summarise what went wrong in a failed run by inspecting log levels/messages."""
        token = get_token_from_context(ctx)
        return pw.summarise_failed_run(run_id=args.run_id, max_logs=args.max_logs, token=token)

    mcp._default_tools_registry.append({
        "name": "summarise_failed_run",
        "description": "Summarise what went wrong in a failed run by inspecting log levels/messages.",
        "category": "flows"
    })

    @mcp.tool()
    def triage_latest_failures(args: TriageLatestFailuresArgs, ctx: Optional[Context] = None) -> Any:
        """Fetch recent failed runs and return a compact summary for each."""
        token = get_token_from_context(ctx)
        return pw.triage_latest_failures(
            started_after=args.started_after,
            limit=args.limit,
            per_run_log_limit=args.per_run_log_limit,
            token=token
        )

    mcp._default_tools_registry.append({
        "name": "triage_latest_failures",
        "description": "Fetch recent failed runs and return a compact summary for each.",
        "category": "flows"
    })

    @mcp.tool()
    def download_payload(args: DownloadPayloadArgs, ctx: Optional[Context] = None) -> Any:
        """Download payload bytes for a given payload metadata ID (returned as base64)."""
        token = get_token_from_context(ctx)
        ctype, raw = pw.download_payload(args.payload_metadata_id, token=token)
        return {"content_type": ctype, "bytes_base64": base64.b64encode(raw).decode("ascii")}

    mcp._default_tools_registry.append({
        "name": "download_payload",
        "description": "Download payload bytes for a given payload metadata ID (returned as base64).",
        "category": "payloads"
    })

    @mcp.tool()
    def start_flow(args: StartFlowArgs, ctx: Optional[Context] = None) -> Any:
        """Trigger a flow run via the Start service (/flows/{id}/start)."""
        token = get_token_from_context(ctx)
        return pw.start_flow(flow_id=args.flow_id, payload=args.payload, token=token)

    mcp._default_tools_registry.append({
        "name": "start_flow",
        "description": "Trigger a flow run via the Start service (/flows/{id}/start).",
        "category": "flows"
    })

    @mcp.tool()
    def list_data_pools(args: ListDataPoolsArgs, ctx: Optional[Context] = None) -> Any:
        """List all data/dedupe pools."""
        token = get_token_from_context(ctx)
        return pw.list_data_pools(page=args.page, per_page=args.per_page, token=token)

    mcp._default_tools_registry.append({
        "name": "list_data_pools",
        "description": "List all data/dedupe pools.",
        "category": "data"
    })

    @mcp.tool()
    def get_deduped_data(args: GetDedupedDataArgs, ctx: Optional[Context] = None) -> Any:
        """Retrieve deduplicated data for a specific pool."""
        token = get_token_from_context(ctx)
        return pw.get_deduped_data(pool_id=args.pool_id, page=args.page, per_page=args.per_page, token=token)

    mcp._default_tools_registry.append({
        "name": "get_deduped_data",
        "description": "Retrieve deduplicated data for a specific pool.",
        "category": "data"
    })

    @mcp.tool()
    def get_marketplace_apps(args: GetMarketplaceAppsArgs, ctx: Optional[Context] = None) -> Any:
        """List marketplace apps from the Patchworks marketplace."""
        token = get_token_from_context(ctx)
        return pw.get_marketplace_apps(
            page=args.page,
            per_page=args.per_page,
            include=args.include,
            filter_name=args.filter_name,
            filter_allowed=args.filter_allowed,
            filter_private=args.filter_private,
            sort=args.sort,
            token=token
        )

    mcp._default_tools_registry.append({
        "name": "get_marketplace_apps",
        "description": "List marketplace apps from the Patchworks marketplace.",
        "category": "marketplace"
    })

    @mcp.tool()
    def get_marketplace_app(args: GetMarketplaceAppArgs, ctx: Optional[Context] = None) -> Any:
        """Get details of a specific marketplace app by ID."""
        token = get_token_from_context(ctx)
        return pw.get_marketplace_app(
            marketplace_app_id=args.marketplace_app_id,
            include=args.include,
            token=token
        )

    mcp._default_tools_registry.append({
        "name": "get_marketplace_app",
        "description": "Get details of a specific marketplace app by ID.",
        "category": "marketplace"
    })

    # Helper functions for flow creation
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
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
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

    @mcp.tool()
    def create_process_flow_from_prompt(args: CreateProcessFlowByPromptArgs, ctx: Optional[Context] = None) -> Any:
        """
        Build a generic flow from a natural-language prompt and import it.
        Produces a Try/Catch → Source Connector → Batch → Map → Destination Connector skeleton.
        """
        token = get_token_from_context(ctx)
        parts = _guess_parts_from_prompt(args.prompt)
        body = _build_generic_import_json(
            parts["source"], parts["destination"], parts["entity"],
            priority=args.priority,
            schedule_cron=args.schedule_cron,
            enable=args.enable
        )
        return pw.import_flow(body, token=token)

    mcp._default_tools_registry.append({
        "name": "create_process_flow_from_prompt",
        "description": "Build a generic flow from a natural-language prompt and import it. Produces a Try/Catch → Source Connector → Batch → Map → Destination Connector skeleton.",
        "category": "flow-creation"
    })

    @mcp.tool()
    def create_process_flow_from_json(args: CreateProcessFlowFromJsonArgs, ctx: Optional[Context] = None) -> Any:
        """
        Import a flow with the exact JSON body provided.
        Useful when you want to post a full export unchanged.
        """
        token = get_token_from_context(ctx)
        return pw.import_flow(args.body, token=token)

    mcp._default_tools_registry.append({
        "name": "create_process_flow_from_json",
        "description": "Import a flow with the exact JSON body provided. Useful when you want to post a full export unchanged.",
        "category": "flow-creation"
    })