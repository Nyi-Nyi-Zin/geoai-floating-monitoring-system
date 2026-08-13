"""Import area-weighted Maubin daily ERA5 rainfall history."""

from __future__ import annotations

import argparse
import json
import math
import uuid
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from pyproj import Transformer
from shapely.geometry import box, shape
from shapely.ops import transform
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.models.rainfall_history import RainfallHistory
from app.services.rainfall_history import (
    SOURCE_KEY,
    SOURCE_RESOLUTION_M,
)

DEFAULT_BOUNDARY = Path(
    "data/reference/maubin_township_boundary_mimu2020.geojson"
)
ARCHIVE_API_URL = "https://archive-api.open-meteo.com/v1/archive"
GRID_STEP_DEGREES = 0.25
UPSERT_BATCH_SIZE = 1_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch Copernicus ERA5 daily rainfall for model grid cells "
            "intersecting Maubin and store area-weighted township history."
        )
    )
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=date(2015, 1, 1),
    )
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        default=date(2025, 12, 31),
    )
    parser.add_argument("--boundary", type=Path, default=DEFAULT_BOUNDARY)
    parser.add_argument(
        "--api-url",
        default=ARCHIVE_API_URL,
        help="Open-Meteo historical archive endpoint.",
    )
    return parser.parse_args()


def read_boundary(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") == "FeatureCollection":
        features = payload.get("features", [])
        if len(features) != 1:
            raise ValueError("Boundary FeatureCollection must contain one feature")
        geometry = features[0]["geometry"]
    elif payload.get("type") == "Feature":
        geometry = payload["geometry"]
    else:
        geometry = payload
    boundary = shape(geometry)
    if boundary.is_empty or not boundary.is_valid:
        raise ValueError("Boundary geometry must be non-empty and valid")
    return boundary


def grid_samples(boundary) -> list[dict[str, float]]:
    transformer = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:32646",
        always_xy=True,
    )
    boundary_projected = transform(transformer.transform, boundary)
    min_lon, min_lat, max_lon, max_lat = boundary.bounds
    start_lon = math.floor(min_lon / GRID_STEP_DEGREES) * GRID_STEP_DEGREES
    end_lon = math.ceil(max_lon / GRID_STEP_DEGREES) * GRID_STEP_DEGREES
    start_lat = math.floor(min_lat / GRID_STEP_DEGREES) * GRID_STEP_DEGREES
    end_lat = math.ceil(max_lat / GRID_STEP_DEGREES) * GRID_STEP_DEGREES
    half_step = GRID_STEP_DEGREES / 2

    samples: list[dict[str, float]] = []
    longitude = start_lon
    while longitude <= end_lon + 1e-9:
        latitude = start_lat
        while latitude <= end_lat + 1e-9:
            footprint = box(
                longitude - half_step,
                latitude - half_step,
                longitude + half_step,
                latitude + half_step,
            )
            footprint_projected = transform(
                transformer.transform,
                footprint,
            )
            intersection_area = boundary_projected.intersection(
                footprint_projected
            ).area
            if intersection_area > 0:
                samples.append(
                    {
                        "latitude": round(latitude, 4),
                        "longitude": round(longitude, 4),
                        "area_m2": intersection_area,
                    }
                )
            latitude += GRID_STEP_DEGREES
        longitude += GRID_STEP_DEGREES

    total_area = sum(sample["area_m2"] for sample in samples)
    if not samples or total_area <= 0:
        raise ValueError("No ERA5 grid cells intersect the township boundary")
    for sample in samples:
        sample["weight"] = sample.pop("area_m2") / total_area
    return samples


def parse_archive_payload(
    payload: list[dict[str, Any]] | dict[str, Any],
    samples: list[dict[str, float]],
) -> dict[date, list[tuple[float, float]]]:
    locations = payload if isinstance(payload, list) else [payload]
    if len(locations) != len(samples):
        raise ValueError("Historical API returned an unexpected location count")

    values_by_date: dict[date, list[tuple[float, float]]] = defaultdict(list)
    for location, sample in zip(locations, samples, strict=True):
        daily = location.get("daily") or {}
        dates = daily.get("time") or []
        precipitation = daily.get("precipitation_sum") or []
        if len(dates) != len(precipitation):
            raise ValueError("Historical API returned inconsistent daily arrays")
        for raw_date, raw_value in zip(dates, precipitation, strict=True):
            if raw_value is not None:
                values_by_date[date.fromisoformat(raw_date)].append(
                    (max(0.0, float(raw_value)), sample["weight"])
                )
    return values_by_date


def weighted_percentile(
    values: list[tuple[float, float]],
    percentile: float,
) -> float:
    ordered = sorted(values)
    total_weight = sum(weight for _, weight in ordered)
    threshold = total_weight * percentile
    cumulative = 0.0
    for value, weight in ordered:
        cumulative += weight
        if cumulative >= threshold:
            return value
    return ordered[-1][0]


def aggregate_history(
    values_by_date: dict[date, list[tuple[float, float]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for observed_date, values in sorted(values_by_date.items()):
        available_weight = sum(weight for _, weight in values)
        if available_weight <= 0:
            continue
        mean_mm = sum(value * weight for value, weight in values)
        mean_mm /= available_weight
        rows.append(
            {
                "observed_date": observed_date,
                "mean_precipitation_mm": mean_mm,
                "max_precipitation_mm": max(value for value, _ in values),
                "p90_precipitation_mm": weighted_percentile(values, 0.9),
                "grid_cell_count": len(values),
            }
        )

    prefix = [0.0]
    for row in rows:
        prefix.append(prefix[-1] + row["mean_precipitation_mm"])
    for index, row in enumerate(rows):
        for days in (3, 7, 30):
            start = max(0, index + 1 - days)
            row[f"accumulation_{days}d_mm"] = (
                prefix[index + 1] - prefix[start]
            )
    return rows


def fetch_history(
    *,
    start_date: date,
    end_date: date,
    samples: list[dict[str, float]],
    api_url: str,
    client: httpx.Client,
) -> list[dict[str, Any]]:
    if end_date < start_date:
        raise ValueError("end-date must be on or after start-date")
    combined: dict[date, list[tuple[float, float]]] = {}
    for year in range(start_date.year, end_date.year + 1):
        chunk_start = max(start_date, date(year, 1, 1))
        chunk_end = min(end_date, date(year, 12, 31))
        response = client.get(
            api_url,
            params={
                "latitude": ",".join(
                    str(sample["latitude"]) for sample in samples
                ),
                "longitude": ",".join(
                    str(sample["longitude"]) for sample in samples
                ),
                "start_date": chunk_start.isoformat(),
                "end_date": chunk_end.isoformat(),
                "daily": "precipitation_sum",
                "timezone": "Asia/Yangon",
                "models": "era5",
                "cell_selection": "nearest",
            },
        )
        response.raise_for_status()
        combined.update(parse_archive_payload(response.json(), samples))
        print(f"Fetched ERA5 rainfall for {chunk_start} to {chunk_end}.")
    return aggregate_history(combined)


def load_history(rows: list[dict[str, Any]]) -> int:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required")
    engine = create_engine(settings.database_url)
    payloads = [
        {
            "id": uuid.uuid4(),
            "source_key": SOURCE_KEY,
            **row,
            "source_resolution_m": SOURCE_RESOLUTION_M,
            "quality_status": "reanalysis",
        }
        for row in rows
    ]
    if not payloads:
        return 0

    with engine.begin() as connection:
        for start in range(0, len(payloads), UPSERT_BATCH_SIZE):
            statement = insert(RainfallHistory).values(
                payloads[start : start + UPSERT_BATCH_SIZE]
            )
            statement = statement.on_conflict_do_update(
                constraint="uq_rainfall_history_source_date",
                set_={
                    "mean_precipitation_mm": statement.excluded.mean_precipitation_mm,
                    "max_precipitation_mm": statement.excluded.max_precipitation_mm,
                    "p90_precipitation_mm": statement.excluded.p90_precipitation_mm,
                    "accumulation_3d_mm": statement.excluded.accumulation_3d_mm,
                    "accumulation_7d_mm": statement.excluded.accumulation_7d_mm,
                    "accumulation_30d_mm": statement.excluded.accumulation_30d_mm,
                    "grid_cell_count": statement.excluded.grid_cell_count,
                    "source_resolution_m": statement.excluded.source_resolution_m,
                    "quality_status": statement.excluded.quality_status,
                    "updated_at": statement.excluded.updated_at,
                },
            )
            connection.execute(statement)
    return len(payloads)


def main() -> None:
    args = parse_args()
    boundary = read_boundary(args.boundary)
    samples = grid_samples(boundary)
    print(f"Using {len(samples)} area-weighted ERA5 grid cells.")
    with httpx.Client(timeout=60.0) as client:
        rows = fetch_history(
            start_date=args.start_date,
            end_date=args.end_date,
            samples=samples,
            api_url=args.api_url,
            client=client,
        )
    imported = load_history(rows)
    print(
        f"Imported {imported:,} daily rainfall rows "
        f"from {args.start_date} through {args.end_date}."
    )


if __name__ == "__main__":
    main()
