import re
from datetime import datetime, timedelta
from statistics import mean, stdev, median


class FeatureEngineer:
    """Convert structured transactions into ML-ready numerical features for fraud detection."""

    # High-risk merchant patterns (keywords indicate suspicious activity)
    HIGH_RISK_PATTERNS = {
        "casino",
        "gambling",
        "crypto",
        "bitcoin",
        "forex",
        "betting",
        "lottery",
        "atm",
        "nightclub",
        "bar",
        "adult",
        "money transfer",
        "wire transfer",
    }

    # Legitimate merchant patterns (low-risk indicators)
    LEGITIMATE_PATTERNS = {
        "salary",
        "payroll",
        "employer",
        "refund",
        "interest",
        "dividend",
        "government",
        "utility",
        "school",
        "hospital",
        "insurance",
        "mortgage",
        "rent",
        "grocery",
        "groceries",
        "pharmacy",
        "supermarket",
    }

    @classmethod
    def engineer_features(cls, transactions: list[dict[str, any]]) -> dict[str, float]:
        """
        Extract comprehensive fraud-detection features from structured transactions.

        Args:
            transactions: List of transaction dicts with keys:
                - amount: float
                - type: str (debit/credit)
                - merchant: str
                - date: str (YYYY-MM-DD format)
                - timestamp: str (optional, ISO format for velocity features)

        Returns:
            Dictionary of numerical features for ML models (all float values).
        """
        if not transactions or len(transactions) == 0:
            return cls._empty_feature_set()

        return {
            # Basic transaction statistics
            **cls._frequency_features(transactions),
            # Amount-based risk signals
            **cls._amount_features(transactions),
            # Merchant risk scoring
            **cls._merchant_features(transactions),
            # Behavioral patterns
            **cls._behavioral_features(transactions),
            # Transaction type analysis
            **cls._transaction_type_features(transactions),
            # Time-based velocity features
            **cls._velocity_features(transactions),
            # Spending spike detection
            **cls._spike_features(transactions),
        }

    @staticmethod
    def _frequency_features(transactions: list[dict[str, any]]) -> dict[str, float]:
        """Features based on transaction frequency and count."""
        total_txns = len(transactions)
        debits = sum(1 for t in transactions if t.get("type", "").lower() == "debit")
        credits = sum(1 for t in transactions if t.get("type", "").lower() == "credit")

        # Calculate average transactions per day
        dates = []
        for t in transactions:
            date_str = t.get("date") or t.get("timestamp", "")
            if date_str:
                try:
                    # Parse date (supports YYYY-MM-DD or ISO format)
                    if "T" in date_str or " " in date_str:
                        date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    else:
                        date_obj = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    dates.append(date_obj.date())
                except (ValueError, AttributeError):
                    pass
        
        # Calculate transactions per day
        if dates and len(dates) > 0:
            unique_days = len(set(dates))
            avg_txn_per_day = float(total_txns) / float(unique_days) if unique_days > 0 else float(total_txns)
        else:
            avg_txn_per_day = float(total_txns)  # Assume all in one day if no dates

        return {
            "total_transactions": float(total_txns),
            "total_debits": float(debits),
            "total_credits": float(credits),
            "debit_credit_ratio": float(debits / credits) if credits > 0 else float(debits),
            "avg_txn_per_day": avg_txn_per_day,
        }

    @staticmethod
    def _amount_features(transactions: list[dict[str, any]]) -> dict[str, float]:
        """Features based on transaction amounts and variance."""
        amounts = [t.get("amount", 0) for t in transactions if t.get("amount")]

        if not amounts:
            return {
                "avg_transaction_amount": 0.0,
                "max_transaction": 0.0,
                "min_transaction": 0.0,
                "transaction_std_dev": 0.0,
                "median_transaction": 0.0,
                "high_value_transactions": 0.0,
                "max_amount_zscore": 0.0,
            }

        avg_amount = mean(amounts)
        max_amount = max(amounts)
        min_amount = min(amounts)
        std_amount = stdev(amounts) if len(amounts) > 1 else 0.0
        median_amount = median(amounts)

        # High-value transactions (above 75th percentile) - FIXED: >= instead of >
        threshold = sorted(amounts)[int(len(amounts) * 0.75)]
        high_value = sum(1 for a in amounts if a >= threshold)

        # Z-score of maximum amount (detect outliers)
        # Formula: (max - mean) / std_dev
        # zscore > 3 is highly suspicious (3 standard deviations from mean)
        max_zscore = (max_amount - avg_amount) / std_amount if std_amount > 0 else 0.0

        return {
            "avg_transaction_amount": float(avg_amount),
            "max_transaction": float(max_amount),
            "min_transaction": float(min_amount),
            "transaction_std_dev": float(std_amount),
            "median_transaction": float(median_amount),
            "high_value_transactions": float(high_value),
            "max_amount_zscore": float(max_zscore),
        }

    @classmethod
    def _merchant_features(cls, transactions: list[dict[str, any]]) -> dict[str, float]:
        """Features based on merchant risk profile."""
        merchants = [t.get("merchant", "").lower() for t in transactions]

        high_risk_count = sum(
            1 for m in merchants if cls._is_high_risk_merchant(m)
        )
        legitimate_count = sum(
            1 for m in merchants if cls._is_legitimate_merchant(m)
        )
        unique_merchants = len(set(merchants))

        return {
            "high_risk_merchants": float(high_risk_count),
            "legitimate_merchants": float(legitimate_count),
            "unique_merchants": float(unique_merchants),
            "merchant_concentration": float(
                1.0 - (unique_merchants / len(merchants)) if merchants else 0.0 # High concentration = suspicious
            ),
        }

    @classmethod
    def _behavioral_features(cls, transactions: list[dict[str, any]]) -> dict[str, float]:
        """Features based on suspicious behavioral patterns."""
        amounts = [t.get("amount", 0) for t in transactions if t.get("amount")]
        merchants = [t.get("merchant", "") for t in transactions]

        # Rapid transaction sequences (same merchant within short sequence)
        rapid_same_merchant = cls._count_rapid_repeats(merchants)

        # Cash-like activity (ATM, transfers)
        cash_activity = sum(
            1 for m in merchants
            if any(kw in m.lower() for kw in ["atm", "cash", "withdrawal", "transfer"])
        )

        # Large debit sequences (potential suspicious spending)
        debits = [
            t.get("amount", 0)
            for t in transactions
            if t.get("type", "").lower() == "debit" and t.get("amount")
        ]
        avg_debit = mean(debits) if debits else 0.0
        large_debits = sum(1 for d in debits if d > avg_debit * 1.5)

        return {
            "rapid_same_merchant_transactions": float(rapid_same_merchant),
            "cash_like_activity": float(cash_activity),
            "large_debit_transactions": float(large_debits),
        }

    @staticmethod
    def _transaction_type_features(transactions: list[dict[str, any]]) -> dict[str, float]:
        """Features analyzing transaction type patterns."""
        debits = [
            t.get("amount", 0)
            for t in transactions
            if t.get("type", "").lower() == "debit" and t.get("amount")
        ]
        credits = [
            t.get("amount", 0)
            for t in transactions
            if t.get("type", "").lower() == "credit" and t.get("amount")
        ]

        total_debited = sum(debits)
        total_credited = sum(credits)

        return {
            "total_debited": float(total_debited),
            "total_credited": float(total_credited),
            "avg_debit_amount": float(mean(debits)) if debits else 0.0,
            "avg_credit_amount": float(mean(credits)) if credits else 0.0,
        }

    @staticmethod
    def _velocity_features(transactions: list[dict[str, any]]) -> dict[str, float]:
        """
        Time-based velocity features (transactions per time window).
        
        Requires 'timestamp' field in ISO format or 'date' with time info.
        If timestamps not available, returns zeros.
        """
        timestamps = []
        for t in transactions:
            ts_str = t.get("timestamp") or t.get("date")
            if ts_str:
                try:
                    # Try parsing ISO format with time
                    if "T" in ts_str or " " in ts_str:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        timestamps.append(ts)
                except (ValueError, AttributeError):
                    pass
        
        if len(timestamps) < 2:
            return {
                "txn_velocity_5min": 0.0,
                "txn_velocity_1hour": 0.0,
                "txn_velocity_24hour": 0.0,
            }
        
        # Sort by time
        timestamps.sort()
        reference_time = timestamps[-1]  # Most recent transaction
        
        # Count transactions in time windows
        five_min_ago = reference_time - timedelta(minutes=5)
        one_hour_ago = reference_time - timedelta(hours=1)
        twentyfour_hour_ago = reference_time - timedelta(hours=24)
        
        velocity_5min = sum(1 for ts in timestamps if ts >= five_min_ago)
        velocity_1hour = sum(1 for ts in timestamps if ts >= one_hour_ago)
        velocity_24hour = sum(1 for ts in timestamps if ts >= twentyfour_hour_ago)
        
        return {
            "txn_velocity_5min": float(velocity_5min),
            "txn_velocity_1hour": float(velocity_1hour),
            "txn_velocity_24hour": float(velocity_24hour),
        }

    @staticmethod
    def _spike_features(transactions: list[dict[str, any]]) -> dict[str, float]:
        """
        Spending spike detection features.
        
        Detects sudden large transactions compared to normal spending.
        """
        amounts = [t.get("amount", 0) for t in transactions if t.get("amount")]
        
        if not amounts or len(amounts) < 2:
            return {
                "amount_spike_ratio": 0.0,
                "max_to_median_ratio": 0.0,
            }
        
        avg_amount = mean(amounts)
        max_amount = max(amounts)
        median_amount = median(amounts)
        
        # Spike ratio: how much larger is max compared to average
        spike_ratio = max_amount / avg_amount if avg_amount > 0 else 0.0
        
        # Max to median ratio (another spike indicator)
        max_to_median = max_amount / median_amount if median_amount > 0 else 0.0
        
        return {
            "amount_spike_ratio": float(spike_ratio),
            "max_to_median_ratio": float(max_to_median),
        }

    @classmethod
    def _is_high_risk_merchant(cls, merchant: str) -> bool:
        """Check if merchant name matches high-risk patterns."""
        merchant_lower = merchant.lower()
        return any(pattern in merchant_lower for pattern in cls.HIGH_RISK_PATTERNS)

    @classmethod
    def _is_legitimate_merchant(cls, merchant: str) -> bool:
        """Check if merchant name matches legitimate patterns."""
        merchant_lower = merchant.lower()
        return any(pattern in merchant_lower for pattern in cls.LEGITIMATE_PATTERNS)

    @staticmethod
    def _count_rapid_repeats(merchants: list[str], window: int = 3) -> int:
        """Count sequences where same merchant appears multiple times in a window."""
        count = 0
        for i in range(len(merchants) - window + 1):
            window_merchants = merchants[i : i + window]
            # Count if any merchant appears more than once in the window
            if len(window_merchants) != len(set(window_merchants)):
                count += 1
        return count

    @staticmethod
    def _empty_feature_set() -> dict[str, float]:
        """Return a zero-filled feature set for empty transaction lists."""
        return {
            "total_transactions": 0.0,
            "total_debits": 0.0,
            "total_credits": 0.0,
            "debit_credit_ratio": 0.0,
            "avg_txn_per_day": 0.0,
            "avg_transaction_amount": 0.0,
            "max_transaction": 0.0,
            "min_transaction": 0.0,
            "transaction_std_dev": 0.0,
            "median_transaction": 0.0,
            "high_value_transactions": 0.0,
            "max_amount_zscore": 0.0,
            "high_risk_merchants": 0.0,
            "legitimate_merchants": 0.0,
            "unique_merchants": 0.0,
            "merchant_concentration": 0.0,
            "rapid_same_merchant_transactions": 0.0,
            "cash_like_activity": 0.0,
            "large_debit_transactions": 0.0,
            "total_debited": 0.0,
            "total_credited": 0.0,
            "avg_debit_amount": 0.0,
            "avg_credit_amount": 0.0,
            "txn_velocity_5min": 0.0,
            "txn_velocity_1hour": 0.0,
            "txn_velocity_24hour": 0.0,
            "amount_spike_ratio": 0.0,
            "max_to_median_ratio": 0.0,
        }

    @classmethod
    def compute_fraud_score(cls, features: dict[str, float]) -> float:
        """
        Compute a simple fraud risk score (0-100) from features.

        Reasoning:
        - High-risk merchants: +5 points each
        - Large debit transactions: +2 points each
        - Rapid repeats: +3 points each
        - Cash-like activity: +1.5 points each
        - High velocity (5min): +4 points per transaction
        - High velocity (1hour): +1 point per transaction
        - Spending spike: +2 points per spike ratio unit above 10
        - High std dev (volatile): +0.01 per unit of std dev
        - Legitimate merchants: -3 points each

        Returns:
            Float between 0 (low risk) and 100+ (high risk)
        """
        score = 0.0

        # High-risk merchant activity
        score += features.get("high_risk_merchants", 0) * 5.0

        # Large suspicious debits
        score += features.get("large_debit_transactions", 0) * 2.0

        # Rapid repeated merchants
        score += features.get("rapid_same_merchant_transactions", 0) * 3.0

        # Cash-like activity
        score += features.get("cash_like_activity", 0) * 1.5

        # Transaction velocity (high frequency suspicious)
        score += features.get("txn_velocity_5min", 0) * 4.0  # Very high weight
        score += features.get("txn_velocity_1hour", 0) * 1.0

        # Spending spikes (large sudden amounts)
        spike_ratio = features.get("amount_spike_ratio", 0)
        if spike_ratio > 10.0:
            score += (spike_ratio - 10.0) * 2.0  # Penalize spikes above 10x

        # Transaction volatility (high std dev = unusual pattern)
        score += features.get("transaction_std_dev", 0) * 0.01

        # High transaction frequency per day (fraud often increases activity)
        avg_daily = features.get("avg_txn_per_day", 0)
        if avg_daily > 10.0:
            score += (avg_daily - 10.0) * 1.5  # Penalize >10 transactions/day

        # Z-score outliers (transactions much larger than normal)
        zscore = features.get("max_amount_zscore", 0)
        if zscore > 3.0:
            score += (zscore - 3.0) * 3.0  # Strong penalty for >3 std devs

        # Penalize legitimate patterns
        score -= min(features.get("legitimate_merchants", 0) * 3.0, 20.0)

        # Normalize to 0-100
        return max(0.0, min(100.0, score))
