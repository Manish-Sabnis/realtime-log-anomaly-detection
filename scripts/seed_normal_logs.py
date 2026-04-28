"""
scripts/seed_normal_logs.py
Seeds normal baseline logs into the database for model training.

What it does
------------
1. Starts sending normal traffic to the ingestor
2. Runs for a set duration (default 5 minutes)
3. Prints a summary of windows created
4. Tells you exactly what to run next

Usage
-----
    python3 scripts/seed_normal_logs.py
    python3 scripts/seed_normal_logs.py --duration 300 --burst 3
    python3 scripts/seed_normal_logs.py --url http://localhost:7000
"""

import sys
import json
import time
import argparse
import datetime
import random
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "services" / "log-generator" / "scenarios"))
sys.path.insert(0, str(ROOT / "services" / "ingestor-api"))

import normal


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
    print(f"[seed] Waiting for ingestor at {url} ...", flush=True)
    for attempt in range(15):
        try:
            with urllib.request.urlopen(f"{url}/status", timeout=3) as r:
                data = json.loads(r.read())
                if data.get("status") == "ok":
                    print(f"[seed] Ingestor is up. ({data['total_logs_stored']} logs already stored)", flush=True)
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


def main():
    parser = argparse.ArgumentParser(description="Seed normal baseline logs")
    parser.add_argument("--url",      default="http://localhost:7000")
    parser.add_argument("--duration", type=int, default=300,
                        help="Seconds to run (default: 300 = 5 minutes)")
    parser.add_argument("--burst",    type=int, default=3,
                        help="Log volume multiplier (default: 3 = ~117 logs/batch)")
    parser.add_argument("--interval", type=float, default=2.0,
                        help="Seconds between batches (default: 2)")
    args = parser.parse_args()

    print("=" * 60)
    print("  Baseline Seeder")
    print("=" * 60)
    print(f"  Duration:  {args.duration}s (~{args.duration // 60} minutes)")
    print(f"  Burst:     {args.burst} (~{39 * args.burst} logs/batch)")
    print(f"  Interval:  {args.interval}s")
    print(f"  Target:    {args.url}")
    print(f"  Expected windows: ~{args.duration // 60}")
    print()

    if not wait_for_ingestor(args.url):
        print("\nCould not reach ingestor. Is app.py running?")
        print("   Run: python3 services/ingestor-api/app.py")
        sys.exit(1)

    start_time  = time.time()
    batch_num   = 0
    total_sent  = 0

    print(f"\n[seed] Sending normal traffic for {args.duration}s...\n")

    try:
        while time.time() - start_time < args.duration:
            logs   = normal.generate(burst=args.burst)
            result = send_batch(logs, args.url)
            batch_num  += 1
            accepted    = result.get("accepted", 0)
            total_sent += accepted

            elapsed  = int(time.time() - start_time)
            ts       = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] batch #{batch_num:03d} | accepted={accepted} | "
                  f"total={total_sent} | elapsed={elapsed}s", flush=True)

            if "error" in result:
                print(f"         ⚠ {result['error']}", flush=True)

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n[seed] Interrupted.")

    elapsed = int(time.time() - start_time)
    print(f"\n{'='*60}")
    print(f"  Seeding complete.")
    print(f"  Batches sent:  {batch_num}")
    print(f"  Logs accepted: {total_sent}")
    print(f"  Time elapsed:  {elapsed}s")
    print(f"{'='*60}")
    print(f"\nNext step — train the model:")
    print(f"   python3 pipelines/train_baseline.py")


if __name__ == "__main__":
    main()