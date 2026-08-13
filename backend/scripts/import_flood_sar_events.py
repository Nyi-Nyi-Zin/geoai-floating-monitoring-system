"""Import an Earth Engine export of Sentinel-1 SAR flood event polygons."""

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
from scripts.flood_label_sources import LABEL_SOURCE_SAR, SOURCE_KEY_PREFIX
from scripts.import_flood_events import parse_iso_date
from scripts.import_flood_extents import (
    group_feature_collection,
    load_feature_collection,
    prepare_extent_geometry,
    source_key_group_suffix,
)

SOURCE_URL = (
    "https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD"
)
SOURCE_NAME = "Copernicus Sentinel-1 GRD (Earth Engine)"
LICENSE_NAME = "Copernicus Data Space Ecosystem / ESA"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import Sentinel-1 SAR flood event polygons clipped to Maubin. "
            "These are independent validation labels, not MODIS/GFD training labels."
        )
    )
    parser.add_argument("file", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-clip", action="store_true")
    return parser.parse_args()


def normalize_sar_properties(properties: dict[str, Any]) -> dict[str, Any]:
    """Accept both repo export names and common Earth Engine alias names."""
    normalized = dict(properties)
    alias_map = {
        "polarization": "sar_polarization",
        "vh_threshold_db": "sar_vh_threshold_db",
        "resolution_m": "processing_scale_m",
    }
    for alias, canonical in alias_map.items():
        if normalized.get(canonical) is None and normalized.get(alias) is not None:
            normalized[canonical] = normalized[alias]
    if normalized.get("baseline_window_days") is None:
        normalized["baseline_window_days"] = 21
    if normalized.get("permanent_water_excluded") is None:
        normalized["permanent_water_excluded"] = False
    return normalized


def consistent_sar_event_properties(
    event_id: Any, payload: dict[str, Any]
) -> dict[str, Any]:
    properties = [
        normalize_sar_properties(feature.get("properties") or {})
        for feature in payload["features"]
    ]
    required = ("event_start_date", "event_end_date")
    result: dict[str, Any] = {"event_id": str(event_id)}
    for name in required:
        values = {item.get(name) for item in properties}
        if None in values or len(values) != 1:
            raise ValueError(f"Event {event_id} has missing or inconsistent {name}")
        result[name] = values.pop()
    for name in (
        "reference_gfd_event_id",
        "event_year",
        "source_dataset",
        "label_method",
        "sar_polarization",
        "sar_vh_threshold_db",
        "baseline_window_days",
        "processing_scale_m",
        "permanent_water_excluded",
        "dfo_country",
        "dfo_main_cause",
    ):
        values = {item.get(name) for item in properties if item.get(name) is not None}
        result[name] = next(iter(values)) if len(values) == 1 else None
    if result.get("reference_gfd_event_id") is None:
        event_key = str(event_id)
        if event_key.startswith("sar-"):
            result["reference_gfd_event_id"] = event_key.removeprefix("sar-")
    result["label_source"] = LABEL_SOURCE_SAR
    return result


def import_sar_events(args: argparse.Namespace) -> dict[str, Any]:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is required")
    print(f"Loading {args.file} ...", flush=True)
    collection = load_feature_collection(args.file)
    print(f"Loaded {len(collection.get('features', []))} polygon fragments", flush=True)
    grouped = group_feature_collection(collection, "event_id")
    print(f"Grouped into {len(grouped)} SAR events", flush=True)
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
            metadata = consistent_sar_event_properties(raw_event_id, event_collection)
            start = parse_iso_date(metadata["event_start_date"], "event_start_date")
            end = parse_iso_date(metadata["event_end_date"], "event_end_date")
            try:
                print(
                    f"Dissolving event {event_id} "
                    f"({len(event_collection.get('features', []))} fragments)...",
                    flush=True,
                )
                geometry, source_feature_count = prepare_extent_geometry(
                    event_collection, boundary, db=db
                )
            except ValueError as exc:
                if "do not overlap" not in str(exc):
                    raise
                skipped.append({"event_id": event_id, "reason": str(exc)})
                continue

            reference = metadata.get("reference_gfd_event_id")
            reference_note = (
                f" Reference GFD event {reference}."
                if reference is not None
                else ""
            )
            payload = FloodExtentCreate(
                source_key=f"{SOURCE_KEY_PREFIX[LABEL_SOURCE_SAR]}{event_id}",
                event_name=f"SAR event {event_id} ({start.isoformat()})",
                event_id=event_id,
                observed_date=start,
                observed_start_date=start,
                observed_end_date=end,
                sensor="Sentinel-1",
                classification="flood",
                confidence="moderate",
                field_validated=False,
                source_name=SOURCE_NAME,
                source_url=SOURCE_URL,
                license_name=LICENSE_NAME,
                notes=(
                    "Independent Sentinel-1 VH change-detection extent for validation."
                    f"{reference_note} Not field validated."
                ),
                geometry=mapping(geometry),
                properties={
                    **metadata,
                    "source_file": args.file.name,
                    "source_feature_count": source_feature_count,
                    "processing": (
                        "make_valid, dissolve by event_id, and township clip"
                    ),
                },
            )
            if args.dry_run:
                imported.append(
                    {
                        "source_key": payload.source_key,
                        "event_id": event_id,
                        "reference_gfd_event_id": reference,
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
                        "reference_gfd_event_id": reference,
                        "area_km2": result.properties.area_km2,
                    }
                )
        return {
            "label_source": LABEL_SOURCE_SAR,
            "events": len(imported),
            "records": imported,
            "skipped": skipped,
            "dry_run": args.dry_run,
        }
    finally:
        db.close()


def main() -> None:
    print(json.dumps(import_sar_events(parse_args()), indent=2))


if __name__ == "__main__":
    main()
