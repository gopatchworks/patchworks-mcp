from __future__ import annotations
import os, json, logging, base64
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

if not CORE_API or not TOKEN:
    raise RuntimeError("Set PATCHWORKS_CORE_API (or PATCHWORKS_BASE_URL) and PATCHWORKS_TOKEN")

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
    page: int = 1,
    per_page: int = 50,
    sort: Optional[str] = "-started_at",
    include: Optional[str] = None
) -> Any:
    """
    GET /flow-runs  (Core API)
    For failures: status=3
    """
    params: Dict[str, Any] = {"page": page, "per_page": per_page}
    if sort:
        params["sort"] = sort
    if include:
        params["include"] = include
    if status is not None:
        params["filter[status]"] = status
    if started_after:
        params["filter[started_after]"] = started_after
    r = session.get(_url(CORE_API, "/flow-runs"), params=params, timeout=TIMEOUT)
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
    """
    if not START_API:
        raise RuntimeError("PATCHWORKS_START_API is not set; required for starting flows.")
    body = payload or {}
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

    return {
        "run_id": run_id,
        "levels": levels,
        "log_count": len(extracted),
        "highlights": highlights,
        "logs": extracted,  # caller can render/inspect
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
