"""Export static v7 cell context from the already validated training artefact.

The seed contains only per-cell predictors that do not vary between events. Dynamic
rainfall and discharge values remain absent and are supplied by timestamped
prospective snapshots at refresh time.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


SOURCE = Path("/home/ubuntu/deltawatch-model-outputs/maubin_training_events_v7.csv")
TARGET = Path("/home/ubuntu/webdev-static-assets/maubin_v7_static_feature_seed.json")
STATIC_COLUMNS = [
    "cell_id",
    "elevation_mean_m",
    "elevation_percentile",
    "local_relief_m",
    "distance_to_waterway_m",
    "land_cover_dominant_code",
    "osm_drainage_distance_m",
    "osm_levee_distance_m",
]


def main() -> None:
    frame = pd.read_csv(SOURCE, usecols=STATIC_COLUMNS)
    unique = frame.drop_duplicates(subset=["cell_id"], keep="first").sort_values("cell_id")
    if len(unique) != frame["cell_id"].nunique():
        raise RuntimeError("Cell identifier uniqueness check failed")
    for column in STATIC_COLUMNS[1:]:
        per_cell = frame.groupby("cell_id")[column].nunique(dropna=False)
        if int(per_cell.max()) != 1:
            raise RuntimeError(f"Static feature varies across events: {column}")
    payload = {
        "schema": "maubin-v7-static-cell-features-v1",
        "model_version": "maubin-flood-event-hgb-v7",
        "static_feature_names": STATIC_COLUMNS[1:],
        "cell_count": int(len(unique)),
        "cells": unique.to_dict(orient="records"),
    }
    TARGET.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"target": str(TARGET), "cell_count": payload["cell_count"]}))


if __name__ == "__main__":
    main()
