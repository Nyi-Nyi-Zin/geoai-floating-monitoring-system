"""Evaluate a rainfall-only Myanmar Admin 1 temporal baseline under the frozen protocol.

This is a diagnostic model-selection experiment, not an operational model. It writes
evaluation evidence only and deliberately never exports a fitted model, a regional
score, a probability service, a forecast, or an alert.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, precision_recall_fscore_support, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


SOURCE = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_admin1_event_rainfall_lags.csv")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs/myanmar_rainfall_temporal_baseline_evaluation.json")
REPORT = Path("/home/ubuntu/deltawatch-permanent/model_pipeline/myanmar_rainfall_temporal_baseline_evaluation.md")
FEATURES = ["rainfall_lag_1d_mm", "rainfall_lag_3d_mm", "rainfall_lag_7d_mm", "rainfall_lag_14d_mm", "rainfall_lag_30d_mm"]
DEVELOPMENT_END = "2008-05-03"
VALIDATION_START = "2010-06-15"
VALIDATION_END = "2016-06-01"
HOLDOUT_START = "2018-06-15"


def metrics(y_true: np.ndarray, probability: np.ndarray, threshold: float) -> dict[str, float | None]:
    label = (probability >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, label, average="binary", zero_division=0)
    return {
        "precision": round(float(precision), 6),
        "recall": round(float(recall), 6),
        "f1": round(float(f1), 6),
        "roc_auc": round(float(roc_auc_score(y_true, probability)), 6) if len(np.unique(y_true)) > 1 else None,
        "pr_auc": round(float(average_precision_score(y_true, probability)), 6) if len(np.unique(y_true)) > 1 else None,
        "positive_rate": round(float(y_true.mean()), 6),
    }


def main() -> None:
    with SOURCE.open("r", encoding="utf-8", newline="") as handle:
        all_rows = [row for row in csv.DictReader(handle) if row["coverage_status"] == "observed"]
    development = [row for row in all_rows if row["event_start"] <= DEVELOPMENT_END]
    validation = [row for row in all_rows if VALIDATION_START <= row["event_start"] <= VALIDATION_END]
    holdout = [row for row in all_rows if row["event_start"] >= HOLDOUT_START]
    if not all((development, validation, holdout)):
        raise RuntimeError("Temporal split contains no rows")
    def matrix(rows: list[dict[str, str]]) -> tuple[np.ndarray, np.ndarray]:
        return np.array([[float(row[feature]) for feature in FEATURES] for row in rows]), np.array([int(row["observed_flood_presence"]) for row in rows])
    x_dev, y_dev = matrix(development)
    x_validation, y_validation = matrix(validation)
    x_holdout, y_holdout = matrix(holdout)
    model = Pipeline([("scale", StandardScaler()), ("logit", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42))])
    model.fit(x_dev, y_dev)
    validation_probability = model.predict_proba(x_validation)[:, 1]
    candidates = np.arange(0.2, 0.81, 0.01)
    threshold = float(max(candidates, key=lambda value: f1_score(y_validation, validation_probability >= value, zero_division=0)))
    holdout_probability = model.predict_proba(x_holdout)[:, 1]
    result = {
        "schema": "deltawatch-myanmar-rainfall-temporal-baseline-v1",
        "candidate": "rainfall_lags_only_logistic_regression",
        "feature_names": FEATURES,
        "splits": {
            "development": {"end": DEVELOPMENT_END, "rows": len(development), "events": sorted({row["event_id"] for row in development})},
            "validation": {"start": VALIDATION_START, "end": VALIDATION_END, "rows": len(validation), "events": sorted({row["event_id"] for row in validation})},
            "frozen_holdout": {"start": HOLDOUT_START, "rows": len(holdout), "events": sorted({row["event_id"] for row in holdout})},
        },
        "validation_threshold_selected": round(threshold, 2),
        "validation_metrics": metrics(y_validation, validation_probability, threshold),
        "frozen_holdout_metrics": metrics(y_holdout, holdout_probability, threshold),
        "promotion_decision": "rejected_not_eligible_for_nationwide_prediction",
        "rejection_reasons": [
            "Rainfall-only centroid inputs omit required terrain, land-cover, waterway, and upstream-flow context.",
            "Only 12 metadata-selected historical events are available; the frozen holdout contains two events.",
            "No region-specific prospective validation, local gauge evidence, tide inputs, or verified field outcomes are available.",
            "This model is not exported and no probabilities, forecasts, risks, or alerts are made available to the interface.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    report = f"""# Myanmar Rainfall-Only Temporal Baseline Evaluation

**Status:** Rejected diagnostic baseline; not a nationwide prediction model.  
**Protocol:** `myanmar_nationwide_validation_protocol.md`.

| Split | Rows | Events | Precision | Recall | F1 | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|
| Validation | {result['splits']['validation']['rows']} | {len(result['splits']['validation']['events'])} | {result['validation_metrics']['precision']:.3f} | {result['validation_metrics']['recall']:.3f} | {result['validation_metrics']['f1']:.3f} | {result['validation_metrics']['roc_auc']} | {result['validation_metrics']['pr_auc']} |
| Frozen 2018 holdout | {result['splits']['frozen_holdout']['rows']} | {len(result['splits']['frozen_holdout']['events'])} | {result['frozen_holdout_metrics']['precision']:.3f} | {result['frozen_holdout_metrics']['recall']:.3f} | {result['frozen_holdout_metrics']['f1']:.3f} | {result['frozen_holdout_metrics']['roc_auc']} | {result['frozen_holdout_metrics']['pr_auc']} |

The threshold of **{result['validation_threshold_selected']:.2f}** was selected on the validation period only. The frozen 2018 holdout was not used for threshold selection. Nonetheless, this candidate is **rejected**: it uses centroid rainfall lags only, has too few historical events, omits required hydrologic and static context, and has no prospective local validation. No model artefact, probability, forecast, risk score, or alert has been exported.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
