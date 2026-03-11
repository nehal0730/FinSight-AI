"""
Financial Risk Report Generator

Generates structured compliance reports combining ML risk scores,
anomaly explanations, and document insights with optional LLM enhancement.

Author: FinSight AI
"""

from datetime import datetime
from typing import Any, Optional
from app.services.fraud.risk_explainer import RiskExplainer


class ReportGenerator:
    """Generate structured financial risk reports for compliance review."""

    # Risk level thresholds
    HIGH_RISK_THRESHOLD = 70.0
    MEDIUM_RISK_THRESHOLD = 45.0
    LOW_MEDIUM_THRESHOLD = 35.0

    @classmethod
    def generate_financial_risk_report(
        cls,
        risk_score: float,
        anomaly_score: float,
        is_fraud: bool,
        features: dict[str, float],
        transactions: list[dict[str, Any]],
        document_name: Optional[str] = None,
        document_insights: Optional[dict[str, Any]] = None,
        use_llm: bool = False,
    ) -> dict[str, Any]:
        """Generate comprehensive financial compliance report.

        Args:
            risk_score: Combined risk score (0-100)
            anomaly_score: ML anomaly score (0-1)
            is_fraud: Final fraud verdict (True/False)
            features: Engineered feature dictionary
            transactions: List of transaction dictionaries
            document_name: Name of analyzed document
            document_insights: Additional document metadata
            use_llm: If True, use LLM to generate natural language summary and recommendation

        Returns:
            Structured report dictionary with:
            - report_id, timestamp, document_name
            - risk_level, risk_score, is_fraud
            - detected_issues (list of issues)
            - key_metrics (transaction summary)
            - recommendation
            - llm_summary (only if use_llm=True)
            - formatted_report (human-readable text)
        """
        # Generate unique report ID
        report_id = cls._generate_report_id(document_name)
        timestamp = datetime.now().isoformat()

        # Determine risk level
        risk_level = cls._determine_risk_level(risk_score, is_fraud)

        # Get detected issues from RiskExplainer
        detected_issues = RiskExplainer.explain_risk(features, transactions)

        # Extract key metrics
        key_metrics = cls._extract_key_metrics(features, transactions)

        # Generate recommendation (rule-based by default)
        recommendation = cls._generate_recommendation(risk_score, is_fraud, detected_issues)
        
        # LLM Enhancement (optional)
        llm_summary = None
        llm_recommendation = None
        if use_llm:
            try:
                from app.services.fraud.llm_report_generator import get_llm_report_generator
                llm_gen = get_llm_report_generator()
                
                llm_summary = llm_gen.generate_fraud_summary(
                    risk_score=risk_score,
                    is_fraud=is_fraud,
                    detected_issues=detected_issues,
                    key_metrics=key_metrics,
                    document_name=document_name or "Unknown Document"
                )
                
                llm_recommendation = llm_gen.generate_recommendation(
                    risk_score=risk_score,
                    is_fraud=is_fraud,
                    detected_issues=detected_issues
                )
                
                # Override rule-based recommendation with LLM version
                recommendation = llm_recommendation
                
            except Exception as e:
                from app.utils.logging import api_logger
                api_logger.warning(f"LLM report generation failed, using rule-based: {e}")

        # Build structured report
        report = {
            "report_id": report_id,
            "timestamp": timestamp,
            "document_name": document_name or "Unknown Document",
            "risk_level": risk_level,
            "risk_score": round(risk_score, 2),
            "anomaly_score": round(anomaly_score, 4),
            "is_fraud": is_fraud,
            "detected_issues": detected_issues,
            "key_metrics": key_metrics,
            "recommendation": recommendation,
        }
        
        # Add LLM-generated content if available
        if llm_summary:
            report["llm_summary"] = llm_summary

        # Add document insights if provided
        if document_insights:
            report["document_insights"] = document_insights

        # Generate formatted text report
        report["formatted_report"] = cls._format_text_report(report)

        return report

    @classmethod
    def _generate_report_id(cls, document_name: Optional[str] = None) -> str:
        """Generate unique report identifier."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if document_name:
            # Clean document name for ID
            clean_name = "".join(c for c in document_name if c.isalnum() or c in ("-", "_"))[:30]
            return f"RISK_REPORT_{clean_name}_{timestamp}"
        return f"RISK_REPORT_{timestamp}"

    @classmethod
    def _determine_risk_level(cls, risk_score: float, is_fraud: bool) -> str:
        """Determine risk level category."""
        if is_fraud and risk_score >= cls.HIGH_RISK_THRESHOLD:
            return "HIGH"
        elif is_fraud or risk_score >= cls.MEDIUM_RISK_THRESHOLD:
            return "MEDIUM"
        elif risk_score >= cls.LOW_MEDIUM_THRESHOLD:
            return "LOW-MEDIUM"
        else:
            return "LOW"

    @classmethod
    def _extract_key_metrics(
        cls, features: dict[str, float], transactions: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Extract key transaction metrics for report summary."""
        max_txn = features.get("max_transaction", features.get("max_amount", 0.0))
        rapid_velocity = int(features.get("txn_velocity_5min", 0))
        rapid_same_merchant = int(features.get("rapid_same_merchant_transactions", 0))

        return {
            "total_transactions": int(features.get("total_transactions", 0)),
            "total_debited": round(features.get("total_debited", 0.0), 2),
            "total_credited": round(features.get("total_credited", 0.0), 2),
            "high_risk_merchants": int(features.get("high_risk_merchants", 0)),
            "max_transaction_amount": round(float(max_txn), 2),
            "unique_merchants": int(features.get("unique_merchants", 0)),
            # Keep one summary metric that captures either time-window velocity or repeat behavior.
            "rapid_transactions": max(rapid_velocity, rapid_same_merchant),
            "large_debits": int(features.get("large_debit_transactions", 0)),
        }

    @classmethod
    def _generate_recommendation(
        cls, risk_score: float, is_fraud: bool, detected_issues: list[str]
    ) -> str:
        """Generate compliance recommendation based on risk assessment."""
        if is_fraud and risk_score >= cls.HIGH_RISK_THRESHOLD:
            return (
                "URGENT: Manual compliance review required. "
                "Consider immediate account review, transaction blocking, or escalation to fraud investigation team."
            )
        elif is_fraud:
            return (
                "Manual compliance review required. "
                "Monitor account closely and investigate flagged transactions. "
                "Consider enhanced verification procedures."
            )
        elif risk_score >= cls.MEDIUM_RISK_THRESHOLD:
            return (
                "Enhanced monitoring recommended. "
                "Review flagged patterns and verify account holder identity if suspicious activity continues."
            )
        elif risk_score >= cls.LOW_MEDIUM_THRESHOLD:
            return (
                "Continue standard monitoring. "
                "Some unusual patterns detected but no immediate action required. "
                "Track for trend analysis."
            )
        else:
            return (
                "No action required. "
                "Transaction pattern is within normal range. Continue standard compliance procedures."
            )

    @classmethod
    def _format_text_report(cls, report: dict[str, Any]) -> str:
        """Generate human-readable formatted text report."""
        lines = []
        lines.append("=" * 70)
        lines.append("FINANCIAL RISK COMPLIANCE REPORT")
        lines.append("=" * 70)
        lines.append("")

        # Header information
        lines.append(f"Report ID: {report['report_id']}")
        lines.append(f"Generated: {report['timestamp']}")
        lines.append(f"Document: {report['document_name']}")
        lines.append("")

        # Risk Assessment
        lines.append("-" * 70)
        lines.append("RISK ASSESSMENT")
        lines.append("-" * 70)
        lines.append(f"Risk Level: {report['risk_level']} ({report['risk_score']}/100)")
        lines.append(f"ML Anomaly Score: {report['anomaly_score']}")
        lines.append(f"Fraud Verdict: {'YES - Fraudulent activity detected' if report['is_fraud'] else 'NO - Activity within normal range'}")
        lines.append("")

        # Detected Issues
        lines.append("-" * 70)
        lines.append("DETECTED ISSUES")
        lines.append("-" * 70)
        if report["detected_issues"]:
            for idx, issue in enumerate(report["detected_issues"], 1):
                lines.append(f"{idx}. {issue}")
        else:
            lines.append("No significant issues detected.")
        lines.append("")

        # Key Metrics
        lines.append("-" * 70)
        lines.append("KEY TRANSACTION METRICS")
        lines.append("-" * 70)
        metrics = report["key_metrics"]
        lines.append(f"Total Transactions: {metrics['total_transactions']}")
        lines.append(f"Total Debited: ${metrics['total_debited']:,.2f}")
        lines.append(f"Total Credited: ${metrics['total_credited']:,.2f}")
        lines.append(f"High-Risk Merchants: {metrics['high_risk_merchants']}")
        lines.append(f"Max Transaction: ${metrics['max_transaction_amount']:,.2f}")
        lines.append(f"Unique Merchants: {metrics['unique_merchants']}")
        lines.append(f"Rapid Transactions (5min): {metrics['rapid_transactions']}")
        lines.append(f"Large Debits: {metrics['large_debits']}")
        lines.append("")

        # Recommendation
        lines.append("-" * 70)
        lines.append("RECOMMENDATION")
        lines.append("-" * 70)
        lines.append(report["recommendation"])
        lines.append("")

        # Document Insights (if available)
        if "document_insights" in report:
            lines.append("-" * 70)
            lines.append("DOCUMENT INSIGHTS")
            lines.append("-" * 70)
            insights = report["document_insights"]
            for key, value in insights.items():
                lines.append(f"{key.replace('_', ' ').title()}: {value}")
            lines.append("")

        lines.append("=" * 70)
        lines.append("END OF REPORT")
        lines.append("=" * 70)

        return "\n".join(lines)

    @classmethod
    def generate_summary_report(cls, report: dict[str, Any]) -> str:
        """Generate short summary version of report for quick review.

        Args:
            report: Full report dictionary from generate_financial_risk_report

        Returns:
            Condensed text summary (3-5 lines)
        """
        risk_emoji = {
            "HIGH": "🔴",
            "MEDIUM": "🟡",
            "LOW-MEDIUM": "🟠",
            "LOW": "🟢",
        }
        emoji = risk_emoji.get(report["risk_level"], "⚪")

        summary_lines = [
            f"{emoji} {report['risk_level']} Risk Score: {report['risk_score']}/100",
            f"Document: {report['document_name']}",
        ]

        if report["detected_issues"]:
            issues_summary = ", ".join(report["detected_issues"][:3])
            if len(report["detected_issues"]) > 3:
                issues_summary += f" (+{len(report['detected_issues']) - 3} more)"
            summary_lines.append(f"Issues: {issues_summary}")

        # Extract action from recommendation
        rec = report["recommendation"]
        if "URGENT" in rec:
            summary_lines.append("Action: Immediate manual review required")
        elif "Manual compliance review" in rec:
            summary_lines.append("Action: Manual compliance review required")
        elif "Enhanced monitoring" in rec:
            summary_lines.append("Action: Enhanced monitoring recommended")
        elif "Continue standard monitoring" in rec:
            summary_lines.append("Action: Continue monitoring")
        else:
            summary_lines.append("Action: No immediate action required")

        return " | ".join(summary_lines)


# Example usage
if __name__ == "__main__":
    # Demo: Generate sample report
    print("=" * 70)
    print("DEMO: Financial Risk Report Generator")
    print("=" * 70)
    print()

    # Sample high-risk scenario
    demo_features = {
        "total_transactions": 8,
        "total_debited": 3550.0,
        "total_credited": 0.0,
        "high_risk_merchants": 3,
        "max_amount": 900.0,
        "unique_merchants": 4,
        "txn_velocity_5min": 2,
        "large_debit_transactions": 4,
        "amount_spike_ratio": 8.5,
    }

    demo_transactions = [
        {"merchant": "LuckyStar Casino", "amount": 500.0, "type": "debit"},
        {"merchant": "LuckyStar Casino", "amount": 450.0, "type": "debit"},
        {"merchant": "CryptoExchange BTC", "amount": 700.0, "type": "debit"},
        {"merchant": "Wire Transfer - Unknown", "amount": 900.0, "type": "debit"},
        {"merchant": "ATM Withdrawal", "amount": 300.0, "type": "debit"},
        {"merchant": "ATM Withdrawal", "amount": 350.0, "type": "debit"},
        {"merchant": "MoneyGram Transfer", "amount": 250.0, "type": "debit"},
        {"merchant": "Western Union", "amount": 100.0, "type": "debit"},
    ]

    document_insights = {
        "bank_name": "HDFC Bank",
        "account_type": "Savings",
        "statement_period": "Jan 2024",
        "account_holder": "[REDACTED]",
    }

    # Generate report
    report = ReportGenerator.generate_financial_risk_report(
        risk_score=78.5,
        anomaly_score=0.82,
        is_fraud=True,
        features=demo_features,
        transactions=demo_transactions,
        document_name="HDFC_Statement_Jan2024.pdf",
        document_insights=document_insights,
    )

    # Print formatted report
    print(report["formatted_report"])
    print()

    # Print summary
    print("-" * 70)
    print("SUMMARY VERSION:")
    print("-" * 70)
    print(ReportGenerator.generate_summary_report(report))
    print()

    # Print JSON structure
    print("-" * 70)
    print("JSON STRUCTURE (for API response):")
    print("-" * 70)
    import json

    # Don't include formatted_report in JSON (too verbose)
    json_report = {k: v for k, v in report.items() if k != "formatted_report"}
    print(json.dumps(json_report, indent=2))
