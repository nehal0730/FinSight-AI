"""
Unit tests for Financial Risk Report Generator

Tests report generation, formatting, and summary creation.
"""

import unittest
from app.services.fraud.report_generator import ReportGenerator


class TestReportGenerator(unittest.TestCase):
    """Test cases for ReportGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_features = {
            "total_transactions": 10,
            "total_debited": 5000.0,
            "total_credited": 3000.0,
            "high_risk_merchants": 2,
            "max_amount": 1200.0,
            "unique_merchants": 5,
            "txn_velocity_5min": 1,
            "large_debit_transactions": 3,
            "amount_spike_ratio": 6.5,
        }

        self.sample_transactions = [
            {"merchant": "Test Casino", "amount": 1200.0, "type": "debit"},
            {"merchant": "Regular Store", "amount": 50.0, "type": "debit"},
            {"merchant": "Salary", "amount": 3000.0, "type": "credit"},
        ]

        self.document_insights = {
            "bank_name": "Test Bank",
            "account_type": "Checking",
            "statement_period": "Jan 2024",
        }

    def test_generate_high_risk_report(self):
        """Test generating a high-risk fraud report."""
        report = ReportGenerator.generate_financial_risk_report(
            risk_score=78.5,
            anomaly_score=0.82,
            is_fraud=True,
            features=self.sample_features,
            transactions=self.sample_transactions,
            document_name="test_statement.pdf",
            document_insights=self.document_insights,
        )

        # Validate structure
        self.assertIn("report_id", report)
        self.assertIn("timestamp", report)
        self.assertEqual(report["document_name"], "test_statement.pdf")
        self.assertEqual(report["risk_level"], "HIGH")
        self.assertEqual(report["risk_score"], 78.5)
        self.assertEqual(report["anomaly_score"], 0.82)
        self.assertTrue(report["is_fraud"])
        self.assertIsInstance(report["detected_issues"], list)
        self.assertIsInstance(report["key_metrics"], dict)
        self.assertIn("recommendation", report)
        self.assertIn("formatted_report", report)

        # Validate recommendation is urgent
        self.assertIn("URGENT", report["recommendation"])

    def test_generate_medium_risk_report(self):
        """Test generating a medium-risk fraud report."""
        report = ReportGenerator.generate_financial_risk_report(
            risk_score=55.0,
            anomaly_score=0.62,
            is_fraud=True,
            features=self.sample_features,
            transactions=self.sample_transactions,
            document_name="test_medium.pdf",
        )

        self.assertEqual(report["risk_level"], "MEDIUM")
        self.assertEqual(report["risk_score"], 55.0)
        self.assertTrue(report["is_fraud"])
        self.assertIn("Manual compliance review", report["recommendation"])
        self.assertNotIn("URGENT", report["recommendation"])

    def test_generate_low_risk_report(self):
        """Test generating a low-risk report."""
        report = ReportGenerator.generate_financial_risk_report(
            risk_score=25.0,
            anomaly_score=0.30,
            is_fraud=False,
            features=self.sample_features,
            transactions=self.sample_transactions,
        )

        self.assertEqual(report["risk_level"], "LOW")
        self.assertFalse(report["is_fraud"])
        self.assertIn("No action required", report["recommendation"])

    def test_report_id_generation(self):
        """Test unique report ID generation."""
        report1 = ReportGenerator.generate_financial_risk_report(
            risk_score=50.0,
            anomaly_score=0.5,
            is_fraud=False,
            features=self.sample_features,
            transactions=self.sample_transactions,
            document_name="doc1.pdf",
        )

        report2 = ReportGenerator.generate_financial_risk_report(
            risk_score=50.0,
            anomaly_score=0.5,
            is_fraud=False,
            features=self.sample_features,
            transactions=self.sample_transactions,
            document_name="doc2.pdf",
        )

        # Report IDs should be different
        self.assertNotEqual(report1["report_id"], report2["report_id"])
        self.assertIn("doc1pdf", report1["report_id"])
        self.assertIn("doc2pdf", report2["report_id"])

    def test_key_metrics_extraction(self):
        """Test key metrics extraction from features."""
        report = ReportGenerator.generate_financial_risk_report(
            risk_score=50.0,
            anomaly_score=0.5,
            is_fraud=False,
            features=self.sample_features,
            transactions=self.sample_transactions,
        )

        metrics = report["key_metrics"]
        
        # Validate all expected metrics present
        self.assertEqual(metrics["total_transactions"], 10)
        self.assertEqual(metrics["total_debited"], 5000.0)
        self.assertEqual(metrics["total_credited"], 3000.0)
        self.assertEqual(metrics["high_risk_merchants"], 2)
        self.assertEqual(metrics["max_transaction_amount"], 1200.0)
        self.assertEqual(metrics["unique_merchants"], 5)
        self.assertEqual(metrics["rapid_transactions"], 1)
        self.assertEqual(metrics["large_debits"], 3)

    def test_formatted_report_structure(self):
        """Test formatted text report contains all sections."""
        report = ReportGenerator.generate_financial_risk_report(
            risk_score=60.0,
            anomaly_score=0.65,
            is_fraud=True,
            features=self.sample_features,
            transactions=self.sample_transactions,
            document_name="test.pdf",
            document_insights=self.document_insights,
        )

        formatted = report["formatted_report"]
        
        # Check all required sections present
        self.assertIn("FINANCIAL RISK COMPLIANCE REPORT", formatted)
        self.assertIn("RISK ASSESSMENT", formatted)
        self.assertIn("DETECTED ISSUES", formatted)
        self.assertIn("KEY TRANSACTION METRICS", formatted)
        self.assertIn("RECOMMENDATION", formatted)
        self.assertIn("DOCUMENT INSIGHTS", formatted)
        self.assertIn("Report ID:", formatted)
        self.assertIn("Generated:", formatted)

    def test_summary_report_generation(self):
        """Test summary report generation."""
        report = ReportGenerator.generate_financial_risk_report(
            risk_score=78.5,
            anomaly_score=0.82,
            is_fraud=True,
            features=self.sample_features,
            transactions=self.sample_transactions,
            document_name="urgent.pdf",
        )

        summary = ReportGenerator.generate_summary_report(report)
        
        # Validate summary format
        self.assertIn("HIGH", summary)
        self.assertIn("78.5/100", summary)
        self.assertIn("urgent.pdf", summary)
        self.assertIn("Action:", summary)
        self.assertIn("Immediate manual review", summary)

    def test_risk_level_emoji_in_summary(self):
        """Test risk level emoji mapping in summary."""
        # High risk
        high_report = ReportGenerator.generate_financial_risk_report(
            risk_score=75.0, anomaly_score=0.8, is_fraud=True,
            features=self.sample_features, transactions=self.sample_transactions,
        )
        high_summary = ReportGenerator.generate_summary_report(high_report)
        self.assertIn("🔴", high_summary)

        # Medium risk
        med_report = ReportGenerator.generate_financial_risk_report(
            risk_score=55.0, anomaly_score=0.6, is_fraud=True,
            features=self.sample_features, transactions=self.sample_transactions,
        )
        med_summary = ReportGenerator.generate_summary_report(med_report)
        self.assertIn("🟡", med_summary)

        # Low risk
        low_report = ReportGenerator.generate_financial_risk_report(
            risk_score=20.0, anomaly_score=0.25, is_fraud=False,
            features=self.sample_features, transactions=self.sample_transactions,
        )
        low_summary = ReportGenerator.generate_summary_report(low_report)
        self.assertIn("🟢", low_summary)

    def test_document_insights_optional(self):
        """Test report generation without document insights."""
        report = ReportGenerator.generate_financial_risk_report(
            risk_score=50.0,
            anomaly_score=0.5,
            is_fraud=False,
            features=self.sample_features,
            transactions=self.sample_transactions,
        )

        # Should not have document_insights key
        self.assertNotIn("document_insights", report)

        # Should not have document insights section in formatted report
        formatted = report["formatted_report"]
        self.assertNotIn("DOCUMENT INSIGHTS", formatted)

    def test_risk_level_determination(self):
        """Test risk level determination logic."""
        # HIGH: is_fraud=True and score >= 70
        self.assertEqual(
            ReportGenerator._determine_risk_level(75.0, True), "HIGH"
        )

        # MEDIUM: is_fraud=True but score < 70
        self.assertEqual(
            ReportGenerator._determine_risk_level(55.0, True), "MEDIUM"
        )

        # MEDIUM: is_fraud=False but score >= 45
        self.assertEqual(
            ReportGenerator._determine_risk_level(50.0, False), "MEDIUM"
        )

        # LOW: is_fraud=False and score < 45
        self.assertEqual(
            ReportGenerator._determine_risk_level(40.0, False), "LOW"
        )

        # LOW: is_fraud=False and score < 35
        self.assertEqual(
            ReportGenerator._determine_risk_level(25.0, False), "LOW"
        )

    def test_detected_issues_integration(self):
        """Test integration with RiskExplainer for detected issues."""
        report = ReportGenerator.generate_financial_risk_report(
            risk_score=60.0,
            anomaly_score=0.65,
            is_fraud=True,
            features=self.sample_features,
            transactions=self.sample_transactions,
        )

        # Should have detected issues from RiskExplainer
        self.assertIsInstance(report["detected_issues"], list)
        
        # If there are high-risk features, they should be explained
        if self.sample_features.get("high_risk_merchants", 0) > 0:
            self.assertGreater(len(report["detected_issues"]), 0)


if __name__ == "__main__":
    unittest.main()
