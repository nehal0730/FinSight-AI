import unittest
from app.services.fraud import FeatureEngineer, FraudDetector


class FeatureEngineeringTests(unittest.TestCase):
    """Test feature engineering for fraud detection."""

    def test_engineer_features_basic_transactions(self):
        """Test feature extraction from typical transaction mix."""
        transactions = [
            {"amount": 50000.0, "type": "credit", "merchant": "Salary Deposit"},
            {"amount": 5000.0, "type": "debit", "merchant": "GroceryMart"},
            {"amount": 2000.0, "type": "debit", "merchant": "Pharmacy"},
            {"amount": 8000.0, "type": "debit", "merchant": "Netflix"},
            {"amount": 500.0, "type": "debit", "merchant": "Coffee Shop"},
        ]

        features = FeatureEngineer.engineer_features(transactions)

        # Basic assertions
        assert features["total_transactions"] == 5.0
        assert features["total_credits"] == 1.0
        assert features["total_debits"] == 4.0
        assert features["avg_transaction_amount"] > 0
        assert features["max_transaction"] == 50000.0
        assert features["legitimate_merchants"] > 0

    def test_engineer_features_high_risk_transactions(self):
        """Test feature extraction with suspicious merchants."""
        transactions = [
            {"amount": 45000.0, "type": "debit", "merchant": "CasinoXYZ"},
            {"amount": 12000.0, "type": "debit", "merchant": "Gambling House"},
            {"amount": 5000.0, "type": "debit", "merchant": "Crypto Exchange"},
            {"amount": 50000.0, "type": "credit", "merchant": "Employer Salary"},
        ]

        features = FeatureEngineer.engineer_features(transactions)

        # Should detect high-risk merchants
        assert features["high_risk_merchants"] == 3.0
        assert features["total_transactions"] == 4.0

    def test_engineer_features_empty_transactions(self):
        """Test handling of empty transaction list."""
        features = FeatureEngineer.engineer_features([])

        assert features["total_transactions"] == 0.0
        assert features["avg_transaction_amount"] == 0.0
        assert features["high_risk_merchants"] == 0.0

    def test_fraud_score_calculation(self):
        """Test fraud risk score computation."""
        # Suspicious profile
        suspicious_features = {
            "high_risk_merchants": 3.0,
            "large_debit_transactions": 5.0,
            "rapid_same_merchant_transactions": 2.0,
            "cash_like_activity": 4.0,
            "transaction_std_dev": 15000.0,
            "legitimate_merchants": 1.0,
        }

        score = FeatureEngineer.compute_fraud_score(suspicious_features)

        # Should be moderately high risk
        assert score > 20.0

    def test_fraud_score_legitimate_profile(self):
        """Test fraud score for legitimate transaction pattern."""
        legitimate_features = {
            "high_risk_merchants": 0.0,
            "large_debit_transactions": 0.0,
            "rapid_same_merchant_transactions": 0.0,
            "cash_like_activity": 0.0,
            "transaction_std_dev": 500.0,
            "legitimate_merchants": 10.0,
        }

        score = FeatureEngineer.compute_fraud_score(legitimate_features)

        # Should be low risk
        assert score < 10.0

    def test_merchant_risk_detection(self):
        """Test merchant-specific risk classification."""
        assert FeatureEngineer._is_high_risk_merchant("CasinoXYZ") is True
        assert FeatureEngineer._is_high_risk_merchant("Casino Royal") is True
        assert FeatureEngineer._is_high_risk_merchant("Bitcoin Exchange") is True

        assert FeatureEngineer._is_legitimate_merchant("Salary") is True
        assert FeatureEngineer._is_legitimate_merchant("GroceryMart") is True
        assert FeatureEngineer._is_legitimate_merchant("Hospital") is True

    def test_rapid_repeat_detection(self):
        """Test detection of rapid merchant repeats."""
        merchants = [
            "Amazon",
            "Amazon",
            "Netflix",
            "Amazon",
            "Netflix",
            "Netflix",
        ]

        rapid_count = FeatureEngineer._count_rapid_repeats(merchants, window=3)

        # Should detect repeating pattern
        assert rapid_count > 0

    def test_feature_vector_consistency(self):
        """Test that feature vector has expected keys and numeric values."""
        transactions = [
            {"amount": 10000.0, "type": "debit", "merchant": "Store"},
            {"amount": 5000.0, "type": "credit", "merchant": "Employer"},
        ]

        features = FeatureEngineer.engineer_features(transactions)

        # All features should be numeric
        for key, value in features.items():
            assert isinstance(value, float), f"{key} is not float: {type(value)}"

        # Check expected keys exist
        expected_keys = {
            "total_transactions",
            "avg_transaction_amount",
            "max_transaction",
            "high_risk_merchants",
            "unique_merchants",
        }
        assert expected_keys.issubset(set(features.keys()))

    def test_hybrid_verdict_uses_both_signals(self):
        """Hybrid verdict should elevate risk when both signals are moderately suspicious."""
        result = FraudDetector.combine_fraud_verdict(
            fraud_score=30.0,
            anomaly_score=0.63,
            model_is_fraud=False,
        )

        assert result["combined_score"] > 0
        assert result["is_fraud"] is True
        assert result["risk_level"] == "high"

    def test_hybrid_verdict_low_when_both_low(self):
        """Hybrid verdict should stay low for clearly normal behavior."""
        result = FraudDetector.combine_fraud_verdict(
            fraud_score=6.0,
            anomaly_score=0.18,
            model_is_fraud=False,
        )

        assert result["is_fraud"] is False
        assert result["risk_level"] == "low"


if __name__ == "__main__":
    unittest.main()
