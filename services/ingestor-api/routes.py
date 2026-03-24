"""
routes.py
All route handler functions for the ingestor-api.

Routes
------
POST  /ingest           — ingest a single log event
POST  /ingest/batch     — ingest up to 500 log events at once
GET   /logs             — query stored logs (with filters)
GET   /anomalies        — query stored anomaly results
GET   /status           — health check + counts
"""

import json
from typing import Any
from schemas import validate_log, validate_log_batch, ValidationError
from storage import (
    insert_log, insert_log_batch,
    query_logs, count_logs,
    query_anomaly_results,
)

def _json_body(handler) -> tuple[Any, str | None]:
    """
    Read and parse the request body as JSON.
    Returns (parsed_data, error_message).
    """
    try:
        length = int(handler.headers.get("Content-Length", 0))
        raw = handler.rfile.read(length)
        return json.loads(raw), None
    except (json.JSONDecodeError, ValueError) as e:
        return None, f"Invalid JSON: {e}"


def _send_json(handler, status: int, payload: Any) -> None:
    body = json.dumps(payload, ensure_ascii=False, default=str).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")   # for dashboard
    handler.end_headers()
    handler.wfile.write(body)


def _parse_qs(path: str) -> dict[str, str]:
    """Extract query string params from path like /logs?service=auth-service&limit=100"""
    if "?" not in path:
        return {}
    qs = path.split("?", 1)[1]
    params = {}
    for part in qs.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            params[k] = v
    return params


def handle_ingest(handler) -> None:
    """POST /ingest — single log event."""
    data, err = _json_body(handler)
    if err:
        _send_json(handler, 400, {"error": err})
        return

    try:
        clean = validate_log(data)
    except ValidationError as e:
        _send_json(handler, 422, {"error": str(e)})
        return

    row_id = insert_log(clean)
    _send_json(handler, 201, {"status": "accepted", "id": row_id})


def handle_ingest_batch(handler) -> None:
    """POST /ingest/batch — up to 500 log events."""
    data, err = _json_body(handler)
    if err:
        _send_json(handler, 400, {"error": err})
        return

    if not isinstance(data, list):
        _send_json(handler, 400, {"error": "Request body must be a JSON array."})
        return

    if len(data) > 500:
        _send_json(handler, 413, {"error": "Batch size exceeds limit of 500."})
        return

    valid, errors = validate_log_batch(data)
    ids = insert_log_batch(valid) if valid else []

    _send_json(handler, 207, {   # 207 Multi-Status
        "accepted": len(ids),
        "rejected": len(errors),
        "ids": ids,
        "errors": errors[:10],   # cap error detail returned
    })


def handle_get_logs(handler) -> None:
    """GET /logs?start=...&end=...&service=...&log_level=...&limit=..."""
    params = _parse_qs(handler.path)
    try:
        limit = min(int(params.get("limit", 200)), 1000)
    except ValueError:
        limit = 200

    logs = query_logs(
        start=params.get("start"),
        end=params.get("end"),
        service=params.get("service"),
        log_level=params.get("log_level"),
        limit=limit,
    )
    _send_json(handler, 200, {"count": len(logs), "logs": logs})


def handle_get_anomalies(handler) -> None:
    """GET /anomalies?limit=..."""
    params = _parse_qs(handler.path)
    try:
        limit = min(int(params.get("limit", 50)), 200)
    except ValueError:
        limit = 50

    results = query_anomaly_results(limit=limit)
    _send_json(handler, 200, {"count": len(results), "anomalies": results})


def handle_status(handler) -> None:
    """GET /status — health check."""
    total = count_logs()
    _send_json(handler, 200, {
        "status": "ok",
        "service": "ingestor-api",
        "total_logs_stored": total,
    })