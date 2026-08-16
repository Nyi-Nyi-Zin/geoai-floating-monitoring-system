"""Generate chronologically out-of-sample v7 hindcast probabilities for dashboard events."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline


STATIC = Path("/home/ubuntu/webdev-static-assets")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs")
THRESHOLD = 0.71
FEATURES = [
    "elevation_mean_m", "elevation_percentile", "local_relief_m", "distance_to_waterway_m", "land_cover_dominant_code",
    "osm_drainage_distance_m", "osm_levee_distance_m",
    "rainfall_lag_1d_mm", "rainfall_lag_3d_mm", "rainfall_lag_7d_mm", "rainfall_lag_14d_mm", "rainfall_lag_30d_mm",
    "discharge_lag_1d_m3s", "discharge_lag_3d_m3s", "discharge_lag_7d_m3s", "discharge_lag_14d_m3s", "discharge_lag_30d_m3s",
]


def model_pipeline() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", HistGradientBoostingClassifier(max_iter=250, learning_rate=0.06, max_leaf_nodes=24, l2_regularization=1.2, random_state=42)),
    ])


def fit_balanced(frame: pd.DataFrame) -> Pipeline:
    model = model_pipeline()
    positives = int(frame["flooded_label"].sum())
    negatives = int(len(frame) - positives)
    weights = np.where(frame["flooded_label"].to_numpy() == 1, negatives / max(positives, 1), 1.0)
    model.fit(frame[FEATURES], frame["flooded_label"], model__sample_weight=weights)
    return model


def main() -> None:
    predictors = pd.read_csv(OUTPUT / "maubin_training_events_v7.csv", dtype={"event_id": str, "cell_id": str})
    labels = pd.read_csv(OUTPUT / "native_gfd_cell_labels.csv", dtype={"event_id": str, "cell_id": str})
    frame = predictors.drop(columns=["flooded_label"]).merge(
        labels[["event_id", "cell_id", "flooded_label"]], on=["event_id", "cell_id"], how="inner", validate="one_to_one"
    )
    frame["event_start"] = pd.to_datetime(frame["event_start"])
    seed = json.loads((STATIC / "maubin_hindcast_seed.json").read_text(encoding="utf-8"))
    events = sorted(seed["events"], key=lambda event: event["start_date"])
    predictions = []
    event_availability = []
    for event in events:
        event_id = str(event["id"])
        start = pd.Timestamp(event["start_date"])
        history = frame.loc[frame["event_start"] < start].copy()
        target = frame.loc[frame["event_id"] == event_id].copy()
        previous_event_count = history["event_id"].nunique()
        if previous_event_count < 2 or history["flooded_label"].sum() == 0:
            event_availability.append({"event_id": event_id, "prediction_status": "unavailable", "reason": "insufficient earlier labelled events"})
            continue
        model = fit_balanced(history)
        probability = model.predict_proba(target[FEATURES])[:, 1]
        predictions.extend({
            "event_id": event_id,
            "cell_id": row.cell_id,
            "probability": round(float(score), 4),
            "predicted_label": bool(score >= THRESHOLD),
            "prediction_status": "chronological_out_of_sample",
        } for row, score in zip(target.itertuples(), probability))
        event_availability.append({
            "event_id": event_id, "prediction_status": "chronological_out_of_sample", "prior_event_count": int(previous_event_count)})

    candidate_metrics = json.loads((OUTPUT / "candidate_metrics_v7.json").read_text(encoding="utf-8"))
    v6_metrics = json.loads((OUTPUT / "v6_native_gfd_test_metrics.json").read_text(encoding="utf-8"))
    selected = candidate_metrics["models"]["v7_hydrologic_hgb"]
    seed["predictions"] = predictions
    seed["model"] = {
        "version": "maubin-flood-event-hgb-v7",
        "status": "experimental",
        "threshold": THRESHOLD,
        "metrics": selected["test"],
        "validation_metrics": selected["validation"],
        "comparison": {
            "baseline": "maubin-flood-event-logistic-v6",
            "common_holdout": "2018 native GFD labels (events 4632 and 4666)",
            "v6": v6_metrics,
            "v7": selected["test"],
        },
        "predictors": {
            "terrain": "Copernicus DEM terrain fields and ESA WorldCover context",
            "rainfall": "ERA5-based Open-Meteo lag totals for 1, 3, 7, 14 and 30 days before each event",
            "upstream_inflow_proxy": "GloFAS-based Open-Meteo river discharge lag totals for 1, 3, 7, 14 and 30 days before each event",
            "drainage_and_levees": "OpenStreetMap mapped drain, ditch, canal, levee and embankment distances",
            "tide": "deferred from v7: a validated, Maubin-relevant tide and surge time series covering the 2018 holdout is required",
        },
        "label_source": "Official GFD native 250 m raster pixels; permanent water excluded",
        "evaluation_protocol": "Threshold selected on 2009–2016 validation events; final model fit on pre-2018 events and evaluated on held-out 2018 events.",
    }
    seed["prediction_availability"] = event_availability
    path = OUTPUT / "maubin_hindcast_seed_v7.json"
    path.write_text(json.dumps(seed, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"path": str(path), "prediction_count": len(predictions), "availability": event_availability, "model": seed["model"]}, indent=2))


if __name__ == "__main__":
    main()
