"""
scripts/trigger_anomaly.py
Fires an anomaly scenario at the running ingestor for demo purposes.

Usage
-----
    python3 scripts/trigger_anomaly.py --scenario login_storm
    python3 scripts/trigger_anomaly.py --scenario latency_spike
    python3 scripts/trigger_anomaly.py --scenario payment_outage

    # Run for 3 minutes then stop
    python3 scripts/trigger_anomaly.py --scenario login_storm --duration 180

Options
-------
--scenario   login_storm | latency_spike | payment_outage   (required)
--url        ingestor base URL                               (default: http://localhost:7000)
--duration   seconds to run                                  (default: 120)
--interval   seconds between batches                         (default: 2)
"""

import sys
import json
import time
import argparse
import datetime
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "services" / "log-generator" / "scenarios"))

import login_storm
import latency_spike
import payment_outage

SCENARIOS = {
    "login_storm":    login_storm.generate,
    "latency_spike":  latency_spike.generate,
    "payment_outage": payment_outage.generate,
}

SCENARIO_DESC = {
    "login_storm":    "Brute force login failure storm — auth-service",
    "latency_spike":  "API gateway latency spike — api-gateway",
    "payment_outage": "Payment provider outage — payment-service + notification-service",
}


def send_batch(logs: list, url: str) -> dict:
    body = json.dumps(logs).encode()
    req  = urllib.request.Request(
        f"{url}/ingest/batch", data=body,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.URLError as e:
        return {"error": str(e)}


def wait_for_ingestor(url: str) -> bool:
    for _ in range(10):
        try:
            with urllib.request.urlopen(f"{url}/status", timeout=3) as r:
                if json.loads(r.read()).get("status") == "ok":
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


def main():
    parser = argparse.ArgumentParser(description="Trigger an anomaly scenario")
    parser.add_argument("--scenario", required=True, choices=list(SCENARIOS.keys()))
    parser.add_argument("--url",      default="http://localhost:7000")
    parser.add_argument("--duration", type=int,   default=120,
                        help="Seconds to run (default: 120)")
    parser.add_argument("--interval", type=float, default=2.0,
                        help="Seconds between batches (default: 2)")
    args = parser.parse_args()

    generate_fn = SCENARIOS[args.scenario]
    desc        = SCENARIO_DESC[args.scenario]

    print("=" * 60)
    print(f"  ANOMALY TRIGGER")
    print("=" * 60)
    print(f"  Scenario:  {args.scenario}")
    print(f"  What:      {desc}")
    print(f"  Duration:  {args.duration}s")
    print(f"  Target:    {args.url}")
    print()

    if not wait_for_ingestor(args.url):
        print("Could not reach ingestor. Is app.py running?")
        sys.exit(1)

    start_time = time.time()
    batch_num  = 0
    total_sent = 0

    print(f"[trigger] Firing {args.scenario} for {args.duration}s...\n")

    try:
        while time.time() - start_time < args.duration:
            logs   = generate_fn()
            result = send_batch(logs, args.url)
            batch_num  += 1
            accepted    = result.get("accepted", 0)
            total_sent += accepted

            ts = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] batch #{batch_num:03d} | {args.scenario} | "
                  f"accepted={accepted} | total={total_sent}", flush=True)

            if "error" in result:
                print(f"         ⚠ {result['error']}", flush=True)

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n[trigger] Stopped.")

    elapsed = int(time.time() - start_time)
    print(f"\n{'='*60}")
    print(f"  Anomaly scenario complete.")
    print(f"  Scenario:      {args.scenario}")
    print(f"  Batches sent:  {batch_num}")
    print(f"  Logs sent:     {total_sent}")
    print(f"  Duration:      {elapsed}s")
    print(f"{'='*60}")
    print(f"\n  The detector should have flagged these windows.")
    print(f"  Check results: GET http://localhost:7000/anomalies")


if __name__ == "__main__":
    main()