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
import datetime
from urllib.parse import parse_qs, urlparse
from typing import Any, Optional, Tuple
from schemas import validate_log, validate_log_batch, ValidationError
from storage import (
    insert_log, insert_log_batch,
    query_logs, count_logs,
    query_anomaly_results,
)

def _json_body(handler) -> Tuple[Any, Optional[str]]:
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
    parsed = parse_qs(urlparse(path).query)
    return {k: v[-1] for k, v in parsed.items() if v}


def _safe_limit(params: dict[str, str], default: int, maximum: int) -> int:
    try:
        return min(max(int(params.get("limit", default)), 1), maximum)
    except ValueError:
        return default


def _minute_key(ts: str) -> Optional[str]:
    try:
        dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    dt = dt.replace(second=0, microsecond=0)
    return dt.isoformat()


def _summarise_logs(logs: list[dict]) -> dict:
    services = ["auth-service", "api-gateway", "payment-service", "notification-service"]
    levels = ["DEBUG", "INFO", "WARN", "ERROR"]

    level_counts = {level: 0 for level in levels}
    service_rows = {service: [] for service in services}
    buckets: dict[str, dict[str, Any]] = {}

    for log in logs:
        level = log.get("log_level")
        service = log.get("service_name")

        if level in level_counts:
            level_counts[level] += 1
        if service in service_rows:
            service_rows[service].append(log)

        key = _minute_key(log.get("timestamp", ""))
        if key:
            bucket = buckets.setdefault(key, {"window_start": key, "total_logs": 0, "error_count": 0})
            bucket["total_logs"] += 1
            if level == "ERROR":
                bucket["error_count"] += 1

    service_health = []
    for service in services:
        rows = service_rows[service]
        total = len(rows)
        errors = sum(1 for row in rows if row.get("log_level") == "ERROR")
        warnings = sum(1 for row in rows if row.get("log_level") == "WARN")
        latencies = [row.get("latency_ms") for row in rows if isinstance(row.get("latency_ms"), (int, float))]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        event_counts: dict[str, int] = {}
        for row in rows:
            event = row.get("event_type")
            if isinstance(event, str):
                event_counts[event] = event_counts.get(event, 0) + 1

        top_events = [
            {"event_type": event, "count": count}
            for event, count in sorted(event_counts.items(), key=lambda item: item[1], reverse=True)[:5]
        ]

        service_health.append({
            "service_name": service,
            "total_logs": total,
            "error_count": errors,
            "warning_count": warnings,
            "error_rate": round(errors / total, 4) if total else 0.0,
            "avg_latency_ms": round(avg_latency, 2),
            "top_events": top_events,
        })

    timeline = []
    for bucket in sorted(buckets.values(), key=lambda item: item["window_start"]):
        total = bucket["total_logs"]
        bucket["error_rate"] = round(bucket["error_count"] / total, 4) if total else 0.0
        timeline.append(bucket)

    return {
        "total_logs": len(logs),
        "level_counts": level_counts,
        "error_count": level_counts["ERROR"],
        "warning_count": level_counts["WARN"],
        "service_health": service_health,
        "log_timeline": timeline,
    }


def _dashboard_payload(log_limit: int = 1000, anomaly_limit: int = 100) -> dict:
    logs = query_logs(limit=log_limit)
    anomalies = query_anomaly_results(limit=anomaly_limit)
    summary = _summarise_logs(logs)

    latest_anomaly = anomalies[0] if anomalies else None
    active_incident_windows = sum(1 for row in anomalies if row.get("is_anomalous"))

    return {
        "status": "ok",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_logs_stored": count_logs(),
        "recent_logs": summary,
        "anomaly_summary": {
            "count": len(anomalies),
            "active_incident_windows": active_incident_windows,
            "latest": latest_anomaly,
            "threshold": 0.75,
        },
        "anomaly_timeline": anomalies,
        "service_health": summary["service_health"],
        "log_timeline": summary["log_timeline"],
    }


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
    limit = _safe_limit(params, default=200, maximum=1000)

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
    limit = _safe_limit(params, default=50, maximum=200)

    results = query_anomaly_results(limit=limit)
    _send_json(handler, 200, {"count": len(results), "anomalies": results})


def handle_dashboard_overview(handler) -> None:
    """GET /dashboard/overview?limit=1000"""
    params = _parse_qs(handler.path)
    log_limit = _safe_limit(params, default=1000, maximum=5000)
    anomaly_limit = _safe_limit({"limit": params.get("anomaly_limit", "100")}, default=100, maximum=500)
    _send_json(handler, 200, _dashboard_payload(log_limit=log_limit, anomaly_limit=anomaly_limit))


def handle_dashboard_service_health(handler) -> None:
    """GET /dashboard/service-health?limit=1000"""
    params = _parse_qs(handler.path)
    log_limit = _safe_limit(params, default=1000, maximum=5000)
    payload = _dashboard_payload(log_limit=log_limit, anomaly_limit=100)
    _send_json(handler, 200, {
        "status": "ok",
        "generated_at": payload["generated_at"],
        "service_health": payload["service_health"],
    })


def handle_dashboard_timeline(handler) -> None:
    """GET /dashboard/timeline?limit=1000&anomaly_limit=100"""
    params = _parse_qs(handler.path)
    log_limit = _safe_limit(params, default=1000, maximum=5000)
    anomaly_limit = _safe_limit({"limit": params.get("anomaly_limit", "100")}, default=100, maximum=500)
    payload = _dashboard_payload(log_limit=log_limit, anomaly_limit=anomaly_limit)
    _send_json(handler, 200, {
        "status": "ok",
        "generated_at": payload["generated_at"],
        "log_timeline": payload["log_timeline"],
        "anomaly_timeline": payload["anomaly_timeline"],
    })


def handle_status(handler) -> None:
    """GET /status — health check."""
    total = count_logs()
    _send_json(handler, 200, {
        "status": "ok",
        "service": "ingestor-api",
        "total_logs_stored": total,
    })
