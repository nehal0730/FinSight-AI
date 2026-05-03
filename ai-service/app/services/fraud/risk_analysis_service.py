"""Shared fraud pipeline orchestration for API endpoints.

This service centralizes transaction extraction, feature engineering,
ML inference, risk explanations, and report generation.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from app.services.fraud.feature_engineering import FeatureEngineer
from app.services.fraud.fraud_detector import FraudDetector
from app.services.fraud.report_generator import ReportGenerator
from app.services.fraud.risk_explainer import RiskExplainer
from app.services.fraud.transaction_extractor import TransactionExtractor
from ml.predict import get_inference_engine


class RiskAnalysisService:
    """Run the full ML risk pipeline on extracted text."""

    @classmethod
    def analyze_text(
        cls,
        cleaned_text: str,
        document_name: str | None = None,
        document_insights: dict[str, Any] | None = None,
        use_llm: bool = False,
    ) -> dict[str, Any] | None:
        """Analyze cleaned text and return fraud, explanation, and report outputs.

        Returns None when no transactions are found.
        """
        extractor = TransactionExtractor()
        transactions = extractor.extract_transactions(cleaned_text)
        if not transactions:
            return None

        engineer = FeatureEngineer()
        features = engineer.engineer_features(transactions)
        fraud_score = engineer.compute_fraud_score(features)

        features_array = np.array(list(features.values()), dtype=float).reshape(1, -1)
        inference = get_inference_engine()
        ml_result = inference.predict(features_array)
        expected_feature_count = int(getattr(inference.scaler, "n_features_in_", 0))
        provided_feature_count = int(features_array.shape[1])
        alignment_action = str(
            getattr(inference, "last_feature_alignment_action", "none")
        )

        model_metadata = {
            "pipeline_version": "hybrid-v2",
            "model_artifact": str(inference.model_path),
            "scaler_artifact": str(inference.scaler_path),
            "expected_feature_count": expected_feature_count,
            "provided_feature_count": provided_feature_count,
            "feature_alignment_action": alignment_action,
        }

        model_risk_score = float(ml_result.get("risk_score", ml_result["anomaly_score"]))

        hybrid_result = FraudDetector.combine_fraud_verdict(
            fraud_score=fraud_score,
            anomaly_score=model_risk_score,
            model_is_fraud=bool(ml_result["is_fraud"]),
        )

        takeover_signal = RiskExplainer.detect_account_takeover_signal(transactions)
        final_risk_score = max(float(hybrid_result["combined_score"]), float(takeover_signal["score"]))
        final_is_fraud = bool(hybrid_result["is_fraud"]) or float(takeover_signal["score"]) >= 70.0
        reasons = RiskExplainer.explain_risk(features, transactions)
        if takeover_signal["reason"] and takeover_signal["reason"] not in reasons:
            reasons.insert(0, takeover_signal["reason"])

        report = ReportGenerator.generate_financial_risk_report(
            risk_score=final_risk_score,
            anomaly_score=float(ml_result["anomaly_score"]),
            is_fraud=final_is_fraud,
            features=features,
            transactions=transactions,
            document_name=document_name,
            document_insights=document_insights,
            use_llm=use_llm,
        )

        final_risk_level = str(report.get("risk_level", "LOW"))

        return {
            "transactions": transactions,
            "features": features,
            "fraud_score": float(fraud_score),
            "anomaly_score": float(ml_result["anomaly_score"]),
            "model_risk_score": model_risk_score,
            "model_is_fraud": bool(ml_result["is_fraud"]),
            "model_risk_level": str(ml_result["risk_level"]),
            "combined_score": float(hybrid_result["combined_score"]),
            "takeover_score": float(takeover_signal["score"]),
            "is_fraud": final_is_fraud,
            "hybrid_risk_level": str("high" if final_risk_score >= 70 else "medium" if final_risk_score >= 45 else "low"),
            "final_risk_level": final_risk_level,
            "reasons": reasons,
            "report": report,
            "model_metadata": model_metadata,
        }
