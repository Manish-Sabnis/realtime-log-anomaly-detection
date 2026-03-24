"""
scenarios/payment_outage.py
Anomaly: Payment service outage.

What changes vs normal
----------------------
- payment_timeout rate jumps from ~1% → ~60%
- payment_failure rate jumps from ~2% → ~35%
- payment_success drops to ~5%
- notification_failed spikes (delivery receipts failing downstream)
- auth and api-gateway remain normal
- simulates a payment provider going down
"""

import random
import datetime
import uuid


def _ts() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def generate() -> list[dict]:
    logs = []
    for _ in range(10):
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

    for _ in range(25):
        r = random.random()
        if r < 0.60:
            logs.append({
                "timestamp": _ts(),
                "service_name": "payment-service",
                "host": "payment-service-1",
                "log_level": "ERROR",
                "event_type": "payment_timeout",
                "message": "Payment provider timeout",
                "user_id": random.choice(["alice", "bob", "carol", "dave", "eve"]),
                "transaction_id": str(uuid.uuid4()),
                "amount": round(random.uniform(5, 500), 2),
                "currency": "USD",
            })
        elif r < 0.95:
            logs.append({
                "timestamp": _ts(),
                "service_name": "payment-service",
                "host": "payment-service-1",
                "log_level": "ERROR",
                "event_type": "payment_failure",
                "message": "Payment failed",
                "user_id": random.choice(["alice", "bob", "carol", "dave", "eve"]),
                "transaction_id": str(uuid.uuid4()),
                "amount": round(random.uniform(5, 500), 2),
                "currency": "USD",
            })
        else:
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

    for _ in range(10):
        if random.random() < 0.70:
            logs.append({
                "timestamp": _ts(),
                "service_name": "notification-service",
                "host": "notification-service-1",
                "log_level": "ERROR",
                "event_type": "notification_failed",
                "message": "Notification delivery failed",
                "notification_id": str(uuid.uuid4()),
                "channel": random.choice(["email", "sms"]),
                "recipient": f"user{random.randint(1,100)}@example.com",
            })
        else:
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