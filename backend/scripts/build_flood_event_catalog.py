"""Build a HYDRAFloods-style flood event catalog with terrain and rainfall metadata."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.db.session import engine
from scripts.flood_label_sources import (
    LABEL_SOURCE_GFD,
    LABEL_SOURCE_SAR,
    LabelSource,
    label_source_sql_clause,
    normalize_label_source,
)

CELL_AREA_KM2 = 0.25

CATALOG_SQL = """
WITH events AS (
  SELECT
    event_id,
    MIN(observed_start_date) AS start_date,
    MAX(observed_end_date) AS end_date,
    ST_Area(ST_UnaryUnion(ST_Collect(geometry))::geography) / 1e6 AS flood_area_km2,
    source_key
  FROM flood_extents
  WHERE event_id IS NOT NULL AND observed_start_date IS NOT NULL
  {source_filter}
  GROUP BY event_id, source_key
),
event_union AS (
  SELECT
    event_id,
    MIN(start_date) AS start_date,
    MAX(end_date) AS end_date,
    SUM(flood_area_km2) AS flood_area_km2,
    MAX(source_key) AS source_key
  FROM events
  GROUP BY event_id
),
overlap AS (
  SELECT
    e.event_id,
    AVG(
      CASE
        WHEN (c.properties->>'hand_mean_m')::double precision BETWEEN 0 AND 5000
          THEN (c.properties->>'hand_mean_m')::double precision
      END
    ) AS mean_hand_m,
    AVG((c.properties->>'local_relief_m')::double precision) AS mean_local_relief_m,
    AVG((c.properties->>'distance_to_river_m')::double precision) AS mean_river_distance_m,
    AVG((c.properties->>'distance_to_canal_m')::double precision) AS mean_canal_distance_m,
    MAX(
      COALESCE((f.properties->>'event_count')::integer, 0)
    ) AS max_historical_event_count
  FROM event_union AS e
  JOIN flood_extents AS fe
    ON fe.event_id = e.event_id
  JOIN geo_assets AS c
    ON c.asset_type = 'terrain_cell'
    AND ST_Intersects(c.geometry, fe.geometry)
  LEFT JOIN flood_extents AS f
    ON f.source_key LIKE 'maubin:gfd:frequency:%'
    AND ST_Intersects(c.geometry, f.geometry)
  GROUP BY e.event_id
)
SELECT
  e.event_id,
  e.start_date,
  e.end_date,
  ROUND(e.flood_area_km2::numeric, 3) AS flood_area_km2,
  e.source_key,
  r.mean_precipitation_mm AS rainfall_24h_mm,
  r.accumulation_3d_mm AS rainfall_72h_mm,
  r.accumulation_7d_mm AS rainfall_7d_mm,
  r.accumulation_30d_mm AS rainfall_30d_mm,
  o.mean_hand_m,
  o.mean_local_relief_m,
  o.mean_river_distance_m,
  o.mean_canal_distance_m,
  COALESCE(o.max_historical_event_count, 0) AS historical_flood_frequency
FROM event_union AS e
LEFT JOIN rainfall_history AS r ON r.observed_date = e.start_date
LEFT JOIN overlap AS o ON o.event_id = e.event_id
ORDER BY e.start_date, e.event_id
"""


def json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def fetch_catalog(label_source: LabelSource) -> list[dict[str, Any]]:
    if engine is None:
        raise RuntimeError("DATABASE_URL is required")
    source_filter = label_source_sql_clause(label_source)
    query = text(CATALOG_SQL.format(source_filter=source_filter))
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(query).mappings()]


def enrich_catalog(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return rows
    max_area = max(float(row["flood_area_km2"] or 0) for row in rows)
    for row in rows:
        row["event_id"] = str(row["event_id"])
        row["start_date"] = str(row["start_date"])
        row["end_date"] = str(row["end_date"])
        row["max_flood_area_km2"] = round(max_area, 3)
        row["label_source"] = (
            "sar"
            if str(row.get("source_key", "")).startswith("maubin:sar:")
            else "gfd"
        )
    return rows


def export_catalog(rows: list[dict[str, Any]], output: Path) -> None:
    fields = [
        "event_id",
        "start_date",
        "end_date",
        "flood_area_km2",
        "max_flood_area_km2",
        "rainfall_24h_mm",
        "rainfall_72h_mm",
        "rainfall_7d_mm",
        "rainfall_30d_mm",
        "mean_hand_m",
        "mean_local_relief_m",
        "mean_river_distance_m",
        "mean_canal_distance_m",
        "historical_flood_frequency",
        "label_source",
        "source_key",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export flood event catalog with terrain and rainfall metadata."
    )
    parser.add_argument(
        "--label-source",
        default=LABEL_SOURCE_GFD,
        help="Label provenance filter: gfd, sar, or all.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/derived/maubin_flood_event_catalog.csv"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("data/derived/maubin_flood_event_catalog.json"),
    )
    args = parser.parse_args()
    label_source = normalize_label_source(args.label_source)
    rows = enrich_catalog(fetch_catalog(label_source))
    export_catalog(rows, args.output)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(
            [{key: json_safe(value) for key, value in row.items()} for row in rows],
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        {
            "events": len(rows),
            "label_source": label_source,
            "csv": str(args.output),
            "json": str(args.json_output),
        }
    )


if __name__ == "__main__":
    main()
