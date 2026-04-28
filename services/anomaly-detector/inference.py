"""
inference.py
Combines window stats + model scores → final anomaly output (Schema v1).

This is the module that produces the exact output format defined in the design doc:

{
    "window_start": ...,
    "window_end": ...,
    "anomaly_score": ...,
    "is_anomalous": ...,
    "affected_services": [...],
    "top_contributing_patterns": [...],
    "metrics": { baseline vs current }
}
"""

import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from feature_extractor import FEATURE_COLUMNS

# ── Feature → service mapping ─────────────────────────────────────────────────
# Used to determine which services contributed most to an anomaly.

FEATURE_SERVICE_MAP = {
    "login_failure_rate":    "auth-service",
    "login_failure_count":   "auth-service",
    "error_rate":            "auth-service",       # multi-service but auth dominates errors

    "high_latency_rate":     "api-gateway",
    "high_latency_count":    "api-gateway",

    "payment_timeout_rate":  "payment-service",
    "payment_failure_rate":  "payment-service",
    "payment_timeout_count": "payment-service",
    "payment_failure_count": "payment-service",

    "notif_failure_rate":    "notification-service",
    "notif_failed_count":    "notification-service",
}

# Human-readable pattern labels
FEATURE_LABELS = {
    "login_failure_rate":    "login failure rate",
    "login_failure_count":   "login failure count",
    "high_latency_rate":     "high latency rate",
    "high_latency_count":    "high latency count",
    "payment_timeout_rate":  "payment timeout rate",
    "payment_timeout_count": "payment timeout count",
    "payment_failure_rate":  "payment failure rate",
    "payment_failure_count": "payment failure count",
    "notif_failure_rate":    "notification failure rate",
    "error_rate":            "overall error rate",
    "avg_latency_ms":        "average latency",
    "p95_latency_ms":        "p95 latency",
}


def build_anomaly_output(
    window_stats: dict,
    score_result: dict,
    model,
) -> dict:
    """
    Combine window stats + model score → final anomaly output dict.

    Parameters
    ----------
    window_stats  : output of window_aggregator.aggregate_window()
    score_result  : output of model.score()
    model         : trained AnomalyModel instance (for baseline stats)
    """
    deviations: np.ndarray = score_result["deviations"]

    # ── Top contributing patterns ─────────────────────────────────────────────
    # Rank features by deviation from baseline, keep top 5 that are meaningful.
    indexed = [
        (FEATURE_COLUMNS[i], float(deviations[i]))
        for i in range(len(FEATURE_COLUMNS))
        if FEATURE_COLUMNS[i] in FEATURE_LABELS
    ]
    indexed.sort(key=lambda x: x[1], reverse=True)

    top_patterns = []
    for feat, dev in indexed[:5]:
        if dev < 1.0:   # less than 1 std dev — not interesting
            continue
        top_patterns.append({
            "feature":          feat,
            "label":            FEATURE_LABELS.get(feat, feat),
            "deviation_ratio":  round(dev, 2),
        })

    # ── Affected services ─────────────────────────────────────────────────────
    affected: dict[str, float] = {}
    for feat, dev in indexed[:10]:
        svc = FEATURE_SERVICE_MAP.get(feat)
        if svc and dev >= 1.5:
            affected[svc] = max(affected.get(svc, 0.0), dev)

    affected_services = sorted(affected.keys(), key=lambda s: affected[s], reverse=True)

    # ── Human-readable metrics ────────────────────────────────────────────────
    # Pull baseline values from model and compare to current window.
    def _baseline(feature: str) -> float:
        if model.baseline_mean is None:
            return 0.0
        idx = FEATURE_COLUMNS.index(feature)
        return round(float(model.baseline_mean[idx]), 4)

    metrics = {
        "baseline_error_rate":     _baseline("error_rate"),
        "current_error_rate":      window_stats.get("error_rate", 0.0),

        "baseline_login_failure_rate": _baseline("login_failure_rate"),
        "current_login_failure_rate":  window_stats.get("login_failure_rate", 0.0),

        "baseline_latency_ms":     round(_baseline("avg_latency_ms"), 1),
        "current_latency_ms":      window_stats.get("avg_latency_ms", 0.0),

        "baseline_payment_timeout_rate": _baseline("payment_timeout_rate"),
        "current_payment_timeout_rate":  window_stats.get("payment_timeout_rate", 0.0),

        "total_logs": window_stats.get("total_logs", 0),
    }

    return {
        "window_start":               window_stats["window_start"],
        "window_end":                 window_stats["window_end"],
        "anomaly_score":              score_result["anomaly_score"],
        "is_anomalous":               score_result["is_anomalous"],
        "affected_services":          affected_services,
        "top_contributing_patterns":  top_patterns,
        "metrics":                    metrics,
    }


def score_window(window_stats: dict, model) -> dict:
    """
    Convenience function: extract features, score, build output.
    Single entry point used by run_detector.py.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from feature_extractor import extract

    x = extract(window_stats)
    score_result = model.score(x)
    return build_anomaly_output(window_stats, score_result, model)