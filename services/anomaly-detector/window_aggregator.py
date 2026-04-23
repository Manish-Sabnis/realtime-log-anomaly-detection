"""
window_aggregator.py
Groups raw logs from the database into 1-minute windows.

Each window becomes a flat dict of statistics — the raw material
that feature_extractor.py will turn into a model-ready vector.

A window covers [window_start, window_start + 60s).
"""

import sys
import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ingestor-api"))

from storage import query_logs, get_connection


# ── Time helpers ──────────────────────────────────────────────────────────────

def _floor_to_minute(ts: str) -> datetime.datetime:
    dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt.replace(second=0, microsecond=0)


def _iso(dt: datetime.datetime) -> str:
    return dt.isoformat()


# ── Core aggregation ──────────────────────────────────────────────────────────

def aggregate_window(window_start: datetime.datetime) -> Optional[dict]:
    """
    Aggregate all logs in the 60-second window starting at window_start.
    Returns a stats dict, or None if the window has no logs.
    """
    window_end = window_start + datetime.timedelta(seconds=60)

    logs = query_logs(
        start=_iso(window_start),
        end=_iso(window_end),
        limit=10_000,
    )

    if not logs:
        return None

    total = len(logs)

    # ── Level counts ──────────────────────────────────────────────────────────
    level_counts = {"INFO": 0, "WARN": 0, "ERROR": 0, "DEBUG": 0}
    for log in logs:
        level_counts[log["log_level"]] = level_counts.get(log["log_level"], 0) + 1

    error_rate = level_counts["ERROR"] / total
    warn_rate  = level_counts["WARN"]  / total

    # ── Service distribution ──────────────────────────────────────────────────
    service_counts = {
        "auth-service":         0,
        "api-gateway":          0,
        "payment-service":      0,
        "notification-service": 0,
    }
    for log in logs:
        service_counts[log["service_name"]] = service_counts.get(log["service_name"], 0) + 1

    service_fractions = {k: v / total for k, v in service_counts.items()}

    # ── Event type counts ─────────────────────────────────────────────────────
    event_counts: dict[str, int] = {}
    for log in logs:
        et = log["event_type"]
        event_counts[et] = event_counts.get(et, 0) + 1

    login_success_count   = event_counts.get("login_success",       0)
    login_failure_count   = event_counts.get("login_failure",       0)
    high_latency_count    = event_counts.get("high_latency",        0)
    payment_timeout_count = event_counts.get("payment_timeout",     0)
    payment_failure_count = event_counts.get("payment_failure",     0)
    payment_success_count = event_counts.get("payment_success",     0)
    notif_failed_count    = event_counts.get("notification_failed", 0)
    notif_sent_count      = event_counts.get("notification_sent",   0)
    api_request_count     = event_counts.get("api_request",         0)

    # ── Derived rates ─────────────────────────────────────────────────────────
    auth_total        = login_success_count + login_failure_count
    login_failure_rate = (login_failure_count / auth_total) if auth_total > 0 else 0.0

    payment_total        = payment_success_count + payment_failure_count + payment_timeout_count
    payment_timeout_rate = (payment_timeout_count / payment_total) if payment_total > 0 else 0.0
    payment_failure_rate = (payment_failure_count / payment_total) if payment_total > 0 else 0.0

    notif_total        = notif_sent_count + notif_failed_count
    notif_failure_rate = (notif_failed_count / notif_total) if notif_total > 0 else 0.0

    api_total          = api_request_count + high_latency_count
    high_latency_rate  = (high_latency_count / api_total) if api_total > 0 else 0.0

    # ── Latency stats ─────────────────────────────────────────────────────────
    latencies = [log["latency_ms"] for log in logs if log.get("latency_ms") is not None]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    max_latency = max(latencies) if latencies else 0.0

    if latencies:
        sorted_lat  = sorted(latencies)
        p95_idx     = int(0.95 * len(sorted_lat))
        p95_latency = sorted_lat[min(p95_idx, len(sorted_lat) - 1)]
    else:
        p95_latency = 0.0

    # ── Assemble ──────────────────────────────────────────────────────────────
    return {
        "window_start": _iso(window_start),
        "window_end":   _iso(window_end),

        "total_logs":   total,

        "error_rate":   round(error_rate, 4),
        "warn_rate":    round(warn_rate,  4),

        "login_failure_count": login_failure_count,
        "login_success_count": login_success_count,
        "login_failure_rate":  round(login_failure_rate, 4),

        "high_latency_count":  high_latency_count,
        "high_latency_rate":   round(high_latency_rate,  4),
        "api_request_count":   api_request_count,

        "payment_timeout_count": payment_timeout_count,
        "payment_failure_count": payment_failure_count,
        "payment_success_count": payment_success_count,
        "payment_timeout_rate":  round(payment_timeout_rate, 4),
        "payment_failure_rate":  round(payment_failure_rate, 4),

        "notif_failed_count": notif_failed_count,
        "notif_failure_rate": round(notif_failure_rate, 4),

        "avg_latency_ms": round(avg_latency, 2),
        "max_latency_ms": round(max_latency, 2),
        "p95_latency_ms": round(p95_latency, 2),

        "frac_auth":         round(service_fractions["auth-service"],         4),
        "frac_api_gateway":  round(service_fractions["api-gateway"],          4),
        "frac_payment":      round(service_fractions["payment-service"],       4),
        "frac_notification": round(service_fractions["notification-service"],  4),
    }


def get_all_windows(since: Optional[str] = None, until: Optional[str] = None) -> list[dict]:
    """
    Discover every 1-minute window that has logs between since and until,
    aggregate each one, return sorted oldest → newest.
    """
    conn = get_connection()
    row  = conn.execute("SELECT MIN(timestamp), MAX(timestamp) FROM logs").fetchone()
    conn.close()

    if not row or row[0] is None:
        return []

    db_min = _floor_to_minute(row[0])
    db_max = _floor_to_minute(row[1]) + datetime.timedelta(seconds=60)

    start = _floor_to_minute(since) if since else db_min
    end   = _floor_to_minute(until) if until else db_max

    windows, cursor = [], start
    while cursor < end:
        stats = aggregate_window(cursor)
        if stats:
            windows.append(stats)
        cursor += datetime.timedelta(seconds=60)

    return windows


def get_latest_window() -> Optional[dict]:
    """
    Aggregate the most recently completed 1-minute window.
    Used by the continuous detector loop.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    current_minute    = now.replace(second=0, microsecond=0)
    last_window_start = current_minute - datetime.timedelta(seconds=60)
    return aggregate_window(last_window_start)