"""Clip, dissolve, and import a GeoJSON flood label into PostGIS."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from geoalchemy2.shape import from_shape, to_shape
from shapely import make_valid, union_all, wkt as shapely_wkt
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, mapping, shape
from shapely.ops import unary_union
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.geo_asset import GeoAsset
from app.schemas.flood_extent import FloodExtentCreate
from app.services.flood_extent import FloodExtentService, polygon_to_multipolygon


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import polygonal historical flood labels from GeoJSON, dissolve "
            "them, and clip the result to the stored Maubin boundary."
        )
    )
    parser.add_argument("file", type=Path)
    parser.add_argument("--source-key", required=True)
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--observed-date", required=True, type=date.fromisoformat)
    parser.add_argument("--sensor", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--license-name", required=True)
    parser.add_argument(
        "--classification",
        choices=("flood", "possible_flood"),
        default="flood",
    )
    parser.add_argument(
        "--confidence",
        choices=("high", "moderate", "low", "unknown"),
        default="unknown",
    )
    parser.add_argument("--field-validated", action="store_true")
    parser.add_argument("--notes")
    parser.add_argument(
        "--group-by-property",
        help=(
            "Import one dissolved extent per distinct GeoJSON property value. "
            "The value is preserved in metadata and appended to source-key."
        ),
    )
    parser.add_argument(
        "--no-clip",
        action="store_true",
        help="Do not clip to the stored township boundary.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_feature_collection(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "FeatureCollection":
        raise ValueError("Input must be a GeoJSON FeatureCollection")
    if not payload.get("features"):
        raise ValueError("Input FeatureCollection has no features")
    return payload


def _polygonal_parts(geometry) -> list[Polygon]:
    geometry = make_valid(geometry)
    if geometry.is_empty:
        return []
    if isinstance(geometry, Polygon):
        return [geometry] if geometry.area > 0 else []
    if isinstance(geometry, MultiPolygon):
        return [polygon for polygon in geometry.geoms if polygon.area > 0]
    if isinstance(geometry, GeometryCollection):
        return [
            polygon
            for part in geometry.geoms
            for polygon in _polygonal_parts(part)
        ]
    return []


def _dissolve_polygons(polygons: list[Polygon], chunk_size: int = 500) -> Polygon | MultiPolygon:
    if not polygons:
        raise ValueError("No polygons to dissolve")
    if len(polygons) == 1:
        return make_valid(polygons[0])
    if len(polygons) <= chunk_size:
        return make_valid(union_all(polygons))
    chunks = [
        union_all(polygons[index : index + chunk_size])
        for index in range(0, len(polygons), chunk_size)
    ]
    return make_valid(union_all(chunks))


POSTGIS_DISSOLVE_THRESHOLD = 500


def _dissolve_polygons_postgis(
    db: Session,
    polygons: list[Polygon],
    clip_geometry: Polygon | MultiPolygon | None = None,
) -> MultiPolygon:
    db.execute(
        text(
            """
            CREATE TEMP TABLE IF NOT EXISTS _import_fragments (
                id serial PRIMARY KEY,
                geom geometry(Geometry, 4326) NOT NULL
            ) ON COMMIT DROP
            """
        )
    )
    db.execute(text("TRUNCATE _import_fragments"))
    if not polygons:
        raise ValueError("No polygons to dissolve")
    batch_size = 250
    for start in range(0, len(polygons), batch_size):
        batch = polygons[start : start + batch_size]
        values_sql = ", ".join(
            f"(ST_GeomFromText(:wkt_{index}, 4326))" for index in range(len(batch))
        )
        params = {
            f"wkt_{index}": polygon.wkt for index, polygon in enumerate(batch)
        }
        db.execute(
            text(f"INSERT INTO _import_fragments (geom) VALUES {values_sql}"),
            params,
        )
    clip_sql = "merged.geom"
    params: dict[str, Any] = {}
    if clip_geometry is not None:
        clip_sql = "ST_Intersection(merged.geom, ST_GeomFromText(:clip_wkt, 4326))"
        params["clip_wkt"] = clip_geometry.wkt
    dissolved_wkt = db.scalar(
        text(
            f"""
            WITH merged AS (
                SELECT ST_UnaryUnion(ST_Collect(geom)) AS geom
                FROM _import_fragments
            )
            SELECT ST_AsText({clip_sql}) FROM merged
            """
        ),
        params,
    )
    if not dissolved_wkt:
        raise ValueError("Flood polygons do not overlap the Maubin township boundary")
    geometry = make_valid(shapely_wkt.loads(str(dissolved_wkt)))
    clipped_polygons = _polygonal_parts(geometry)
    if not clipped_polygons:
        raise ValueError("Flood polygons do not overlap the Maubin township boundary")
    return polygon_to_multipolygon(_dissolve_polygons(clipped_polygons))


def prepare_extent_geometry(
    payload: dict[str, Any],
    clip_geometry=None,
    *,
    db: Session | None = None,
    postgis_threshold: int = POSTGIS_DISSOLVE_THRESHOLD,
) -> tuple[MultiPolygon, int]:
    polygons: list[Polygon] = []
    for feature in payload.get("features", []):
        geometry_payload = feature.get("geometry")
        if not geometry_payload:
            continue
        polygons.extend(_polygonal_parts(shape(geometry_payload)))
    if not polygons:
        raise ValueError("Input contains no valid Polygon or MultiPolygon features")

    if db is not None and len(polygons) >= postgis_threshold:
        return _dissolve_polygons_postgis(db, polygons, clip_geometry), len(polygons)

    dissolved = _dissolve_polygons(polygons)
    if clip_geometry is not None:
        dissolved = make_valid(dissolved.intersection(clip_geometry))
    clipped_polygons = _polygonal_parts(dissolved)
    if not clipped_polygons:
        raise ValueError("Flood polygons do not overlap the Maubin township boundary")
    return polygon_to_multipolygon(_dissolve_polygons(clipped_polygons)), len(polygons)


def group_feature_collection(
    payload: dict[str, Any],
    property_name: str,
) -> list[tuple[Any, dict[str, Any]]]:
    groups: dict[Any, list[dict[str, Any]]] = {}
    for feature in payload.get("features", []):
        properties = feature.get("properties") or {}
        if property_name not in properties:
            raise ValueError(
                f"Input feature is missing group property '{property_name}'"
            )
        value = properties[property_name]
        if not isinstance(value, (str, int, float, bool)) or value == "":
            raise ValueError(
                f"Group property '{property_name}' must be a scalar value"
            )
        groups.setdefault(value, []).append(feature)
    return [
        (value, {"type": "FeatureCollection", "features": features})
        for value, features in sorted(
            groups.items(),
            key=lambda item: (
                0 if isinstance(item[0], (int, float)) else 1,
                float(item[0]) if isinstance(item[0], (int, float)) else 0,
                str(item[0]),
            ),
        )
    ]


def source_key_group_suffix(value: Any) -> str:
    suffix = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value)).strip("-")
    if not suffix:
        raise ValueError("Group value cannot produce an empty source-key suffix")
    return suffix


def import_extent(args: argparse.Namespace) -> dict[str, Any]:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is required")
    payload = load_feature_collection(args.file)
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

        grouped_payloads = (
            group_feature_collection(payload, args.group_by_property)
            if args.group_by_property
            else [(None, payload)]
        )
        results: list[dict[str, Any]] = []
        skipped_groups: list[dict[str, Any]] = []
        for group_value, group_payload in grouped_payloads:
            try:
                geometry, source_feature_count = prepare_extent_geometry(
                    group_payload,
                    boundary,
                )
            except ValueError as exc:
                if not args.group_by_property or "do not overlap" not in str(exc):
                    raise
                skipped_groups.append(
                    {"group_value": group_value, "reason": str(exc)}
                )
                continue
            source_key = args.source_key
            metadata: dict[str, Any] = {
                "source_file": args.file.name,
                "source_feature_count": source_feature_count,
                "processing": "make_valid, dissolve, and township clip",
                "permanent_water_excluded": True,
            }
            if args.group_by_property:
                source_key = (
                    f"{source_key}:{args.group_by_property}="
                    f"{source_key_group_suffix(group_value)}"
                )
                metadata["group_by_property"] = args.group_by_property
                metadata[args.group_by_property] = group_value

            create_payload = FloodExtentCreate(
                source_key=source_key,
                event_name=args.event_name,
                observed_date=args.observed_date,
                sensor=args.sensor,
                classification=args.classification,
                confidence=args.confidence,
                field_validated=args.field_validated,
                source_name=args.source_name,
                source_url=args.source_url,
                license_name=args.license_name,
                notes=args.notes,
                geometry=mapping(geometry),
                properties=metadata,
            )
            if args.dry_run:
                results.append(
                    {
                        "source_key": source_key,
                        "group_value": group_value,
                        "source_features": source_feature_count,
                        "geometry_type": geometry.geom_type,
                        "bounds": list(geometry.bounds),
                    }
                )
                continue
            result = FloodExtentService(db).upsert(create_payload)
            results.append(
                {
                    "id": str(result.id),
                    "source_key": result.properties.source_key,
                    "group_value": group_value,
                    "source_features": source_feature_count,
                    "area_km2": result.properties.area_km2,
                }
            )
        return {
            "records": len(results),
            "groups": results,
            "skipped_groups": skipped_groups,
            "dry_run": args.dry_run,
        }
    finally:
        db.close()


def main() -> None:
    result = import_extent(parse_args())
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
