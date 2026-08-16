"""Build leakage-safe cell-by-event examples for Maubin flood hindcast experiments.

Inputs are immutable local copies of managed seed artefacts and public-source downloads.
Dynamic features stop at the day before each GFD event begins so event labels cannot leak
into the predictor table.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

from shapely.geometry import shape
from shapely.strtree import STRtree


PROJECT = Path("/home/ubuntu/deltawatch-permanent")
STATIC = Path("/home/ubuntu/webdev-static-assets")
OUTPUT = Path("/home/ubuntu/deltawatch-model-outputs")
OUTPUT.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def daily_series(payload: dict, variable: str) -> dict[str, float]:
    daily = payload.get("daily", {})
    dates = daily.get("time", [])
    values = daily.get(variable, [])
    return {date: float(value) for date, value in zip(dates, values) if value is not None}


def lag_total(series: dict[str, float], event_start: str, days: int) -> float:
    from datetime import date

    target = date.fromisoformat(event_start)
    return round(sum(series.get((target - timedelta(days=offset)).isoformat(), 0.0) for offset in range(1, days + 1)), 4)


def approximate_meters(degrees: float) -> float:
    return round(degrees * 111_000, 1)


def event_label_counts(cells: list[dict], events: list[dict]) -> dict[str, int]:
    summaries: dict[str, int] = {}
    for event in events:
        event_geometry = shape(event["geometry"])
        summaries[str(event["id"])] = sum(1 for cell in cells if event_geometry.intersects(cell["geometry"]))
    return summaries


def main() -> None:
    spatial = load_json(STATIC / "maubin_spatial_seed.json")
    hindcast = load_json(STATIC / "maubin_hindcast_seed.json")
    rainfall = load_json(Path("/home/ubuntu/maubin_era5_2002_2018.json"))
    discharge = load_json(Path("/home/ubuntu/maubin_glofas_2002_2018.json"))
    infrastructure = load_json(Path("/home/ubuntu/maubin_osm_drainage_embankment.json"))

    terrain_cells: list[dict] = []
    for feature in spatial.get("features", []):
        properties = feature.get("properties", {})
        if properties.get("asset_type") != "terrain_cell":
            continue
        terrain_cells.append({"id": str(properties["id"]), "properties": properties, "geometry": shape(feature["geometry"])})

    events = sorted(hindcast.get("events", []), key=lambda event: event["start_date"])
    rainfall_series = daily_series(rainfall, "precipitation_sum")
    discharge_series = daily_series(discharge, "river_discharge")

    drainage_geometries = []
    levee_geometries = []
    for element in infrastructure.get("elements", []):
        geometry = element.get("geometry")
        if not geometry or len(geometry) < 2:
            continue
        coordinates = [(point["lon"], point["lat"]) for point in geometry]
        from shapely.geometry import LineString

        line = LineString(coordinates)
        tags = element.get("tags", {})
        if tags.get("waterway") in {"drain", "ditch", "canal"}:
            drainage_geometries.append(line)
        if tags.get("barrier") == "levee" or tags.get("man_made") == "embankment" or tags.get("embankment") == "yes":
            levee_geometries.append(line)

    drainage_tree = STRtree(drainage_geometries) if drainage_geometries else None
    levee_tree = STRtree(levee_geometries) if levee_geometries else None

    static_rows = []
    for cell in terrain_cells:
        centroid = cell["geometry"].centroid
        properties = cell["properties"]
        drainage_distance = None
        levee_distance = None
        if drainage_tree:
            nearest_index = drainage_tree.nearest(centroid)
            drainage_distance = approximate_meters(centroid.distance(drainage_geometries[nearest_index]))
        if levee_tree:
            nearest_index = levee_tree.nearest(centroid)
            levee_distance = approximate_meters(centroid.distance(levee_geometries[nearest_index]))
        static_rows.append({
            "cell_id": cell["id"],
            "geometry": cell["geometry"],
            "elevation_mean_m": float(properties.get("elevation_mean_m") or 0),
            "elevation_percentile": float(properties.get("elevation_percentile") or 0),
            "local_relief_m": float(properties.get("local_relief_m") or 0),
            "distance_to_waterway_m": float(properties.get("distance_to_waterway_m") or 0),
            "land_cover_dominant_code": int(properties.get("land_cover_dominant_code") or 0),
            "osm_drainage_distance_m": drainage_distance,
            "osm_levee_distance_m": levee_distance,
        })

    event_labels = event_label_counts(terrain_cells, events)
    with (OUTPUT / "event_label_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["event_id", "start_date", "end_date", "area_km2", "intersecting_cells"])
        writer.writeheader()
        for event in events:
            writer.writerow({
                "event_id": event["id"],
                "start_date": event["start_date"],
                "end_date": event["end_date"],
                "area_km2": event["area_km2"],
                "intersecting_cells": event_labels[str(event["id"])],
            })

    fieldnames = [
        "event_id", "event_start", "event_end", "cell_id", "flooded_label",
        "elevation_mean_m", "elevation_percentile", "local_relief_m", "distance_to_waterway_m", "land_cover_dominant_code",
        "osm_drainage_distance_m", "osm_levee_distance_m",
        "rainfall_lag_1d_mm", "rainfall_lag_3d_mm", "rainfall_lag_7d_mm", "rainfall_lag_14d_mm", "rainfall_lag_30d_mm",
        "discharge_lag_1d_m3s", "discharge_lag_3d_m3s", "discharge_lag_7d_m3s", "discharge_lag_14d_m3s", "discharge_lag_30d_m3s",
    ]
    row_count = 0
    with (OUTPUT / "maubin_training_events_v7.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for event in events:
            event_geometry = shape(event["geometry"])
            dynamic = {
                "rainfall_lag_1d_mm": lag_total(rainfall_series, event["start_date"], 1),
                "rainfall_lag_3d_mm": lag_total(rainfall_series, event["start_date"], 3),
                "rainfall_lag_7d_mm": lag_total(rainfall_series, event["start_date"], 7),
                "rainfall_lag_14d_mm": lag_total(rainfall_series, event["start_date"], 14),
                "rainfall_lag_30d_mm": lag_total(rainfall_series, event["start_date"], 30),
                "discharge_lag_1d_m3s": lag_total(discharge_series, event["start_date"], 1),
                "discharge_lag_3d_m3s": lag_total(discharge_series, event["start_date"], 3),
                "discharge_lag_7d_m3s": lag_total(discharge_series, event["start_date"], 7),
                "discharge_lag_14d_m3s": lag_total(discharge_series, event["start_date"], 14),
                "discharge_lag_30d_m3s": lag_total(discharge_series, event["start_date"], 30),
            }
            for cell in static_rows:
                writer.writerow({
                    "event_id": event["id"],
                    "event_start": event["start_date"],
                    "event_end": event["end_date"],
                    "cell_id": cell["cell_id"],
                    "flooded_label": int(event_geometry.intersects(cell["geometry"])),
                    **{key: value for key, value in cell.items() if key not in {"cell_id", "geometry"}},
                    **dynamic,
                })
                row_count += 1

    manifest = {
        "terrain_cells": len(terrain_cells),
        "events": len(events),
        "training_rows": row_count,
        "rainfall_source": "Open-Meteo archive API (ERA5-based daily precipitation)",
        "discharge_source": "Open-Meteo flood API backed by GloFAS historical river discharge",
        "infrastructure_source": "OpenStreetMap Overpass query for drain, ditch, canal, levee and embankment tags",
        "tide_feature_status": "deferred: FES2022 access requires registration; no local-gauge series has been verified",
        "leakage_control": "All dynamic rolling windows end one day before each GFD event start date.",
        "drainage_feature_count": len(drainage_geometries),
        "levee_feature_count": len(levee_geometries),
    }
    (OUTPUT / "data_manifest_v7.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
