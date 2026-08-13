from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import create_engine, text

from app.core.config import settings

DEFAULT_RASTER = Path(
    "data/raw/Copernicus_DSM_COG_10_N16_00_E095_00_DEM.tif"
)
DATASET_ID_PREFIX = "maubin-copdem-glo30"
RASTER_SOURCE_KEY = "copdem:glo30:n16e095:2021"
LICENSE_NOTICE = (
    "produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and "
    "© Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS "
    "by the European Union and ESA; all rights reserved"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Load a Copernicus DEM GeoTIFF into PostGIS and create "
            "township-clipped terrain screening cells."
        )
    )
    parser.add_argument("--raster", type=Path, default=DEFAULT_RASTER)
    parser.add_argument(
        "--cell-size-m",
        type=int,
        default=500,
        choices=(100, 250, 500, 1000),
    )
    return parser.parse_args()


def dataset_id(cell_size_m: int) -> str:
    return f"{DATASET_ID_PREFIX}-{cell_size_m}m-v1"


def validate_geotiff(path: Path) -> bytes:
    data = path.read_bytes()
    if len(data) < 8 or data[:4] not in {b"II*\x00", b"MM\x00*"}:
        raise ValueError(f"{path} is not a valid TIFF file")
    return data


LOAD_RASTER_SQL = text(
    """
    INSERT INTO terrain_rasters (
        source_key,
        source_name,
        resolution_m,
        license_notice,
        rast,
        updated_at
    )
    VALUES (
        :source_key,
        :source_name,
        :resolution_m,
        :license_notice,
        ST_SetBandNoDataValue(
            ST_FromGDALRaster(:raster_bytes, 4326),
            1,
            -3.4028234663852886e38
        ),
        now()
    )
    ON CONFLICT (source_key) DO UPDATE SET
        source_name = EXCLUDED.source_name,
        resolution_m = EXCLUDED.resolution_m,
        license_notice = EXCLUDED.license_notice,
        rast = EXCLUDED.rast,
        updated_at = now()
    """
)


CREATE_GRID_SQL = text(
    """
    CREATE TEMP TABLE prepared_terrain_cells ON COMMIT DROP AS
    WITH boundary AS (
        SELECT ST_Transform(geometry, 32646) AS geom
        FROM geo_assets
        WHERE asset_type = 'township_boundary'
        ORDER BY updated_at DESC
        LIMIT 1
    ),
    grid AS (
        SELECT
            square.i,
            square.j,
            ST_Intersection(square.geom, boundary.geom) AS geom,
            ST_Transform(
                ST_Intersection(square.geom, boundary.geom),
                4326
            ) AS geom_wgs84
        FROM boundary
        CROSS JOIN LATERAL ST_SquareGrid(:cell_size_m, boundary.geom) AS square
        WHERE ST_Intersects(square.geom, boundary.geom)
    ),
    clipped AS (
        SELECT
            grid.i,
            grid.j,
            grid.geom,
            grid.geom_wgs84,
            ST_Clip(
                prepared_raster_tiles.rast,
                1,
                grid.geom_wgs84,
                true
            ) AS clipped_rast
        FROM grid
        JOIN prepared_raster_tiles
          ON ST_Intersects(
              prepared_raster_tiles.footprint,
              grid.geom_wgs84
          )
        WHERE NOT ST_IsEmpty(grid.geom)
    ),
    merged AS (
        SELECT
            clipped.i,
            clipped.j,
            clipped.geom,
            ST_Union(clipped.clipped_rast) AS clipped_rast
        FROM clipped
        GROUP BY clipped.i, clipped.j, clipped.geom
    ),
    summarized AS (
        SELECT
            merged.i,
            merged.j,
            merged.geom,
            (ST_SummaryStats(merged.clipped_rast, 1, true)).*
        FROM merged
    ),
    waterways AS (
        SELECT ST_UnaryUnion(
            ST_Collect(ST_Transform(geometry, 32646))
        ) AS geom
        FROM geo_assets
        WHERE asset_type IN ('river_segment', 'canal_segment')
    )
    SELECT
        summarized.i,
        summarized.j,
        summarized.geom,
        summarized.count AS sample_count,
        summarized.mean AS elevation_mean_m,
        summarized.min AS elevation_min_m,
        summarized.max AS elevation_max_m,
        summarized.stddev AS elevation_stddev_m,
        ST_Distance(
            ST_Centroid(summarized.geom),
            waterways.geom
        ) AS distance_to_waterway_m,
        ST_Area(summarized.geom)
            / power(CAST(:cell_size_m AS double precision), 2)
            AS coverage_fraction
    FROM summarized
    CROSS JOIN waterways
    WHERE summarized.count > 0
    """
)

CREATE_RASTER_TILES_SQL = text(
    """
    CREATE TEMP TABLE prepared_raster_tiles ON COMMIT DROP AS
    SELECT
        tile.rast,
        ST_ConvexHull(tile.rast) AS footprint
    FROM terrain_rasters AS source
    CROSS JOIN LATERAL ST_Tile(
        source.rast,
        256,
        256,
        true
    ) AS tile(rast)
    WHERE source.source_key = :raster_source_key
    """
)

INDEX_RASTER_TILES_SQL = text(
    """
    CREATE INDEX prepared_raster_tiles_footprint_gix
    ON prepared_raster_tiles
    USING gist (footprint)
    """
)


UPSERT_CELLS_SQL = text(
    """
    INSERT INTO geo_assets (
        id,
        name,
        asset_type,
        source_key,
        description,
        geometry,
        properties,
        created_at,
        updated_at
    )
    SELECT
        gen_random_uuid(),
        'Terrain cell ' || i || '/' || j,
        'terrain_cell',
        :dataset_id || ':' || i || ':' || j,
        'Township-clipped terrain screening cell; not a flood prediction.',
        ST_Transform(geom, 4326),
        jsonb_build_object(
            'terrain_dataset_id', :dataset_id,
            'source', 'Copernicus DEM GLO-30',
            'source_resolution_m', 30,
            'cell_size_m', :cell_size_m,
            'grid_i', i,
            'grid_j', j,
            'sample_count', sample_count,
            'elevation_mean_m', round(elevation_mean_m::numeric, 2),
            'elevation_min_m', round(elevation_min_m::numeric, 2),
            'elevation_max_m', round(elevation_max_m::numeric, 2),
            'elevation_stddev_m', round(elevation_stddev_m::numeric, 2),
            'distance_to_waterway_m', round(distance_to_waterway_m::numeric, 1),
            'coverage_fraction', round(coverage_fraction::numeric, 4),
            'screening_only', true
        ),
        now(),
        now()
    FROM prepared_terrain_cells
    ON CONFLICT (source_key) DO UPDATE SET
        name = EXCLUDED.name,
        asset_type = EXCLUDED.asset_type,
        description = EXCLUDED.description,
        geometry = EXCLUDED.geometry,
        properties = EXCLUDED.properties,
        updated_at = now()
    """
)

DELETE_EXISTING_CELLS_SQL = text(
    """
    DELETE FROM geo_assets
    WHERE asset_type = 'terrain_cell'
    """
)


ADD_PERCENTILES_SQL = text(
    """
    WITH ranked AS (
        SELECT
            id,
            percent_rank() OVER (
                ORDER BY (properties->>'elevation_mean_m')::double precision
            ) * 100 AS elevation_percentile
        FROM geo_assets
        WHERE asset_type = 'terrain_cell'
          AND properties->>'terrain_dataset_id' = :dataset_id
    )
    UPDATE geo_assets AS asset
    SET
        properties = jsonb_set(
            asset.properties,
            '{elevation_percentile}',
            to_jsonb(round(ranked.elevation_percentile::numeric, 1))
        ),
        updated_at = now()
    FROM ranked
    WHERE asset.id = ranked.id
    """
)

ADD_DERIVED_METRICS_SQL = text(
    """
    UPDATE geo_assets
    SET
        properties = properties || jsonb_build_object(
            'local_relief_m',
            round(
                (
                    (properties->>'elevation_max_m')::numeric
                    - (properties->>'elevation_min_m')::numeric
                ),
                2
            ),
            'relief_angle_degrees',
            round(
                degrees(
                    atan(
                        (
                            (properties->>'elevation_max_m')::double precision
                            - (properties->>'elevation_min_m')::double precision
                        )
                        / (properties->>'cell_size_m')::double precision
                    )
                )::numeric,
                3
            )
        ),
        updated_at = now()
    WHERE asset_type = 'terrain_cell'
      AND properties->>'terrain_dataset_id' = :dataset_id
    """
)


SUMMARY_SQL = text(
    """
    SELECT
        count(*) AS cell_count,
        min((properties->>'elevation_min_m')::double precision) AS min_elevation_m,
        max((properties->>'elevation_max_m')::double precision) AS max_elevation_m,
        avg((properties->>'elevation_mean_m')::double precision) AS mean_elevation_m
    FROM geo_assets
    WHERE asset_type = 'terrain_cell'
      AND properties->>'terrain_dataset_id' = :dataset_id
    """
)


def prepare_terrain_grid(
    raster_path: Path,
    *,
    cell_size_m: int,
) -> dict[str, float | int]:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required to prepare terrain cells")

    raster_bytes = validate_geotiff(raster_path)
    current_dataset_id = dataset_id(cell_size_m)
    engine = create_engine(settings.database_url)

    with engine.begin() as connection:
        # PostGIS disables GDAL drivers by default. Enable only the GeoTIFF
        # reader for this transaction; no out-of-database raster access is used.
        connection.execute(
            text("SET LOCAL postgis.gdal_enabled_drivers = 'GTiff'")
        )
        connection.execute(
            LOAD_RASTER_SQL,
            {
                "source_key": RASTER_SOURCE_KEY,
                "source_name": "Copernicus DEM GLO-30 2021 N16E095",
                "resolution_m": 30,
                "license_notice": LICENSE_NOTICE,
                "raster_bytes": raster_bytes,
            },
        )
        connection.execute(
            CREATE_RASTER_TILES_SQL,
            {"raster_source_key": RASTER_SOURCE_KEY},
        )
        connection.execute(INDEX_RASTER_TILES_SQL)
        connection.execute(
            CREATE_GRID_SQL,
            {
                "cell_size_m": cell_size_m,
            },
        )
        connection.execute(
            DELETE_EXISTING_CELLS_SQL,
        )
        connection.execute(
            UPSERT_CELLS_SQL,
            {
                "cell_size_m": cell_size_m,
                "dataset_id": current_dataset_id,
            },
        )
        connection.execute(
            ADD_PERCENTILES_SQL,
            {"dataset_id": current_dataset_id},
        )
        connection.execute(
            ADD_DERIVED_METRICS_SQL,
            {"dataset_id": current_dataset_id},
        )
        summary = connection.execute(
            SUMMARY_SQL,
            {"dataset_id": current_dataset_id},
        ).mappings().one()

    return {
        "cell_count": int(summary["cell_count"]),
        "min_elevation_m": float(summary["min_elevation_m"]),
        "max_elevation_m": float(summary["max_elevation_m"]),
        "mean_elevation_m": float(summary["mean_elevation_m"]),
    }


def main() -> None:
    args = parse_args()
    summary = prepare_terrain_grid(
        args.raster,
        cell_size_m=args.cell_size_m,
    )
    print(
        "Prepared "
        f"{summary['cell_count']} terrain cells; "
        f"elevation {summary['min_elevation_m']:.1f}–"
        f"{summary['max_elevation_m']:.1f} m "
        f"(mean {summary['mean_elevation_m']:.1f} m)."
    )


if __name__ == "__main__":
    main()
