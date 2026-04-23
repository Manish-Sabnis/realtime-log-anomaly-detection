"""
pipelines/train_baseline.py
Training pipeline — run this once to build the Isolation Forest baseline model.

What it does
------------
1. Reads all logs from data/raw/logs.db
2. Aggregates them into 1-minute windows
3. Extracts feature vectors
4. Trains an Isolation Forest
5. Saves the model to data/models/isolation_forest.pkl

Usage
-----
    python3 pipelines/train_baseline.py

    # Only use logs from a specific time range
    python3 pipelines/train_baseline.py --since 2026-04-01T00:00:00 --until 2026-04-02T00:00:00

    # Save model to a custom path
    python3 pipelines/train_baseline.py --model-path data/models/my_model.pkl
"""

import sys
import argparse
from pathlib import Path

# Make sibling services importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "services" / "anomaly-detector"))
sys.path.insert(0, str(ROOT / "services" / "ingestor-api"))

from window_aggregator import get_all_windows
from feature_extractor import extract_batch, feature_names, describe
from model import AnomalyModel


def main():
    parser = argparse.ArgumentParser(description="Train baseline anomaly model")
    parser.add_argument("--since",      type=str, default=None,
                        help="Only use logs after this ISO-8601 timestamp")
    parser.add_argument("--until",      type=str, default=None,
                        help="Only use logs before this ISO-8601 timestamp")
    parser.add_argument("--model-path", type=str, default=None,
                        help="Where to save the model (default: data/models/isolation_forest.pkl)")
    parser.add_argument("--describe",   action="store_true",
                        help="Print feature vectors for all windows before training")
    args = parser.parse_args()

    print("=" * 60)
    print("  Baseline Training Pipeline")
    print("=" * 60)

    # ── Step 1: Aggregate windows ─────────────────────────────────────────────
    print("\n[1/4] Aggregating log windows from database...")
    windows = get_all_windows(since=args.since, until=args.until)

    if not windows:
        print("\nNo windows found in the database.")
        print("   Make sure the ingestor is running and you've sent some logs.")
        print("   Run: python3 services/log-generator/generator.py --mode normal --duration 300")
        sys.exit(1)

    print(f"      Found {len(windows)} windows.")

    # Print per-window summary
    print(f"\n      {'Window start':<32} {'logs':>6} {'err%':>6} {'login_fail%':>11} {'avg_lat':>9}")
    print("      " + "-" * 68)
    for w in windows:
        print(
            f"      {w['window_start']:<32} "
            f"{w['total_logs']:>6} "
            f"{w['error_rate']*100:>5.1f}% "
            f"{w['login_failure_rate']*100:>10.1f}% "
            f"{w['avg_latency_ms']:>9.1f}ms"
        )

    # ── Step 2: Extract features ──────────────────────────────────────────────
    print(f"\n[2/4] Extracting feature vectors...")
    X = extract_batch(windows)
    print(f"      Feature matrix: {X.shape[0]} windows × {X.shape[1]} features")
    print(f"      Features: {feature_names()}")

    if args.describe:
        for w in windows:
            describe(w)

    # ── Step 3: Train model ───────────────────────────────────────────────────
    print(f"\n[3/4] Training Isolation Forest...")
    model_path = Path(args.model_path) if args.model_path else None
    model = AnomalyModel(model_path=model_path)

    try:
        model.train(X)
    except ValueError as e:
        print(f"\nTraining failed: {e}")
        sys.exit(1)

    # ── Step 4: Save model ────────────────────────────────────────────────────
    print(f"\n[4/4] Saving model...")
    model.save()
    print(f"      Saved to: {model.model_path}")

    # ── Sanity check: score training windows ──────────────────────────────────
    print(f"\n{'='*60}")
    print("  Sanity Check — Scoring Training Windows")
    print(f"{'='*60}")
    print(f"\n  {'Window start':<32} {'score':>7} {'anomalous':>10}")
    print("  " + "-" * 53)

    from inference import score_window
    anomaly_count = 0
    for w in windows:
        result = score_window(w, model)
        flag = "YES" if result["is_anomalous"] else "no"
        if result["is_anomalous"]:
            anomaly_count += 1
        print(f"  {w['window_start']:<32} {result['anomaly_score']:>7.4f}  {flag}")

    print(f"\n  {anomaly_count}/{len(windows)} training windows flagged as anomalous.")
    print("  (A small number is expected due to contamination=0.05)")
    print(f"\nTraining complete. Model ready at: {model.model_path}")
    print("   Next: python3 pipelines/run_detector.py")


if __name__ == "__main__":
    main()