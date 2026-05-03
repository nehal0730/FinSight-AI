"""
FinSight AI — Model Inference Module

Module: ml/predict.py
Purpose: Load trained model and generate fraud risk predictions

Used by: /analyze endpoint for real-time fraud scoring
"""

import os
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


class FraudDetectionInference:
    """Inference engine for fraud detection model."""

    def __init__(
        self,
        model_path: str = os.getenv("FRAUD_MODEL_PATH", "models/fraud_model_engineered.pkl"),
        scaler_path: str = os.getenv("FRAUD_SCALER_PATH", "models/scaler_engineered.pkl"),
    ):
        self.model_path = Path(model_path)
        self.scaler_path = Path(scaler_path)
        self.model = None
        self.scaler = None
        self.last_feature_alignment_action = "none"
        self.last_input_feature_count = 0
        self._load_artifacts()

    def _load_artifacts(self):
        """Load trained model and scaler from disk."""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        if not self.scaler_path.exists():
            raise FileNotFoundError(f"Scaler not found: {self.scaler_path}")

        import joblib

        self.model = joblib.load(self.model_path)
        self.scaler = joblib.load(self.scaler_path)
        print(f"[INFO] Model loaded from {self.model_path}")

    def expected_feature_count(self) -> int:
        """Return expected model input feature count from scaler metadata."""
        if self.scaler is None:
            return 0
        return int(getattr(self.scaler, "n_features_in_", 0))

    def _align_feature_dimensions(self, features: np.ndarray) -> tuple[np.ndarray, str]:
        """Pad or trim features to match scaler/model expected input dimension."""
        expected = int(getattr(self.scaler, "n_features_in_", features.shape[1]))
        current = int(features.shape[1])

        if current == expected:
            return features, "none"

        if current < expected:
            pad_width = expected - current
            aligned = np.pad(features, ((0, 0), (0, pad_width)), mode="constant")
            print(
                f"[WARN] Feature vector had {current} columns; padded to {expected}."
            )
            return aligned, "padded"

        aligned = features[:, :expected]
        print(
            f"[WARN] Feature vector had {current} columns; truncated to {expected}."
        )
        return aligned, "truncated"

    @staticmethod
    def anomaly_to_risk_score(anomaly_score: float) -> float:
        """Map anomaly score to calibrated risk score in [0, 1] using sigmoid.

        The midpoint is intentionally above 0.5 because the underlying IsolationForest
        can assign mid-range scores to normal statements with recurring but legitimate
        debits like EMI payments.
        """
        calibrated = 1.0 / (1.0 + np.exp(-8.0 * (float(anomaly_score) - 0.58)))
        return float(np.clip(calibrated, 0.0, 1.0))

    def predict(self, features: np.ndarray) -> dict[str, Any]:
        """
        Score transaction features for fraud risk.

        Args:
            features: numpy array of shape (n_samples, n_features)

        Returns:
            {
                "anomaly_score": float,       # 0-1, higher = more suspicious
                "is_fraud": bool,             # True if flagged as anomaly
                "risk_level": str,            # "low", "medium", "high"
            }
        """
        if features.ndim == 1:
            features = features.reshape(1, -1)

        self.last_input_feature_count = int(features.shape[1])
        features, action = self._align_feature_dimensions(features)
        self.last_feature_alignment_action = action

        # Preprocess
        X_scaled = self.scaler.transform(features)

        # Generate predictions
        raw_scores = self.model.score_samples(X_scaled)
        anomaly_scores = -raw_scores  # Negate for intuitive interpretation
        risk_scores = np.array([self.anomaly_to_risk_score(score) for score in anomaly_scores])
        predictions = self.model.predict(X_scaled)  # 1=normal, -1=anomaly

        # Package results
        result = {
            "anomaly_score": float(anomaly_scores[0]),
            "risk_score": float(risk_scores[0]),
            "is_fraud": bool(predictions[0] == -1),
            "risk_level": self._score_to_risk_level(risk_scores[0]),
        }

        return result

    def batch_predict(self, features: np.ndarray) -> list[dict[str, Any]]:
        """
        Score multiple transactions.

        Args:
            features: numpy array of shape (n_samples, n_features)

        Returns:
            List of prediction dicts
        """
        if features.ndim == 1:
            features = features.reshape(1, -1)

        self.last_input_feature_count = int(features.shape[1])
        features, action = self._align_feature_dimensions(features)
        self.last_feature_alignment_action = action
        X_scaled = self.scaler.transform(features)

        raw_scores = self.model.score_samples(X_scaled)
        anomaly_scores = -raw_scores
        risk_scores = np.array([self.anomaly_to_risk_score(score) for score in anomaly_scores])
        predictions = self.model.predict(X_scaled)

        results = [
            {
                "anomaly_score": float(score),
                "risk_score": float(risk_score),
                "is_fraud": bool(pred == -1),
                "risk_level": self._score_to_risk_level(risk_score),
            }
            for score, risk_score, pred in zip(anomaly_scores, risk_scores, predictions)
        ]

        return results

    @staticmethod
    def _score_to_risk_level(score: float) -> str:
        """
        Convert anomaly score to human-readable risk level.

        Thresholds:
        - score < 0.3:  LOW (normal behavior)
        - 0.3 <= score < 0.6: MEDIUM (potential risk)
        - score >= 0.6: HIGH (suspicious activity)
        """
        if score < 0.3:
            return "low"
        elif score < 0.6:
            return "medium"
        else:
            return "high"


# Global inference engine (lazy-loaded on first request)
_inference_engine = None


def get_inference_engine() -> FraudDetectionInference:
    """Get or initialize the inference engine."""
    global _inference_engine
    if _inference_engine is None:
        _inference_engine = FraudDetectionInference()
    return _inference_engine


def predict_fraud_risk(features: np.ndarray) -> dict[str, Any]:
    """
    Convenience function for API endpoints.

    Example usage in /analyze route:
    ────────────────────────────────
    features = engineer_features(transactions)  # from FeatureEngineer
    risk = predict_fraud_risk(features)
    return {
        "transactions": transactions,
        "features": features,
        "fraud_risk": risk,
    }
    """
    engine = get_inference_engine()
    return engine.predict(features)
