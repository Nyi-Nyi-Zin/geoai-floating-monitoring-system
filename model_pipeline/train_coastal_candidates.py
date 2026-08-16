"""Compare v7 features against authorised GTSM coastal-proxy v8 candidates.

Thresholds are selected solely on the 2009–2016 validation interval; 2018
remains untouched until final reporting. The GTSM node is a coastal proxy, not
a local stage gauge, so a candidate is eligible only if its common holdout
metrics improve without concealing that limitation.
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
    logistic_pipeline,
    metrics,
    random_forest_pipeline,
)


OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs")
COASTAL_PROXY_FEATURES = [
    "coastal_total_water_lag_1d_m",
    "coastal_total_water_lag_3d_max_m",
    "coastal_surge_lag_1d_m",
    "coastal_surge_lag_3d_max_m",
]


def build_model(model_type: str, features: list[str]):
    if model_type == "logistic":
        return logistic_pipeline(features)
    if model_type == "hgb":
        return hgb_pipeline(features)
    return random_forest_pipeline(features)


def fit(model, model_type: str, frame: pd.DataFrame, features: list[str]) -> None:
    if model_type == "hgb":
        positives = int(frame["flooded_label"].sum())
        negatives = int(len(frame) - positives)
        weights = np.where(frame["flooded_label"].to_numpy() == 1, negatives / max(positives, 1), 1.0)
        model.fit(frame[features], frame["flooded_label"], model__sample_weight=weights)
    else:
        model.fit(frame[features], frame["flooded_label"])


def main() -> None:
    predictors = pd.read_csv(OUTPUT / "maubin_training_events_v8.csv")
    labels = pd.read_csv(OUTPUT / "native_gfd_cell_labels.csv")
    frame = predictors.drop(columns=["flooded_label"]).merge(
        labels[["event_id", "cell_id", "flooded_label", "flood_fraction"]],
        on=["event_id", "cell_id"],
        how="inner",
        validate="one_to_one",
    )
    frame["event_start"] = pd.to_datetime(frame["event_start"])
    train = frame.loc[frame["event_start"] < TRAIN_CUTOFF].copy()
    validation = frame.loc[(frame["event_start"] >= TRAIN_CUTOFF) & (frame["event_start"] < TEST_START)].copy()
    pretest = frame.loc[frame["event_start"] < TEST_START].copy()
    test = frame.loc[frame["event_start"] >= TEST_START].copy()

    v7_features = STATIC_FEATURES + INFRASTRUCTURE_FEATURES + HYDROLOGIC_FEATURES
    v8_features = v7_features + COASTAL_PROXY_FEATURES
    experiments = {
        "v7_hydrologic_hgb_common": ("hgb", v7_features),
        "v8_coastal_logistic": ("logistic", v8_features),
        "v8_coastal_hgb": ("hgb", v8_features),
        "v8_coastal_rf": ("rf", v8_features),
    }
    results: dict[str, object] = {
        "split": {"train_before": TRAIN_CUTOFF, "validation": "2009-2016", "held_out_test": "2018"},
        "coastal_proxy_caveat": "Nearest valid GTSM coastal node; not a Maubin local gauge.",
        "models": {},
    }
    predictions: dict[str, np.ndarray] = {}

    for name, (model_type, features) in experiments.items():
        selection_model = build_model(model_type, features)
        fit(selection_model, model_type, train, features)
        validation_probabilities = selection_model.predict_proba(validation[features])[:, 1]
        threshold = choose_threshold(validation["flooded_label"], validation_probabilities)

        final_model = build_model(model_type, features)
        fit(final_model, model_type, pretest, features)
        test_probabilities = final_model.predict_proba(test[features])[:, 1]
        results["models"][name] = {
            "algorithm": model_type,
            "features": features,
            "validation": metrics(validation["flooded_label"], validation_probabilities, threshold),
            "test": metrics(test["flooded_label"], test_probabilities, threshold),
        }
        predictions[name] = test_probabilities

    (OUTPUT / "candidate_metrics_v8_coastal.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    prediction_frame = test[["event_id", "event_start", "cell_id", "flooded_label", "flood_fraction"]].copy()
    for name, probabilities in predictions.items():
        prediction_frame[f"{name}_probability"] = probabilities
    prediction_frame.to_csv(OUTPUT / "candidate_test_predictions_v8_coastal.csv", index=False)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
