"""Evaluate pre-specified feature representations on the v7 chronological split.

The experiment changes neither labels nor source coverage. It tests (1) one-hot
encoding of nominal ESA land-cover codes and (2) a concise set of pre-event
rainfall/discharge ratios. All dynamic inputs remain values ending before the
event start; the selection interval is 2009–2016 and 2018 stays held out.
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


def fit(model, frame: pd.DataFrame, features: list[str]) -> None:
    positives = int(frame["flooded_label"].sum())
    negatives = int(len(frame) - positives)
    weights = np.where(frame["flooded_label"].to_numpy() == 1, negatives / max(positives, 1), 1.0)
    model.fit(frame[features], frame["flooded_label"], model__sample_weight=weights)


def feature_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    enriched = frame.copy()
    denominator = 0.1
    enriched["rainfall_1d_to_3d_ratio"] = enriched["rainfall_lag_1d_mm"] / (enriched["rainfall_lag_3d_mm"] + denominator)
    enriched["rainfall_3d_to_7d_ratio"] = enriched["rainfall_lag_3d_mm"] / (enriched["rainfall_lag_7d_mm"] + denominator)
    enriched["rainfall_7d_to_30d_ratio"] = enriched["rainfall_lag_7d_mm"] / (enriched["rainfall_lag_30d_mm"] + denominator)
    enriched["discharge_1d_to_7d_ratio"] = enriched["discharge_lag_1d_m3s"] / (enriched["discharge_lag_7d_m3s"] + denominator)
    enriched["discharge_7d_to_30d_ratio"] = enriched["discharge_lag_7d_m3s"] / (enriched["discharge_lag_30d_m3s"] + denominator)
    ratio_features = [
        "rainfall_1d_to_3d_ratio", "rainfall_3d_to_7d_ratio", "rainfall_7d_to_30d_ratio",
        "discharge_1d_to_7d_ratio", "discharge_7d_to_30d_ratio",
    ]

    dummies = pd.get_dummies(enriched["land_cover_dominant_code"].astype("string"), prefix="landcover", dtype=float)
    enriched = pd.concat([enriched.drop(columns=["land_cover_dominant_code"]), dummies], axis=1)
    onehot_base = [feature for feature in BASE_FEATURES if feature != "land_cover_dominant_code"] + list(dummies.columns)
    return enriched, onehot_base, ratio_features


def main() -> None:
    predictors = pd.read_csv(OUTPUT / "maubin_training_events_v7.csv")
    labels = pd.read_csv(OUTPUT / "native_gfd_cell_labels.csv")
    frame = predictors.drop(columns=["flooded_label"]).merge(
        labels[["event_id", "cell_id", "flooded_label", "flood_fraction", "valid_pixel_count"]],
        on=["event_id", "cell_id"],
        how="inner",
        validate="one_to_one",
    )
    frame, onehot_base, ratio_features = feature_frame(frame)
    frame["event_start"] = pd.to_datetime(frame["event_start"])
    train = frame.loc[frame["event_start"] < TRAIN_CUTOFF].copy()
    validation = frame.loc[(frame["event_start"] >= TRAIN_CUTOFF) & (frame["event_start"] < TEST_START)].copy()
    pretest = frame.loc[frame["event_start"] < TEST_START].copy()
    test = frame.loc[frame["event_start"] >= TEST_START].copy()

    baseline_features = [feature for feature in BASE_FEATURES if feature != "land_cover_dominant_code"] + ["land_cover_dominant_code"]
    # Keep the original numeric code in a duplicate column for the faithful baseline.
    frame["land_cover_dominant_code"] = predictors["land_cover_dominant_code"].to_numpy()
    train["land_cover_dominant_code"] = frame.loc[train.index, "land_cover_dominant_code"]
    validation["land_cover_dominant_code"] = frame.loc[validation.index, "land_cover_dominant_code"]
    pretest["land_cover_dominant_code"] = frame.loc[pretest.index, "land_cover_dominant_code"]
    test["land_cover_dominant_code"] = frame.loc[test.index, "land_cover_dominant_code"]

    experiments = {
        "v7_hgb_reproduction": baseline_features,
        "v12_hgb_onehot_landcover": onehot_base,
        "v12_hgb_onehot_landcover_and_hydro_ratios": onehot_base + ratio_features,
    }
    results: dict[str, object] = {
        "experiment": "Nominal land-cover representation and pre-event hydrologic ratios; no new source data or label information.",
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
    (OUTPUT / "candidate_metrics_v12_feature_representation.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    test_predictions = test[["event_id", "event_start", "cell_id", "flooded_label", "flood_fraction"]].copy()
    for name, probabilities in predictions.items():
        test_predictions[f"{name}_probability"] = probabilities
    test_predictions.to_csv(OUTPUT / "candidate_test_predictions_v12_feature_representation.csv", index=False)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
