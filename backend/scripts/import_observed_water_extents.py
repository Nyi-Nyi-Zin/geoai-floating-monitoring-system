"""Import OpenGeoAI / Sentinel-derived observed water extent polygons."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.geo_asset import GeoAsset
from app.schemas.observed_water_extent import ObservedWaterExtentCreate
from app.services.observed_water_extent import ObservedWaterExtentService
from scripts.import_flood_events import parse_iso_date
from scripts.import_flood_extents import (
    group_feature_collection,
    load_feature_collection,
    prepare_extent_geometry,
    source_key_group_suffix,
)

DEFAULT_SOURCE_URL = "https://opengeoai.org/"
DEFAULT_SOURCE_NAME = "OpenGeoAI"
DEFAULT_LICENSE_NAME = "See source dataset licence"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import satellite-observed water extent polygons clipped to Maubin. "
            "These are dynamic water-surface snapshots, not OSM river channels "
            "or flood event labels."
        )
    )
    parser.add_argument("file", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-clip", action="store_true")
    parser.add_argument(
        "--group-by-property",
        default="observed_at",
        help="Feature property used to group/dissolve imports (default: observed_at)",
    )
    return parser.parse_args()


def as_confidence_score(value: Any) -> float | None:
    if value is None:
        return None
    number = float(value)
    if number > 1.0 and number <= 100.0:
        number /= 100.0
    if number < 0.0 or number > 1.0:
        raise ValueError(f"confidence_score must be between 0 and 1, got {value}")
    return number


def build_payload(
    *,
    group_key: str,
    features: list[dict[str, Any]],
    geometry,
    boundary,
) -> ObservedWaterExtentCreate:
    props = features[0].get("properties") or {}
    observed_raw = props.get("observed_at") or props.get("date") or group_key
    if isinstance(observed_raw, date):
        observed_at = observed_raw
    else:
        observed_at = parse_iso_date(str(observed_raw), "observed_at")
    source = str(props.get("source") or props.get("imagery_source") or "Sentinel-2")
    method = str(
        props.get("method")
        or props.get("detection_method")
        or "OpenGeoAI water segmentation"
    )
    event_id = props.get("event_id")
    source_key = str(
        props.get("source_key")
        or f"maubin:observed-water:{source.lower().replace(' ', '-')}:{observed_at}:{source_key_group_suffix(group_key)}"
    )
    name = str(
        props.get("name")
        or f"Observed water · {source} · {observed_at.isoformat()}"
    )
    return ObservedWaterExtentCreate(
        source_key=source_key,
        name=name,
        observed_at=observed_at,
        source=source,
        method=method,
        confidence_score=as_confidence_score(
            props.get("confidence_score", props.get("confidence"))
        ),
        event_id=str(event_id) if event_id not in (None, "") else None,
        source_name=str(props.get("source_name") or DEFAULT_SOURCE_NAME),
        source_url=str(props.get("source_url") or DEFAULT_SOURCE_URL),
        license_name=str(props.get("license_name") or DEFAULT_LICENSE_NAME),
        notes=props.get("notes"),
        geometry=mapping(geometry),
        properties={
            "import_group": group_key,
            "feature_count": len(features),
            **{
                key: value
                for key, value in props.items()
                if key
                not in {
                    "source_key",
                    "name",
                    "observed_at",
                    "date",
                    "source",
                    "imagery_source",
                    "method",
                    "detection_method",
                    "confidence_score",
                    "confidence",
                    "event_id",
                    "source_name",
                    "source_url",
                    "license_name",
                    "notes",
                }
            },
        },
    )


def main() -> None:
    args = parse_args()
    if not args.file.is_file():
        raise SystemExit(
            f"GeoJSON file not found: {args.file}\n"
            "Provide a real observed-water export, or test with:\n"
            "  python -m scripts.import_observed_water_extents "
            "data/raw/maubin_observed_water_demo.geojson"
        )
    payload = load_feature_collection(args.file)
    grouped = group_feature_collection(payload, args.group_by_property)
    db = SessionLocal()
    try:
        boundary = None
        if not args.no_clip:
            boundary_asset = db.scalar(
                select(GeoAsset)
                .where(GeoAsset.asset_type == "township_boundary")
                .order_by(GeoAsset.updated_at.desc())
                .limit(1)
            )
            if boundary_asset is not None:
                boundary = to_shape(boundary_asset.geometry)

        imported = 0
        for group_key, group_collection in grouped:
            geometry, _source_feature_count = prepare_extent_geometry(
                group_collection,
                boundary,
            )
            create_payload = build_payload(
                group_key=str(group_key),
                features=group_collection["features"],
                geometry=geometry,
                boundary=boundary,
            )
            if args.dry_run:
                print(json.dumps(create_payload.model_dump(mode="json"), indent=2))
                imported += 1
                continue
            ObservedWaterExtentService(db).upsert(create_payload)
            imported += 1
        if args.dry_run:
            print(f"Dry run complete — {imported} observed water extent(s) validated.")
        else:
            print(f"Imported {imported} observed water extent(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
