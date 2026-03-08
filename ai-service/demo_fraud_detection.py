"""
Demo: Fraud Detection on Bank Statement Text

Shows complete workflow:
1. Extract transactions from bank statement
2. Engineer 28 features
3. Score with trained Isolation Forest model
4. Get fraud risk assessment
"""

from app.services.transaction_extractor import TransactionExtractor
from app.services.feature_engineering import FeatureEngineer
from ml.predict import get_inference_engine
import numpy as np


def main():
    print("\n" + "="*60)
    print("  FinSight AI - Fraud Detection Demo")
    print("="*60 + "\n")
    
    # Sample bank statement text (realistic patterns)
    bank_statement = """
    ACCOUNT STATEMENT - January 2025
    
    Date          Description                    Debit       Credit
    ----------------------------------------------------------------
    05 Jan 2025   POS GROCERY_STORE             1,200.00
    06 Jan 2025   UPI PHARMACY                    450.00
    07 Jan 2025   NEFT SALARY_DEPOSIT                      45,000.00
    08 Jan 2025   ATM_WITHDRAWAL               20,000.00
    08 Jan 2025   ATM_WITHDRAWAL               20,000.00
    08 Jan 2025   ATM_WITHDRAWAL               20,000.00
    09 Jan 2025   POS CASINO                   85,000.00
    10 Jan 2025   CRYPTO_EXCHANGE             150,000.00
    11 Jan 2025   POS RESTAURANT                  800.00
    """
    
    print("[1] Extracting transactions from bank statement...")
    extractor = TransactionExtractor()
    transactions = extractor.extract_transactions(bank_statement)
    
    print(f"[OK] Found {len(transactions)} transactions:\n")
    for i, txn in enumerate(transactions, 1):
        print(f"  {i}. {txn['date']} | {txn['merchant']:25} | Rs.{txn['amount']:>10,.2f} | {txn['type']}")
    
    print(f"\n[2] Engineering 28-D feature vector...")
    engineer = FeatureEngineer()
    features = engineer.engineer_features(transactions)
    basic_fraud_score = engineer.compute_fraud_score(features)
    
    print(f"[OK] Features extracted:")
    print(f"  - Total transactions: {features['total_transactions']}")
    print(f"  - Avg txns per day: {features['avg_txn_per_day']:.2f}")
    print(f"  - High-risk merchants: {features['high_risk_merchants']}")
    print(f"  - Legitimate merchants: {features['legitimate_merchants']}")
    print(f"  - Transaction velocity (5min): {features['txn_velocity_5min']}")
    print(f"  - Amount spike ratio: {features['amount_spike_ratio']:.2f}")
    print(f"  - Max amount z-score: {features['max_amount_zscore']:.2f}")
    print(f"  - Max to median ratio: {features['max_to_median_ratio']:.2f}")
    print(f"  - Basic fraud score: {basic_fraud_score:.1f}/100")
    
    print(f"\n[3] Scoring with Isolation Forest model...")
    features_array = np.array(list(features.values())).reshape(1, -1)
    inference = get_inference_engine()
    result = inference.predict(features_array)
    
    print(f"[OK] ML Model Results:")
    print(f"  - Anomaly Score: {result['anomaly_score']:.4f}")
    print(f"  - Is Fraud: {result['is_fraud']}")
    print(f"  - Risk Level: {result['risk_level'].upper()}")
    
    print(f"\n[4] Fraud Analysis Summary:")
    print(f"{'='*60}")
    
    if result['is_fraud'] or basic_fraud_score > 50:
        print("[WARNING] HIGH FRAUD RISK DETECTED")
        print("\nRed Flags:")
        if features['high_risk_merchants'] > 0:
            print("  • High-risk merchants detected (Casino, Crypto)")
        if features['txn_velocity_5min'] > 2:
            print("  • Rapid transaction velocity (multiple ATM withdrawals)")
        if features['amount_spike_ratio'] > 5:
            print("  • Unusual spending spike detected")
        if features['large_debit_transactions'] > 0:
            print("  • Large debit transactions flagged")
        if features['avg_txn_per_day'] > 10:
            print(f"  • High transaction frequency ({features['avg_txn_per_day']:.1f} transactions/day)")
        if features['max_amount_zscore'] > 3:
            print(f"  • Extreme amount outlier detected (z-score: {features['max_amount_zscore']:.2f})")
    else:
        print("[OK] LOW FRAUD RISK")
        print("  Transaction patterns appear normal.")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
