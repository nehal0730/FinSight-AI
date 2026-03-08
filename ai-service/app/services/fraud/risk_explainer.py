"""Risk explainer service for generating human-readable fraud explanations.

Analyzes engineered features and transaction patterns to produce clear,
actionable explanations for why a transaction set was flagged as risky.
"""

from __future__ import annotations

from typing import Any


class RiskExplainer:
    """Generate human-readable explanations for fraud risk scores."""

    # Explanation thresholds
    HIGH_RISK_MERCHANT_THRESHOLD = 1
    LARGE_DEBIT_THRESHOLD = 1
    RAPID_REPEAT_THRESHOLD = 2
    VELOCITY_5MIN_THRESHOLD = 1
    VELOCITY_1HOUR_THRESHOLD = 3
    SPIKE_RATIO_THRESHOLD = 5.0
    HIGH_VALUE_THRESHOLD = 3
    AVG_DAILY_TXN_THRESHOLD = 10.0
    CASH_LIKE_THRESHOLD = 2
    STD_DEV_THRESHOLD = 20000.0
    ZSCORE_THRESHOLD = 3.0

    @classmethod
    def explain_risk(
        cls,
        features: dict[str, float],
        transactions: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """Generate list of human-readable risk explanations from features.

        Args:
            features: Engineered feature dictionary from FeatureEngineer
            transactions: Optional raw transaction list for merchant details

        Returns:
            List of explanation strings ordered by severity
        """
        explanations = []

        # High-risk merchant activity
        high_risk_count = features.get("high_risk_merchants", 0)
        if high_risk_count >= cls.HIGH_RISK_MERCHANT_THRESHOLD:
            merchant_types = cls._identify_high_risk_types(transactions)
            if merchant_types:
                explanations.append(
                    f"Transactions with high-risk merchants detected: {', '.join(merchant_types)}"
                )
            else:
                count_str = "Multiple" if high_risk_count > 1 else "A"
                explanations.append(
                    f"{count_str} transaction{'s' if high_risk_count > 1 else ''} "
                    f"with gambling, casino, or crypto merchants"
                )

        # Large debit transactions
        large_debits = features.get("large_debit_transactions", 0)
        if large_debits >= cls.LARGE_DEBIT_THRESHOLD:
            max_txn = features.get("max_transaction", 0)
            explanations.append(
                f"Unusually large withdrawal amount detected (up to {cls._format_amount(max_txn)})"
            )

        # Rapid repeated transactions
        rapid_repeats = features.get("rapid_same_merchant_transactions", 0)
        if rapid_repeats >= cls.RAPID_REPEAT_THRESHOLD:
            explanations.append(
                "Multiple rapid transactions to the same merchant within short time window"
            )

        # Transaction velocity (very suspicious)
        velocity_5min = features.get("txn_velocity_5min", 0)
        if velocity_5min >= cls.VELOCITY_5MIN_THRESHOLD:
            explanations.append(
                f"Extremely high transaction velocity: {int(velocity_5min)} transactions within 5 minutes"
            )

        velocity_1hour = features.get("txn_velocity_1hour", 0)
        if velocity_1hour >= cls.VELOCITY_1HOUR_THRESHOLD:
            explanations.append(
                f"High transaction frequency: {int(velocity_1hour)} transactions within 1 hour"
            )

        # Spending spikes
        spike_ratio = features.get("amount_spike_ratio", 0)
        if spike_ratio >= cls.SPIKE_RATIO_THRESHOLD:
            explanations.append(
                f"Abnormal spending spike detected ({spike_ratio:.1f}x above average)"
            )

        # High-value transaction concentration
        high_value_count = features.get("high_value_transactions", 0)
        if high_value_count >= cls.HIGH_VALUE_THRESHOLD:
            explanations.append(
                f"Multiple high-value transactions detected ({int(high_value_count)})"
            )

        # Unusual daily transaction frequency
        avg_daily = features.get("avg_txn_per_day", 0)
        if avg_daily >= cls.AVG_DAILY_TXN_THRESHOLD:
            explanations.append(
                f"Unusually high transaction frequency ({avg_daily:.1f} transactions per day)"
            )

        # Cash-like activity patterns
        cash_like = features.get("cash_like_activity", 0)
        if cash_like >= cls.CASH_LIKE_THRESHOLD:
            explanations.append(
                "Multiple ATM or cash-equivalent transactions detected"
            )

        # High transaction volatility
        std_dev = features.get("transaction_std_dev", 0)
        if std_dev >= cls.STD_DEV_THRESHOLD:
            explanations.append(
                "High variation in transaction amounts (inconsistent spending pattern)"
            )

        # Statistical outliers
        zscore = features.get("max_amount_zscore", 0)
        if zscore >= cls.ZSCORE_THRESHOLD:
            explanations.append(
                f"Transaction amount significantly deviates from normal pattern (z-score: {zscore:.1f})"
            )

        # If no specific patterns found but score is high
        if not explanations:
            explanations.append(
                "Transaction pattern differs from typical behavior (ML model confidence)"
            )

        return explanations

    @staticmethod
    def _identify_high_risk_types(
        transactions: list[dict[str, Any]] | None
    ) -> list[str]:
        """Extract specific high-risk merchant categories from transactions."""
        if not transactions:
            return []

        risk_categories = set()
        high_risk_keywords = {
            "casino": "Casinos",
            "gambling": "Gambling",
            "crypto": "Cryptocurrency exchanges",
            "bitcoin": "Cryptocurrency exchanges",
            "forex": "Forex trading",
            "betting": "Betting sites",
            "lottery": "Lottery",
            "atm": "ATM withdrawals",
            "nightclub": "Nightclubs",
            "adult": "Adult entertainment",
        }

        for txn in transactions:
            merchant = txn.get("merchant", "").lower()
            for keyword, category in high_risk_keywords.items():
                if keyword in merchant and category not in risk_categories:
                    risk_categories.add(category)

        return sorted(risk_categories)

    @staticmethod
    def _format_amount(amount: float) -> str:
        """Format amount with currency symbol."""
        if amount >= 100000:
            return f"${amount/1000:.0f}K"
        elif amount >= 1000:
            return f"${amount:,.0f}"
        else:
            return f"${amount:.2f}"

    @classmethod
    def explain_combined_verdict(
        cls,
        features: dict[str, float],
        fraud_score: float,
        anomaly_score: float,
        combined_score: float,
        is_fraud: bool,
        transactions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Generate comprehensive explanation combining rules and ML insights.

        Args:
            features: Engineered feature dictionary
            fraud_score: Rule-based score (0-100)
            anomaly_score: ML anomaly score (0-1)
            combined_score: Hybrid score (0-100)
            is_fraud: Final fraud verdict
            transactions: Optional raw transaction list

        Returns:
            {
                "verdict": str,
                "confidence": str,
                "primary_reasons": list[str],
                "risk_factors": {
                    "rule_based_score": float,
                    "ml_anomaly_score": float,
                    "combined_score": float
                },
                "recommendation": str
            }
        """
        primary_reasons = cls.explain_risk(features, transactions)

        # Determine confidence level
        if combined_score >= 70:
            confidence = "High"
        elif combined_score >= 45:
            confidence = "Medium"
        else:
            confidence = "Low"

        # Generate verdict text
        if is_fraud:
            if combined_score >= 70:
                verdict = "HIGH RISK - Fraudulent activity strongly suspected"
            else:
                verdict = "MEDIUM RISK - Suspicious activity detected"
        else:
            if combined_score >= 35:
                verdict = "LOW-MEDIUM RISK - Some unusual patterns detected"
            else:
                verdict = "LOW RISK - Activity appears normal"

        # Generate recommendation
        if is_fraud and combined_score >= 70:
            recommendation = "Immediate review recommended. Consider blocking account or flagging for manual investigation."
        elif is_fraud:
            recommendation = "Manual review recommended. Monitor account for additional suspicious activity."
        elif combined_score >= 35:
            recommendation = "Continue monitoring. No immediate action required."
        else:
            recommendation = "No action required. Transaction pattern is within normal range."

        return {
            "verdict": verdict,
            "confidence": confidence,
            "primary_reasons": primary_reasons[:5],  # Top 5 reasons
            "risk_factors": {
                "rule_based_score": round(fraud_score, 2),
                "ml_anomaly_score": round(anomaly_score, 4),
                "combined_score": round(combined_score, 2),
            },
            "recommendation": recommendation,
        }


def explain_fraud_risk(
    features: dict[str, float],
    transactions: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Convenience function for generating risk explanations."""
    return RiskExplainer.explain_risk(features, transactions)
