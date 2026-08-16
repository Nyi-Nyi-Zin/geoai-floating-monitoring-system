"""Evaluate a leakage-safe historical flood-susceptibility feature.

Each event-cell row receives flood frequency computed strictly from GFD labels before
that event.  To preserve a clean final test, 2018 event labels are never used to
construct a feature for any held-out 2018 row.  This remains a hindcast/research
feature until availability timing of historical GFD products is independently
validated for any operational use.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from train_chronological_candidates import (
    HYDROLOGIC_FEATURES,
    INFRASTRUCTURE_FEATURES,
    STATIC_FEATURES,
    TEST_START,
    TRAIN_CUTOFF,
    choose_threshold,
    hgb_pipeline,
    metrics,
)


OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs")
BASE_FEATURES = STATIC_FEATURES + INFRASTRUCTURE_FEATURES + HYDROLOGIC_FEATURES
HISTORICAL_FEATURES = ["prior_gfd_flood_rate", "prior_gfd_flood_count", "prior_gfd_event_count"]


def fit(model, frame: pd.DataFrame, features: list[str]) -> None:
    positives = int(frame["flooded_label"].sum())
    negatives = int(len(frame) - positives)
    weights = np.where(frame["flooded_label"].to_numpy() == 1, negatives / max(positives, 1), 1.0)
    model.fit(frame[features], frame["flooded_label"], model__sample_weight=weights)


def add_prior_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Build event-time causal flood-history statistics for each grid cell."""
    result = frame.copy()
    result["event_start"] = pd.to_datetime(result["event_start"])
    feature_rows: list[pd.DataFrame] = []
    cumulative_count: pd.Series | None = None
    cumulative_events = 0

    for event_start, event_frame in result.sort_values(["event_start", "event_id"]).groupby("event_start", sort=True):
        event_frame = event_frame.copy()
        # No labels from the test interval can become historical predictors.
        if event_start >= pd.Timestamp(TEST_START):
            frozen_counts = cumulative_count if cumulative_count is not None else pd.Series(0.0, index=event_frame["cell_id"])
            event_frame["prior_gfd_flood_count"] = event_frame["cell_id"].map(frozen_counts).fillna(0.0)
            event_frame["prior_gfd_event_count"] = float(cumulative_events)
            event_frame["prior_gfd_flood_rate"] = event_frame["prior_gfd_flood_count"] / max(cumulative_events, 1)
            feature_rows.append(event_frame)
            continue

        prior_counts = cumulative_count if cumulative_count is not None else pd.Series(dtype=float)
        event_frame["prior_gfd_flood_count"] = event_frame["cell_id"].map(prior_counts).fillna(0.0)
        event_frame["prior_gfd_event_count"] = float(cumulative_events)
        event_frame["prior_gfd_flood_rate"] = event_frame["prior_gfd_flood_count"] / max(cumulative_events, 1)
        feature_rows.append(event_frame)

        current = event_frame.set_index("cell_id")["flooded_label"].astype(float)
        cumulative_count = current if cumulative_count is None else cumulative_count.add(current, fill_value=0.0)
        cumulative_events += 1

    return pd.concat(feature_rows, ignore_index=True)


def main() -> None:
    predictors = pd.read_csv(OUTPUT / "maubin_training_events_v7.csv")
    labels = pd.read_csv(OUTPUT / "native_gfd_cell_labels.csv")
    frame = predictors.drop(columns=["flooded_label"]).merge(
        labels[["event_id", "cell_id", "flooded_label", "flood_fraction", "valid_pixel_count"]],
        on=["event_id", "cell_id"],
        how="inner",
        validate="one_to_one",
    )
    frame = add_prior_features(frame)
    train = frame.loc[frame["event_start"] < TRAIN_CUTOFF].copy()
    validation = frame.loc[(frame["event_start"] >= TRAIN_CUTOFF) & (frame["event_start"] < TEST_START)].copy()
    pretest = frame.loc[frame["event_start"] < TEST_START].copy()
    test = frame.loc[frame["event_start"] >= TEST_START].copy()

    experiments = {
        "v7_hgb_reproduction": BASE_FEATURES,
        "v10_hgb_prior_flood_history": BASE_FEATURES + HISTORICAL_FEATURES,
        "v10_hgb_prior_flood_rate_only": BASE_FEATURES + ["prior_gfd_flood_rate"],
    }
    results: dict[str, object] = {
        "experiment": "Strictly prior-event GFD flood susceptibility; all 2018 labels excluded from held-out feature construction.",
        "split": {"train_before": TRAIN_CUTOFF, "validation": "2009-2016", "held_out_test": "2018"},
        "selection_basis": "Highest validation F1 only; 2018 metrics are not used for selection.",
        "models": {},
    }
    predictions: dict[str, np.ndarray] = {}

    for name, features in experiments.items():
        selection_model = hgb_pipeline(features)
        fit(selection_model, train, features)
        validation_probabilities = selection_model.predict_proba(validation[features])[:, 1]
        threshold = choose_threshold(validation["flooded_label"], validation_probabilities)

        final_model = hgb_pipeline(features)
        fit(final_model, pretest, features)
        test_probabilities = final_model.predict_proba(test[features])[:, 1]
        results["models"][name] = {
            "features": features,
            "validation": metrics(validation["flooded_label"], validation_probabilities, threshold),
            "test": metrics(test["flooded_label"], test_probabilities, threshold),
        }
        predictions[name] = test_probabilities

    selected = max(results["models"], key=lambda name: results["models"][name]["validation"]["f1"])
    results["selected_candidate"] = selected
    (OUTPUT / "candidate_metrics_v10_historical_susceptibility.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    test_predictions = test[["event_id", "event_start", "cell_id", "flooded_label", "flood_fraction"]].copy()
    for name, probabilities in predictions.items():
        test_predictions[f"{name}_probability"] = probabilities
    test_predictions.to_csv(OUTPUT / "candidate_test_predictions_v10_historical_susceptibility.csv", index=False)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
