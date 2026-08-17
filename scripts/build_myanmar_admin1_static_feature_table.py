"""Build an auditable, non-predictive Myanmar Admin 1 event feature table.

Inputs are leakage-safe rainfall lags ending before the event, true-polygon GFD
Admin 1 labels, and static source descriptors. This is preparation only: no model
is trained, no score or probability is generated, and no alert is created.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


BASE = Path("/home/ubuntu/deltawatch-model-outputs")
RAINFALL = BASE / "myanmar_admin1_event_rainfall_lags.csv"
FLOOD_COVERAGE = BASE / "myanmar_gfd_admin1_historical_coverage.csv"
RIVERS = BASE / "myanmar_admin1_hydrorivers_static.json"
DEM = BASE / "myanmar_admin1_copernicus_dem_static.json"
WORLDCOVER = BASE / "myanmar_admin1_worldcover_static.json"
OUTPUT = BASE / "myanmar_admin1_event_static_feature_table.csv"
MANIFEST = BASE / "myanmar_admin1_event_static_feature_table_manifest.json"

EVENT_SPLITS = {
    2041: "development", 2276: "development", 2859: "development", 3068: "development",
    3125: "development", 3169: "development", 3302: "development",
    3662: "validation", 4283: "validation", 4365: "validation",
    4632: "holdout", 4666: "holdout",
}
STATIC_FIELDS = [
    "river_intersecting_reach_count", "river_clipped_length_km", "river_max_strahler_order",
    "river_length_weighted_mean_discharge_m3s", "terrain_mean_elevation_m",
    "terrain_median_elevation_m", "terrain_p10_elevation_m", "terrain_p90_elevation_m",
    "terrain_regional_relief_p90_p10_m", "land_cover_dominant_code",
    "land_cover_dominant_share", "land_cover_tree_cover_share", "land_cover_cropland_share",
    "land_cover_permanent_water_share", "land_cover_herbaceous_wetland_share", "land_cover_mangrove_share",
]


def read_static(path: Path) -> tuple[dict[str, dict], dict]:
    document = json.loads(path.read_text(encoding="utf-8"))
    regions = {row["admin1_pcode"]: row for row in document["regions"]}
    if len(regions) != 18:
        raise RuntimeError(f"Expected 18 regions in {path.name}, found {len(regions)}")
    return regions, document


def main() -> None:
    rivers, river_source = read_static(RIVERS)
    terrain, terrain_source = read_static(DEM)
    land_cover, land_cover_source = read_static(WORLDCOVER)
    with RAINFALL.open(newline="", encoding="utf-8") as handle:
        rainfall_rows = list(csv.DictReader(handle))
    with FLOOD_COVERAGE.open(newline="", encoding="utf-8") as handle:
        coverage_rows = list(csv.DictReader(handle))
    coverage = {(row["event_id"], row["admin1_pcode"]): row for row in coverage_rows}
    if len(rainfall_rows) != 216 or len(coverage) != 216:
        raise RuntimeError("Expected 216 rows in each leakage-safe event-region input")

    output_rows = []
    for rain in rainfall_rows:
        event_id = int(rain["event_id"])
        pcode = rain["admin1_pcode"]
        label = coverage.get((rain["event_id"], pcode))
        if label is None:
            raise RuntimeError(f"Missing GFD coverage label for event {event_id}, {pcode}")
        if event_id not in EVENT_SPLITS:
            raise RuntimeError(f"Unregistered event split for {event_id}")
        if rain["coverage_status"] != label["coverage_status"]:
            raise RuntimeError(f"Coverage mismatch for event {event_id}, {pcode}")
        river = rivers.get(pcode)
        terrain_row = terrain.get(pcode)
        lc = land_cover.get(pcode)
        if not river or not terrain_row or not lc:
            raise RuntimeError(f"Missing static context for {pcode}")
        shares = lc["class_sample_shares"]
        output_rows.append({
            "event_id": event_id,
            "event_start": rain["event_start"],
            "temporal_split": EVENT_SPLITS[event_id],
            "admin1_pcode": pcode,
            "admin1_name": rain["admin1_name"],
            "coverage_status": rain["coverage_status"],
            "observed_flood_presence": int(label["observed_flood_presence"]),
            "flooded_fraction_label": float(label["flooded_fraction"]),
            "rainfall_lag_1d_mm": float(rain["rainfall_lag_1d_mm"]),
            "rainfall_lag_3d_mm": float(rain["rainfall_lag_3d_mm"]),
            "rainfall_lag_7d_mm": float(rain["rainfall_lag_7d_mm"]),
            "rainfall_lag_14d_mm": float(rain["rainfall_lag_14d_mm"]),
            "rainfall_lag_30d_mm": float(rain["rainfall_lag_30d_mm"]),
            "river_intersecting_reach_count": int(river["intersecting_reach_count"]),
            "river_clipped_length_km": float(river["clipped_river_length_km"]),
            "river_max_strahler_order": int(river["max_strahler_order"]),
            "river_length_weighted_mean_discharge_m3s": float(river["length_weighted_mean_discharge_m3s"]),
            "terrain_mean_elevation_m": float(terrain_row["mean_elevation_m"]),
            "terrain_median_elevation_m": float(terrain_row["median_elevation_m"]),
            "terrain_p10_elevation_m": float(terrain_row["p10_elevation_m"]),
            "terrain_p90_elevation_m": float(terrain_row["p90_elevation_m"]),
            "terrain_regional_relief_p90_p10_m": float(terrain_row["regional_relief_p90_p10_m"]),
            "land_cover_dominant_code": int(lc["dominant_land_cover_code"]),
            "land_cover_dominant_share": float(lc["dominant_land_cover_share"]),
            "land_cover_tree_cover_share": float(shares["10"]),
            "land_cover_cropland_share": float(shares["40"]),
            "land_cover_permanent_water_share": float(shares["80"]),
            "land_cover_herbaceous_wetland_share": float(shares["90"]),
            "land_cover_mangrove_share": float(shares["95"]),
        })

    fieldnames = list(output_rows[0])
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)
    split_counts = {
        split: {"rows": sum(row["temporal_split"] == split for row in output_rows), "events": len({row["event_id"] for row in output_rows if row["temporal_split"] == split}), "positive_rows": sum(row["temporal_split"] == split and row["observed_flood_presence"] == 1 for row in output_rows)}
        for split in ("development", "validation", "holdout")
    }
    manifest = {
        "schema": "deltawatch-myanmar-admin1-event-static-feature-table-v1",
        "row_count": len(output_rows),
        "region_count": len({row["admin1_pcode"] for row in output_rows}),
        "event_count": len({row["event_id"] for row in output_rows}),
        "split_counts": split_counts,
        "input_contract": {
            "rainfall_lags": "Pre-event ERA5 daily rainfall lags; each lag ends before event start.",
            "labels": "True-polygon Admin 1 historical GFD coverage; historical labels are output columns and not feature columns.",
            "static_river_source": river_source["schema"],
            "static_terrain_source": terrain_source["schema"],
            "static_land_cover_source": land_cover_source["schema"],
            "frozen_split": "Development 2002-2008, validation 2010-2016, holdout 2018. Holdout rows must not influence transforms, model selection, or thresholds.",
        },
        "feature_columns": [name for name in fieldnames if name not in {"event_id", "event_start", "temporal_split", "admin1_pcode", "admin1_name", "coverage_status", "observed_flood_presence", "flooded_fraction_label"}],
        "label_columns": ["observed_flood_presence", "flooded_fraction_label"],
        "limits": [
            "This table is a historical analysis artefact, not an operational feature feed.",
            "No current/upstream flow, gauge stage, tide, levee, drainage-capacity, or prospective verified-outcome source is present in this table.",
            "No model is fitted and no flood probability, forecast, risk score, predicted label, or alert is created.",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "manifest": str(MANIFEST), "rows": len(output_rows), "split_counts": split_counts}, indent=2))


if __name__ == "__main__":
    main()
