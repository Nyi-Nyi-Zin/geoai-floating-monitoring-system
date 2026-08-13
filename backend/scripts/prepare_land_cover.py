"""Clip ESA WorldCover to Maubin and enrich terrain cells with class shares."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform
from sqlalchemy import create_engine, text

from app.core.config import settings

DEFAULT_SOURCE = (
    "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
    "ESA_WorldCover_10m_2021_v200_N15E093_Map.tif"
)
DEFAULT_BOUNDARY = Path(
    "data/reference/maubin_township_boundary_mimu2020.geojson"
)
DEFAULT_OUTPUT = Path(
    "data/processed/maubin_esa_worldcover_10m_2021_v200.tif"
)
RASTER_SOURCE_KEY = "esa:worldcover:10m:2021:v200:maubin"
LAND_COVER_DATASET_ID = "maubin-esa-worldcover-10m-2021-v200"
LICENSE_NOTICE = "ESA WorldCover 2021 v200, licensed under CC BY 4.0"

WORLD_COVER_CLASSES: dict[int, dict[str, str]] = {
    10: {"name": "Tree cover", "color": "#006400"},
    20: {"name": "Shrubland", "color": "#ffbb22"},
    30: {"name": "Grassland", "color": "#ffff4c"},
    40: {"name": "Cropland", "color": "#f096ff"},
    50: {"name": "Built-up", "color": "#fa0000"},
    60: {"name": "Bare / sparse vegetation", "color": "#b4b4b4"},
    70: {"name": "Snow and ice", "color": "#f0f0f0"},
    80: {"name": "Permanent water bodies", "color": "#0064c8"},
    90: {"name": "Herbaceous wetland", "color": "#0096a0"},
    95: {"name": "Mangroves", "color": "#00cf75"},
    100: {"name": "Moss and lichen", "color": "#fae6a0"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read the Cloud-Optimized ESA WorldCover tile, clip it to Maubin, "
            "load the clip into PostGIS, and enrich existing terrain cells."
        )
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="Local GeoTIFF path or HTTPS Cloud-Optimized GeoTIFF URL.",
    )
    parser.add_argument("--boundary", type=Path, default=DEFAULT_BOUNDARY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--clip-only",
        action="store_true",
        help="Create the clipped GeoTIFF without changing the database.",
    )
    return parser.parse_args()


def read_boundary(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") == "FeatureCollection":
        features = payload.get("features", [])
        if len(features) != 1:
            raise ValueError("Boundary FeatureCollection must contain one feature")
        geometry = features[0].get("geometry")
    elif payload.get("type") == "Feature":
        geometry = payload.get("geometry")
    else:
        geometry = payload
    boundary = shape(geometry)
    if boundary.is_empty or not boundary.is_valid:
        raise ValueError("Boundary geometry must be non-empty and valid")
    return mapping(boundary)


def validate_geotiff(path: Path) -> bytes:
    data = path.read_bytes()
    if len(data) < 8 or data[:4] not in {b"II*\x00", b"MM\x00*"}:
        raise ValueError(f"{path} is not a valid TIFF file")
    return data


def clip_worldcover(
    source: str,
    boundary_path: Path,
    output_path: Path,
) -> dict[str, int]:
    try:
        import rasterio
        from rasterio.mask import mask
    except ImportError as exc:  # pragma: no cover - installation guard
        raise RuntimeError(
            "rasterio is required; install backend requirements first"
        ) from exc

    boundary_wgs84 = shape(read_boundary(boundary_path))
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
    ):
        with rasterio.open(source) as source_raster:
            if source_raster.crs is None:
                raise ValueError("WorldCover raster must declare a CRS")
            transformer = Transformer.from_crs(
                "EPSG:4326",
                source_raster.crs,
                always_xy=True,
            )
            boundary_source_crs = transform(
                transformer.transform,
                boundary_wgs84,
            )
            clipped, clipped_transform = mask(
                source_raster,
                [mapping(boundary_source_crs)],
                crop=True,
                nodata=0,
                filled=True,
            )
            profile = source_raster.profile.copy()
            profile.update(
                driver="GTiff",
                width=clipped.shape[2],
                height=clipped.shape[1],
                transform=clipped_transform,
                count=1,
                dtype="uint8",
                nodata=0,
                compress="DEFLATE",
                predictor=1,
                tiled=True,
                blockxsize=256,
                blockysize=256,
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as destination:
        destination.write(clipped.astype("uint8"))
        destination.update_tags(
            dataset_id=LAND_COVER_DATASET_ID,
            source="ESA WorldCover 2021 v200",
            license="CC BY 4.0",
        )

    return {
        "width": int(clipped.shape[2]),
        "height": int(clipped.shape[1]),
        "valid_pixels": int((clipped[0] != 0).sum()),
    }


LOAD_RASTER_SQL = text(
    """
    INSERT INTO land_cover_rasters (
        source_key,
        source_name,
        reference_year,
        resolution_m,
        license_notice,
        class_legend,
        rast,
        updated_at
    )
    VALUES (
        :source_key,
        :source_name,
        2021,
        10,
        :license_notice,
        CAST(:class_legend AS jsonb),
        ST_SetBandNoDataValue(
            ST_FromGDALRaster(:raster_bytes, 4326),
            1,
            0
        ),
        now()
    )
    ON CONFLICT (source_key) DO UPDATE SET
        source_name = EXCLUDED.source_name,
        reference_year = EXCLUDED.reference_year,
        resolution_m = EXCLUDED.resolution_m,
        license_notice = EXCLUDED.license_notice,
        class_legend = EXCLUDED.class_legend,
        rast = EXCLUDED.rast,
        updated_at = now()
    """
)

CREATE_TILES_SQL = text(
    """
    CREATE TEMP TABLE prepared_land_cover_tiles ON COMMIT DROP AS
    SELECT
        tile.rast,
        ST_ConvexHull(tile.rast) AS footprint
    FROM land_cover_rasters AS source
    CROSS JOIN LATERAL ST_Tile(source.rast, 256, 256, true) AS tile(rast)
    WHERE source.source_key = :source_key
    """
)

INDEX_TILES_SQL = text(
    """
    CREATE INDEX prepared_land_cover_tiles_footprint_gix
    ON prepared_land_cover_tiles
    USING gist (footprint)
    """
)

CREATE_COUNTS_SQL = text(
    """
    CREATE TEMP TABLE prepared_land_cover_counts ON COMMIT DROP AS
    SELECT
        cell.id AS cell_id,
        value_count.value::integer AS class_code,
        sum(value_count.count)::bigint AS pixel_count
    FROM geo_assets AS cell
    JOIN prepared_land_cover_tiles AS tile
      ON ST_Intersects(tile.footprint, cell.geometry)
    CROSS JOIN LATERAL ST_ValueCount(
        ST_Clip(tile.rast, 1, cell.geometry, true),
        1,
        true
    ) AS value_count
    WHERE cell.asset_type = 'terrain_cell'
      AND value_count.value <> 0
    GROUP BY cell.id, value_count.value
    """
)

UPDATE_CELLS_SQL = text(
    """
    WITH totals AS (
        SELECT cell_id, sum(pixel_count) AS total_pixels
        FROM prepared_land_cover_counts
        GROUP BY cell_id
    ),
    ranked AS (
        SELECT
            counts.*,
            row_number() OVER (
                PARTITION BY counts.cell_id
                ORDER BY counts.pixel_count DESC, counts.class_code
            ) AS dominance_rank
        FROM prepared_land_cover_counts AS counts
    ),
    summarized AS (
        SELECT
            counts.cell_id,
            totals.total_pixels,
            max(counts.class_code) FILTER (
                WHERE counts.dominance_rank = 1
            ) AS dominant_code,
            jsonb_object_agg(
                counts.class_code::text,
                round(
                    100.0 * counts.pixel_count / totals.total_pixels,
                    2
                )
                ORDER BY counts.class_code
            ) AS class_percentages
        FROM ranked AS counts
        JOIN totals ON totals.cell_id = counts.cell_id
        GROUP BY counts.cell_id, totals.total_pixels
    )
    UPDATE geo_assets AS cell
    SET
        properties = cell.properties || jsonb_build_object(
            'land_cover_dataset_id', CAST(:dataset_id AS text),
            'land_cover_reference_year', 2021,
            'land_cover_source_resolution_m', 10,
            'land_cover_pixel_count', summarized.total_pixels,
            'land_cover_dominant_code', summarized.dominant_code,
            'land_cover_dominant_name',
                CASE summarized.dominant_code
                    WHEN 10 THEN 'Tree cover'
                    WHEN 20 THEN 'Shrubland'
                    WHEN 30 THEN 'Grassland'
                    WHEN 40 THEN 'Cropland'
                    WHEN 50 THEN 'Built-up'
                    WHEN 60 THEN 'Bare / sparse vegetation'
                    WHEN 70 THEN 'Snow and ice'
                    WHEN 80 THEN 'Permanent water bodies'
                    WHEN 90 THEN 'Herbaceous wetland'
                    WHEN 95 THEN 'Mangroves'
                    WHEN 100 THEN 'Moss and lichen'
                    ELSE 'Unknown'
                END,
            'land_cover_percentages', summarized.class_percentages
        ),
        updated_at = now()
    FROM summarized
    WHERE cell.id = summarized.cell_id
    """
)

SUMMARY_SQL = text(
    """
    WITH class_totals AS (
        SELECT
            class_code,
            sum(pixel_count)::bigint AS pixel_count
        FROM prepared_land_cover_counts
        GROUP BY class_code
    ),
    total AS (
        SELECT sum(pixel_count)::numeric AS pixel_count
        FROM class_totals
    )
    SELECT
        class_totals.class_code,
        class_totals.pixel_count,
        round(
            100.0 * class_totals.pixel_count / total.pixel_count,
            2
        ) AS percentage
    FROM class_totals
    CROSS JOIN total
    ORDER BY class_totals.pixel_count DESC
    """
)


def load_and_enrich(raster_path: Path) -> list[dict[str, Any]]:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required to enrich terrain cells")

    raster_bytes = validate_geotiff(raster_path)
    engine = create_engine(settings.database_url)
    class_legend = json.dumps(
        {str(code): details for code, details in WORLD_COVER_CLASSES.items()}
    )

    with engine.begin() as connection:
        connection.execute(
            text("SET LOCAL postgis.gdal_enabled_drivers = 'GTiff'")
        )
        connection.execute(
            LOAD_RASTER_SQL,
            {
                "source_key": RASTER_SOURCE_KEY,
                "source_name": "ESA WorldCover 10 m 2021 v200 — Maubin clip",
                "license_notice": LICENSE_NOTICE,
                "class_legend": class_legend,
                "raster_bytes": raster_bytes,
            },
        )
        connection.execute(CREATE_TILES_SQL, {"source_key": RASTER_SOURCE_KEY})
        connection.execute(INDEX_TILES_SQL)
        connection.execute(CREATE_COUNTS_SQL)
        connection.execute(
            UPDATE_CELLS_SQL,
            {"dataset_id": LAND_COVER_DATASET_ID},
        )
        rows = connection.execute(SUMMARY_SQL).mappings().all()

    return [
        {
            "class_code": int(row["class_code"]),
            "class_name": WORLD_COVER_CLASSES[int(row["class_code"])]["name"],
            "pixel_count": int(row["pixel_count"]),
            "percentage": float(row["percentage"]),
        }
        for row in rows
    ]


def main() -> None:
    args = parse_args()
    clip_summary = clip_worldcover(
        args.source,
        args.boundary,
        args.output,
    )
    print(
        "Clipped ESA WorldCover to "
        f"{clip_summary['width']}×{clip_summary['height']} pixels; "
        f"{clip_summary['valid_pixels']:,} valid 10 m pixels."
    )
    if args.clip_only:
        return
    class_summary = load_and_enrich(args.output)
    print("Enriched terrain cells with land-cover composition:")
    for item in class_summary:
        print(
            f"- {item['class_name']}: {item['percentage']:.2f}% "
            f"({item['pixel_count']:,} pixels)"
        )


if __name__ == "__main__":
    main()
