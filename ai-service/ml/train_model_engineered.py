"""Train fraud detection model on engineered features (not raw Kaggle data).

This creates a synthetic dataset of transactions with corresponding fraud labels,
engineers 28 features from them, and trains the Isolation Forest model to work
with our actual transaction processing pipeline.
"""

import argparse
import csv
import json
import numpy as np
import joblib
from pathlib import Path
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from dataclasses import dataclass

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.fraud.feature_engineering import FeatureEngineer


@dataclass
class ModelArtifacts:
    """Bundle trained model with metadata."""
    model: IsolationForest
    scaler: StandardScaler
    feature_names: list
    contamination: float
    n_samples: int
    fraud_count: int


def generate_synthetic_transactions(n_normal=9500, n_fraud=500, random_seed=42):
    """Generate realistic synthetic transaction dataset with fraud labels.
    
    Generates 10k transactions matching real-world patterns:
    - Normal: Groceries, bills, salary, shopping (95%)
    - Fraud: Casinos, crypto, rapid ATM, unusual hours (5%)
    
    Args:
        n_normal: Number of normal transactions (default: 9500)
        n_fraud: Number of fraudulent transactions (default: 500)
        random_seed: For reproducibility
        
    Returns:
        Tuple of (transactions_list, fraud_labels)
    """
    np.random.seed(random_seed)
    transactions = []
    labels = []
    
    base_date = datetime(2025, 1, 1)
    
    # === NORMAL TRANSACTIONS (95%) ===
    normal_merchants = {
        "daily": ["GROCERY", "PHARMACY", "GAS_STATION", "RESTAURANT", "COFFEE_SHOP"],
        "bills": ["ELECTRICITY", "WATER_BILL", "INTERNET_PROVIDER", "PHONE_BILL"],
        "income": ["SALARY_DEPOSIT", "FREELANCE_PAYMENT", "DIVIDEND_CREDIT"],
        "shopping": ["AMAZON", "RETAIL_STORE", "BOOKSTORE", "CLOTHING_STORE"],
        "healthcare": ["HOSPITAL", "DOCTOR_CLINIC", "DENTAL_CARE"],
        "education": ["UNIVERSITY_FEE", "ONLINE_COURSE", "TUITION"],
    }
    
    for i in range(n_normal):
        # Random date over 90 days
        date = base_date + timedelta(
            days=int(np.random.randint(0, 90)),
            hours=int(np.random.randint(8, 22))  # Business hours
        )
        
        # Select category and merchant
        category = np.random.choice(list(normal_merchants.keys()))
        merchant = np.random.choice(normal_merchants[category])
        
        # Realistic amount distributions by category
        if category == "daily":
            amount = np.random.lognormal(mean=5.5, sigma=1.2)  # $50-$500 avg
        elif category == "bills":
            amount = np.random.lognormal(mean=6.5, sigma=0.8)  # $200-$2000
        elif category == "income":
            amount = np.random.lognormal(mean=9.5, sigma=0.5)  # $5k-$30k salary
            merchant = merchant  # Credit type
        elif category == "shopping":
            amount = np.random.lognormal(mean=6.0, sigma=1.5)  # $100-$1000
        elif category == "healthcare":
            amount = np.random.lognormal(mean=7.0, sigma=1.0)  # $500-$3000
        else:  # education
            amount = np.random.lognormal(mean=8.0, sigma=0.7)  # $1k-$10k
        
        # Type: income = credit, others = debit
        txn_type = "credit" if category == "income" else "debit"
        
        transactions.append({
            "date": date.strftime("%Y-%m-%d %H:%M:%S"),
            "amount": float(np.clip(amount, 10, 100000)),  # Cap amounts
            "type": txn_type,
            "merchant": merchant
        })
        labels.append(0)  # Normal
    
    # === FRAUDULENT TRANSACTIONS (5%) ===
    fraud_patterns = {
        "casino": ["CASINO", "GAMBLING_SITE", "ONLINE_POKER", "SPORTS_BETTING"],
        "crypto": ["CRYPTO_EXCHANGE", "BITCOIN_ATM", "NFT_MARKETPLACE"],
        "atm": ["ATM_WITHDRAWAL", "CASH_ADVANCE"],
        "nightlife": ["NIGHTCLUB", "BAR_LATE_NIGHT"],
        "suspicious": ["UNKNOWN_MERCHANT", "OVERSEAS_TRANSFER", "WIRE_TRANSFER"]
    }
    
    for i in range(n_fraud):
        # Fraud often at unusual hours (late night / early morning)
        date = base_date + timedelta(
            days=int(np.random.randint(0, 90)),
            hours=int(np.random.choice([0, 1, 2, 3, 23]))  # Unusual hours
        )
        
        # Select fraud pattern
        pattern = np.random.choice(list(fraud_patterns.keys()))
        merchant = np.random.choice(fraud_patterns[pattern])
        
        # Fraud characteristics: high amounts
        if pattern in ["casino", "crypto"]:
            amount = np.random.uniform(15000, 150000)  # Large risky spending
        elif pattern == "atm":
            # Rapid ATM withdrawals (velocity pattern)
            amount = np.random.uniform(5000, 20000)
        else:
            amount = np.random.uniform(8000, 80000)
        
        transactions.append({
            "date": date.strftime("%Y-%m-%d %H:%M:%S"),
            "amount": float(amount),
            "type": "debit",  # Fraud typically debits
            "merchant": merchant
        })
        labels.append(1)  # Fraud
    
    # Shuffle to mix normal and fraud
    combined = list(zip(transactions, labels))
    np.random.shuffle(combined)
    transactions, labels = zip(*combined)
    
    return list(transactions), np.array(labels)


def save_synthetic_transactions(
    transactions: list[dict],
    labels: np.ndarray,
    output_path: str,
):
    """Persist generated synthetic transactions to CSV for inspection."""
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["date", "amount", "type", "merchant", "fraud"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for txn, label in zip(transactions, labels):
            writer.writerow(
                {
                    "date": txn.get("date", ""),
                    "amount": txn.get("amount", 0.0),
                    "type": txn.get("type", ""),
                    "merchant": txn.get("merchant", ""),
                    "fraud": int(label),
                }
            )

    print(f"[INFO] Synthetic dataset saved: {out_path}")


class FraudDetectionTrainer:
    """Train Isolation Forest on engineered features."""
    
    def __init__(self, contamination=0.05, n_estimators=200, random_state=42):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.model = None
        self.scaler = None
        self.engineer = FeatureEngineer()
        self.feature_names = None
        
    def train_pipeline(self, transactions, labels=None):
        """Train full pipeline: engineer features → normalize → fit model.
        
        Args:
            transactions: List of transaction dicts
            labels: Fraud labels (0=normal, 1=fraud) [optional, for validation]
            
        Returns:
            ModelArtifacts with trained model and metadata
        """
        print("\n" + "="*60)
        print("  FinSight AI — Fraud Detection Model Training")
        print("="*60)
        
        # Step 1: Engineer features
        print(f"[INFO] Engineering features from {len(transactions)} transactions...")
        features_list = []
        
        for txn in transactions:
            # Create a single-item list for feature engineering
            features = self.engineer.engineer_features([txn])
            features_list.append(list(features.values()))
        
        X = np.array(features_list)
        self.feature_names = list(self.engineer.engineer_features([transactions[0]]).keys())
        
        print(f"[INFO] Shape: ({X.shape[0]}, {X.shape[1]})")
        print(f"[INFO] Features: {X.shape[1]} (dimension matches feature engineering output)")
        
        # Step 2: Normalize
        print("[INFO] Preprocessing: fitting StandardScaler...")
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        print(f"[INFO] Data shape after scaling: {X_scaled.shape}")
        
        # Step 3: Train Isolation Forest
        print(f"[INFO] Training IsolationForest (n_estimators={self.n_estimators}, contamination={self.contamination})...")
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1
        )
        self.model.fit(X_scaled)
        
        # Predictions
        predictions = self.model.predict(X_scaled)
        anomaly_scores = self.model.score_samples(X_scaled)
        
        n_fraud = (predictions == -1).sum()
        fraud_rate = n_fraud / len(predictions) * 100
        
        print(f"[INFO] Transactions flagged: {n_fraud} ({fraud_rate:.3f}%)")
        
        # Step 4: Evaluation (if labels provided)
        if labels is not None:
            self._evaluate(predictions, labels)
        
        # Step 5: Summary
        print("\n" + "="*60)
        print("[DONE] Model ready for inference pipeline")
        print("="*60 + "\n")
        
        return ModelArtifacts(
            model=self.model,
            scaler=self.scaler,
            feature_names=self.feature_names,
            contamination=self.contamination,
            n_samples=len(transactions),
            fraud_count=n_fraud
        )
    
    def _evaluate(self, predictions, true_labels):
        """Print evaluation metrics."""
        from sklearn.metrics import classification_report, confusion_matrix
        
        print("\n" + "="*60)
        print("CLASSIFICATION REPORT")
        print("="*60)
        
        # Convert predictions: -1 (anomaly) → 1 (fraud), 1 (normal) → 0
        pred_labels = (predictions == -1).astype(int)
        
        print(classification_report(true_labels, pred_labels, 
                                   target_names=["Normal", "Fraud"]))
        
        print("CONFUSION MATRIX")
        print(confusion_matrix(true_labels, pred_labels))
    
    def save_artifacts(
        self,
        model_dir="models",
        scaler_dir="models",
        model_filename="fraud_model_engineered.pkl",
        scaler_filename="scaler_engineered.pkl",
        feature_names_filename="feature_names_engineered.json",
    ):
        """Save model, scaler, and feature names with engineered-specific names."""
        Path(model_dir).mkdir(parents=True, exist_ok=True)
        Path(scaler_dir).mkdir(parents=True, exist_ok=True)
        
        # Save model
        model_path = Path(model_dir) / model_filename
        joblib.dump(self.model, model_path)
        print(f"[INFO] Model saved:  {model_path}")
        
        # Save scaler
        scaler_path = Path(scaler_dir) / scaler_filename
        joblib.dump(self.scaler, scaler_path)
        print(f"[INFO] Scaler saved: {scaler_path}")
        
        # Save feature names for reference
        meta_path = Path(model_dir) / feature_names_filename
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.feature_names, f, indent=2)
        print(f"[INFO] Features saved: {meta_path}")


def main():
    parser = argparse.ArgumentParser(description="Train fraud detection model on engineered features")
    parser.add_argument("--n-normal", type=int, default=9500, help="Number of normal transactions")
    parser.add_argument("--n-fraud", type=int, default=500, help="Number of fraudulent transactions")
    parser.add_argument("--contamination", type=float, default=0.05, help="Anomaly contamination rate")
    parser.add_argument("--model-dir", type=str, default="models", help="Model save directory")
    parser.add_argument("--model-file", type=str, default="fraud_model_engineered.pkl", help="Model artifact filename")
    parser.add_argument("--scaler-file", type=str, default="scaler_engineered.pkl", help="Scaler artifact filename")
    parser.add_argument("--feature-names-file", type=str, default="feature_names_engineered.json", help="Feature names artifact filename")
    parser.add_argument(
        "--synthetic-output",
        type=str,
        default="data/synthetic_transactions.csv",
        help="Path to save generated synthetic transaction rows",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    
    args = parser.parse_args()
    
    # Generate synthetic data
    print(f"[INFO] Generating 10k synthetic transactions: {args.n_normal} normal, {args.n_fraud} fraud...")
    transactions, labels = generate_synthetic_transactions(
        n_normal=args.n_normal,
        n_fraud=args.n_fraud,
        random_seed=args.seed
    )

    # Save generated synthetic rows for manual inspection/debugging.
    save_synthetic_transactions(
        transactions=transactions,
        labels=labels,
        output_path=args.synthetic_output,
    )
    
    # Train
    trainer = FraudDetectionTrainer(
        contamination=args.contamination,
        random_state=args.seed
    )
    artifacts = trainer.train_pipeline(transactions, labels)
    trainer.save_artifacts(
        model_dir=args.model_dir,
        model_filename=args.model_file,
        scaler_filename=args.scaler_file,
        feature_names_filename=args.feature_names_file,
    )


if __name__ == "__main__":
    main()
