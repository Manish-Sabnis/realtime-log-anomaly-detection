# Real-Time Log Anomaly Detection

A window-based anomaly detection system for application logs. It ingests structured logs from simulated microservices, aggregates them into 1-minute windows, and uses an Isolation Forest model to detect abnormal system behaviour in real time.

## How It Works

The system has two layers.

The first layer is the application layer. A log generator simulates four microservices producing realistic structured logs: auth-service, api-gateway, payment-service, and notification-service. These logs are sent to an ingestion API which validates and stores them in a SQLite database.

The second layer is the detection layer. A window aggregator groups logs into 1-minute windows and computes behavioural statistics: error rates, login failure rates, latency percentiles, payment timeout rates, and service distribution. These statistics become feature vectors that an Isolation Forest model scores for anomalousness. Results are stored and exposed via API.

The key design decision is that the model does not analyse individual logs. It analyses windows of behaviour. A single failed login is noise. Sixty percent of logins failing in one minute is a signal.

## Architecture

```
Log Generator
     |
     | HTTP POST /ingest/batch
     v
Ingestor API (port 7000)
     |
     v
SQLite Database (data/raw/logs.db)
     |
     v
Window Aggregator (1-minute windows)
     |
     v
Feature Extractor (14 rate-based features)
     |
     v
Isolation Forest Model
     |
     v
Anomaly Results (GET /anomalies)
```

## Repository Structure

```
realtime-log-anomaly-detection/
|
+-- services/
|   +-- ingestor-api/          # HTTP server, schema validation, SQLite storage
|   +-- log-generator/         # Simulated microservice traffic
|       +-- scenarios/         # normal, login_storm, latency_spike, payment_outage
|   +-- anomaly-detector/      # Feature extraction, model, inference
|
+-- pipelines/
|   +-- train_baseline.py      # Trains and saves the Isolation Forest
|   +-- run_detector.py        # Continuous scoring loop
|
+-- scripts/
|   +-- seed_normal_logs.py    # Seeds baseline training data
|   +-- trigger_anomaly.py     # Fires anomaly scenarios for demo
|   +-- run_demo.sh            # Starts the full system
|   +-- stop_demo.sh           # Stops everything
|
+-- data/
|   +-- models/                # Saved model artifacts (.pkl)
|   +-- raw/                   # SQLite database (gitignored)
|
+-- docs/                      # Design documents and schema definitions
+-- experiments/               # Notebooks for model exploration
```

## Setup

**Requirements**

Python 3.10 or higher. All dependencies are pure Python with no system-level requirements beyond that.

```bash
pip install -r requirements.txt
```

**Dependencies**

The ingestor API uses only the Python standard library. The detector requires scikit-learn, numpy, and pandas. The log generator uses only the standard library plus requests.

## Running the Full Demo

The demo has five steps. Run them in order.

**Step 1: Start the ingestor API**

```bash
python3 services/ingestor-api/app.py
```

This starts the HTTP server on port 7000 and initialises the database. Leave it running in its own terminal.

**Step 2: Wipe any existing data**

If you have run the system before, clear the database before seeding fresh baseline data. Mixing old anomaly windows into training data will corrupt the model.

```bash
python3 - <<'EOF'
import sqlite3
conn = sqlite3.connect("data/raw/logs.db")
conn.execute("DELETE FROM logs")
conn.execute("DELETE FROM anomaly_results")
conn.commit()
conn.close()
print("done")
EOF
```

**Step 3: Seed baseline data**

Run the seeder for at least 20 minutes. This generates clean normal traffic that the model will learn from. Each minute of seeding produces one training window.

```bash
python3 scripts/seed_normal_logs.py --duration 1200 --burst 3
```

Note the UTC start and end timestamps printed in the window table. You will need them in the next step.

**Step 4: Train the model**

Pass the UTC time range of your seeding run. Do not include the first or last partial window.

```bash
python3 pipelines/train_baseline.py \
  --since 2026-04-23T11:40:00 \
  --until 2026-04-23T12:10:00
```

A healthy training run shows at most 2 to 3 windows flagged as anomalous out of 20. If significantly more are flagged, the training data is contaminated with anomaly windows or has inconsistent volume. Wipe the database and reseed.

**Step 5: Start the detector**

```bash
python3 pipelines/run_detector.py --interval 60
```

The detector scores the most recently completed 1-minute window every 60 seconds and prints results to stdout. It also writes results to the database, accessible via the API.

**Step 6: Trigger anomaly scenarios**

In a separate terminal, fire one of the three anomaly scenarios:

```bash
python3 scripts/trigger_anomaly.py --scenario login_storm --duration 120
python3 scripts/trigger_anomaly.py --scenario latency_spike --duration 120
python3 scripts/trigger_anomaly.py --scenario payment_outage --duration 120
```

After triggering, wait up to 60 seconds for the detector to score the anomaly window. You will see output like:

```
[17:49:56] ANOMALY  score=0.9712  window=2026-04-23T12:18:00 -> 2026-04-23T12:19:00
           Affected services: auth-service
           Top patterns:
             login failure rate        deviation=84.75x
             overall error rate        deviation=93.53x
           Login failures:  baseline=0.051  current=0.593
```

## API Reference

All endpoints are on port 7000.

**GET /status**

Health check. Returns total log count.

```json
{
  "status": "ok",
  "service": "ingestor-api",
  "total_logs_stored": 45231
}
```

**POST /ingest**

Ingest a single log event. Body must be a valid JSON object matching Log Schema v1.

**POST /ingest/batch**

Ingest up to 500 log events in one request. Body must be a JSON array.

Returns a 207 Multi-Status response with counts of accepted and rejected events.

**GET /logs**

Query stored logs. Supports query parameters: `start`, `end`, `service`, `log_level`, `limit`.

**GET /anomalies**

Returns recent anomaly window results, newest first.

```json
{
  "count": 2,
  "anomalies": [
    {
      "window_start": "2026-04-23T12:18:00+00:00",
      "window_end":   "2026-04-23T12:19:00+00:00",
      "anomaly_score": 0.9712,
      "is_anomalous": true,
      "affected_services": ["auth-service"],
      "top_contributing_patterns": [
        {
          "feature": "login_failure_rate",
          "label": "login failure rate",
          "deviation_ratio": 84.75
        }
      ],
      "metrics": {
        "baseline_error_rate": 0.027,
        "current_error_rate": 0.265,
        "baseline_login_failure_rate": 0.051,
        "current_login_failure_rate": 0.593,
        "baseline_latency_ms": 159.3,
        "current_latency_ms": 150.2,
        "baseline_payment_timeout_rate": 0.010,
        "current_payment_timeout_rate": 0.005
      }
    }
  ]
}
```

## Log Schema v1

Every log event must be a JSON object with these required fields:

| Field | Type | Values |
|---|---|---|
| timestamp | string | ISO-8601 UTC |
| service_name | string | auth-service, api-gateway, payment-service, notification-service |
| host | string | any non-empty string |
| log_level | string | INFO, WARN, ERROR, DEBUG |
| event_type | string | see list below |
| message | string | any non-empty string |

Valid event types: `login_success`, `login_failure`, `token_refresh`, `logout`, `api_request`, `high_latency`, `rate_limit_exceeded`, `api_error`, `payment_success`, `payment_failure`, `payment_timeout`, `refund_issued`, `notification_sent`, `notification_failed`, `notification_queued`.

Optional metadata fields: `user_id`, `ip`, `request_id`, `latency_ms`, `transaction_id`, `amount`, `currency`, `channel`, `recipient`, `notification_id`.

## Anomaly Scenarios

**login_storm**

Simulates a brute force attack. Login failure rate jumps from baseline 5% to roughly 75 to 80%. Detected via `login_failure_rate` and `error_rate` deviations.

**latency_spike**

Simulates a slow upstream dependency. API gateway high-latency event rate jumps from 5% to 70%. Latency values spike from 80-200ms to 1500-4000ms. Detected via `high_latency_rate` and `avg_latency_ms` deviations.

**payment_outage**

Simulates a payment provider going down. Payment timeout rate jumps from 1% to 60%. Payment failure rate jumps from 2% to 35%. Notification failures also spike as delivery receipts cannot be sent. Detected via `payment_timeout_rate` and `payment_failure_rate` deviations.

## Model Details

**Algorithm:** Isolation Forest (scikit-learn)

**Features:** 14 rate-based features. Raw counts were intentionally excluded to make the model robust to varying log volumes across windows.

```
error_rate, warn_rate,
login_failure_rate,
high_latency_rate,
payment_timeout_rate, payment_failure_rate,
notif_failure_rate,
avg_latency_ms, max_latency_ms, p95_latency_ms,
frac_auth, frac_api_gateway, frac_payment, frac_notification
```

**Window size:** 60 seconds

**Training data:** Clean normal traffic only. Minimum 15 windows recommended, 20+ preferred.

**Anomaly threshold:** 0.75 on a 0 to 1 scale. Scores above this value are flagged as anomalous.

**Scoring:** Raw Isolation Forest scores are normalised using the mean and standard deviation of training scores, then clipped to the 0 to 1 range. This makes the threshold stable across datasets of different sizes.

## Important Operational Notes

**Training data must be clean.** If anomaly windows are mixed into training data, the model learns that anomalies are normal and inverts its scoring. Always wipe the database and reseed from scratch before training.

**Timestamps in the database are UTC.** The seeder and generator stamp logs with the system clock in UTC. If your machine is not UTC, the window timestamps will appear offset from your local time. Use the window table printed by `train_baseline.py` to identify the correct UTC range for the `--since` and `--until` flags.

**The model does not auto-retrain.** After triggering anomaly scenarios, the anomaly windows are stored in the database. If you retrain without filtering the time range, those windows will contaminate the new baseline. Always use `--since` and `--until` when retraining.

**The detector must be restarted after retraining.** It loads the model once at startup. Kill and restart `run_detector.py` after running `train_baseline.py`.
