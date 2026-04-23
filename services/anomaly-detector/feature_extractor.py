"""
feature_extractor.py
Converts window stat dicts (from window_aggregator) into numpy feature vectors
ready for the Isolation Forest model.

Why a separate module?
  The feature list must be identical at training time and inference time.
  Having one canonical FEATURE_COLUMNS list here guarantees that.
  Any change to features only needs to happen in one place.
"""

import numpy as np

# ── Canonical feature list ────────────────────────────────────────────────────
# ORDER MATTERS — must be the same when training and when scoring.
# Do not reorder without retraining the model.

FEATURE_COLUMNS = [
    # Error signal
    "error_rate",
    "warn_rate",

    # Auth behaviour
    "login_failure_rate",

    # API gateway behaviour
    "high_latency_rate",

    # Payment behaviour
    "payment_timeout_rate",
    "payment_failure_rate",

    # Notification behaviour
    "notif_failure_rate",

    # Latency
    "avg_latency_ms",
    "max_latency_ms",
    "p95_latency_ms",

    # Service distribution
    "frac_auth",
    "frac_api_gateway",
    "frac_payment",
    "frac_notification",
]


def extract(window_stats: dict) -> np.ndarray:
    """
    Convert a single window stats dict → 1-D numpy array of shape (n_features,).

    Missing features default to 0.0 so the function is safe even if the
    aggregator adds new optional fields later.
    """
    return np.array(
        [float(window_stats.get(col, 0.0)) for col in FEATURE_COLUMNS],
        dtype=np.float64,
    )


def extract_batch(windows: list[dict]) -> np.ndarray:
    """
    Convert a list of window stat dicts → 2-D numpy array of shape
    (n_windows, n_features).

    Used by the training pipeline to build the full feature matrix at once.
    """
    if not windows:
        return np.empty((0, len(FEATURE_COLUMNS)), dtype=np.float64)
    return np.vstack([extract(w) for w in windows])


def feature_names() -> list[str]:
    """Return the canonical feature column names (useful for debugging)."""
    return list(FEATURE_COLUMNS)


def describe(window_stats: dict) -> None:
    """
    Pretty-print the feature vector for a single window.
    Useful during exploration / debugging.
    """
    vec = extract(window_stats)
    print(f"\nWindow: {window_stats.get('window_start')} → {window_stats.get('window_end')}")
    print(f"{'Feature':<30} {'Value':>12}")
    print("-" * 44)
    for name, val in zip(FEATURE_COLUMNS, vec):
        print(f"{name:<30} {val:>12.4f}")
    print()