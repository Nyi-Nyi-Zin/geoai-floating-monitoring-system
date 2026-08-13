"""Import an Earth Engine export containing individual Maubin GFD events."""

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
from app.schemas.flood_extent import FloodExtentCreate
from app.services.flood_extent import FloodExtentService
from scripts.import_flood_extents import (
    group_feature_collection,
    load_feature_collection,
    prepare_extent_geometry,
    source_key_group_suffix,
)

SOURCE_URL = (
    "https://developers.google.com/earth-engine/datasets/catalog/"
    "GLOBAL_FLOOD_DB_MODIS_EVENTS_V1"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import individual GFD event polygons clipped to Maubin."
    )
    parser.add_argument("file", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-clip", action="store_true")
    return parser.parse_args()


def parse_iso_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO YYYY-MM-DD string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {field}: {value!r}") from exc


def consistent_event_properties(
    event_id: Any, payload: dict[str, Any]
) -> dict[str, Any]:
    properties = [feature.get("properties") or {} for feature in payload["features"]]
    required = ("event_start_date", "event_end_date")
    result: dict[str, Any] = {"event_id": str(event_id)}
    for name in required:
        values = {item.get(name) for item in properties}
        if None in values or len(values) != 1:
            raise ValueError(f"Event {event_id} has missing or inconsistent {name}")
        result[name] = values.pop()
    for name in (
        "event_year",
        "dfo_country",
        "dfo_main_cause",
        "dfo_severity",
        "dfo_dead",
        "dfo_displaced",
        "source_dataset",
        "processing_scale_m",
        "permanent_water_excluded",
    ):
        values = {item.get(name) for item in properties if item.get(name) is not None}
        result[name] = next(iter(values)) if len(values) == 1 else None
    return result


def import_events(args: argparse.Namespace) -> dict[str, Any]:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is required")
    collection = load_feature_collection(args.file)
    grouped = group_feature_collection(collection, "event_id")
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
            if boundary_asset is None:
                raise RuntimeError("Maubin township boundary is not registered")
            boundary = to_shape(boundary_asset.geometry)

        imported: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        for raw_event_id, event_collection in grouped:
            event_id = source_key_group_suffix(raw_event_id)
            metadata = consistent_event_properties(raw_event_id, event_collection)
            start = parse_iso_date(metadata["event_start_date"], "event_start_date")
            end = parse_iso_date(metadata["event_end_date"], "event_end_date")
            try:
                geometry, source_feature_count = prepare_extent_geometry(
                    event_collection, boundary
                )
            except ValueError as exc:
                if "do not overlap" not in str(exc):
                    raise
                skipped.append({"event_id": event_id, "reason": str(exc)})
                continue

            payload = FloodExtentCreate(
                source_key=f"maubin:gfd:event:{event_id}",
                event_name=f"GFD event {event_id} ({start.isoformat()})",
                event_id=event_id,
                observed_date=start,
                observed_start_date=start,
                observed_end_date=end,
                sensor="Terra/Aqua MODIS",
                classification="flood",
                confidence="moderate",
                field_validated=False,
                source_name="Global Flood Database v1",
                source_url=SOURCE_URL,
                license_name="CC BY-NC 4.0",
                notes=(
                    "Satellite-observed maximum event extent; permanent water excluded. "
                    "Not field validated."
                ),
                geometry=mapping(geometry),
                properties={
                    **metadata,
                    "source_file": args.file.name,
                    "source_feature_count": source_feature_count,
                    "processing": "make_valid, dissolve by event_id, and township clip",
                },
            )
            if args.dry_run:
                imported.append(
                    {
                        "source_key": payload.source_key,
                        "event_id": event_id,
                        "event_start_date": start.isoformat(),
                        "event_end_date": end.isoformat(),
                        "source_features": source_feature_count,
                        "bounds": list(geometry.bounds),
                    }
                )
            else:
                result = FloodExtentService(db).upsert(payload)
                imported.append(
                    {
                        "id": str(result.id),
                        "source_key": result.properties.source_key,
                        "event_id": event_id,
                        "area_km2": result.properties.area_km2,
                    }
                )
        return {
            "events": len(imported),
            "records": imported,
            "skipped": skipped,
            "dry_run": args.dry_run,
        }
    finally:
        db.close()


def main() -> None:
    print(json.dumps(import_events(parse_args()), indent=2))


if __name__ == "__main__":
    main()
