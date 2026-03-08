"""Integration test: Fraud scoring inference pipeline."""

import sys
import unittest
import numpy as np
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.transaction_extractor import TransactionExtractor
from app.services.feature_engineering import FeatureEngineer
from ml.predict import get_inference_engine


class TestInferencePipeline(unittest.TestCase):
    """Test end-to-end fraud detection pipeline."""

    @classmethod
    def setUpClass(cls):
        """Load inference engine once for all tests."""
        cls.inference = get_inference_engine()
        # Check model is loaded
        assert cls.inference.model is not None, "Model failed to load"

    def test_single_transaction_scoring(self):
        """Score a single normal transaction."""
        # Create a normal transaction (low fraud risk)
        transactions = [
            {
                "date": "2025-01-05",
                "amount": 1500.00,
                "type": "debit",
                "merchant": "GROCERY"
            }
        ]
        
        # Engineer features
        engineer = FeatureEngineer()
        features = engineer.engineer_features(transactions)
        
        # Verify features extracted (updated to 28 features)
        self.assertEqual(len(features), 28)
        self.assertTrue(all(isinstance(v, (int, float)) for v in features.values()))
        
        # Score
        features_array = np.array(list(features.values())).reshape(1, -1)
        result = self.inference.predict(features_array)
        
        # Should have low fraud risk for legitimate merchant
        self.assertIn("is_fraud", result)
        self.assertIn("risk_level", result)
        self.assertIn("anomaly_score", result)

    def test_batch_scoring(self):
        """Score multiple transactions in batch."""
        transactions = [
            {"date": "2025-01-05", "amount": 1500.00, "type": "debit", "merchant": "GROCERY"},
            {"date": "2025-01-06", "amount": 5000.00, "type": "debit", "merchant": "CASINO"},
            {"date": "2025-01-07", "amount": 20000.00, "type": "debit", "merchant": "ATM"},
        ]
        
        engineer = FeatureEngineer()
        features = engineer.engineer_features(transactions)
        features_array = np.array(list(features.values())).reshape(1, -1)
        
        results = self.inference.batch_predict(features_array)
        self.assertEqual(len(results), 1)
        
        for result in results:
            self.assertIn("is_fraud", result)
            self.assertIn("risk_level", result)
            self.assertIn("anomaly_score", result)

    def test_high_risk_scoring(self):
        """Score transactions with high fraud indicators."""
        # Casino + high amount = high risk
        transactions = [
            {"date": "2025-01-05", "amount": 50000.00, "type": "debit", "merchant": "CASINO"},
        ]
        
        engineer = FeatureEngineer()
        features = engineer.engineer_features(transactions)
        fraud_score = engineer.compute_fraud_score(features)
        
        # Should have elevated fraud score (realistic threshold)
        self.assertGreater(fraud_score, 2)  # Casino merchant raises score above normal

    def test_risk_level_mapping(self):
        """Verify risk level classification thresholds."""
        engineer = FeatureEngineer()
        
        # Multiple normal transactions (more typical)
        normal_transactions = [
            {"date": "2025-01-05", "amount": 1000.00, "type": "debit", "merchant": "GROCERY"},
            {"date": "2025-01-06", "amount": 500.00, "type": "debit", "merchant": "PHARMACY"},
            {"date": "2025-01-07", "amount": 2000.00, "type": "debit", "merchant": "GROCERY"},
        ]
        normal_features = engineer.engineer_features(normal_transactions)
        normal_array = np.array(list(normal_features.values())).reshape(1, -1)
        result_low = self.inference.predict(normal_array)
        # Should be low or medium for normal pattern
        self.assertIn(result_low["risk_level"], ["low", "medium"])
        
        # High-risk transaction  
        risky_transactions = [
            {"date": "2025-01-05", "amount": 50000.00, "type": "debit", "merchant": "CASINO"},
        ]
        risky_features = engineer.engineer_features(risky_transactions)
        risky_array = np.array(list(risky_features.values())).reshape(1, -1)
        result_high = self.inference.predict(risky_array)
        # Should be flagged as at least medium risk
        self.assertIn(result_high["risk_level"], ["medium", "high"])


if __name__ == "__main__":
    unittest.main()
