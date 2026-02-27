from __future__ import annotations
import os, json, logging, base64
from datetime import datetime, timezone
from typing import Any, Optional, Dict, List, Tuple
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load env from a local .env (works whether launched from the project dir or by Claude)
load_dotenv()
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)

# ------------------------------------------------------------------------------
# Environment / Config
# ------------------------------------------------------------------------------

# Core API for reads/search/triage, e.g. https://core.wearepatchworks.com/api/v1
CORE_API = os.getenv("PATCHWORKS_CORE_API", "").rstrip("/")

# Start API to trigger a flow, e.g. https://start.wearepatchworks.com/api/v1
START_API = os.getenv("PATCHWORKS_START_API", "").rstrip("/")

# Back-compat: allow PATCHWORKS_BASE_URL to set CORE_API if present
if not CORE_API:
    CORE_API = os.getenv("PATCHWORKS_BASE_URL", "").rstrip("/")

TOKEN = os.getenv("PATCHWORKS_TOKEN", "")
TIMEOUT = float(os.getenv("PATCHWORKS_TIMEOUT_SECONDS", "20"))

# Dashboard base URL for generating deep links to flow runs / flows.
# e.g. https://app.wearepatchworks.com  (no trailing slash)
DASHBOARD_URL = os.getenv("PATCHWORKS_DASHBOARD_URL", "https://app.wearepatchworks.com").rstrip("/")

if not CORE_API or not TOKEN:
    raise RuntimeError("Set PATCHWORKS_CORE_API (or PATCHWORKS_BASE_URL) and PATCHWORKS_TOKEN")

# Commerce Foundation callback URLs (per-operation, configured per deployment)
CF_CALLBACK_ORDERS = os.getenv("PATCHWORKS_CALLBACK_ORDERS", "")
CF_CALLBACK_CUSTOMERS = os.getenv("PATCHWORKS_CALLBACK_CUSTOMERS", "")
CF_CALLBACK_PRODUCTS = os.getenv("PATCHWORKS_CALLBACK_PRODUCTS", "")
CF_CALLBACK_PRODUCT_VARIANTS = os.getenv("PATCHWORKS_CALLBACK_PRODUCT_VARIANTS", "")
CF_CALLBACK_INVENTORY = os.getenv("PATCHWORKS_CALLBACK_INVENTORY", "")
CF_CALLBACK_FULFILLMENTS = os.getenv("PATCHWORKS_CALLBACK_FULFILLMENTS", "")
CF_CALLBACK_RETURNS = os.getenv("PATCHWORKS_CALLBACK_RETURNS", "")
CF_CALLBACK_CREATE_ORDER = os.getenv("PATCHWORKS_CALLBACK_CREATE_ORDER", "")
CF_CALLBACK_UPDATE_ORDER = os.getenv("PATCHWORKS_CALLBACK_UPDATE_ORDER", "")
CF_CALLBACK_CANCEL_ORDER = os.getenv("PATCHWORKS_CALLBACK_CANCEL_ORDER", "")
CF_CALLBACK_FULFILL_ORDER = os.getenv("PATCHWORKS_CALLBACK_FULFILL_ORDER", "")
CF_CALLBACK_CREATE_RETURN = os.getenv("PATCHWORKS_CALLBACK_CREATE_RETURN", "")

# NOTE:
# If your gateway expects 'Bearer <token>', include 'Bearer ' in PATCHWORKS_TOKEN.
# Example:
#   PATCHWORKS_TOKEN=Bearer eyJhbGciOi...

log = logging.getLogger("patchworks-client")
log.setLevel(logging.INFO)

session = requests.Session()
session.headers.update({
    "Authorization": TOKEN,
    "Accept": "application/json",
    "Content-Type": "application/json",
})

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def _url(root: str, path: str) -> str:
    return f"{root}/{path.lstrip('/')}"

def _handle(r: requests.Response) -> Any:
    """Uniform HTTP handler with token redaction."""
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        body = (r.text or "")[:2000]
        redacted = body.replace(TOKEN, "***REDACTED***") if TOKEN else body
        raise RuntimeError(f"Patchworks HTTP {r.status_code}: {redacted}") from e
    if not r.text:
        return None
    try:
        return r.json()
    except Exception:
        return r.text

# ------------------------------------------------------------------------------
# Flows & Flow Runs
# ------------------------------------------------------------------------------

def get_all_flows(page: int = 1, per_page: int = 50, include: Optional[str] = None) -> Any:
    """
    GET /flows  (Core API)
    """
    params: Dict[str, Any] = {"page": page, "per_page": per_page}
    if include:
        params["include"] = include
    r = session.get(_url(CORE_API, "/flows"), params=params, timeout=TIMEOUT)
    return _handle(r)

def get_flow_runs(
    status: Optional[int] = None,
    started_after: Optional[str] = None,
    flow_id: Optional[int] = None,
    page: int = 1,
    per_page: int = 50,
    sort: Optional[str] = "-started_at",
    include: Optional[str] = None
) -> Any:
    """
    GET /flow-runs  (Core API)
    For failures: status=3, partial success: status=5
    """
    params: Dict[str, Any] = {"page": page, "per_page": per_page}
    if sort:
        params["sort"] = sort
    if include:
        params["include"] = include
    if status is not None:
        params["filter[status]"] = status
    if flow_id is not None:
        params["filter[flow_id]"] = flow_id
    if started_after:
        params["filter[started_after]"] = started_after
    r = session.get(_url(CORE_API, "/flow-runs"), params=params, timeout=TIMEOUT)
    return _handle(r)

def get_flow_run(run_id: str, include: Optional[str] = None) -> Any:
    """
    GET /flow-runs/{id}  (Core API)
    Fetch a single flow run's metadata — useful for resolving flow_id from a run ID.
    """
    params: Dict[str, Any] = {}
    if include:
        params["include"] = include
    r = session.get(_url(CORE_API, f"/flow-runs/{run_id}"), params=params, timeout=TIMEOUT)
    return _handle(r)

def get_flow_run_logs(
    run_id: str,
    per_page: int = 10,
    page: int = 1,
    sort: str = "id",
    include: str = "flowRunLogMetadata",
    fields_flowStep: str = "id,name",
    load_payload_ids: bool = True
) -> Any:
    """
    GET /flow-runs/{id}/flow-run-logs  (Core API)
    """
    params: Dict[str, Any] = {
        "per_page": per_page,
        "page": page,
        "sort": sort,
        "include": include,
        "fields[flowStep]": fields_flowStep,
        "load_payload_ids": "true" if load_payload_ids else "false",
    }
    r = session.get(_url(CORE_API, f"/flow-runs/{run_id}/flow-run-logs"), params=params, timeout=TIMEOUT)
    return _handle(r)

def download_payload(payload_metadata_id: str) -> Tuple[str, bytes]:
    """
    GET /payload-metadata/{id}/download  (Core API)
    Returns (content_type, raw_bytes)
    """
    url = _url(CORE_API, f"/payload-metadata/{payload_metadata_id}/download")
    r = session.get(url, timeout=TIMEOUT)
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        body = (r.text or "")[:1000]
        redacted = body.replace(TOKEN, "***REDACTED***") if TOKEN else body
        raise RuntimeError(f"Patchworks HTTP {r.status_code}: {redacted}") from e
    return r.headers.get("Content-Type", "application/octet-stream"), r.content

def start_flow(flow_id: str, payload: Optional[Dict[str, Any]] = None) -> Any:
    """
    POST /flows/{id}/start  (Start API)
    Requires PATCHWORKS_START_API = https://start.wearepatchworks.com/api/v1

    The payload (if provided) is JSON-stringified and sent as
    {"payload": "<JSON string>"} — the Start API requires the payload
    field to be a string, not a nested object.
    """
    if not START_API:
        raise RuntimeError("PATCHWORKS_START_API is not set; required for starting flows.")
    body: Dict[str, Any] = {}
    if payload:
        body["payload"] = json.dumps(payload)
    r = session.post(_url(START_API, f"/flows/{flow_id}/start"), data=json.dumps(body), timeout=TIMEOUT)
    return _handle(r)


# ------------------------------------------------------------------------------
# Data Pools (Core API)
# ------------------------------------------------------------------------------

def list_data_pools(page: int = 1, per_page: int = 50) -> Any:
    """
    GET /data-pool/
    Returns a paginated list of data/dedupe pools.
    """
    params: Dict[str, Any] = {"page": page, "per_page": per_page}
    r = session.get(_url(CORE_API, "/data-pool/"), params=params, timeout=TIMEOUT)
    return _handle(r)

def get_deduped_data(pool_id: str, page: int = 1, per_page: int = 50) -> Any:
    """
    GET /data-pool/{id}/deduped-data
    Returns deduplicated data rows within the specified pool.
    """
    params: Dict[str, Any] = {"page": page, "per_page": per_page}
    r = session.get(_url(CORE_API, f"/data-pool/{pool_id}/deduped-data"), params=params, timeout=TIMEOUT)
    return _handle(r)


# ------------------------------------------------------------------------------
# Failure triage helpers
# ------------------------------------------------------------------------------

def summarise_failed_run(run_id: str, max_logs: int = 50) -> Dict[str, Any]:
    """
    Pull logs for a failed run and produce a lightweight summary from log_level/log_message.
    """
    logs = get_flow_run_logs(
        run_id, per_page=max_logs, page=1, sort="id",
        include="flowRunLogMetadata", fields_flowStep="id,name", load_payload_ids=True
    )
    items: List[Dict[str, Any]] = logs.get("data", []) if isinstance(logs, dict) else []

    extracted: List[Dict[str, Any]] = []
    for item in items:
        attrs = item.get("attributes", {}) if isinstance(item, dict) else {}
        entry = {
            "id": item.get("id"),
            "timestamp": attrs.get("created_at") or attrs.get("timestamp"),
            "level": (attrs.get("log_level") or attrs.get("level") or "").upper(),
            "message": attrs.get("log_message") or attrs.get("message"),
            "flow_step_id": attrs.get("flow_step_id") or attrs.get("step_id"),
            "payload_metadata_id": attrs.get("payload_metadata_id"),
        }
        extracted.append(entry)

    levels: Dict[str, int] = {}
    first_error = None
    last_error = None
    for e in extracted:
        lvl = e["level"]
        if lvl:
            levels[lvl] = levels.get(lvl, 0) + 1
        if lvl in ("ERROR", "FATAL") and not first_error and e.get("message"):
            first_error = e
        if lvl in ("ERROR", "FATAL") and e.get("message"):
            last_error = e

    highlights: List[str] = []
    if first_error:
        highlights.append(f"First error: [{first_error['level']}] {first_error.get('message')}")
    if last_error and last_error is not first_error:
        highlights.append(f"Last error:  [{last_error['level']}] {last_error.get('message')}")
    if not highlights and extracted:
        tail = extracted[-1]
        highlights.append(f"Last log line: [{tail.get('level')}] {tail.get('message')}")

    # Collect payload metadata IDs from logs so callers know payloads are available
    available_payloads: List[Dict[str, Any]] = []
    for e in extracted:
        pid = e.get("payload_metadata_id")
        if pid:
            available_payloads.append({
                "payload_metadata_id": pid,
                "flow_step_id": e.get("flow_step_id"),
                "hint": f"Payload available — call download_payload with ID '{pid}' to retrieve it.",
            })

    # Only include ERROR/FATAL log entries (not the full log dump) to keep
    # the tool result small and avoid blowing the token budget on follow-up turns.
    error_logs = [e for e in extracted if e.get("level") in ("ERROR", "FATAL")]

    return {
        "run_id": run_id,
        "run_log_url": _run_log_url(run_id),
        "levels": levels,
        "log_count": len(extracted),
        "highlights": highlights,
        "available_payloads": available_payloads,
        "error_logs": error_logs,
    }

def triage_latest_failures(
    started_after: Optional[str] = None,
    limit: int = 20,
    per_run_log_limit: int = 50
) -> Dict[str, Any]:
    """
    Fetch recent failed flow-runs (status=3), then summarise each by inspecting log_level/log_message.
    - started_after: optional timestamp/epoch-ms (string) to filter newer runs
    - limit: max number of failed runs to summarise
    - per_run_log_limit: how many log entries to pull per run for the summary
    """
    runs_resp = get_flow_runs(
        status=3,  # FAILURE
        started_after=started_after,
        page=1,
        per_page=max(1, min(limit, 200)),
        sort="-started_at",
        include=None,
    )

    data = runs_resp.get("data", []) if isinstance(runs_resp, dict) else []
    results: List[Dict[str, Any]] = []

    for run in data[:limit]:
        run_id = run.get("id")
        attrs = (run.get("attributes") or {}) if isinstance(run, dict) else {}
        try:
            summary = summarise_failed_run(run_id, max_logs=per_run_log_limit)
        except Exception as e:
            summary = {
                "run_id": run_id,
                "error": f"Failed to summarise logs: {e}",
                "levels": {},
                "log_count": 0,
                "highlights": [],
                "logs": [],
            }

        results.append({
            "run_id": run_id,
            "status": attrs.get("status"),
            "started_at": attrs.get("started_at"),
            "finished_at": attrs.get("finished_at"),
            "flow_id": attrs.get("flow_id"),
            "flow_version_id": attrs.get("flow_version_id"),
            "summary": summary,
        })

    return {
        "count": len(results),
        "started_after": started_after,
        "items": results,
    }

# ------------------------------------------------------------------------------
# Flows: Import (POST /flows/import)
# ------------------------------------------------------------------------------

def import_flow(payload: Dict[str, Any]) -> Any:
    """
    POST /flows/import  (Core API)
    Body is the full import JSON for a flow+systems bundle.
    """
    url = _url(CORE_API, "/flows/import")
    r = session.post(url, data=json.dumps(payload), timeout=TIMEOUT)
    return _handle(r)


# ------------------------------------------------------------------------------
# Composite / high-level investigation helpers
# ------------------------------------------------------------------------------

def _run_log_url(run_id: str) -> str:
    """Build a dashboard deep-link to a flow run's log page."""
    return f"{DASHBOARD_URL}/flow-run-logs/{run_id}"


# Maximum number of payloads to download inside investigate_failure to keep
# total execution time short (each download is a blocking HTTP call).
_MAX_PAYLOAD_DOWNLOADS = 2


def _parse_ts(value: str) -> Optional[datetime]:
    """Best-effort parse of a timestamp string into a UTC datetime."""
    if not value:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%fZ",   # ISO-8601 with fractional seconds
        "%Y-%m-%dT%H:%M:%SZ",       # ISO-8601
        "%Y-%m-%dT%H:%M:%S.%f",     # without Z
        "%Y-%m-%dT%H:%M:%S",        # without Z
        "%Y-%m-%d %H:%M:%S",        # human-friendly (from Slack alert)
    ):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _best_run_by_timestamp(
    runs: List[Dict[str, Any]], target: datetime,
) -> Optional[Dict[str, Any]]:
    """
    Pick the run whose started_at or finished_at is closest to *target*.
    Returns the best-matching run dict, or None if runs is empty.
    """
    best_run = None
    best_delta = None
    for run in runs:
        attrs = run.get("attributes", {}) if isinstance(run, dict) else {}
        for ts_field in ("finished_at", "started_at"):
            ts_val = attrs.get(ts_field)
            if not ts_val:
                continue
            parsed = _parse_ts(str(ts_val))
            if not parsed:
                continue
            delta = abs((parsed - target).total_seconds())
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best_run = run
    return best_run


def investigate_failure(
    flow_id: Optional[int] = None,
    flow_name: Optional[str] = None,
    run_id: Optional[str] = None,
    include_payload: bool = False,
    failed_at: Optional[str] = None,
) -> Dict[str, Any]:
    """
    All-in-one failure investigation.  Accepts a flow name/ID or a specific run ID.
    Steps:
      1. If only flow_name given, resolve to flow_id via get_all_flows.
      2. Find the most recent failed run for that flow (or use the given run_id).
         If *failed_at* is supplied (ISO-8601 or "YYYY-MM-DD HH:MM:SS"), match the
         run whose started_at/finished_at is closest to that timestamp — this ensures
         we investigate the exact run the alert refers to.
      3. Summarise the failed run (logs, errors, highlights).
      4. Download catch-route payloads to follow the alert chain (always) and
         include full payload data in the result only if include_payload is True.
    Returns a rich diagnostic object in a single tool call.
    """
    result: Dict[str, Any] = {"flow_id": flow_id, "flow_name": flow_name}

    # -- Step 1: resolve flow_name → flow_id if needed -------------------------
    if flow_name and not flow_id:
        page = 1
        found = False
        while not found:
            flows_resp = get_all_flows(page=page, per_page=200)
            data = flows_resp.get("data", []) if isinstance(flows_resp, dict) else []
            if not data:
                break
            for f in data:
                attrs = f.get("attributes", {}) if isinstance(f, dict) else {}
                name = attrs.get("name", "")
                if name.lower() == flow_name.lower():
                    flow_id = f.get("id")
                    result["flow_id"] = flow_id
                    result["flow_name"] = name
                    result["flow_enabled"] = attrs.get("is_enabled")
                    found = True
                    break
            meta = flows_resp.get("meta", {})
            if page >= meta.get("last_page", page):
                break
            page += 1

        if not flow_id:
            result["error"] = f"Could not find a flow named '{flow_name}'."
            return result

    # -- Step 2: find the correct problematic run ---------------------------------
    # Try/Catch flows are tricky: the Odoo call can fail with a 422 but the
    # overall run finishes as SUCCESS (2) because the catch branch handled it
    # (e.g. sent a Slack alert).  So we MUST also consider SUCCESS runs when
    # a timestamp is provided — it's the only way to find the right one.
    #
    # Strategy:
    #   A. When failed_at IS provided → search ALL statuses (3, 5, 2, 1) and
    #      pick the run closest to that timestamp.
    #   B. When failed_at is NOT provided → search only 3 and 5 (the old
    #      behaviour) so we don't surface random successful runs.
    target_ts = _parse_ts(failed_at) if failed_at else None

    if not run_id:
        # Choose which statuses to search based on whether we have a timestamp
        statuses_to_search = (3, 5, 2, 1) if target_ts else (3, 5)

        candidate_runs: List[Dict[str, Any]] = []
        for search_status in statuses_to_search:
            runs_resp = get_flow_runs(
                status=search_status, flow_id=flow_id,
                page=1, per_page=10, sort="-started_at",
            )
            data = runs_resp.get("data", []) if isinstance(runs_resp, dict) else []
            candidate_runs.extend(data)

        if candidate_runs:
            if target_ts:
                # Timestamp-match: pick the run closest to the alert's timestamp
                run = _best_run_by_timestamp(candidate_runs, target_ts)
            else:
                # No timestamp — fall back to most recent (sorted by started_at desc)
                run = candidate_runs[0]

            if run:
                attrs = run.get("attributes", {}) if isinstance(run, dict) else {}
                run_id = run.get("id")
                result["run_status"] = attrs.get("status")
                result["run_started_at"] = attrs.get("started_at")
                result["run_finished_at"] = attrs.get("finished_at")

        if not run_id:
            # Widen the search — look for any recent run (no status filter).
            runs_resp2 = get_flow_runs(
                flow_id=flow_id, page=1, per_page=10, sort="-started_at",
            )
            data2 = runs_resp2.get("data", []) if isinstance(runs_resp2, dict) else []
            if data2:
                if target_ts:
                    run = _best_run_by_timestamp(data2, target_ts)
                else:
                    run = data2[0]
                if run:
                    attrs = run.get("attributes", {}) if isinstance(run, dict) else {}
                    run_id = run.get("id")
                    result["run_status"] = attrs.get("status")
                    result["run_started_at"] = attrs.get("started_at")
                    result["note"] = "No failed/partial-success run found; using closest matching run instead."

        if not run_id:
            result["error"] = f"No recent runs found for flow_id={flow_id}."
            return result

    result["run_id"] = run_id
    result["run_log_url"] = _run_log_url(run_id)

    # -- Step 3: summarise the run ----------------------------------------------
    try:
        summary = summarise_failed_run(run_id, max_logs=50)
        result["summary"] = summary
    except Exception as e:
        result["summary_error"] = str(e)
        return result

    # -- Step 4: follow the alert/catch chain -----------------------------------
    # ALWAYS attempt to follow the chain by downloading the first payload to
    # look for an originating run ID.  Alert/catch flows won't have useful error
    # detail themselves — the real error is in the originating run.
    # The `include_payload` flag only controls whether full payload data is
    # included in the response (which costs tokens).
    originating_run_id = None
    payloads_decoded: List[Dict[str, Any]] = []

    if summary.get("available_payloads"):
        for p_info in summary["available_payloads"][:_MAX_PAYLOAD_DOWNLOADS]:
            pid = p_info.get("payload_metadata_id")
            if not pid:
                continue
            try:
                ctype, raw = download_payload(pid)
                decoded: Any = None
                if "json" in ctype.lower():
                    try:
                        decoded = json.loads(raw)
                    except Exception:
                        decoded = raw.decode("utf-8", errors="replace")
                else:
                    decoded = raw.decode("utf-8", errors="replace")

                if include_payload:
                    payloads_decoded.append({
                        "payload_metadata_id": pid,
                        "flow_step_id": p_info.get("flow_step_id"),
                        "content_type": ctype,
                        "data": decoded,
                    })

                # Look for a reference to an originating flow run ID in the payload
                if isinstance(decoded, dict) and not originating_run_id:
                    for key in ("flow_run_id", "run_id", "original_run_id",
                                "source_run_id", "flowRunId"):
                        if decoded.get(key):
                            originating_run_id = str(decoded[key])
                            break
                    # Also check nested structures (one level deep)
                    if not originating_run_id:
                        for val in decoded.values():
                            if isinstance(val, dict):
                                for key in ("flow_run_id", "run_id", "original_run_id",
                                            "source_run_id", "flowRunId"):
                                    if val.get(key):
                                        originating_run_id = str(val[key])
                                        break
                            if originating_run_id:
                                break

                # Stop downloading more payloads once we've found an originating run
                if originating_run_id:
                    break

            except Exception as e:
                if include_payload:
                    payloads_decoded.append({
                        "payload_metadata_id": pid,
                        "error": str(e),
                    })

    if include_payload and payloads_decoded:
        result["payloads"] = payloads_decoded

    # If we found an originating run, summarise it — this is the REAL failure
    if originating_run_id and originating_run_id != run_id:
        result["originating_run_id"] = originating_run_id
        result["originating_run_log_url"] = _run_log_url(originating_run_id)

        # Fetch the originating run's metadata to get its flow_id and flow_name
        # so the model knows which flow to retry.
        try:
            orig_run_resp = get_flow_run(originating_run_id)
            orig_run_data = orig_run_resp.get("data", {}) if isinstance(orig_run_resp, dict) else {}
            orig_attrs = orig_run_data.get("attributes", {}) if isinstance(orig_run_data, dict) else {}

            # flow_id may be in attributes or relationships
            orig_flow_id = orig_attrs.get("flow_id")
            if not orig_flow_id:
                rels = orig_run_data.get("relationships", {}) if isinstance(orig_run_data, dict) else {}
                flow_rel = rels.get("flow", {}).get("data", {})
                if isinstance(flow_rel, dict):
                    orig_flow_id = flow_rel.get("id")

            if orig_flow_id:
                result["originating_flow_id"] = orig_flow_id

            orig_flow_name = orig_attrs.get("flow_name") or orig_attrs.get("name")
            if orig_flow_name:
                result["originating_flow_name"] = orig_flow_name

            result["originating_run_started_at"] = orig_attrs.get("started_at")
            result["originating_run_status"] = orig_attrs.get("status")
        except Exception:
            pass  # Non-critical — we still have the run ID and log URL

        try:
            orig_summary = summarise_failed_run(originating_run_id, max_logs=50)
            result["originating_run_summary"] = orig_summary

            # Build an informative note with the originating flow ID for retrying
            note_parts = [
                f"This is an alert/catch flow. The actual failure occurred in "
                f"run {originating_run_id}."
            ]
            if result.get("originating_flow_id"):
                note_parts.append(
                    f"To retry, use start_flow with flow_id='{result['originating_flow_id']}' "
                    f"(NOT the alert flow)."
                )
            note_parts.append(f"See: {_run_log_url(originating_run_id)}")
            result["note"] = " ".join(note_parts)
        except Exception as e:
            result["originating_run_summary_error"] = str(e)

    return result


def get_run_payloads(
    run_id: str,
    step_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch all payloads for a given flow run in a single call.
    Optionally filter by step_name (e.g. 'Catch', 'Try/Catch', 'Source Connector').
    Returns decoded payload content for each payload found in the run logs.
    """
    logs_resp = get_flow_run_logs(
        run_id=run_id, per_page=200, page=1, sort="id",
        include="flowRunLogMetadata", fields_flowStep="id,name",
        load_payload_ids=True,
    )
    items = logs_resp.get("data", []) if isinstance(logs_resp, dict) else []

    payload_entries: List[Dict[str, Any]] = []
    seen_ids: set = set()

    for item in items:
        attrs = item.get("attributes", {}) if isinstance(item, dict) else {}
        pid = attrs.get("payload_metadata_id")
        if not pid or pid in seen_ids:
            continue

        # If step_name filter is set, check the flow step name
        if step_name:
            step_info = attrs.get("flow_step", {}) or {}
            sname = step_info.get("name", "") or attrs.get("flow_step_name", "")
            if step_name.lower() not in sname.lower():
                continue

        seen_ids.add(pid)
        entry: Dict[str, Any] = {
            "payload_metadata_id": pid,
            "log_message": attrs.get("log_message") or attrs.get("message"),
            "flow_step_id": attrs.get("flow_step_id"),
        }

        try:
            ctype, raw = download_payload(pid)
            if "json" in ctype.lower():
                try:
                    entry["data"] = json.loads(raw)
                except Exception:
                    entry["data"] = raw.decode("utf-8", errors="replace")
            else:
                entry["data"] = raw.decode("utf-8", errors="replace")
            entry["content_type"] = ctype
        except Exception as e:
            entry["error"] = str(e)

        payload_entries.append(entry)

    return {
        "run_id": run_id,
        "step_filter": step_name,
        "payload_count": len(payload_entries),
        "payloads": payload_entries,
    }


# ------------------------------------------------------------------------------
# Commerce Foundation helpers
# ------------------------------------------------------------------------------

def _cf_post(callback_url: str, operation_name: str, inputSchema: Optional[str] = None) -> Any:
    """Post to a Commerce Foundation callback URL."""
    if not callback_url:
        raise RuntimeError(
            f"No callback URL configured for '{operation_name}'. "
            f"Set the corresponding PATCHWORKS_CALLBACK_* environment variable."
        )
    body = {}
    if inputSchema:
        body["inputSchema"] = inputSchema
    r = session.post(callback_url, data=json.dumps(body), timeout=TIMEOUT)
    return _handle(r)

# ------------------------------------------------------------------------------
# Commerce Foundation - Query Tools
# ------------------------------------------------------------------------------

def get_orders(inputSchema: Optional[str] = None) -> Any:
    return _cf_post(CF_CALLBACK_ORDERS, "get_orders", inputSchema)

def get_customers(inputSchema: Optional[str] = None) -> Any:
    return _cf_post(CF_CALLBACK_CUSTOMERS, "get_customers", inputSchema)

def get_products(inputSchema: Optional[str] = None) -> Any:
    return _cf_post(CF_CALLBACK_PRODUCTS, "get_products", inputSchema)

def get_product_variants(inputSchema: Optional[str] = None) -> Any:
    return _cf_post(CF_CALLBACK_PRODUCT_VARIANTS, "get_product_variants", inputSchema)

def get_inventory(inputSchema: Optional[str] = None) -> Any:
    return _cf_post(CF_CALLBACK_INVENTORY, "get_inventory", inputSchema)

def get_fulfillments(inputSchema: Optional[str] = None) -> Any:
    return _cf_post(CF_CALLBACK_FULFILLMENTS, "get_fulfillments", inputSchema)

def get_returns(inputSchema: Optional[str] = None) -> Any:
    return _cf_post(CF_CALLBACK_RETURNS, "get_returns", inputSchema)

# ------------------------------------------------------------------------------
# Commerce Foundation - Action Tools
# ------------------------------------------------------------------------------

def create_sales_order(inputSchema: Optional[str] = None) -> Any:
    return _cf_post(CF_CALLBACK_CREATE_ORDER, "create_sales_order", inputSchema)

def update_order(inputSchema: Optional[str] = None) -> Any:
    return _cf_post(CF_CALLBACK_UPDATE_ORDER, "update_order", inputSchema)

def cancel_order(inputSchema: Optional[str] = None) -> Any:
    return _cf_post(CF_CALLBACK_CANCEL_ORDER, "cancel_order", inputSchema)

def fulfill_order(inputSchema: Optional[str] = None) -> Any:
    return _cf_post(CF_CALLBACK_FULFILL_ORDER, "fulfill_order", inputSchema)

def create_return(inputSchema: Optional[str] = None) -> Any:
    return _cf_post(CF_CALLBACK_CREATE_RETURN, "create_return", inputSchema)      
