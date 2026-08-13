from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from pyproj import Transformer
from shapely import make_valid
from shapely.geometry import GeometryCollection, LineString, MultiLineString
from shapely.geometry import mapping, shape
from shapely.ops import substring, transform, unary_union

SUPPORTED_WATERWAYS = {"river", "stream", "canal", "drain"}
WGS84_TO_UTM_46N = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:32646",
    always_xy=True,
)
UTM_46N_TO_WGS84 = Transformer.from_crs(
    "EPSG:32646",
    "EPSG:4326",
    always_xy=True,
)


def read_feature_collection(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "FeatureCollection":
        raise ValueError(f"{path} must contain a GeoJSON FeatureCollection")
    if not isinstance(payload.get("features"), list):
        raise ValueError(f"{path} has no GeoJSON features array")
    return payload


def get_boundary(boundary_collection: dict[str, Any]) -> Any:
    polygons = []
    for feature in boundary_collection["features"]:
        geometry = make_valid(shape(feature["geometry"]))
        if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
            continue
        polygons.append(geometry)
    if not polygons:
        raise ValueError("Boundary file contains no polygon geometry")
    boundary = unary_union(polygons)
    if boundary.is_empty:
        raise ValueError("Boundary geometry is empty")
    return boundary


def linear_parts(geometry: Any) -> Iterable[LineString]:
    if isinstance(geometry, LineString):
        yield geometry
    elif isinstance(geometry, MultiLineString | GeometryCollection):
        for part in geometry.geoms:
            yield from linear_parts(part)


def segment_line(
    line: LineString,
    *,
    max_length_m: float,
) -> Iterable[tuple[LineString, float]]:
    projected = transform(WGS84_TO_UTM_46N.transform, line)
    start_m = 0.0
    while start_m < projected.length:
        end_m = min(start_m + max_length_m, projected.length)
        segment = substring(projected, start_m, end_m)
        if isinstance(segment, LineString) and segment.length > 0:
            yield (
                transform(UTM_46N_TO_WGS84.transform, segment),
                segment.length,
            )
        start_m = end_m


def prepare_boundary_feature(
    boundary_collection: dict[str, Any],
    boundary: Any,
) -> dict[str, Any]:
    properties = boundary_collection["features"][0].get("properties") or {}
    pcode = str(properties.get("pcode") or "MMR017019")
    return {
        "type": "Feature",
        "geometry": mapping(boundary),
        "properties": {
            "name": str(properties.get("township") or "Maubin Township"),
            "asset_type": "township_boundary",
            "source_key": f"boundary:mimu:{pcode}",
            "description": "Maubin Township project area boundary.",
            "metadata": {
                "source": "MIMU Township Boundary 2020 via UNOSAT",
                "pcode": pcode,
                "township": properties.get("township", "Maubin"),
                "district": properties.get("district", "Maubin"),
                "state": properties.get("state", "Ayeyarwady"),
                "attribution": "Township boundary © MIMU",
            },
        },
    }


def prepare_waterways(
    source_collection: dict[str, Any],
    boundary_collection: dict[str, Any],
    *,
    segment_length_m: float = 500.0,
) -> dict[str, Any]:
    if segment_length_m <= 0:
        raise ValueError("Segment length must be greater than zero")

    boundary = get_boundary(boundary_collection)
    prepared_features = [
        prepare_boundary_feature(boundary_collection, boundary),
    ]
    waterway_count = 0
    dataset_id = f"maubin-osm-waterways-{int(segment_length_m)}m-v1"

    for source_feature in source_collection["features"]:
        source_properties = source_feature.get("properties") or {}
        waterway = source_properties.get("waterway")
        if waterway not in SUPPORTED_WATERWAYS:
            continue

        source_geometry = make_valid(shape(source_feature["geometry"]))
        clipped_geometry = source_geometry.intersection(boundary)
        parts = [part for part in linear_parts(clipped_geometry) if not part.is_empty]
        if not parts:
            continue

        osm_id = str(source_properties.get("@id", "unknown"))
        source_name = (
            source_properties.get("name:en")
            or source_properties.get("name")
            or f"OSM {waterway} {osm_id}"
        )
        source_sequence = 0
        for part_index, part in enumerate(parts, start=1):
            for segment, actual_length_m in segment_line(
                part,
                max_length_m=segment_length_m,
            ):
                source_sequence += 1
                waterway_count += 1
                metadata = {
                    "source": "OpenStreetMap",
                    "source_dataset": "Maubin OSM waterway export",
                    "dataset_id": dataset_id,
                    "osm_id": osm_id,
                    "waterway": waterway,
                    "aoi": "Maubin Township",
                    "aoi_pcode": "MMR017019",
                    "part_index": part_index,
                    "segment_index": source_sequence,
                    "segment_length_m": round(actual_length_m, 2),
                    "configured_segment_length_m": segment_length_m,
                    "boundary_source": "MIMU Township Boundary 2020 via UNOSAT",
                    "attribution": (
                        "© OpenStreetMap contributors; township boundary © MIMU"
                    ),
                }
                for key in (
                    "name",
                    "name:en",
                    "name:my",
                    "boat",
                    "wikidata",
                    "wikipedia",
                ):
                    value = source_properties.get(key)
                    if value is not None:
                        metadata[key.replace(":", "_")] = value

                prepared_features.append(
                    {
                        "type": "Feature",
                        "geometry": mapping(segment),
                        "properties": {
                            "name": f"{source_name} · {source_sequence:03d}",
                            "asset_type": f"{waterway}_segment",
                            "source_key": (
                                f"osm:{osm_id}:maubin:{part_index}:"
                                f"{source_sequence}:{int(segment_length_m)}"
                            ),
                            "description": (
                                f"{waterway.title()} monitoring segment in "
                                "Maubin Township."
                            ),
                            "metadata": metadata,
                        },
                    }
                )

    if waterway_count == 0:
        raise ValueError("No supported waterway geometry intersects the boundary")

    return {
        "type": "FeatureCollection",
        "name": "maubin_township_waterways",
        "features": prepared_features,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clip and normalize OSM waterways for GeoAsset bulk import."
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--segment-length-m",
        type=float,
        default=500.0,
        help="Maximum monitoring segment length in metres (default: 500).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prepared = prepare_waterways(
        read_feature_collection(args.source),
        read_feature_collection(args.boundary),
        segment_length_m=args.segment_length_m,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(prepared, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    waterway_count = len(prepared["features"]) - 1
    print(
        f"Prepared {waterway_count} waterway segments and 1 boundary: "
        f"{args.output}"
    )


if __name__ == "__main__":
    main()
