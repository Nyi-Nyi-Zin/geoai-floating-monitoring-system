"""Evaluate stable within-township spatial-location features on the v7 data.

Cell centroid coordinates are extracted from the existing Maubin terrain seed. They
do not use an event label or post-event observation, so they are stable static
context. Candidate selection remains validation-only and all 2018 events remain
the common held-out comparison.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import shape

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


STATIC = Path("/home/ubuntu/webdev-static-assets")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs")
BASE_FEATURES = STATIC_FEATURES + INFRASTRUCTURE_FEATURES + HYDROLOGIC_FEATURES
LOCATION_FEATURES = ["centroid_lon", "centroid_lat", "distance_to_township_center_m"]


def load_cell_locations() -> pd.DataFrame:
    seed = json.loads((STATIC / "maubin_spatial_seed.json").read_text(encoding="utf-8"))
    rows: list[dict[str, float | str]] = []
    cells = [feature for feature in seed.get("features", []) if feature.get("properties", {}).get("asset_type") == "terrain_cell"]
    centroids = [shape(feature["geometry"]).centroid for feature in cells]
    mean_lon = float(np.mean([point.x for point in centroids]))
    mean_lat = float(np.mean([point.y for point in centroids]))
    for feature, centroid in zip(cells, centroids):
        distance_deg = float(np.hypot(centroid.x - mean_lon, centroid.y - mean_lat))
        rows.append({
            "cell_id": str(feature["properties"]["id"]),
            "centroid_lon": float(centroid.x),
            "centroid_lat": float(centroid.y),
            "distance_to_township_center_m": distance_deg * 111_000,
        })
    return pd.DataFrame(rows)


def fit(model, frame: pd.DataFrame, features: list[str]) -> None:
    positives = int(frame["flooded_label"].sum())
    negatives = int(len(frame) - positives)
    weights = np.where(frame["flooded_label"].to_numpy() == 1, negatives / max(positives, 1), 1.0)
    model.fit(frame[features], frame["flooded_label"], model__sample_weight=weights)


def main() -> None:
    predictors = pd.read_csv(OUTPUT / "maubin_training_events_v7.csv")
    labels = pd.read_csv(OUTPUT / "native_gfd_cell_labels.csv")
    frame = predictors.drop(columns=["flooded_label"]).merge(
        labels[["event_id", "cell_id", "flooded_label", "flood_fraction", "valid_pixel_count"]],
        on=["event_id", "cell_id"],
        how="inner",
        validate="one_to_one",
    ).merge(load_cell_locations(), on="cell_id", how="inner", validate="many_to_one")
    frame["event_start"] = pd.to_datetime(frame["event_start"])
    train = frame.loc[frame["event_start"] < TRAIN_CUTOFF].copy()
    validation = frame.loc[(frame["event_start"] >= TRAIN_CUTOFF) & (frame["event_start"] < TEST_START)].copy()
    pretest = frame.loc[frame["event_start"] < TEST_START].copy()
    test = frame.loc[frame["event_start"] >= TEST_START].copy()

    experiments = {
        "v7_hgb_reproduction": BASE_FEATURES,
        "v11_hgb_centroid_coordinates": BASE_FEATURES + ["centroid_lon", "centroid_lat"],
        "v11_hgb_full_location_context": BASE_FEATURES + LOCATION_FEATURES,
    }
    results: dict[str, object] = {
        "experiment": "Stable terrain-cell coordinate context from the existing Maubin spatial seed; no additional event labels or dynamic observations.",
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
    (OUTPUT / "candidate_metrics_v11_spatial_location.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    test_predictions = test[["event_id", "event_start", "cell_id", "flooded_label", "flood_fraction"]].copy()
    for name, probabilities in predictions.items():
        test_predictions[f"{name}_probability"] = probabilities
    test_predictions.to_csv(OUTPUT / "candidate_test_predictions_v11_spatial_location.csv", index=False)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
