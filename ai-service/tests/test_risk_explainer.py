"""Unit tests for risk explainer service."""

import unittest
from app.services.fraud import RiskExplainer, FeatureEngineer


class TestRiskExplainer(unittest.TestCase):
    """Test risk explanation generation."""

    def test_explain_high_risk_merchants(self):
        """Explain high-risk merchant transactions."""
        features = {
            "high_risk_merchants": 2.0,
            "large_debit_transactions": 0.0,
        }
        transactions = [
            {"merchant": "Casino Royal", "amount": 500},
            {"merchant": "Bitcoin Exchange", "amount": 1000},
        ]

        explanations = RiskExplainer.explain_risk(features, transactions)

        assert len(explanations) > 0
        assert any("high-risk" in exp.lower() for exp in explanations)
        assert any("casino" in exp.lower() or "crypto" in exp.lower() for exp in explanations)

    def test_explain_large_debits(self):
        """Explain large debit transactions."""
        features = {
            "large_debit_transactions": 3.0,
            "max_transaction": 50000.0,
            "high_risk_merchants": 0.0,
        }

        explanations = RiskExplainer.explain_risk(features)

        assert len(explanations) > 0
        assert any("large" in exp.lower() or "withdrawal" in exp.lower() for exp in explanations)

    def test_explain_velocity(self):
        """Explain high transaction velocity."""
        features = {
            "txn_velocity_5min": 5.0,
            "high_risk_merchants": 0.0,
        }

        explanations = RiskExplainer.explain_risk(features)

        assert len(explanations) > 0
        assert any("velocity" in exp.lower() or "5 minutes" in exp.lower() for exp in explanations)

    def test_explain_spending_spike(self):
        """Explain spending spike patterns."""
        features = {
            "amount_spike_ratio": 8.5,
            "high_risk_merchants": 0.0,
        }

        explanations = RiskExplainer.explain_risk(features)

        assert len(explanations) > 0
        assert any("spike" in exp.lower() for exp in explanations)

    def test_no_explanations_for_normal(self):
        """Normal transactions should have minimal or generic explanations."""
        features = {
            "high_risk_merchants": 0.0,
            "large_debit_transactions": 0.0,
            "txn_velocity_5min": 0.0,
            "amount_spike_ratio": 1.0,
        }

        explanations = RiskExplainer.explain_risk(features)

        # Should have fallback explanation
        assert len(explanations) == 1
        assert "ML model" in explanations[0] or "typical" in explanations[0]

    def test_comprehensive_explanation(self):
        """Test comprehensive verdict explanation."""
        features = {
            "high_risk_merchants": 2.0,
            "large_debit_transactions": 1.0,
            "max_transaction": 5000.0,
        }

        result = RiskExplainer.explain_combined_verdict(
            features=features,
            fraud_score=55.0,
            anomaly_score=0.72,
            combined_score=62.0,
            is_fraud=True,
        )

        assert "verdict" in result
        assert "confidence" in result
        assert "primary_reasons" in result
        assert "risk_factors" in result
        assert "recommendation" in result
        assert len(result["primary_reasons"]) > 0

    def test_format_amount(self):
        """Test amount formatting utility."""
        assert RiskExplainer._format_amount(50.25) == "$50.25"
        assert RiskExplainer._format_amount(1500) == "$1,500"
        assert RiskExplainer._format_amount(150000) == "$150K"

    def test_identify_high_risk_types(self):
        """Test extraction of high-risk merchant categories."""
        transactions = [
            {"merchant": "Lucky Star Casino"},
            {"merchant": "CryptoExchange BTC Buy"},
            {"merchant": "FreshMart Grocery"},
        ]

        categories = RiskExplainer._identify_high_risk_types(transactions)

        assert "Casinos" in categories
        assert "Cryptocurrency exchanges" in categories
        assert len(categories) == 2  # Only high-risk ones

    def test_integration_with_feature_engineer(self):
        """Test end-to-end with real feature engineering."""
        transactions = [
            {"date": "2026-03-01", "amount": 500.0, "type": "debit", "merchant": "Casino"},
            {"date": "2026-03-01", "amount": 450.0, "type": "debit", "merchant": "Casino"},
        ]

        engineer = FeatureEngineer()
        features = engineer.engineer_features(transactions)
        explanations = RiskExplainer.explain_risk(features, transactions)

        assert len(explanations) > 0
        assert isinstance(explanations[0], str)


if __name__ == "__main__":
    unittest.main()
