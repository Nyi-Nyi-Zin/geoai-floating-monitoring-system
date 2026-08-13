"""Build event-cell labels aligned with rainfall on each flood event date."""

from __future__ import annotations

import argparse
import csv
import math
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.db.session import engine
from scripts.flood_label_sources import (
    LABEL_SOURCE_GFD,
    LabelSource,
    label_source_sql_clause,
    normalize_label_source,
)
from scripts.train_flood_susceptibility import FEATURE_NAMES as STATIC_FEATURE_NAMES

RAINFALL_FEATURE_NAMES = [
    "rainfall_mean_1d_mm",
    "rainfall_max_1d_mm",
    "rainfall_p90_1d_mm",
    "rainfall_accumulation_3d_mm",
    "rainfall_accumulation_7d_mm",
    "rainfall_accumulation_14d_mm",
    "rainfall_accumulation_30d_mm",
    "rainfall_anomaly_7d",
]
TERRAIN_FEATURE_NAMES = [
    "hand_mean_m",
    "distance_to_river_m",
    "distance_to_canal_m",
    "historical_event_count",
]
ENGINEERED_FEATURE_NAMES = [
    "waterway_proximity_index",
    "river_proximity_index",
    "canal_proximity_index",
    "surface_water_influence_pct",
    "flatness_index",
    "low_hand_waterway_risk",
    "rainfall_7d_x_waterway_proximity",
    "rainfall_30d_x_low_elevation",
    "rainfall_3d_x_surface_water",
    "rainfall_7d_x_flatness",
    "rainfall_intensity_ratio",
]
LANDCOVER_FEATURE_NAMES = [
    "landcover_tree_pct",
    "landcover_shrub_pct",
    "landcover_grass_pct",
    "landcover_cropland_pct",
    "landcover_built_pct",
    "landcover_bare_pct",
    "landcover_water_pct",
    "landcover_wetland_pct",
    "landcover_mangrove_pct",
]
FEATURE_NAMES = [
    *STATIC_FEATURE_NAMES,
    *TERRAIN_FEATURE_NAMES,
    *RAINFALL_FEATURE_NAMES,
    *ENGINEERED_FEATURE_NAMES,
]

DEFAULT_HAND_M = 50.0
DEFAULT_RIVER_DISTANCE_M = 5_000.0
DEFAULT_CANAL_DISTANCE_M = 5_000.0
GEOMETRY_SIMPLIFY_TOLERANCE = 0.002


CELL_CATALOG_SQL = text(
    f"""
    SELECT
      id AS geo_asset_id,
      name,
      ST_X(ST_Centroid(geometry)) AS centroid_lon,
      ST_Y(ST_Centroid(geometry)) AS centroid_lat,
      (properties->>'elevation_mean_m')::double precision AS elevation_mean_m,
      (properties->>'elevation_min_m')::double precision AS elevation_min_m,
      (properties->>'elevation_max_m')::double precision AS elevation_max_m,
      COALESCE((properties->>'elevation_stddev_m')::double precision, 0) AS elevation_stddev_m,
      (properties->>'elevation_percentile')::double precision AS elevation_percentile,
      (properties->>'distance_to_waterway_m')::double precision AS distance_to_waterway_m,
      (properties->>'local_relief_m')::double precision AS local_relief_m,
      COALESCE((properties->'land_cover_percentages'->>'10')::double precision, 0) AS landcover_tree_pct,
      COALESCE((properties->'land_cover_percentages'->>'20')::double precision, 0) AS landcover_shrub_pct,
      COALESCE((properties->'land_cover_percentages'->>'30')::double precision, 0) AS landcover_grass_pct,
      COALESCE((properties->'land_cover_percentages'->>'40')::double precision, 0) AS landcover_cropland_pct,
      COALESCE((properties->'land_cover_percentages'->>'50')::double precision, 0) AS landcover_built_pct,
      COALESCE((properties->'land_cover_percentages'->>'60')::double precision, 0) AS landcover_bare_pct,
      COALESCE((properties->'land_cover_percentages'->>'80')::double precision, 0) AS landcover_water_pct,
      COALESCE((properties->'land_cover_percentages'->>'90')::double precision, 0) AS landcover_wetland_pct,
      COALESCE((properties->'land_cover_percentages'->>'95')::double precision, 0) AS landcover_mangrove_pct,
      COALESCE(
        (properties->>'hand_mean_m')::double precision,
        {DEFAULT_HAND_M}
      ) AS hand_mean_m,
      COALESCE(
        (properties->>'distance_to_river_m')::double precision,
        (properties->>'distance_to_waterway_m')::double precision,
        {DEFAULT_RIVER_DISTANCE_M}
      ) AS distance_to_river_m,
      COALESCE(
        (properties->>'distance_to_canal_m')::double precision,
        (properties->>'distance_to_waterway_m')::double precision,
        {DEFAULT_CANAL_DISTANCE_M}
      ) AS distance_to_canal_m
    FROM geo_assets
    WHERE asset_type = 'terrain_cell'
    ORDER BY id
    """
)

HISTORICAL_EVENT_COUNT_SQL = text(
    """
    SELECT
      c.id AS geo_asset_id,
      COALESCE(MAX((f.properties->>'event_count')::integer), 0) AS historical_event_count
    FROM geo_assets AS c
    LEFT JOIN flood_extents AS f
      ON f.source_key LIKE 'maubin:gfd:frequency:%'
      AND c.geometry && f.geometry
      AND ST_Intersects(c.geometry, f.geometry)
    WHERE c.asset_type = 'terrain_cell'
    GROUP BY c.id
    """
)


def event_metadata_sql(label_source: LabelSource = LABEL_SOURCE_GFD) -> text:
    source_filter = label_source_sql_clause(label_source)
    return text(
        f"""
        SELECT
          e.event_id,
          e.event_start_date,
          e.event_end_date,
          r.mean_precipitation_mm AS rainfall_mean_1d_mm,
          r.max_precipitation_mm AS rainfall_max_1d_mm,
          r.p90_precipitation_mm AS rainfall_p90_1d_mm,
          r.accumulation_3d_mm AS rainfall_accumulation_3d_mm,
          r.accumulation_7d_mm AS rainfall_accumulation_7d_mm,
          r.accumulation_30d_mm AS rainfall_accumulation_30d_mm
        FROM (
          SELECT
            event_id,
            MIN(observed_start_date) AS event_start_date,
            MAX(observed_end_date) AS event_end_date
          FROM flood_extents
          WHERE event_id IS NOT NULL AND observed_start_date IS NOT NULL
          {source_filter}
          GROUP BY event_id
        ) AS e
        JOIN rainfall_history AS r ON r.observed_date = e.event_start_date
        ORDER BY e.event_start_date, e.event_id
        """
    )


def event_flooded_fractions_sql(label_source: LabelSource = LABEL_SOURCE_GFD) -> text:
    source_filter = label_source_sql_clause(label_source)
    return text(
        f"""
        WITH event_geom AS (
          SELECT
            ST_SimplifyPreserveTopology(
              ST_UnaryUnion(ST_Collect(geometry)),
              :simplify_tolerance
            ) AS geometry
          FROM flood_extents
          WHERE event_id = :event_id
            AND observed_start_date IS NOT NULL
            {source_filter}
        )
        SELECT
          c.id AS geo_asset_id,
          LEAST(1.0, GREATEST(0.0,
            ST_Area(ST_Intersection(c.geometry, e.geometry)::geography)
            / NULLIF(ST_Area(c.geometry::geography), 0)
          )) AS flooded_fraction
        FROM geo_assets AS c
        CROSS JOIN event_geom AS e
        WHERE c.asset_type = 'terrain_cell'
          AND e.geometry IS NOT NULL
          AND c.geometry && ST_Envelope(e.geometry)
          AND ST_Intersects(c.geometry, e.geometry)
        """
    )


def event_dataset_sql(label_source: LabelSource = LABEL_SOURCE_GFD) -> text:
    """Legacy single-query builder kept for compatibility in tests/docs."""
    source_filter = label_source_sql_clause(label_source)
    return text(
        f"""
    WITH events AS (
      SELECT
        event_id,
        MIN(observed_start_date) AS event_start_date,
        MAX(observed_end_date) AS event_end_date,
        ST_SimplifyPreserveTopology(
          ST_UnaryUnion(ST_Collect(geometry)),
          {GEOMETRY_SIMPLIFY_TOLERANCE}
        ) AS geometry
      FROM flood_extents
      WHERE event_id IS NOT NULL AND observed_start_date IS NOT NULL
      {source_filter}
      GROUP BY event_id
    ),
    cells AS (
      SELECT
        id,
        name,
        geometry,
        properties,
        ST_Area(geometry::geography) AS cell_area_m2,
        ST_X(ST_Centroid(geometry)) AS centroid_lon,
        ST_Y(ST_Centroid(geometry)) AS centroid_lat,
        COALESCE(
          (properties->>'hand_mean_m')::double precision,
          {DEFAULT_HAND_M}
        ) AS hand_mean_m,
        COALESCE(
          (properties->>'distance_to_river_m')::double precision,
          (properties->>'distance_to_waterway_m')::double precision,
          {DEFAULT_RIVER_DISTANCE_M}
        ) AS distance_to_river_m,
        COALESCE(
          (properties->>'distance_to_canal_m')::double precision,
          (properties->>'distance_to_waterway_m')::double precision,
          {DEFAULT_CANAL_DISTANCE_M}
        ) AS distance_to_canal_m
      FROM geo_assets
      WHERE asset_type = 'terrain_cell'
    ),
    historical_flood AS (
      SELECT
        c.id,
        COALESCE(MAX((f.properties->>'event_count')::integer), 0) AS historical_event_count
      FROM cells AS c
      LEFT JOIN flood_extents AS f
        ON f.source_key LIKE 'maubin:gfd:frequency:%'
        AND c.geometry && f.geometry
        AND ST_Intersects(c.geometry, f.geometry)
      GROUP BY c.id
    )
    SELECT
      e.event_id,
      e.event_start_date,
      e.event_end_date,
      c.id AS geo_asset_id,
      c.name,
      c.centroid_lon,
      c.centroid_lat,
      LEAST(1.0, GREATEST(0.0,
        CASE WHEN c.geometry && ST_Envelope(e.geometry)
          AND ST_Intersects(c.geometry, e.geometry)
          THEN ST_Area(ST_Intersection(c.geometry, e.geometry)::geography)
               / NULLIF(c.cell_area_m2, 0)
          ELSE 0 END
      )) AS flooded_fraction,
      (c.properties->>'elevation_mean_m')::double precision AS elevation_mean_m,
      (c.properties->>'elevation_min_m')::double precision AS elevation_min_m,
      (c.properties->>'elevation_max_m')::double precision AS elevation_max_m,
      COALESCE((c.properties->>'elevation_stddev_m')::double precision, 0) AS elevation_stddev_m,
      (c.properties->>'elevation_percentile')::double precision AS elevation_percentile,
      (c.properties->>'distance_to_waterway_m')::double precision AS distance_to_waterway_m,
      (c.properties->>'local_relief_m')::double precision AS local_relief_m,
      COALESCE((c.properties->'land_cover_percentages'->>'10')::double precision, 0) AS landcover_tree_pct,
      COALESCE((c.properties->'land_cover_percentages'->>'20')::double precision, 0) AS landcover_shrub_pct,
      COALESCE((c.properties->'land_cover_percentages'->>'30')::double precision, 0) AS landcover_grass_pct,
      COALESCE((c.properties->'land_cover_percentages'->>'40')::double precision, 0) AS landcover_cropland_pct,
      COALESCE((c.properties->'land_cover_percentages'->>'50')::double precision, 0) AS landcover_built_pct,
      COALESCE((c.properties->'land_cover_percentages'->>'60')::double precision, 0) AS landcover_bare_pct,
      COALESCE((c.properties->'land_cover_percentages'->>'80')::double precision, 0) AS landcover_water_pct,
      COALESCE((c.properties->'land_cover_percentages'->>'90')::double precision, 0) AS landcover_wetland_pct,
      COALESCE((c.properties->'land_cover_percentages'->>'95')::double precision, 0) AS landcover_mangrove_pct,
      c.hand_mean_m,
      c.distance_to_river_m,
      c.distance_to_canal_m,
      COALESCE(hf.historical_event_count, 0) AS historical_event_count,
      r.mean_precipitation_mm AS rainfall_mean_1d_mm,
      r.max_precipitation_mm AS rainfall_max_1d_mm,
      r.p90_precipitation_mm AS rainfall_p90_1d_mm,
      r.accumulation_3d_mm AS rainfall_accumulation_3d_mm,
      r.accumulation_7d_mm AS rainfall_accumulation_7d_mm,
      r.accumulation_30d_mm AS rainfall_accumulation_30d_mm
    FROM events AS e
    JOIN rainfall_history AS r ON r.observed_date = e.event_start_date
    CROSS JOIN cells AS c
    LEFT JOIN historical_flood AS hf ON hf.id = c.id
    ORDER BY e.event_start_date, e.event_id, c.id
    """
    )


EVENT_DATASET_SQL = event_dataset_sql(LABEL_SOURCE_GFD)


def as_fraction(value: float) -> float:
    """Normalize land-cover shares that may be stored as 0-1 or 0-100."""
    number = float(value)
    if number > 1.0:
        number /= 100.0
    return min(1.0, max(0.0, number))


def flood_excess_fraction(row: dict[str, Any]) -> float:
    """Observed inundation beyond permanent water/wetland/mangrove cover."""
    surface = min(
        1.0,
        as_fraction(row["landcover_water_pct"])
        + as_fraction(row["landcover_wetland_pct"])
        + as_fraction(row["landcover_mangrove_pct"]),
    )
    return max(0.0, float(row["flooded_fraction"]) - surface)


def event_target_label(
    row: dict[str, Any],
    target_threshold: float,
    *,
    label_mode: str = "flood_excess",
) -> int:
    if label_mode == "flood_extent":
        return int(float(row["flooded_fraction"]) >= target_threshold)
    if label_mode != "flood_excess":
        raise ValueError(f"Unsupported label_mode: {label_mode}")
    return int(flood_excess_fraction(row) >= target_threshold)


def temporal_split_map(events: list[tuple[str, date]]) -> dict[str, str]:
    ordered = sorted(set(events), key=lambda item: (item[1], item[0]))
    if len(ordered) < 4:
        raise ValueError(
            "At least 4 rainfall-aligned events are required for temporal splits"
        )
    holdout_count = max(1, len(ordered) // 5)
    if len(ordered) - (2 * holdout_count) < 2:
        holdout_count = 1
    result = {event_id: "train" for event_id, _ in ordered}
    for event_id, _ in ordered[-2 * holdout_count : -holdout_count]:
        result[event_id] = "validation"
    for event_id, _ in ordered[-holdout_count:]:
        result[event_id] = "test"
    return result


def load_rainfall_history_index() -> dict[date, dict[str, float]]:
    if engine is None:
        raise RuntimeError("DATABASE_URL is required")
    query = text(
        """
        SELECT observed_date, mean_precipitation_mm, accumulation_7d_mm
        FROM rainfall_history
        ORDER BY observed_date
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query).mappings().all()
    by_date: dict[date, dict[str, float]] = {}
    daily_means: list[float] = []
    for row in rows:
        observed = row["observed_date"]
        mean_mm = float(row["mean_precipitation_mm"])
        by_date[observed] = {
            "mean_precipitation_mm": mean_mm,
            "accumulation_7d_mm": float(row["accumulation_7d_mm"]),
        }
        daily_means.append(mean_mm)
    prefix = [0.0]
    ordered_dates = sorted(by_date)
    for observed in ordered_dates:
        prefix.append(prefix[-1] + by_date[observed]["mean_precipitation_mm"])
    for index, observed in enumerate(ordered_dates):
        start = max(0, index + 1 - 14)
        by_date[observed]["accumulation_14d_mm"] = prefix[index + 1] - prefix[start]
    week_buckets: dict[int, list[float]] = {}
    for observed in ordered_dates:
        week = observed.isocalendar().week
        week_buckets.setdefault(week, []).append(
            by_date[observed]["accumulation_7d_mm"]
        )
    week_averages = {
        week: sum(values) / len(values) for week, values in week_buckets.items()
    }
    for observed in ordered_dates:
        week = observed.isocalendar().week
        current_7d = by_date[observed]["accumulation_7d_mm"]
        historical_avg = week_averages.get(week, current_7d)
        by_date[observed]["rainfall_anomaly_7d"] = current_7d / max(
            historical_avg, 1.0
        )
    return by_date


def enrich_rainfall_features(
    rows: list[dict[str, Any]],
    rainfall_index: dict[date, dict[str, float]],
) -> None:
    for row in rows:
        event_date = row["event_start_date"]
        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)
        rainfall = rainfall_index.get(event_date)
        if rainfall is None:
            row["rainfall_accumulation_14d_mm"] = float(
                row["rainfall_accumulation_7d_mm"]
            )
            row["rainfall_anomaly_7d"] = 1.0
            continue
        row["rainfall_accumulation_14d_mm"] = float(
            rainfall["accumulation_14d_mm"]
        )
        row["rainfall_anomaly_7d"] = float(rainfall["rainfall_anomaly_7d"])


def load_cell_catalog() -> list[dict[str, Any]]:
    if engine is None:
        raise RuntimeError("DATABASE_URL is required")
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(CELL_CATALOG_SQL).mappings()]


def load_historical_event_counts() -> dict[str, int]:
    if engine is None:
        raise RuntimeError("DATABASE_URL is required")
    with engine.connect() as connection:
        rows = connection.execute(HISTORICAL_EVENT_COUNT_SQL).mappings()
        return {str(row["geo_asset_id"]): int(row["historical_event_count"]) for row in rows}


def load_event_flooded_fractions(
    event_id: str,
    label_source: LabelSource,
) -> dict[str, float]:
    if engine is None:
        raise RuntimeError("DATABASE_URL is required")
    query = event_flooded_fractions_sql(label_source)
    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {
                "event_id": event_id,
                "simplify_tolerance": GEOMETRY_SIMPLIFY_TOLERANCE,
            },
        ).mappings()
        return {
            str(row["geo_asset_id"]): float(row["flooded_fraction"]) for row in rows
        }


def load_event_dataset(
    label_source: LabelSource = LABEL_SOURCE_GFD,
) -> list[dict[str, Any]]:
    if engine is None:
        raise RuntimeError("DATABASE_URL is required")
    rainfall_index = load_rainfall_history_index()
    cells = load_cell_catalog()
    historical_counts = load_historical_event_counts()
    with engine.connect() as connection:
        events = [
            dict(row)
            for row in connection.execute(event_metadata_sql(label_source)).mappings()
        ]
    if not events or not cells:
        raise RuntimeError(
            "No event/rainfall-aligned rows are available for "
            f"label_source={label_source!r}. Check /flood-ml/event-readiness."
        )

    rows: list[dict[str, Any]] = []
    for event in events:
        event_id = str(event["event_id"])
        flooded_fractions = load_event_flooded_fractions(event_id, label_source)
        for cell in cells:
            geo_asset_id = str(cell["geo_asset_id"])
            row = {
                **cell,
                "event_id": event_id,
                "event_start_date": event["event_start_date"],
                "event_end_date": event["event_end_date"],
                "historical_event_count": historical_counts.get(geo_asset_id, 0),
                "flooded_fraction": flooded_fractions.get(geo_asset_id, 0.0),
                "rainfall_mean_1d_mm": event["rainfall_mean_1d_mm"],
                "rainfall_max_1d_mm": event["rainfall_max_1d_mm"],
                "rainfall_p90_1d_mm": event["rainfall_p90_1d_mm"],
                "rainfall_accumulation_3d_mm": event["rainfall_accumulation_3d_mm"],
                "rainfall_accumulation_7d_mm": event["rainfall_accumulation_7d_mm"],
                "rainfall_accumulation_30d_mm": event["rainfall_accumulation_30d_mm"],
            }
            rows.append(row)

    enrich_rainfall_features(rows, rainfall_index)
    for row in rows:
        row["flooded_fraction"] = float(row["flooded_fraction"])
        row["historical_event_count"] = int(row["historical_event_count"])
        for feature in [
            *STATIC_FEATURE_NAMES,
            *TERRAIN_FEATURE_NAMES,
            *RAINFALL_FEATURE_NAMES,
        ]:
            if row[feature] is None:
                raise ValueError(f"Missing {feature} for event {row['event_id']}")
            value = float(row[feature])
            if feature in LANDCOVER_FEATURE_NAMES:
                value = as_fraction(value)
            row[feature] = value
        _append_engineered_features(row)
    return rows


def _append_engineered_features(row: dict[str, Any]) -> None:
    distance_to_waterway = max(float(row["distance_to_waterway_m"]), 0.0)
    distance_to_river = max(float(row["distance_to_river_m"]), 0.0)
    distance_to_canal = max(float(row["distance_to_canal_m"]), 0.0)
    hand_mean = max(float(row["hand_mean_m"]), 0.0)
    elevation_percentile = min(max(float(row["elevation_percentile"]), 0.0), 1.0)
    local_relief = max(float(row["local_relief_m"]), 0.0)
    rainfall_3d = max(float(row["rainfall_accumulation_3d_mm"]), 0.0)
    rainfall_7d = max(float(row["rainfall_accumulation_7d_mm"]), 0.0)
    rainfall_30d = max(float(row["rainfall_accumulation_30d_mm"]), 0.0)
    rainfall_max_1d = max(float(row["rainfall_max_1d_mm"]), 0.0)
    surface_water_influence = min(
        1.0,
        as_fraction(row["landcover_water_pct"])
        + as_fraction(row["landcover_wetland_pct"])
        + as_fraction(row["landcover_mangrove_pct"]),
    )
    low_elevation_index = 1.0 - elevation_percentile
    waterway_proximity_index = 1.0 / (1.0 + distance_to_waterway / 250.0)
    river_proximity_index = 1.0 / (1.0 + distance_to_river / 250.0)
    canal_proximity_index = 1.0 / (1.0 + distance_to_canal / 250.0)
    flatness_index = 1.0 / (1.0 + local_relief)
    low_hand = 1.0 / (1.0 + hand_mean / 3.0)

    row["waterway_proximity_index"] = waterway_proximity_index
    row["river_proximity_index"] = river_proximity_index
    row["canal_proximity_index"] = canal_proximity_index
    row["surface_water_influence_pct"] = surface_water_influence
    row["flatness_index"] = flatness_index
    row["low_hand_waterway_risk"] = low_hand * waterway_proximity_index
    row["rainfall_7d_x_waterway_proximity"] = rainfall_7d * waterway_proximity_index
    row["rainfall_30d_x_low_elevation"] = rainfall_30d * low_elevation_index
    row["rainfall_3d_x_surface_water"] = rainfall_3d * surface_water_influence
    row["rainfall_7d_x_flatness"] = rainfall_7d * flatness_index
    row["rainfall_intensity_ratio"] = rainfall_max_1d / max(
        1.0, math.sqrt(rainfall_7d * max(rainfall_30d, 1.0))
    )


def export_event_dataset(
    rows: list[dict[str, Any]],
    output: Path,
    target_threshold: float,
    *,
    label_mode: str = "flood_excess",
) -> dict[str, int]:
    splits = temporal_split_map(
        [(row["event_id"], row["event_start_date"]) for row in rows]
    )
    fields = [
        "event_id",
        "event_start_date",
        "event_end_date",
        "geo_asset_id",
        "name",
        "centroid_lon",
        "centroid_lat",
        *FEATURE_NAMES,
        "flooded_fraction",
        "flood_excess_fraction",
        "target_label",
        "temporal_split",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    counts = {"train": 0, "validation": 0, "test": 0}
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            split = splits[row["event_id"]]
            counts[split] += 1
            writer.writerow(
                {
                    **{name: row[name] for name in fields if name in row},
                    "flood_excess_fraction": round(flood_excess_fraction(row), 6),
                    "target_label": event_target_label(
                        row, target_threshold, label_mode=label_mode
                    ),
                    "temporal_split": split,
                }
            )
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/derived/maubin_flood_event_dataset_v1.csv"),
    )
    parser.add_argument("--target-threshold", type=float, default=0.10)
    parser.add_argument(
        "--label-mode",
        choices=("flood_excess", "flood_extent"),
        default="flood_excess",
    )
    parser.add_argument(
        "--label-source",
        default=LABEL_SOURCE_GFD,
        help="Label provenance filter: gfd (default training labels), sar, or all.",
    )
    args = parser.parse_args()
    label_source = normalize_label_source(args.label_source)
    rows = load_event_dataset(label_source)
    counts = export_event_dataset(
        rows, args.output, args.target_threshold, label_mode=args.label_mode
    )
    print(
        {
            "events": len({row["event_id"] for row in rows}),
            "rows": len(rows),
            "split_rows": counts,
            "label_mode": args.label_mode,
            "label_source": label_source,
            "output": str(args.output),
        }
    )


if __name__ == "__main__":
    main()
