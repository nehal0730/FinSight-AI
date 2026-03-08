from __future__ import annotations

import argparse
import os
import pickle
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")


@dataclass
class ModelArtifacts:
    """Container for trained model components."""

    model: IsolationForest
    scaler: StandardScaler
    feature_names: list[str]
    contamination: float
    metrics: dict[str, Any]
    trained_at: str


class FraudDetectionTrainer:
    """Production-grade Isolation Forest trainer for fraud detection."""

    def __init__(
        self,
        data_path: str,
        model_dir: str = "models",
        plots_dir: str = "reports/plots",
        model_filename: str = "fraud_model_kaggle.pkl",
        scaler_filename: str = "scaler_kaggle.pkl",
        contamination: float = 0.002,
        n_estimators: int = 200,
        random_state: int = 42,
    ):
        self.data_path = Path(data_path)
        self.model_dir = Path(model_dir)
        self.plots_dir = Path(plots_dir)
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state

        self.model_path = self.model_dir / model_filename
        self.scaler_path = self.model_dir / scaler_filename

    def load_data(self) -> tuple[pd.DataFrame, pd.Series | None, list[str]]:
        """
        Load transaction dataset.

        Supports multiple label column names:
        - 'Class' (credit card dataset)
        - 'isFraud' (IEEE-CIS dataset)
        """
        if not self.data_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.data_path}")

        print(f"[INFO] Loading dataset: {self.data_path}")
        df = pd.read_csv(self.data_path)
        print(f"[INFO] Shape: {df.shape}")

        # Detect and extract labels
        labels = None
        if "Class" in df.columns:
            labels = df["Class"]
            features = df.drop(columns=["Class"])
        elif "isFraud" in df.columns:
            labels = df["isFraud"]
            features = df.drop(columns=["isFraud"])
        else:
            features = df

        # Keep numeric columns only
        features = features.select_dtypes(include=[np.number]).copy()
        features = features.fillna(features.median(numeric_only=True))

        if features.empty:
            raise ValueError("No numeric features found in dataset")

        feature_names = list(features.columns)
        print(f"[INFO] Features: {len(feature_names)}")
        print(f"[INFO] Samples:  {len(features)}")

        if labels is not None:
            fraud_pct = labels.mean() * 100
            print(f"[INFO] Fraud rate: {fraud_pct:.4f}% ({labels.sum()} cases)")

        return features, labels, feature_names

    def preprocess(self, features: pd.DataFrame) -> StandardScaler:
        """
        Scale features to zero-mean unit-variance.
        Returns fitted scaler for inference.
        """
        print("[INFO] Preprocessing: fitting StandardScaler...")
        self.scaler = StandardScaler()
        self.X_scaled = self.scaler.fit_transform(features)
        print(f"[INFO] Data shape after scaling: {self.X_scaled.shape}")
        return self.scaler

    def train(self) -> IsolationForest:
        """
        Train Isolation Forest.

        Why Isolation Forest?
        ─────────────────────
        • Unsupervised: Requires no fraud labels, only normal data.
        • Fast: O(n log n) complexity via random binary trees.
        • Effective: Anomalies isolated in fewer splits than normal points.
        • Robust: Handles high-dimensional vectors from feature engineering.

        Key Parameter: contamination
        ────────────────────────────
        Specifies expected fraud rate. The model flags top `contamination`
        fraction of transactions as anomalies.
        - Credit card dataset: ~0.17% → use 0.002
        - IEEE-CIS dataset:    ~3.5%  → use 0.035
        """
        print(
            f"[INFO] Training IsolationForest "
            f"(n_estimators={self.n_estimators}, contamination={self.contamination})..."
        )
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            max_samples="auto",
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1,  # Parallel computation
        )
        self.model.fit(self.X_scaled)
        print("[INFO] Training complete.")
        return self.model

    def evaluate(self, labels: pd.Series | None) -> dict[str, Any]:
        """
        Compute anomaly scores and evaluation metrics.

        Anomaly Score Interpretation
        ────────────────────────────
        model.score_samples(X) returns scores in [-0.5, 0]:
          • Closer to  0:    NORMAL   (isolated slowly, many splits needed)
          • Closer to -0.5:  ANOMALY  (isolated quickly, few splits needed)

        We negate scores for intuitive interpretation:
          • Higher score → more suspicious
          • Lower score → more normal
        """
        print("[INFO] Computing anomaly scores...")

        raw_scores = self.model.score_samples(self.X_scaled)
        anomaly_scores = -raw_scores  # Negate: higher = more suspicious
        predictions = self.model.predict(self.X_scaled)  # 1=normal, -1=anomaly
        binary_preds = np.where(predictions == -1, 1, 0)

        metrics = {
            "anomaly_scores": anomaly_scores,
            "binary_predictions": binary_preds,
            "n_flagged": int(binary_preds.sum()),
            "flag_rate": float(binary_preds.mean()),
        }

        print(
            f"[INFO] Transactions flagged: "
            f"{metrics['n_flagged']} ({metrics['flag_rate']*100:.3f}%)"
        )

        # Supervised metrics (if labels available)
        if labels is not None:
            y_true = labels.values
            print("\n" + "="*60)
            print("CLASSIFICATION REPORT")
            print("="*60)
            print(
                classification_report(
                    y_true,
                    binary_preds,
                    target_names=["Normal", "Fraud"],
                )
            )

            cm = confusion_matrix(y_true, binary_preds)
            print("\nCONFUSION MATRIX")
            print(cm)

            try:
                roc_auc = roc_auc_score(y_true, anomaly_scores)
                avg_prec = average_precision_score(y_true, anomaly_scores)
                print(f"\nROC-AUC Score:       {roc_auc:.4f}")
                print(f"Average Precision:   {avg_prec:.4f}")
                metrics.update({"roc_auc": roc_auc, "avg_precision": avg_prec})
            except Exception as e:
                print(f"[WARN] Could not compute AUC: {e}")

        return metrics

    def visualize(self, anomaly_scores: np.ndarray, labels: pd.Series | None):
        """Plot anomaly score distribution."""
        self.plots_dir.mkdir(parents=True, exist_ok=True)

        plt.figure(figsize=(12, 5))
        if labels is not None:
            plt.hist(
                anomaly_scores[labels == 0],
                bins=100,
                alpha=0.6,
                label="Normal",
                color="steelblue",
                density=True,
            )
            plt.hist(
                anomaly_scores[labels == 1],
                bins=100,
                alpha=0.7,
                label="Fraud",
                color="crimson",
                density=True,
            )
            plt.legend(fontsize=12)
        else:
            plt.hist(anomaly_scores, bins=100, color="steelblue", alpha=0.8)

        plt.xlabel("Anomaly Score (higher = more suspicious)", fontsize=11)
        plt.ylabel("Density", fontsize=11)
        plt.title(
            "FinSight AI — Isolation Forest Anomaly Score Distribution",
            fontsize=13,
            fontweight="bold",
        )
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        out_path = self.plots_dir / "anomaly_score_distribution.png"
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[INFO] Plot saved: {out_path}")

    def save_artifacts(self):
        """Save trained model and scaler for inference."""
        self.model_dir.mkdir(parents=True, exist_ok=True)

        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)

        print(f"[INFO] Model saved:  {self.model_path}")
        print(f"[INFO] Scaler saved: {self.scaler_path}")

    def train_pipeline(
        self, labels: pd.Series | None = None
    ) -> ModelArtifacts:
        """Execute complete training workflow."""
        features, labels, feature_names = self.load_data()
        self.preprocess(features)
        self.train()
        metrics = self.evaluate(labels)
        self.visualize(metrics["anomaly_scores"], labels)
        self.save_artifacts()

        artifacts = ModelArtifacts(
            model=self.model,
            scaler=self.scaler,
            feature_names=feature_names,
            contamination=self.contamination,
            metrics=metrics,
            trained_at=datetime.now(timezone.utc).isoformat(),
        )
        return artifacts


def main():
    parser = argparse.ArgumentParser(
        description="Train Isolation Forest fraud detection model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-path",
        default="data/creditcard.csv",
        help="Path to CSV dataset",
    )
    parser.add_argument(
        "--model-dir",
        default="models",
        help="Directory to save model artifacts",
    )
    parser.add_argument(
        "--model-file",
        default="fraud_model_kaggle.pkl",
        help="Model artifact filename",
    )
    parser.add_argument(
        "--scaler-file",
        default="scaler_kaggle.pkl",
        help="Scaler artifact filename",
    )
    parser.add_argument(
        "--plots-dir",
        default="reports/plots",
        help="Directory to save visualizations",
    )
    parser.add_argument(
        "--contamination",
        type=float,
        default=0.002,
        help="Expected fraud rate (0.002 for creditcard, 0.035 for IEEE-CIS)",
    )
    parser.add_argument(
        "--n-estimators",
        type=int,
        default=200,
        help="Number of isolation trees",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )

    args = parser.parse_args()

    print("\n" + "="*60)
    print("  FinSight AI — Fraud Detection Model Training")
    print("="*60)

    trainer = FraudDetectionTrainer(
        data_path=args.data_path,
        model_dir=args.model_dir,
        plots_dir=args.plots_dir,
        model_filename=args.model_file,
        scaler_filename=args.scaler_file,
        contamination=args.contamination,
        n_estimators=args.n_estimators,
        random_state=args.random_state,
    )

    artifacts = trainer.train_pipeline()

    print("\n" + "="*60)
    print("[DONE] Model ready for inference pipeline")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

