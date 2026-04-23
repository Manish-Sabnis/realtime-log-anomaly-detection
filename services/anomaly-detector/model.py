"""
model.py
Isolation Forest wrapper.

Responsibilities
----------------
- Train the model on a feature matrix
- Save / load the trained model to disk
- Score a single feature vector → anomaly score + flag
- Keep the anomaly threshold in one place
"""

import pickle
import numpy as np
from pathlib import Path
from sklearn.ensemble import IsolationForest

# ── Config ────────────────────────────────────────────────────────────────────

# contamination = expected fraction of anomalies in training data.
# Training data is normal baseline, so keep this very low.
CONTAMINATION   = 0.05

# Isolation Forest raw scores are in [-1, +1] where more negative = more anomalous.
# We remap to [0, 1] where higher = more anomalous.
# A remapped score above this threshold is flagged as an anomaly.
ANOMALY_THRESHOLD = 0.35

N_ESTIMATORS = 200   # more trees = more stable scores
RANDOM_STATE = 42

# Default model path: data/models/isolation_forest.pkl (relative to repo root)
def _default_model_path() -> Path:
    here      = Path(__file__).resolve().parent          # services/anomaly-detector/
    repo_root = here.parent.parent
    model_dir = repo_root / "data" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    return model_dir / "isolation_forest.pkl"


# ── Model class ───────────────────────────────────────────────────────────────

class AnomalyModel:
    """
    Thin wrapper around sklearn IsolationForest.

    Usage
    -----
        model = AnomalyModel()
        model.train(X)          # X shape: (n_windows, n_features)
        model.save()
        model.load()
        result = model.score(x) # x shape: (n_features,)
    """

    def __init__(self, model_path: Path = None):
        self.model_path = model_path or _default_model_path()
        self._clf: IsolationForest = None
        self.threshold = ANOMALY_THRESHOLD

        # Baseline stats stored at train time — used later to compute
        # deviation ratios in the anomaly output.
        self.baseline_mean: np.ndarray = None
        self.baseline_std:  np.ndarray = None
        self._score_min: float = -0.5
        self._score_max: float =  0.5
        self._score_mean: float = 0.0
        self._score_std:  float = 0.1

    # ── Training ──────────────────────────────────────────────────────────────

    def train(self, X: np.ndarray) -> None:
        """
        Fit the Isolation Forest on a (n_windows, n_features) matrix.
        Stores baseline mean/std for deviation reporting.
        """
        if X.shape[0] < 5:
            raise ValueError(
                f"Need at least 5 windows to train, got {X.shape[0]}. "
                "Run the generator for longer to build more baseline data."
            )

        self._clf = IsolationForest(
            n_estimators=N_ESTIMATORS,
            contamination=CONTAMINATION,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
        self._clf.fit(X)

        self.baseline_mean = X.mean(axis=0)
        self.baseline_std  = X.std(axis=0) + 1e-9

        # Store score range from training data for normalisation
        train_scores    = self._clf.score_samples(X)
        self._score_min  = float(train_scores.min())
        self._score_max  = float(train_scores.max())
        self._score_mean = float(train_scores.mean())
        self._score_std  = float(train_scores.std()) + 1e-9

        self.threshold = 0.75
        print(f"[model] Threshold set to: {self.threshold}")

        print(f"[model] Trained on {X.shape[0]} windows, {X.shape[1]} features.")
        print(f"[model] Model saved to: {self.model_path}")

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self, path: Path = None) -> None:
        target = path or self.model_path
        payload = {
            "clf":            self._clf,
            "baseline_mean":  self.baseline_mean,
            "baseline_std":   self.baseline_std,
            "threshold":      self.threshold,
            "score_min":      self._score_min,
            "score_max":      self._score_max,
            "score_mean":     self._score_mean,
            "score_std":      self._score_std,
        }
        with open(target, "wb") as f:
            pickle.dump(payload, f)

    def load(self, path: Path = None) -> None:
        target = path or self.model_path
        if not Path(target).exists():
            raise FileNotFoundError(
                f"No model found at {target}. "
                "Run pipelines/train_baseline.py first."
            )
        with open(target, "rb") as f:
            payload = pickle.load(f)
        self._clf           = payload["clf"]
        self.baseline_mean  = payload["baseline_mean"]
        self.baseline_std   = payload["baseline_std"]
        self.threshold      = payload.get("threshold", ANOMALY_THRESHOLD)
        self._score_min     = payload.get("score_min", -0.5)
        self._score_max     = payload.get("score_max",  0.5)
        self._score_mean    = payload.get("score_mean", 0.0)
        self._score_std     = payload.get("score_std",  0.1)

    def is_trained(self) -> bool:
        return self._clf is not None

    # ── Scoring ───────────────────────────────────────────────────────────────

    def score(self, x: np.ndarray) -> dict:
        """
        Score a single feature vector x of shape (n_features,).

        Returns
        -------
        {
            "anomaly_score": float,   # 0 (normal) → 1 (anomalous)
            "is_anomalous":  bool,
            "raw_score":     float,   # raw sklearn score_samples output
            "deviations":    np.ndarray,  # per-feature z-scores vs baseline
        }
        """
        if not self.is_trained():
            raise RuntimeError("Model is not trained. Call train() or load() first.")

        x2d = x.reshape(1, -1)

        # sklearn score_samples: more negative = more anomalous
        raw = self._clf.score_samples(x2d)[0]

        # Remap to [0, 1] using the training score range stored at fit time.
        # This makes the score robust regardless of dataset size.
        normalised = (self._score_mean - raw) / (self._score_std * 3.0)
        anomaly_score = float(np.clip(normalised, 0.0, 1.0))

        # Per-feature deviation from baseline (z-score)
        deviations = np.abs((x - self.baseline_mean) / self.baseline_std)

        return {
            "anomaly_score": round(anomaly_score, 4),
            "is_anomalous":  anomaly_score >= self.threshold,
            "raw_score":     round(float(raw), 6),
            "deviations":    deviations,
        }

    def score_batch(self, X: np.ndarray) -> list[dict]:
        """Score multiple windows at once. Returns list of score dicts."""
        return [self.score(X[i]) for i in range(X.shape[0])]