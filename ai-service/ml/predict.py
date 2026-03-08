"""
FinSight AI — Model Inference Module

Module: ml/predict.py
Purpose: Load trained model and generate fraud risk predictions

Used by: /analyze endpoint for real-time fraud scoring
"""

from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


class FraudDetectionInference:
    """Inference engine for fraud detection model."""

    def __init__(
        self,
        model_path: str = "models/fraud_model_engineered.pkl",
        scaler_path: str = "models/scaler_engineered.pkl",
    ):
        self.model_path = Path(model_path)
        self.scaler_path = Path(scaler_path)
        self.model = None
        self.scaler = None
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

        # Preprocess
        X_scaled = self.scaler.transform(features)

        # Generate predictions
        raw_scores = self.model.score_samples(X_scaled)
        anomaly_scores = -raw_scores  # Negate for intuitive interpretation
        predictions = self.model.predict(X_scaled)  # 1=normal, -1=anomaly

        # Package results
        result = {
            "anomaly_score": float(anomaly_scores[0]),
            "is_fraud": bool(predictions[0] == -1),
            "risk_level": self._score_to_risk_level(anomaly_scores[0]),
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
        X_scaled = self.scaler.transform(features)

        raw_scores = self.model.score_samples(X_scaled)
        anomaly_scores = -raw_scores
        predictions = self.model.predict(X_scaled)

        results = [
            {
                "anomaly_score": float(score),
                "is_fraud": bool(pred == -1),
                "risk_level": self._score_to_risk_level(score),
            }
            for score, pred in zip(anomaly_scores, predictions)
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
