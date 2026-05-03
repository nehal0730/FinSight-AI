from __future__ import annotations

import argparse
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import sys

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    precision_recall_curve,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import learning_curve, train_test_split
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.document.pdf_processor import PDFProcessor
from app.services.fraud.transaction_extractor import TransactionExtractor


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
    """Fraud model trainer with supervised comparison + IsolationForest artifacts."""

    def __init__(
        self,
        data_path: str,
        model_dir: str = "models",
        plots_dir: str = "reports/plots",
        model_filename: str = "fraud_model_kaggle.pkl",
        scaler_filename: str = "scaler_kaggle.pkl",
        metrics_filename: str = "model_comparison_metrics.csv",
        contamination: float = 0.002,
        n_estimators: int = 200,
        test_size: float = 0.2,
        max_samples: int | None = None,
        curve_sample_size: int = 50000,
        cv_folds: int = 3,
        random_state: int = 42,
        business_weight_recall: float = 0.6,
        business_weight_precision: float = 0.3,
        business_weight_accuracy: float = 0.1,
        pdf_paths: list[str] | None = None,
    ):
        self.data_path = Path(data_path)
        self.model_dir = Path(model_dir)
        self.plots_dir = Path(plots_dir)
        self.metrics_filename = metrics_filename
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.test_size = test_size
        self.max_samples = max_samples
        self.curve_sample_size = curve_sample_size
        self.cv_folds = cv_folds
        self.random_state = random_state
        self.business_weight_recall = business_weight_recall
        self.business_weight_precision = business_weight_precision
        self.business_weight_accuracy = business_weight_accuracy
        self.pdf_paths = [str(Path(p)) for p in (pdf_paths or [])]

        self.model_path = self.model_dir / model_filename
        self.scaler_path = self.model_dir / scaler_filename
        self.metrics_path = self.plots_dir / self.metrics_filename
        self.business_summary_path = self.plots_dir / "business_score_summary.json"

        self.X_train: pd.DataFrame | None = None
        self.X_test: pd.DataFrame | None = None
        self.y_train: pd.Series | None = None
        self.y_test: pd.Series | None = None
        self.X_train_scaled: np.ndarray | None = None
        self.X_test_scaled: np.ndarray | None = None
        self.model_summaries: list[dict[str, Any]] = []
        self.curves: dict[str, dict[str, np.ndarray]] = {}
        self.conf_matrices: dict[str, np.ndarray] = {}
        self.reports: dict[str, str] = {}
        self._pdf_profile: dict[str, float] | None = None

    def _extract_pdf_profile(self) -> dict[str, float] | None:
        """Extract amount profile from provided PDFs for feature augmentation."""
        if self._pdf_profile is not None:
            return self._pdf_profile

        if not self.pdf_paths:
            return None

        processor = PDFProcessor()
        all_transactions: list[dict[str, Any]] = []

        for raw_path in self.pdf_paths:
            pdf_path = Path(raw_path)
            if not pdf_path.exists() or not pdf_path.is_file():
                print(f"[WARN] Skipping PDF profile path (not found): {pdf_path}")
                continue

            if pdf_path.suffix.lower() != ".pdf":
                print(f"[WARN] Skipping non-PDF path: {pdf_path}")
                continue

            try:
                extracted = processor.extract_text(pdf_path)
                txns = TransactionExtractor.extract_transactions(extracted.extracted_text)
                all_transactions.extend(txns)
                print(
                    f"[INFO] PDF profile source: {pdf_path.name} -> "
                    f"{len(txns)} extracted transactions"
                )
            except Exception as exc:
                print(f"[WARN] Failed to extract PDF profile from {pdf_path}: {exc}")

        amounts = [float(t.get("amount", 0.0)) for t in all_transactions if t.get("amount")]
        if not amounts:
            print("[WARN] No PDF transactions extracted; skipping PDF-derived features.")
            return None

        amount_array = np.asarray(amounts, dtype=float)
        std_val = float(np.std(amount_array))
        safe_std = std_val if std_val > 1e-9 else max(float(np.mean(amount_array)), 1.0)

        self._pdf_profile = {
            "median_amount": float(np.median(amount_array)),
            "p90_amount": float(np.percentile(amount_array, 90)),
            "std_amount": safe_std,
            "transactions_used": float(len(amount_array)),
        }

        print(
            "[INFO] PDF profile ready: "
            f"n={int(self._pdf_profile['transactions_used'])}, "
            f"median={self._pdf_profile['median_amount']:.2f}, "
            f"p90={self._pdf_profile['p90_amount']:.2f}"
        )
        return self._pdf_profile

    def _add_pdf_derived_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """Add exactly two PDF-derived features to Kaggle rows."""
        profile = self._extract_pdf_profile()
        if profile is None:
            return features

        if "Amount" not in features.columns:
            print("[WARN] Column 'Amount' missing; PDF-derived features were not added.")
            return features

        augmented = features.copy()
        median_amount = profile["median_amount"]
        std_amount = profile["std_amount"]
        p90_amount = profile["p90_amount"]

        augmented["pdf_amount_zscore"] = (
            (augmented["Amount"] - median_amount) / std_amount
        ).astype(float)
        augmented["pdf_above_pdf_p90"] = (
            augmented["Amount"] > p90_amount
        ).astype(float)

        print(
            "[INFO] Added PDF-derived features: "
            "pdf_amount_zscore, pdf_above_pdf_p90"
        )
        return augmented

    def _business_weights_normalized(self) -> dict[str, float]:
        """Return normalized business-scoring weights that sum to 1."""
        raw_weights = {
            "recall": max(0.0, float(self.business_weight_recall)),
            "precision": max(0.0, float(self.business_weight_precision)),
            "accuracy": max(0.0, float(self.business_weight_accuracy)),
        }
        total = sum(raw_weights.values())

        if total <= 0:
            return {"recall": 0.6, "precision": 0.3, "accuracy": 0.1}

        return {k: v / total for k, v in raw_weights.items()}

    def _apply_business_scoring(self, summary_df: pd.DataFrame) -> pd.DataFrame:
        """Add business score/rank using weighted recall, precision, and test accuracy."""
        weights = self._business_weights_normalized()
        scored = summary_df.copy()

        scored["business_score"] = (
            weights["recall"] * scored["recall"]
            + weights["precision"] * scored["precision"]
            + weights["accuracy"] * scored["test_accuracy"]
        )

        scored = scored.sort_values(
            by=["business_score", "recall", "f1", "precision"],
            ascending=False,
        ).reset_index(drop=True)
        scored["business_rank"] = np.arange(1, len(scored) + 1)
        return scored

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

        features = self._add_pdf_derived_features(features)

        feature_names = list(features.columns)
        print(f"[INFO] Features: {len(feature_names)}")
        print(f"[INFO] Samples:  {len(features)}")

        if self.max_samples is not None and len(features) > self.max_samples:
            print(
                f"[INFO] Downsampling to {self.max_samples} rows for faster training..."
            )
            sampled_idx = features.sample(
                n=self.max_samples,
                random_state=self.random_state,
            ).index
            features = features.loc[sampled_idx].reset_index(drop=True)
            if labels is not None:
                labels = labels.loc[sampled_idx].reset_index(drop=True)
            print(f"[INFO] New shape after downsampling: {features.shape}")

        if labels is not None:
            fraud_pct = labels.mean() * 100
            print(f"[INFO] Fraud rate: {fraud_pct:.4f}% ({labels.sum()} cases)")

        return features, labels, feature_names

    def preprocess(self, features: pd.DataFrame, labels: pd.Series) -> StandardScaler:
        """
        Split into train/test and fit StandardScaler on train split only.
        """
        print("[INFO] Splitting dataset into train/test...")
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            features,
            labels,
            test_size=self.test_size,
            random_state=self.random_state,
            stratify=labels,
        )
        print(
            f"[INFO] Train shape: {self.X_train.shape}, Test shape: {self.X_test.shape}"
        )

        print("[INFO] Preprocessing: fitting StandardScaler on train split...")
        self.scaler = StandardScaler()
        self.X_train_scaled = self.scaler.fit_transform(self.X_train)
        self.X_test_scaled = self.scaler.transform(self.X_test)
        print(
            f"[INFO] Data shape after scaling - train: {self.X_train_scaled.shape}, "
            f"test: {self.X_test_scaled.shape}"
        )
        return self.scaler

    def _collect_metrics(
        self,
        model_name: str,
        y_train_true: np.ndarray,
        y_test_true: np.ndarray,
        y_train_pred: np.ndarray,
        y_test_pred: np.ndarray,
        y_test_score: np.ndarray,
    ) -> dict[str, Any]:
        """Compute unified train/test classification metrics."""
        train_accuracy = accuracy_score(y_train_true, y_train_pred)
        test_accuracy = accuracy_score(y_test_true, y_test_pred)
        precision = precision_score(y_test_true, y_test_pred, zero_division=0)
        recall = recall_score(y_test_true, y_test_pred, zero_division=0)
        f1 = f1_score(y_test_true, y_test_pred, zero_division=0)

        roc_auc = float("nan")
        avg_precision = float("nan")

        if len(np.unique(y_test_true)) > 1:
            roc_auc = roc_auc_score(y_test_true, y_test_score)
            avg_precision = average_precision_score(y_test_true, y_test_score)

        summary = {
            "model": model_name,
            "train_accuracy": float(train_accuracy),
            "test_accuracy": float(test_accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "roc_auc": float(roc_auc),
            "avg_precision": float(avg_precision),
            "test_flag_rate": float(np.mean(y_test_pred)),
        }

        return summary

    def train_and_evaluate_models(self) -> dict[str, Any]:
        """Train multiple models and collect metrics + curves."""
        if self.y_train is None or self.y_test is None:
            raise ValueError("Labels are required for model comparison")

        y_train = self.y_train.values
        y_test = self.y_test.values

        supervised_models = {
            "LogisticRegression": LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                random_state=self.random_state,
            ),
            "RandomForest": RandomForestClassifier(
                n_estimators=300,
                class_weight="balanced_subsample",
                random_state=self.random_state,
                n_jobs=-1,
            ),
            "GradientBoosting": GradientBoostingClassifier(
                random_state=self.random_state,
            ),
        }

        trained_models: dict[str, Any] = {}
        best_supervised_name = None
        best_supervised_f1 = -1.0

        print("[INFO] Training supervised models for comparison...")
        for model_name, model in supervised_models.items():
            print(f"[INFO] Training {model_name}...")

            if model_name == "LogisticRegression":
                model.fit(self.X_train_scaled, y_train)
                y_train_pred = model.predict(self.X_train_scaled)
                y_test_pred = model.predict(self.X_test_scaled)
                y_test_score = model.predict_proba(self.X_test_scaled)[:, 1]
            else:
                model.fit(self.X_train, y_train)
                y_train_pred = model.predict(self.X_train)
                y_test_pred = model.predict(self.X_test)
                y_test_score = model.predict_proba(self.X_test)[:, 1]

            summary = self._collect_metrics(
                model_name=model_name,
                y_train_true=y_train,
                y_test_true=y_test,
                y_train_pred=y_train_pred,
                y_test_pred=y_test_pred,
                y_test_score=y_test_score,
            )
            self.model_summaries.append(summary)

            fpr, tpr, _ = roc_curve(y_test, y_test_score)
            precision_curve, recall_curve, _ = precision_recall_curve(y_test, y_test_score)
            self.curves[model_name] = {
                "fpr": fpr,
                "tpr": tpr,
                "precision": precision_curve,
                "recall": recall_curve,
            }
            self.conf_matrices[model_name] = confusion_matrix(y_test, y_test_pred)
            self.reports[model_name] = classification_report(
                y_test,
                y_test_pred,
                target_names=["Normal", "Fraud"],
                zero_division=0,
            )
            trained_models[model_name] = model

            if summary["f1"] > best_supervised_f1:
                best_supervised_f1 = summary["f1"]
                best_supervised_name = model_name

        print(
            f"[INFO] Training IsolationForest "
            f"(n_estimators={self.n_estimators}, contamination={self.contamination})..."
        )
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            max_samples="auto",
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1,
        )
        self.model.fit(self.X_train_scaled)

        train_pred_iso = np.where(self.model.predict(self.X_train_scaled) == -1, 1, 0)
        test_pred_iso = np.where(self.model.predict(self.X_test_scaled) == -1, 1, 0)
        train_score_iso = -self.model.score_samples(self.X_train_scaled)
        test_score_iso = -self.model.score_samples(self.X_test_scaled)

        iso_summary = self._collect_metrics(
            model_name="IsolationForest",
            y_train_true=y_train,
            y_test_true=y_test,
            y_train_pred=train_pred_iso,
            y_test_pred=test_pred_iso,
            y_test_score=test_score_iso,
        )
        self.model_summaries.append(iso_summary)

        fpr, tpr, _ = roc_curve(y_test, test_score_iso)
        precision_curve, recall_curve, _ = precision_recall_curve(y_test, test_score_iso)
        self.curves["IsolationForest"] = {
            "fpr": fpr,
            "tpr": tpr,
            "precision": precision_curve,
            "recall": recall_curve,
        }
        self.conf_matrices["IsolationForest"] = confusion_matrix(y_test, test_pred_iso)
        self.reports["IsolationForest"] = classification_report(
            y_test,
            test_pred_iso,
            target_names=["Normal", "Fraud"],
            zero_division=0,
        )

        print("\n" + "=" * 60)
        print("MODEL COMPARISON SUMMARY (TEST)")
        print("=" * 60)
        summary_df = pd.DataFrame(self.model_summaries)
        summary_df = self._apply_business_scoring(summary_df)
        print(
            summary_df[
                [
                    "business_rank",
                    "model",
                    "business_score",
                    "train_accuracy",
                    "test_accuracy",
                    "precision",
                    "recall",
                    "f1",
                    "roc_auc",
                    "avg_precision",
                ]
            ].to_string(index=False)
        )

        best_business_model_name = str(summary_df.iloc[0]["model"])
        best_business_model_score = float(summary_df.iloc[0]["business_score"])

        print("\n" + "-" * 60)
        print(
            f"[INFO] Best model by business score: {best_business_model_name} "
            f"(score={best_business_model_score:.6f})"
        )
        print("-" * 60)

        return {
            "summary_df": summary_df,
            "best_supervised_name": best_supervised_name,
            "best_supervised_model": trained_models.get(best_supervised_name),
            "best_business_model_name": best_business_model_name,
            "best_business_model_score": best_business_model_score,
            "business_weights": self._business_weights_normalized(),
            "isolation_train_scores": train_score_iso,
            "isolation_test_scores": test_score_iso,
            "isolation_test_preds": test_pred_iso,
        }

    def _plot_train_test_accuracy(self, summary_df: pd.DataFrame):
        """Grouped bar chart of train vs test accuracy."""
        self.plots_dir.mkdir(parents=True, exist_ok=True)

        x = np.arange(len(summary_df))
        width = 0.36

        plt.figure(figsize=(12, 6))
        plt.bar(x - width / 2, summary_df["train_accuracy"], width, label="Train")
        plt.bar(x + width / 2, summary_df["test_accuracy"], width, label="Test")

        plt.xticks(x, summary_df["model"], rotation=20)
        plt.ylim(0.0, 1.05)
        plt.ylabel("Accuracy")
        plt.title("Train vs Test Accuracy by Model", fontweight="bold")
        plt.grid(axis="y", alpha=0.3)
        plt.legend()
        plt.tight_layout()

        out_path = self.plots_dir / "train_vs_test_accuracy.png"
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[INFO] Plot saved: {out_path}")

    def _plot_metric_comparison(self, summary_df: pd.DataFrame):
        """Bar charts for precision/recall/F1/ROC-AUC/AP on test split."""
        metrics_to_plot = [
            "precision",
            "recall",
            "f1",
            "roc_auc",
            "avg_precision",
            "business_score",
        ]
        fig, axes = plt.subplots(2, 3, figsize=(16, 9))
        axes = axes.ravel()

        for idx, metric in enumerate(metrics_to_plot):
            axes[idx].bar(summary_df["model"], summary_df[metric], color="steelblue")
            axes[idx].set_title(metric.replace("_", " ").upper())
            axes[idx].set_ylim(0.0, 1.05)
            axes[idx].tick_params(axis="x", rotation=20)
            axes[idx].grid(axis="y", alpha=0.3)

        fig.suptitle("Model Performance Comparison (Test Set)", fontsize=14, fontweight="bold")
        plt.tight_layout()

        out_path = self.plots_dir / "model_metrics_comparison.png"
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[INFO] Plot saved: {out_path}")

    def _plot_curves(self, summary_df: pd.DataFrame):
        """Save ROC and PR curve comparisons for all models."""
        plt.figure(figsize=(10, 7))
        for _, row in summary_df.iterrows():
            model_name = row["model"]
            curve = self.curves[model_name]
            label = f"{model_name} (AUC={row['roc_auc']:.3f})"
            plt.plot(curve["fpr"], curve["tpr"], linewidth=2, label=label)
        plt.plot([0, 1], [0, 1], "k--", linewidth=1)
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title("ROC Curve Comparison", fontweight="bold")
        plt.grid(alpha=0.3)
        plt.legend(fontsize=9)
        plt.tight_layout()

        roc_path = self.plots_dir / "roc_curve_comparison.png"
        plt.savefig(roc_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[INFO] Plot saved: {roc_path}")

        plt.figure(figsize=(10, 7))
        for _, row in summary_df.iterrows():
            model_name = row["model"]
            curve = self.curves[model_name]
            label = f"{model_name} (AP={row['avg_precision']:.3f})"
            plt.plot(curve["recall"], curve["precision"], linewidth=2, label=label)
        plt.xlabel("Recall")
        plt.ylabel("Precision")
        plt.title("Precision-Recall Curve Comparison", fontweight="bold")
        plt.grid(alpha=0.3)
        plt.legend(fontsize=9)
        plt.tight_layout()

        pr_path = self.plots_dir / "precision_recall_curve_comparison.png"
        plt.savefig(pr_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[INFO] Plot saved: {pr_path}")

    def _plot_confusion_matrices(self, summary_df: pd.DataFrame):
        """Confusion matrix heatmaps for each trained model."""
        n_models = len(summary_df)
        n_cols = 2
        n_rows = int(np.ceil(n_models / n_cols))
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(12, 4.8 * n_rows))
        axes = np.array(axes).reshape(-1)

        for idx, (_, row) in enumerate(summary_df.iterrows()):
            model_name = row["model"]
            cm = self.conf_matrices[model_name]
            ax = axes[idx]
            im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
            ax.set_title(model_name)
            ax.set_xticks([0, 1])
            ax.set_yticks([0, 1])
            ax.set_xticklabels(["Normal", "Fraud"])
            ax.set_yticklabels(["Normal", "Fraud"])
            ax.set_xlabel("Predicted")
            ax.set_ylabel("Actual")

            for i in range(cm.shape[0]):
                for j in range(cm.shape[1]):
                    ax.text(j, i, str(cm[i, j]), ha="center", va="center", color="black")

            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        for idx in range(n_models, len(axes)):
            axes[idx].axis("off")

        fig.suptitle("Confusion Matrices (Test Set)", fontsize=14, fontweight="bold")
        plt.tight_layout()
        out_path = self.plots_dir / "confusion_matrices_comparison.png"
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[INFO] Plot saved: {out_path}")

    def _plot_isolation_score_distribution(
        self,
        train_scores: np.ndarray,
        test_scores: np.ndarray,
        y_test: np.ndarray,
    ):
        """Plot IsolationForest anomaly score distributions for train/test."""
        plt.figure(figsize=(12, 6))
        plt.hist(
            train_scores,
            bins=80,
            alpha=0.45,
            label="Train scores",
            color="gray",
            density=True,
        )
        plt.hist(
            test_scores[y_test == 0],
            bins=80,
            alpha=0.55,
            label="Test normal",
            color="steelblue",
            density=True,
        )
        plt.hist(
            test_scores[y_test == 1],
            bins=80,
            alpha=0.65,
            label="Test fraud",
            color="crimson",
            density=True,
        )

        plt.xlabel("Anomaly Score (higher = more suspicious)")
        plt.ylabel("Density")
        plt.title("IsolationForest Anomaly Score Distribution", fontweight="bold")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()

        out_path = self.plots_dir / "isolation_forest_score_distribution.png"
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[INFO] Plot saved: {out_path}")

    def _plot_learning_curve(self, best_model_name: str, best_model: Any):
        """Learning curve for best supervised model (train vs CV score)."""
        if best_model_name == "LogisticRegression":
            X = self.X_train_scaled
        else:
            X = self.X_train.values

        y = self.y_train.values

        if len(y) > self.curve_sample_size:
            sample_idx = np.random.RandomState(self.random_state).choice(
                len(y),
                size=self.curve_sample_size,
                replace=False,
            )
            X = X[sample_idx]
            y = y[sample_idx]

        # Keep CV feasible for highly imbalanced fraud labels.
        class_counts = np.bincount(y.astype(int))
        min_class_count = int(class_counts.min()) if len(class_counts) > 1 else 0
        effective_cv = min(self.cv_folds, min_class_count)

        if effective_cv < 2:
            print(
                "[WARN] Skipping learning curve: not enough minority-class "
                "samples for cross-validation."
            )
            return

        try:
            train_sizes, train_scores, valid_scores = learning_curve(
                estimator=best_model,
                X=X,
                y=y,
                train_sizes=np.linspace(0.2, 1.0, 5),
                cv=effective_cv,
                scoring="f1",
                n_jobs=1,
            )
        except Exception as exc:
            print(f"[WARN] Learning curve generation skipped: {exc}")
            return

        train_mean = train_scores.mean(axis=1)
        valid_mean = valid_scores.mean(axis=1)

        plt.figure(figsize=(10, 6))
        plt.plot(train_sizes, train_mean, marker="o", label="Train F1")
        plt.plot(train_sizes, valid_mean, marker="o", label="Validation F1")
        plt.xlabel("Training Samples")
        plt.ylabel("F1 Score")
        plt.title(f"Learning Curve - {best_model_name}", fontweight="bold")
        plt.grid(alpha=0.3)
        plt.legend()
        plt.tight_layout()

        out_path = self.plots_dir / "best_model_learning_curve.png"
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[INFO] Plot saved: {out_path}")

    def _save_reports(self):
        """Save per-model classification report text files."""
        reports_dir = self.plots_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        for model_name, report in self.reports.items():
            out_path = reports_dir / f"classification_report_{model_name}.txt"
            out_path.write_text(report, encoding="utf-8")
            print(f"[INFO] Report saved: {out_path}")

    def _save_business_summary(
        self,
        best_business_model_name: str,
        best_business_model_score: float,
        business_weights: dict[str, float],
    ):
        """Save the selected business-priority winner and scoring weights."""
        payload = {
            "selected_by": "weighted_business_score",
            "weights": business_weights,
            "best_model": best_business_model_name,
            "best_model_score": best_business_model_score,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.business_summary_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        print(f"[INFO] Business summary saved: {self.business_summary_path}")

    def visualize_all(
        self,
        summary_df: pd.DataFrame,
        train_scores_iso: np.ndarray,
        test_scores_iso: np.ndarray,
        best_supervised_name: str | None,
        best_supervised_model: Any,
        best_business_model_name: str,
        best_business_model_score: float,
        business_weights: dict[str, float],
    ):
        """Generate and save all model comparison visuals."""
        self.plots_dir.mkdir(parents=True, exist_ok=True)

        self._plot_train_test_accuracy(summary_df)
        self._plot_metric_comparison(summary_df)
        self._plot_curves(summary_df)
        self._plot_confusion_matrices(summary_df)
        self._plot_isolation_score_distribution(
            train_scores_iso,
            test_scores_iso,
            self.y_test.values,
        )
        if best_supervised_name is not None and best_supervised_model is not None:
            self._plot_learning_curve(best_supervised_name, best_supervised_model)

        summary_df.to_csv(self.metrics_path, index=False)
        print(f"[INFO] Metrics table saved: {self.metrics_path}")
        self._save_reports()
        self._save_business_summary(
            best_business_model_name=best_business_model_name,
            best_business_model_score=best_business_model_score,
            business_weights=business_weights,
        )

    def save_artifacts(self):
        """Save IsolationForest model and scaler for inference compatibility."""
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

        if labels is None:
            raise ValueError(
                "Dataset labels are required for full model comparison. "
                "Expected 'Class' or 'isFraud' column."
            )

        self.preprocess(features, labels)
        compare_result = self.train_and_evaluate_models()
        self.visualize_all(
            summary_df=compare_result["summary_df"],
            train_scores_iso=compare_result["isolation_train_scores"],
            test_scores_iso=compare_result["isolation_test_scores"],
            best_supervised_name=compare_result["best_supervised_name"],
            best_supervised_model=compare_result["best_supervised_model"],
            best_business_model_name=compare_result["best_business_model_name"],
            best_business_model_score=compare_result["best_business_model_score"],
            business_weights=compare_result["business_weights"],
        )
        self.save_artifacts()

        metrics = {
            "model_comparison": compare_result["summary_df"].to_dict(orient="records"),
            "business_selection": {
                "best_model": compare_result["best_business_model_name"],
                "best_score": compare_result["best_business_model_score"],
                "weights": compare_result["business_weights"],
            },
            "isolation_forest_test_flagged": int(
                np.sum(compare_result["isolation_test_preds"])
            ),
            "isolation_forest_test_flag_rate": float(
                np.mean(compare_result["isolation_test_preds"])
            ),
        }

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
        description="Train and compare fraud detection models with full visual analytics",
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
        "--test-size",
        type=float,
        default=0.2,
        help="Test split ratio",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Optional row cap for faster experimentation",
    )
    parser.add_argument(
        "--curve-sample-size",
        type=int,
        default=50000,
        help="Max training rows used to compute learning curve",
    )
    parser.add_argument(
        "--cv-folds",
        type=int,
        default=3,
        help="CV folds for learning curve",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--business-weight-recall",
        type=float,
        default=0.6,
        help="Business score weight for recall",
    )
    parser.add_argument(
        "--business-weight-precision",
        type=float,
        default=0.3,
        help="Business score weight for precision",
    )
    parser.add_argument(
        "--business-weight-accuracy",
        type=float,
        default=0.1,
        help="Business score weight for test accuracy",
    )
    parser.add_argument(
        "--pdf-paths",
        nargs="+",
        default=None,
        help=(
            "Optional PDF files used only to derive 2 extra amount-based features "
            "on top of Kaggle rows"
        ),
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
        test_size=args.test_size,
        max_samples=args.max_samples,
        curve_sample_size=args.curve_sample_size,
        cv_folds=args.cv_folds,
        random_state=args.random_state,
        business_weight_recall=args.business_weight_recall,
        business_weight_precision=args.business_weight_precision,
        business_weight_accuracy=args.business_weight_accuracy,
        pdf_paths=args.pdf_paths,
    )

    _ = trainer.train_pipeline()

    print("\n" + "="*60)
    print("[DONE] Model ready for inference pipeline")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

