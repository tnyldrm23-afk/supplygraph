"""Leakage-aware real-data Order node classification with temporal holdouts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline

from app.config import Settings
from app.database import Database, load_payload

ROOT = Path(__file__).resolve().parents[1]


def features(order: dict, products: dict) -> dict:
    """Only variables available when an order is placed, never shipment outcomes."""
    from datetime import datetime  # pylint: disable=import-outside-toplevel

    date = datetime.fromisoformat(order["ordered_at"])
    return {
        "scheduled_days": order["scheduled_days"],
        "shipping_mode": order["shipping_mode"],
        "market": order["market"],
        "order_month": str(date.month),
        "weekday": str(date.weekday()),
        "quantity": sum(i["quantity"] for i in order["items"]),
        "catalog_value": sum(products[i["sku"]]["price"] * i["quantity"] for i in order["items"]),
    }


def metrics(labels, probabilities) -> dict:
    """Report ranking, balanced accuracy, probability error and confusion matrix."""
    predicted = probabilities >= 0.5
    return {
        "roc_auc": round(float(roc_auc_score(labels, probabilities)), 4),
        "average_precision": round(float(average_precision_score(labels, probabilities)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(labels, predicted)), 4),
        "brier_score": round(float(brier_score_loss(labels, probabilities)), 4),
        "confusion_matrix_tn_fp_fn_tp": confusion_matrix(labels, predicted).ravel().tolist(),
    }


def train(write_db: bool = False) -> dict:
    """Fit one fixed baseline; use chronological validation and untouched test data."""
    payload = load_payload(str(ROOT / "data/processed/supplygraph.json"))
    orders = sorted(payload["orders"], key=lambda order: (order["ordered_at"], order["id"]))
    products = {p["id"]: p for p in payload["products"]}
    x_data = [features(order, products) for order in orders]
    y_data = np.array([o["late"] for o in orders])
    a, b = int(0.7 * len(orders)), int(0.85 * len(orders))
    # Fit exclusively on the earliest 70%; do not fit vocabulary on holdouts.
    model = make_pipeline(
        DictVectorizer(sparse=True),
        LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42),
    )
    model.fit(x_data[:a], y_data[:a])
    dummy = DummyClassifier(strategy="prior").fit(np.zeros((a, 1)), y_data[:a])
    splits = {"train": (0, a), "validation": (a, b), "test": (b, len(orders))}
    output = {
        "task": "Order node classification: historically late delivery",
        "source": "DataCo-v5, deterministic anonymous 6000-order sample",
        "model": "DictVectorizer + class-balanced LogisticRegression (fixed parameters)",
        "features": sorted(x_data[0]),
        "threshold": 0.5,
        "excluded_leakage": [
            "actual_days",
            "late",
            "Delivery Status",
            "shipping date",
            "Order Status",
            "retailer_id (assumed)",
            "customer personal fields",
        ],
        "split_method": "chronological order-level 70/15/15; no order crosses partitions",
        "seed": 42,
        "splits": {},
        "limitations": [
            "Historical sample, not an industrial deployment validation.",
            "No hyperparameter tuning on validation or test data.",
            "Scheduled duration and shipping mode are related but available at booking.",
            "Assumed graph topology is excluded from this real-observation classifier.",
            "Scores are not calibrated probabilities or causal disruption forecasts.",
        ],
    }
    for name, (start, end) in splits.items():
        labels = y_data[start:end]
        probabilities = model.predict_proba(x_data[start:end])[:, 1]
        output["splits"][name] = {
            "count": end - start,
            "first_order": orders[start]["ordered_at"],
            "last_order": orders[end - 1]["ordered_at"],
            "late_fraction": round(float(labels.mean()), 4),
            "model": metrics(labels, probabilities),
            "prior_baseline": metrics(
                labels, dummy.predict_proba(np.zeros((end - start, 1)))[:, 1]
            ),
        }
    (ROOT / "reports/ml-evaluation.json").write_text(json.dumps(output, indent=2))
    if write_db:
        database = Database(Settings())
        try:
            scores = model.predict_proba(x_data)[:, 1]
            for start in range(0, len(orders), 500):
                database.write(
                    """UNWIND $rows AS row MATCH (o:Order {id:row.id})
                    SET o.predicted_late_score=row.score, o.ml_split=row.split,
                        o.ml_model='temporal-logistic-v1' """,
                    {
                        "rows": [
                            {
                                "id": o["id"],
                                "score": float(scores[idx]),
                                "split": (
                                    "train" if idx < a else "validation" if idx < b else "test"
                                ),
                            }
                            for idx, o in enumerate(orders[start : start + 500], start)
                        ]
                    },
                )
        finally:
            database.close()
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-neo4j", action="store_true")
    args = parser.parse_args()
    print(json.dumps(train(args.write_neo4j), indent=2))
