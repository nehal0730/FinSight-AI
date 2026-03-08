"""Fraud detection service built around anomaly model outputs.

This service provides:
- model loading and anomaly scoring
- anomaly-to-risk conversion
- LOW/MEDIUM/HIGH risk bucketing
- hybrid fraud verdict combining rule score and anomaly score
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


@dataclass(frozen=True)
class RiskThresholds:
    """Risk level cutoffs on normalized risk score (0.0 to 1.0)."""

    low_max: float = 0.40
    medium_max: float = 0.70


class FraudDetector:
    """Utility service for consistent fraud risk interpretation."""

    def __init__(
        self,
        model_path: str = "models/fraud_model.pkl",
        thresholds: RiskThresholds = RiskThresholds(),
    ) -> None:
        self.model_path = Path(model_path)
        self.thresholds = thresholds
        self.model = self._load_model(self.model_path)

    @staticmethod
    def _load_model(model_path: Path) -> Any:
        """Load a serialized sklearn-compatible model from disk."""
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        import joblib

        return joblib.load(model_path)

    @staticmethod
    def _prepare_features(features: Iterable[float] | np.ndarray) -> np.ndarray:
        """Convert incoming features to a 2D numpy array for sklearn APIs."""
        arr = np.asarray(features, dtype=float)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        if arr.ndim != 2:
            raise ValueError("Features must be a 1D or 2D numeric array")
        return arr

    @staticmethod
    def _compute_anomaly_score(model: Any, feature_array: np.ndarray) -> float:
        """Compute anomaly score where higher means more suspicious."""
        if hasattr(model, "score_samples"):
            raw_score = float(model.score_samples(feature_array)[0])
            return -raw_score

        if hasattr(model, "decision_function"):
            raw_score = float(model.decision_function(feature_array)[0])
            return -raw_score

        raise AttributeError(
            "Loaded model must implement score_samples() or decision_function()"
        )

    def predict(self, features: Iterable[float] | np.ndarray) -> dict[str, float | str]:
        """Run fraud risk inference and return normalized risk output."""
        feature_array = self._prepare_features(features)
        anomaly_score = self._compute_anomaly_score(self.model, feature_array)
        risk_score = self.anomaly_to_risk_score(anomaly_score)
        risk_level = self.risk_level_from_score(risk_score, self.thresholds)

        return {
            "risk_score": round(risk_score, 4),
            "risk_level": risk_level,
        }

    @staticmethod
    def anomaly_to_risk_score(anomaly_score: float) -> float:
        """Map anomaly score to calibrated risk score in [0, 1] using sigmoid."""
        calibrated = 1.0 / (1.0 + np.exp(-8.0 * (float(anomaly_score) - 0.5)))
        return float(np.clip(calibrated, 0.0, 1.0))

    @staticmethod
    def risk_level_from_score(
        risk_score: float, thresholds: RiskThresholds = RiskThresholds()
    ) -> str:
        """Convert normalized risk score into LOW/MEDIUM/HIGH buckets."""
        if risk_score < thresholds.low_max:
            return "LOW"
        if risk_score < thresholds.medium_max:
            return "MEDIUM"
        return "HIGH"

    @staticmethod
    def combine_fraud_verdict(
        fraud_score: float,
        anomaly_score: float,
        model_is_fraud: bool,
    ) -> dict[str, float | bool | str]:
        """Combine heuristic and model outputs into one final fraud verdict."""
        safe_fraud = max(0.0, min(100.0, float(fraud_score)))
        safe_anomaly = max(0.0, float(anomaly_score))

        # Convert anomaly scale to 0-100 and compute a weighted hybrid score.
        normalized_anomaly = max(0.0, min(100.0, safe_anomaly * 100.0))
        combined_score = (safe_fraud * 0.55) + (normalized_anomaly * 0.45)

        # Final verdict uses both signals, not just one.
        final_is_fraud = (
            (model_is_fraud and (safe_fraud >= 15.0 or safe_anomaly >= 0.50))
            or safe_anomaly >= 0.68
            or safe_fraud >= 70.0
            or (combined_score >= 44.0 and (safe_anomaly >= 0.55 or safe_fraud >= 35.0))
        )

        if combined_score >= 60.0 or safe_anomaly >= 0.60 or safe_fraud >= 65.0:
            risk_level = "high"
        elif combined_score >= 35.0 or safe_anomaly >= 0.40 or safe_fraud >= 35.0:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "combined_score": round(max(0.0, min(100.0, combined_score)), 4),
            "is_fraud": bool(final_is_fraud),
            "risk_level": risk_level,
        }


def detect_fraud(
    features: Iterable[float] | np.ndarray,
    model_path: str = "models/fraud_model.pkl",
) -> dict[str, float | str]:
    """Convenience helper for one-off fraud detection calls."""
    detector = FraudDetector(model_path=model_path)
    return detector.predict(features)
