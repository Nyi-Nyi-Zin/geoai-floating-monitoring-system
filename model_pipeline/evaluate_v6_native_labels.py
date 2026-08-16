"""Evaluate the existing v6 held-out prediction seed against exact native GFD labels."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score


STATIC = Path("/home/ubuntu/webdev-static-assets")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs")
THRESHOLD = 0.53


def main() -> None:
    hindcast = json.loads((STATIC / "maubin_hindcast_seed.json").read_text(encoding="utf-8"))
    event_dates = {str(event["id"]): event["start_date"] for event in hindcast["events"]}
    predictions = pd.DataFrame(hindcast["predictions"])
    predictions["event_id"] = predictions["event_id"].astype(str)
    predictions["cell_id"] = predictions["cell_id"].astype(str)
    predictions["event_start"] = pd.to_datetime(predictions["event_id"].map(event_dates))
    predictions = predictions.loc[predictions["event_start"] >= "2018-01-01"].copy()
    labels = pd.read_csv(OUTPUT / "native_gfd_cell_labels.csv", dtype={"event_id": str, "cell_id": str})
    labels["event_start"] = pd.to_datetime(labels["event_start"])
    labels = labels.loc[labels["event_start"] >= "2018-01-01", ["event_id", "cell_id", "flooded_label"]]
    frame = predictions.merge(labels, on=["event_id", "cell_id"], how="inner", validate="one_to_one")
    y_true = frame["flooded_label"]
    probability = frame["probability"].to_numpy()
    predicted = probability >= THRESHOLD
    tn, fp, fn, tp = confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()
    result = {
        "model": "maubin-flood-event-logistic-v6",
        "evaluation": "native GFD labels for held-out 2018 events present in the existing seed",
        "rows": int(len(frame)),
        "events": sorted(frame["event_id"].unique().tolist()),
        "positives": int(y_true.sum()),
        "threshold": THRESHOLD,
        "precision": round(float(precision_score(y_true, predicted, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, predicted, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, predicted, zero_division=0)), 4),
        "pr_auc": round(float(average_precision_score(y_true, probability)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, probability)), 4),
        "brier_score": round(float(brier_score_loss(y_true, probability)), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }
    (OUTPUT / "v6_native_gfd_test_metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
