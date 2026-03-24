"""
generator.py
Main log generator — continuously sends logs to the ingestor-api.

Usage
-----
    # Normal traffic indefinitely
    python3 services/log-generator/generator.py

    # Normal traffic, 30 second bursts, then stop
    python3 services/log-generator/generator.py --mode normal --duration 30

    # Trigger a specific anomaly scenario for 60 seconds then revert to normal
    python3 services/log-generator/generator.py --mode login_storm
    python3 services/log-generator/generator.py --mode latency_spike
    python3 services/log-generator/generator.py --mode payment_outage

    # Custom ingestor URL
    python3 services/log-generator/generator.py --url http://localhost:7000

Options
-------
--mode      normal | login_storm | latency_spike | payment_outage  (default: normal)
--url       ingestor base URL                                        (default: http://localhost:7000)
--interval  seconds between each batch                               (default: 2)
--duration  run for N seconds then exit; 0 = run forever             (default: 0)
--burst     volume multiplier for normal mode (used for seeding)     (default: 1)
"""

import sys
import time
import json
import argparse
import datetime
import urllib.request
import urllib.error
from pathlib import Path

# Make scenarios importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scenarios import normal, login_storm, latency_spike, payment_outage

SCENARIO_MAP = {
    "normal":          normal.generate,
    "login_storm":     login_storm.generate,
    "latency_spike":   latency_spike.generate,
    "payment_outage":  payment_outage.generate,
}

SCENARIO_LABELS = {
    "normal":          "NORMAL",
    "login_storm":     "ANOMALY — login storm",
    "latency_spike":   "ANOMALY — latency spike",
    "payment_outage":  "ANOMALY — payment outage",
}


def send_batch(logs: list[dict], url: str) -> dict:
    """POST a batch of logs to /ingest/batch. Returns the response dict."""
    body = json.dumps(logs).encode()
    req = urllib.request.Request(
        f"{url}/ingest/batch",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "detail": e.read().decode()}
    except urllib.error.URLError as e:
        return {"error": str(e.reason)}


def wait_for_ingestor(url: str, retries: int = 10, delay: float = 2.0) -> bool:
    """Poll /status until the ingestor is up."""
    print(f"[generator] Waiting for ingestor at {url} ...", flush=True)
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(f"{url}/status", timeout=3) as r:
                data = json.loads(r.read())
                if data.get("status") == "ok":
                    print(f"[generator] Ingestor is up. ({data['total_logs_stored']} logs stored)", flush=True)
                    return True
        except Exception:
            pass
        print(f"[generator] Attempt {attempt}/{retries} failed, retrying in {delay}s...", flush=True)
        time.sleep(delay)
    return False


def run(mode: str, url: str, interval: float, duration: float, burst: int) -> None:
    if not wait_for_ingestor(url):
        print("[generator] ERROR: Could not reach ingestor. Is it running?", flush=True)
        sys.exit(1)

    generate_fn = SCENARIO_MAP[mode]
    label = SCENARIO_LABELS[mode]
    start_time = time.time()
    batch_num = 0

    print(f"[generator] Starting in mode: {label}", flush=True)
    print(f"[generator] Sending to: {url}", flush=True)
    print(f"[generator] Interval: {interval}s | Duration: {'∞' if duration == 0 else f'{duration}s'}", flush=True)
    print(f"[generator] Press Ctrl+C to stop.\n", flush=True)

    try:
        while True:
            elapsed = time.time() - start_time
            if duration > 0 and elapsed >= duration:
                print(f"\n[generator] Duration {duration}s reached. Stopping.", flush=True)
                break

            # normal.generate accepts burst kwarg; anomaly scenarios don't need it
            if mode == "normal":
                logs = generate_fn(burst=burst)
            else:
                logs = generate_fn()

            result = send_batch(logs, url)
            batch_num += 1

            accepted = result.get("accepted", "?")
            rejected = result.get("rejected", 0)
            ts = datetime.datetime.now().strftime("%H:%M:%S")

            status = "✓" if "error" not in result else "✗"
            print(
                f"[{ts}] {status} batch #{batch_num:04d} | {label} | "
                f"sent={len(logs)} accepted={accepted} rejected={rejected}",
                flush=True,
            )

            if "error" in result:
                print(f"         ERROR: {result['error']}", flush=True)

            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n[generator] Stopped after {batch_num} batches.", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Log Generator")
    parser.add_argument("--mode",     choices=list(SCENARIO_MAP.keys()), default="normal")
    parser.add_argument("--url",      default="http://localhost:7000")
    parser.add_argument("--interval", type=float, default=2.0,
                        help="Seconds between batches (default: 2)")
    parser.add_argument("--duration", type=float, default=0,
                        help="Stop after N seconds; 0 = run forever (default: 0)")
    parser.add_argument("--burst",    type=int, default=1,
                        help="Volume multiplier for normal mode (default: 1)")
    args = parser.parse_args()

    run(
        mode=args.mode,
        url=args.url,
        interval=args.interval,
        duration=args.duration,
        burst=args.burst,
    )


if __name__ == "__main__":
    main()