"""
schemas.py
Log Schema v1 — validation layer.
Every incoming log must pass through validate_log() before storage.
"""

import datetime
from typing import Any

VALID_LOG_LEVELS = {"INFO", "WARN", "ERROR", "DEBUG"}
VALID_SERVICES   = {"auth-service", "api-gateway", "payment-service", "notification-service"}
VALID_EVENT_TYPES = {
    # auth-service
    "login_success", "login_failure", "token_refresh", "logout",
    # api-gateway
    "api_request", "high_latency", "rate_limit_exceeded", "api_error",
    # payment-service
    "payment_success", "payment_failure", "payment_timeout", "refund_issued",
    # notification-service
    "notification_sent", "notification_failed", "notification_queued",
}

# Optional metadata fields and their expected Python types
OPTIONAL_FIELD_TYPES: dict[str, type] = {
    "user_id":          str,
    "ip":               str,
    "request_id":       str,
    "latency_ms":       (int, float),
    "transaction_id":   str,
    "amount":           (int, float),
    "currency":         str,
    "channel":          str,
    "recipient":        str,
    "notification_id":  str,
}


class ValidationError(Exception):
    """Raised when a log event fails schema validation."""
    pass


def validate_log(data: dict[str, Any]) -> dict[str, Any]:
    """
    Validates and normalises a raw log dict against Log Schema v1.

    Returns the cleaned log dict on success.
    Raises ValidationError with a descriptive message on failure.
    """
    if not isinstance(data, dict):
        raise ValidationError("Log must be a JSON object.")



    required = ("timestamp", "service_name", "host", "log_level", "event_type", "message")
    missing = [f for f in required if f not in data]
    if missing:
        raise ValidationError(f"Missing required fields: {missing}")

    # timestamp — must be parseable ISO-8601
    ts_raw = data["timestamp"]
    if not isinstance(ts_raw, str):
        raise ValidationError("Field 'timestamp' must be a string.")
    try:
        # Accept both 'Z' suffix and '+00:00'
        ts_raw_normalised = ts_raw.replace("Z", "+00:00")
        datetime.datetime.fromisoformat(ts_raw_normalised)
    except ValueError:
        raise ValidationError(f"Field 'timestamp' is not valid ISO-8601: {ts_raw!r}")

    # service_name
    service = data["service_name"]
    if not isinstance(service, str):
        raise ValidationError("Field 'service_name' must be a string.")
    if service not in VALID_SERVICES:
        raise ValidationError(
            f"Unknown service_name {service!r}. Must be one of: {sorted(VALID_SERVICES)}"
        )

    # host
    if not isinstance(data["host"], str) or not data["host"].strip():
        raise ValidationError("Field 'host' must be a non-empty string.")

    # log_level
    level = data["log_level"]
    if level not in VALID_LOG_LEVELS:
        raise ValidationError(
            f"Invalid log_level {level!r}. Must be one of: {sorted(VALID_LOG_LEVELS)}"
        )

    # event_type
    event = data["event_type"]
    if not isinstance(event, str):
        raise ValidationError("Field 'event_type' must be a string.")
    if event not in VALID_EVENT_TYPES:
        raise ValidationError(
            f"Unknown event_type {event!r}. Must be one of: {sorted(VALID_EVENT_TYPES)}"
        )

    # message
    if not isinstance(data["message"], str) or not data["message"].strip():
        raise ValidationError("Field 'message' must be a non-empty string.")


    for field, expected_type in OPTIONAL_FIELD_TYPES.items():
        if field in data:
            if not isinstance(data[field], expected_type):
                raise ValidationError(
                    f"Optional field {field!r} must be of type "
                    f"{expected_type if isinstance(expected_type, type) else [t.__name__ for t in expected_type]}."
                )
            # Basic sanity: numeric values must be non-negative
            if isinstance(data[field], (int, float)) and data[field] < 0:
                raise ValidationError(f"Field {field!r} must be non-negative.")



    cleaned = {k: v for k, v in data.items()}
    cleaned["timestamp"] = ts_raw.replace("Z", "+00:00")   
    return cleaned


def validate_log_batch(logs: list) -> tuple[list[dict], list[dict]]:
    """
    Validates a list of log dicts.
    Returns (valid_logs, errors) where errors is a list of
    {"index": i, "error": "message", "raw": original_item}.
    """
    valid, errors = [], []
    for i, item in enumerate(logs):
        try:
            valid.append(validate_log(item))
        except ValidationError as e:
            errors.append({"index": i, "error": str(e), "raw": item})
    return valid, errors