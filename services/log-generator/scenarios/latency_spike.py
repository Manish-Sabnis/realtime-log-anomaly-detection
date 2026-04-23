"""
scenarios/latency_spike.py
Anomaly: API gateway latency spike.

What changes vs normal
----------------------
- api-gateway latency jumps from ~80-200ms → 1500-4000ms
- high_latency event rate spikes from ~5% → ~70%
- auth and payment services remain normal
- simulates a slow upstream dependency or network congestion
"""

import random
import datetime
import uuid


def _ts() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def generate() -> list[dict]:
    logs = []
    for _ in range(30):
        if random.random() < 0.95:
            logs.append({
                "timestamp": _ts(),
                "service_name": "auth-service",
                "host": "auth-service-1",
                "log_level": "INFO",
                "event_type": "login_success",
                "message": "Successful login",
                "user_id": random.choice(["alice", "bob", "carol", "dave"]),
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
                "ip": "192.168.1.99",
            })
    for _ in range(90):
        if random.random() < 0.70:
            logs.append({
                "timestamp": _ts(),
                "service_name": "api-gateway",
                "host": "api-gateway-1",
                "log_level": "WARN",
                "event_type": "high_latency",
                "message": "High latency request",
                "request_id": str(uuid.uuid4()),
                "latency_ms": random.randint(1500, 4000),
            })
        else:
            logs.append({
                "timestamp": _ts(),
                "service_name": "api-gateway",
                "host": "api-gateway-1",
                "log_level": "INFO",
                "event_type": "api_request",
                "message": "API request handled",
                "request_id": str(uuid.uuid4()),
                "latency_ms": random.randint(60, 200),
            })
    for _ in range(24):
        logs.append({
            "timestamp": _ts(),
            "service_name": "payment-service",
            "host": "payment-service-1",
            "log_level": "INFO",
            "event_type": "payment_success",
            "message": "Payment processed",
            "user_id": random.choice(["alice", "bob"]),
            "transaction_id": str(uuid.uuid4()),
            "amount": round(random.uniform(5, 200), 2),
            "currency": "USD",
        })

    for _ in range(18):
        logs.append({
            "timestamp": _ts(),
            "service_name": "notification-service",
            "host": "notification-service-1",
            "log_level": "INFO",
            "event_type": "notification_sent",
            "message": "Notification delivered",
            "notification_id": str(uuid.uuid4()),
            "channel": "email",
            "recipient": "user@example.com",
        })

    random.shuffle(logs)
    return logs