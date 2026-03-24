"""
storage.py
SQLite storage layer.

Schema
------
table: logs
  id            INTEGER  PRIMARY KEY AUTOINCREMENT
  timestamp     TEXT     NOT NULL   (ISO-8601, normalised)
  service_name  TEXT     NOT NULL
  host          TEXT     NOT NULL
  log_level     TEXT     NOT NULL
  event_type    TEXT     NOT NULL
  message       TEXT     NOT NULL
  user_id       TEXT
  ip            TEXT
  request_id    TEXT
  latency_ms    REAL
  transaction_id TEXT
  amount        REAL
  currency      TEXT
  channel       TEXT
  recipient     TEXT
  notification_id TEXT
  ingested_at   TEXT     NOT NULL   (server-side UTC time of ingestion)
"""

import sqlite3
import datetime
import json
import threading
from pathlib import Path
from typing import Any, Optional

# One global lock — SQLite in WAL mode handles concurrent reads fine,
# but writes from multiple threads need serialisation.
_write_lock = threading.Lock()


def _db_path() -> Path:
    """
    Resolve the database path.
    Stored at:  <repo_root>/data/raw/logs.db
    The path is computed relative to this file's location so it works
    regardless of the working directory the server is started from.
    """
    here = Path(__file__).resolve().parent          # services/ingestor-api/
    repo_root = here.parent.parent                  # repo root
    db_dir = repo_root / "data" / "raw"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "logs.db"


def get_connection() -> sqlite3.Connection:
    """Open a connection with sensible defaults."""
    conn = sqlite3.connect(str(_db_path()), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # safe concurrent access
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables and indexes if they don't exist yet."""
    conn = get_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp       TEXT    NOT NULL,
                service_name    TEXT    NOT NULL,
                host            TEXT    NOT NULL,
                log_level       TEXT    NOT NULL,
                event_type      TEXT    NOT NULL,
                message         TEXT    NOT NULL,
                user_id         TEXT,
                ip              TEXT,
                request_id      TEXT,
                latency_ms      REAL,
                transaction_id  TEXT,
                amount          REAL,
                currency        TEXT,
                channel         TEXT,
                recipient       TEXT,
                notification_id TEXT,
                ingested_at     TEXT    NOT NULL
            )
        """)

        # Indexes that the window aggregator queries heavily
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_timestamp
            ON logs (timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_service
            ON logs (service_name)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_event_type
            ON logs (event_type)
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS anomaly_results (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                window_start            TEXT    NOT NULL,
                window_end              TEXT    NOT NULL,
                anomaly_score           REAL    NOT NULL,
                is_anomalous            INTEGER NOT NULL,
                affected_services       TEXT,   -- JSON array
                top_contributing_patterns TEXT, -- JSON array
                metrics                 TEXT,   -- JSON object
                scored_at               TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_anomaly_window
            ON anomaly_results (window_start)
        """)
    conn.close()


_LOG_COLUMNS = (
    "timestamp", "service_name", "host", "log_level",
    "event_type", "message",
    "user_id", "ip", "request_id", "latency_ms",
    "transaction_id", "amount", "currency",
    "channel", "recipient", "notification_id",
)


def insert_log(log: dict[str, Any]) -> int:
    """
    Insert a single validated log event.
    Returns the new row id.
    """
    ingested_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    row = {col: log.get(col) for col in _LOG_COLUMNS}
    row["ingested_at"] = ingested_at

    placeholders = ", ".join(f":{col}" for col in row)
    cols = ", ".join(row.keys())
    sql = f"INSERT INTO logs ({cols}) VALUES ({placeholders})"

    with _write_lock:
        conn = get_connection()
        with conn:
            cur = conn.execute(sql, row)
            row_id = cur.lastrowid
        conn.close()
    return row_id


def insert_log_batch(logs: list[dict[str, Any]]) -> list[int]:
    """
    Insert multiple validated log events in a single transaction.
    Returns list of new row ids.
    """
    if not logs:
        return []

    ingested_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rows = []
    for log in logs:
        row = {col: log.get(col) for col in _LOG_COLUMNS}
        row["ingested_at"] = ingested_at
        rows.append(row)

    placeholders = ", ".join(f":{col}" for col in rows[0])
    cols = ", ".join(rows[0].keys())
    sql = f"INSERT INTO logs ({cols}) VALUES ({placeholders})"

    with _write_lock:
        conn = get_connection()
        with conn:
            ids = []
            for row in rows:
                cur = conn.execute(sql, row)
                ids.append(cur.lastrowid)
        conn.close()
    return ids


def query_logs(
    start: Optional[str] = None,
    end: Optional[str] = None,
    service: Optional[str] = None,
    log_level: Optional[str] = None,
    limit: int = 500,
) -> list[dict]:
    """
    Flexible log query used by both the window aggregator and the query API.
    All filters are optional.
    """
    conditions = []
    params: dict[str, Any] = {}

    if start:
        conditions.append("timestamp >= :start")
        params["start"] = start
    if end:
        conditions.append("timestamp < :end")
        params["end"] = end
    if service:
        conditions.append("service_name = :service")
        params["service"] = service
    if log_level:
        conditions.append("log_level = :log_level")
        params["log_level"] = log_level

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT * FROM logs {where} ORDER BY timestamp DESC LIMIT :limit"
    params["limit"] = limit

    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_logs() -> int:
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
    conn.close()
    return count


def insert_anomaly_result(result: dict[str, Any]) -> int:
    """Store one anomaly window result. Returns new row id."""
    scored_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    row = {
        "window_start":               result["window_start"],
        "window_end":                 result["window_end"],
        "anomaly_score":              result["anomaly_score"],
        "is_anomalous":               int(result["is_anomalous"]),
        "affected_services":          json.dumps(result.get("affected_services", [])),
        "top_contributing_patterns":  json.dumps(result.get("top_contributing_patterns", [])),
        "metrics":                    json.dumps(result.get("metrics", {})),
        "scored_at":                  scored_at,
    }
    sql = """
        INSERT INTO anomaly_results
            (window_start, window_end, anomaly_score, is_anomalous,
             affected_services, top_contributing_patterns, metrics, scored_at)
        VALUES
            (:window_start, :window_end, :anomaly_score, :is_anomalous,
             :affected_services, :top_contributing_patterns, :metrics, :scored_at)
    """
    with _write_lock:
        conn = get_connection()
        with conn:
            cur = conn.execute(sql, row)
            row_id = cur.lastrowid
        conn.close()
    return row_id


def query_anomaly_results(limit: int = 100) -> list[dict]:
    """Return recent anomaly results, newest first."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM anomaly_results ORDER BY window_start DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["affected_services"]         = json.loads(d["affected_services"] or "[]")
        d["top_contributing_patterns"] = json.loads(d["top_contributing_patterns"] or "[]")
        d["metrics"]                   = json.loads(d["metrics"] or "{}")
        d["is_anomalous"]              = bool(d["is_anomalous"])
        results.append(d)
    return results