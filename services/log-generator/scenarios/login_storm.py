"""
scenarios/login_storm.py
Anomaly: Login failure storm (brute force simulation).

What changes vs normal
----------------------
- auth login_failure rate jumps from ~5% → ~80%
- high volume of attempts from the same suspicious IPs
- api-gateway and other services remain normal
- this should be clearly detected as anomalous by the model
"""

import random
import datetime
import uuid


def _ts() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


ATTACKER_IPS = [
    "10.0.0.42",
    "10.0.0.43",
    "185.220.101.5",
    "185.220.101.6",
]


def generate() -> list[dict]:
    logs = []
    for _ in range(40):
        if random.random() < 0.80:
            logs.append({
                "timestamp": _ts(),
                "service_name": "auth-service",
                "host": "auth-service-1",
                "log_level": "ERROR",
                "event_type": "login_failure",
                "message": "Failed login attempt",
                "user_id": f"user_{random.randint(1, 500)}",   # many targets
                "ip": random.choice(ATTACKER_IPS),
            })
        else:
            logs.append({
                "timestamp": _ts(),
                "service_name": "auth-service",
                "host": "auth-service-1",
                "log_level": "INFO",
                "event_type": "login_success",
                "message": "Successful login",
                "user_id": random.choice(["alice", "bob", "carol"]),
                "ip": f"192.168.1.{random.randint(1, 50)}",
            })
    for _ in range(15):
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
    for _ in range(8):
        logs.append({
            "timestamp": _ts(),
            "service_name": "payment-service",
            "host": "payment-service-1",
            "log_level": "INFO",
            "event_type": "payment_success",
            "message": "Payment processed",
            "user_id": random.choice(["alice", "bob", "carol"]),
            "transaction_id": str(uuid.uuid4()),
            "amount": round(random.uniform(5, 200), 2),
            "currency": "USD",
        })
    for _ in range(6):
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