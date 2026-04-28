"""
pipelines/run_detector.py
Continuous anomaly detection loop.

What it does
------------
Every 60 seconds:
  1. Aggregates the last completed 1-minute window
  2. Scores it with the trained Isolation Forest
  3. Builds the full anomaly output (schema v1)
  4. Stores the result in the database (anomaly_results table)
  5. Prints a live summary to stdout

Usage
-----
    python3 pipelines/run_detector.py

    # Custom model path
    python3 pipelines/run_detector.py --model-path data/models/my_model.pkl

    # Faster polling for demos (check every 10 seconds)
    python3 pipelines/run_detector.py --interval 10
"""

import sys
import time
import json
import argparse
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "services" / "anomaly-detector"))
sys.path.insert(0, str(ROOT / "services" / "ingestor-api"))

from window_aggregator import get_latest_window, aggregate_window
from feature_extractor import extract
from model import AnomalyModel
from inference import score_window
from storage import insert_anomaly_result


def _now_str() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


def _print_result(result: dict) -> None:
    """Pretty-print one anomaly result to stdout."""
    flag  = "ANOMALY" if result["is_anomalous"] else "normal "
    score = result["anomaly_score"]
    ws    = result["window_start"]
    we    = result["window_end"]

    print(f"\n[{_now_str()}] {flag}  score={score:.4f}  window={ws} → {we}")

    if result["is_anomalous"]:
        if result["affected_services"]:
            print(f"           Affected services: {', '.join(result['affected_services'])}")

        if result["top_contributing_patterns"]:
            print("           Top patterns:")
            for p in result["top_contributing_patterns"]:
                print(f"             • {p['label']:<35} deviation={p['deviation_ratio']:.2f}x")

        m = result["metrics"]
        print(f"           Error rate:      baseline={m['baseline_error_rate']:.3f}  "
              f"current={m['current_error_rate']:.3f}")
        print(f"           Login failures:  baseline={m['baseline_login_failure_rate']:.3f}  "
              f"current={m['current_login_failure_rate']:.3f}")
        print(f"           Avg latency:     baseline={m['baseline_latency_ms']:.1f}ms  "
              f"current={m['current_latency_ms']:.1f}ms")
        print(f"           Payment timeouts:baseline={m['baseline_payment_timeout_rate']:.3f}  "
              f"current={m['current_payment_timeout_rate']:.3f}")


def run(model_path: Path, interval: int) -> None:

    # ── Load model ────────────────────────────────────────────────────────────
    print("=" * 60)
    print("  Anomaly Detector — Continuous Mode")
    print("=" * 60)

    model = AnomalyModel(model_path=model_path)
    try:
        model.load()
        print(f"[detector] Model loaded from: {model.model_path}")
    except FileNotFoundError as e:
        print(f"\n{e}")
        sys.exit(1)

    print(f"[detector] Anomaly threshold: {model.threshold}")
    print(f"[detector] Polling interval:  {interval}s")
    print(f"[detector] Press Ctrl+C to stop.\n")

    seen_windows: set[str] = set()   # avoid scoring the same window twice

    try:
        while True:
            window = get_latest_window()

            if window is None:
                print(f"[{_now_str()}] No logs in last window. Waiting...")
                time.sleep(interval)
                continue

            ws = window["window_start"]

            if ws in seen_windows:
                # Already scored — wait for next window
                time.sleep(interval)
                continue

            seen_windows.add(ws)

            # ── Score ─────────────────────────────────────────────────────────
            try:
                result = score_window(window, model)
            except Exception as e:
                print(f"[{_now_str()}] Scoring error: {e}")
                time.sleep(interval)
                continue

            # ── Store result ──────────────────────────────────────────────────
            try:
                insert_anomaly_result(result)
            except Exception as e:
                print(f"[{_now_str()}] Storage error: {e}")

            # ── Print ─────────────────────────────────────────────────────────
            _print_result(result)

            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n[detector] Stopped.")


def main():
    parser = argparse.ArgumentParser(description="Continuous anomaly detector")
    parser.add_argument("--model-path", type=str, default=None)
    parser.add_argument("--interval",   type=int, default=60,
                        help="Seconds between window checks (default: 60)")
    args = parser.parse_args()

    model_path = Path(args.model_path) if args.model_path else None
    run(model_path=model_path, interval=args.interval)


if __name__ == "__main__":
    main()