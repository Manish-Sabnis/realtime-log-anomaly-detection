"""
scenarios/normal.py
Normal baseline traffic across all 4 services.

Characteristics
---------------
- auth:        ~95% login_success, ~5% login_failure
- api-gateway: mostly api_request, occasional high_latency (<5%), latency 80-200ms
- payment:     ~97% success, ~2% failure, ~1% timeout
- notification: ~95% sent, ~5% failed
"""

import random
import datetime
import uuid


def _ts() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _users():
    return random.choice(["alice", "bob", "carol", "dave", "eve", "frank"])


def auth_logs(n: int = 10) -> list[dict]:
    logs = []
    for _ in range(n):
        if random.random() < 0.95:
            logs.append({
                "timestamp": _ts(),
                "service_name": "auth-service",
                "host": "auth-service-1",
                "log_level": "INFO",
                "event_type": "login_success",
                "message": "Successful login",
                "user_id": _users(),
                "ip": f"192.168.1.{random.randint(1, 50)}",
            })
        else:
            logs.append({
                "timestamp": _ts(),
                "service_name": "auth-service",
                "host": "auth-service-1",
                "log_level": "ERROR",
                "event_type": "login_failure",
                "message": "Failed login attempt",
                "user_id": "unknown",
                "ip": f"192.168.1.{random.randint(1, 50)}",
            })
    return logs


def api_logs(n: int = 15) -> list[dict]:
    logs = []
    for _ in range(n):
        latency = random.randint(60, 200)
        if random.random() < 0.95:
            logs.append({
                "timestamp": _ts(),
                "service_name": "api-gateway",
                "host": "api-gateway-1",
                "log_level": "INFO",
                "event_type": "api_request",
                "message": "API request handled",
                "request_id": str(uuid.uuid4()),
                "latency_ms": latency,
            })
        else:
            logs.append({
                "timestamp": _ts(),
                "service_name": "api-gateway",
                "host": "api-gateway-1",
                "log_level": "WARN",
                "event_type": "high_latency",
                "message": "High latency request",
                "request_id": str(uuid.uuid4()),
                "latency_ms": random.randint(600, 900),
            })
    return logs


def payment_logs(n: int = 8) -> list[dict]:
    logs = []
    for _ in range(n):
        r = random.random()
        if r < 0.97:
            logs.append({
                "timestamp": _ts(),
                "service_name": "payment-service",
                "host": "payment-service-1",
                "log_level": "INFO",
                "event_type": "payment_success",
                "message": "Payment processed",
                "user_id": _users(),
                "transaction_id": str(uuid.uuid4()),
                "amount": round(random.uniform(5, 200), 2),
                "currency": "USD",
            })
        elif r < 0.99:
            logs.append({
                "timestamp": _ts(),
                "service_name": "payment-service",
                "host": "payment-service-1",
                "log_level": "ERROR",
                "event_type": "payment_failure",
                "message": "Payment failed",
                "user_id": _users(),
                "transaction_id": str(uuid.uuid4()),
                "amount": round(random.uniform(5, 200), 2),
                "currency": "USD",
            })
        else:
            logs.append({
                "timestamp": _ts(),
                "service_name": "payment-service",
                "host": "payment-service-1",
                "log_level": "ERROR",
                "event_type": "payment_timeout",
                "message": "Payment provider timeout",
                "user_id": _users(),
                "transaction_id": str(uuid.uuid4()),
                "amount": round(random.uniform(5, 200), 2),
                "currency": "USD",
            })
    return logs


def notification_logs(n: int = 6) -> list[dict]:
    logs = []
    for _ in range(n):
        if random.random() < 0.95:
            logs.append({
                "timestamp": _ts(),
                "service_name": "notification-service",
                "host": "notification-service-1",
                "log_level": "INFO",
                "event_type": "notification_sent",
                "message": "Notification delivered",
                "notification_id": str(uuid.uuid4()),
                "channel": random.choice(["email", "sms"]),
                "recipient": f"{_users()}@example.com",
            })
        else:
            logs.append({
                "timestamp": _ts(),
                "service_name": "notification-service",
                "host": "notification-service-1",
                "log_level": "ERROR",
                "event_type": "notification_failed",
                "message": "Notification delivery failed",
                "notification_id": str(uuid.uuid4()),
                "channel": random.choice(["email", "sms"]),
                "recipient": f"{_users()}@example.com",
            })
    return logs


def generate(burst: int = 1) -> list[dict]:
    """
    Generate one round of normal traffic across all services.
    burst multiplies volume (used during baseline seeding).
    """
    logs = []
    logs += auth_logs(n=10 * burst)
    logs += api_logs(n=15 * burst)
    logs += payment_logs(n=8 * burst)
    logs += notification_logs(n=6 * burst)
    random.shuffle(logs)
    return logs