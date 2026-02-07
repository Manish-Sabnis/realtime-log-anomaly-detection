# Log Generator Service

## Purpose
This component simulates a multi-service production environment by generating structured log events that follow the project’s log schema. The generated logs are used to test ingestion, anomaly detection, and monitoring components under both normal and abnormal conditions.

## Simulated Services

1. `auth-service`
- Handles user authentication and authorization events.

2. `api-gateway`
- Acts as the entry point for all external requests.

3. `payment-service`
- Processes payment transactions and communicates with external payment providers.

4. `notification-service`
- Sends asynchronous notifications via email or SMS.

## Normal Operating Behavior
Under normal conditions, each service emits a steady stream of INFO-level logs, occasional WARN-level logs, and rare ERROR-level logs. Log messages follow a stable set of templates with variable parameters such as user IDs, request IDs, and timestamps.

## Failure Modes (Intentional Anomalies)
1. `Authentication Failure Storm`
- A sudden increase in failed login attempts.
- Elevated ERROR log frequency in auth-service.
- Short time window (e.g., 2–5 minutes).

2. `API Latency Degradation`
- Gradual increase in request latency warnings.
- WARN logs become dominant in api-gateway.

3. `Payment Provider Timeout`
- Repeated timeout errors when communicating with external services.
- ERROR logs cluster in `payment-service`.

## Control Parameters
The log generator supports configurable parameters to control log emission rate, active failure mode, and duration of abnormal behavior. This allows repeatable experiments and evaluation of anomaly detection latency.

## Non-Goals
This service does not aim to accurately simulate real business logic or system performance. Its sole purpose is to generate realistic log patterns for experimentation and evaluation.