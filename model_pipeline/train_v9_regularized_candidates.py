"""Evaluate regularized v9 HGB candidates on the unchanged v7 feature table.

This is a model-capacity experiment, not a new data-source claim.  It uses the
same native GFD labels, static terrain, ERA5 rainfall-lag, GloFAS discharge-lag,
and OpenStreetMap infrastructure features as v7.  Candidate selection uses the
2009–2016 validation interval only; 2018 is reported as a common held-out test.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from train_chronological_candidates import (
    HYDROLOGIC_FEATURES,
    INFRASTRUCTURE_FEATURES,
    STATIC_FEATURES,
    TEST_START,
    TRAIN_CUTOFF,
    choose_threshold,
    metrics,
)


OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs")
FEATURES = STATIC_FEATURES + INFRASTRUCTURE_FEATURES + HYDROLOGIC_FEATURES


def make_model(params: dict[str, float | int]) -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", HistGradientBoostingClassifier(random_state=42, **params)),
    ])


def sample_weights(frame: pd.DataFrame, positive_weight: str) -> np.ndarray:
    positives = int(frame["flooded_label"].sum())
    negatives = int(len(frame) - positives)
    base_ratio = negatives / max(positives, 1)
    multiplier = {
        "none": 1.0,
        "sqrt": float(np.sqrt(base_ratio)),
        "balanced": float(base_ratio),
    }[positive_weight]
    return np.where(frame["flooded_label"].to_numpy() == 1, multiplier, 1.0)


def fit(model: Pipeline, frame: pd.DataFrame, positive_weight: str) -> None:
    model.fit(
        frame[FEATURES],
        frame["flooded_label"],
        model__sample_weight=sample_weights(frame, positive_weight),
    )


def main() -> None:
    predictors = pd.read_csv(OUTPUT / "maubin_training_events_v7.csv")
    labels = pd.read_csv(OUTPUT / "native_gfd_cell_labels.csv")
    frame = predictors.drop(columns=["flooded_label"]).merge(
        labels[["event_id", "cell_id", "flooded_label", "flood_fraction", "valid_pixel_count"]],
        on=["event_id", "cell_id"],
        how="inner",
        validate="one_to_one",
    )
    frame["event_start"] = pd.to_datetime(frame["event_start"])
    train = frame.loc[frame["event_start"] < TRAIN_CUTOFF].copy()
    validation = frame.loc[(frame["event_start"] >= TRAIN_CUTOFF) & (frame["event_start"] < TEST_START)].copy()
    pretest = frame.loc[frame["event_start"] < TEST_START].copy()
    test = frame.loc[frame["event_start"] >= TEST_START].copy()

    experiments = {
        "v7_hgb_reproduction": ({"max_iter": 250, "learning_rate": 0.06, "max_leaf_nodes": 24, "l2_regularization": 1.2}, "balanced"),
        "v9_hgb_shallow_balanced": ({"max_iter": 220, "learning_rate": 0.05, "max_leaf_nodes": 10, "min_samples_leaf": 40, "l2_regularization": 4.0}, "balanced"),
        "v9_hgb_regularized_balanced": ({"max_iter": 180, "learning_rate": 0.05, "max_leaf_nodes": 14, "min_samples_leaf": 60, "l2_regularization": 8.0}, "balanced"),
        "v9_hgb_shallow_sqrt_weight": ({"max_iter": 220, "learning_rate": 0.05, "max_leaf_nodes": 10, "min_samples_leaf": 40, "l2_regularization": 4.0}, "sqrt"),
        "v9_hgb_regularized_sqrt_weight": ({"max_iter": 180, "learning_rate": 0.05, "max_leaf_nodes": 14, "min_samples_leaf": 60, "l2_regularization": 8.0}, "sqrt"),
    }

    results: dict[str, object] = {
        "experiment": "Regularize model capacity and positive-class weighting using unchanged v7 inputs.",
        "split": {"train_before": TRAIN_CUTOFF, "validation": "2009-2016", "held_out_test": "2018"},
        "selection_basis": "Highest validation F1 only; 2018 metrics are not used for selection.",
        "feature_count": len(FEATURES),
        "features": FEATURES,
        "models": {},
    }
    predictions: dict[str, np.ndarray] = {}

    for name, (params, weighting) in experiments.items():
        selection_model = make_model(params)
        fit(selection_model, train, weighting)
        validation_probabilities = selection_model.predict_proba(validation[FEATURES])[:, 1]
        threshold = choose_threshold(validation["flooded_label"], validation_probabilities)

        final_model = make_model(params)
        fit(final_model, pretest, weighting)
        test_probabilities = final_model.predict_proba(test[FEATURES])[:, 1]

        results["models"][name] = {
            "hyperparameters": params,
            "positive_class_weight": weighting,
            "validation": metrics(validation["flooded_label"], validation_probabilities, threshold),
            "test": metrics(test["flooded_label"], test_probabilities, threshold),
        }
        predictions[name] = test_probabilities

    selected = max(results["models"], key=lambda name: results["models"][name]["validation"]["f1"])
    results["selected_candidate"] = selected
    (OUTPUT / "candidate_metrics_v9_regularization.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    test_predictions = test[["event_id", "event_start", "cell_id", "flooded_label", "flood_fraction"]].copy()
    for name, probabilities in predictions.items():
        test_predictions[f"{name}_probability"] = probabilities
    test_predictions.to_csv(OUTPUT / "candidate_test_predictions_v9_regularization.csv", index=False)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
