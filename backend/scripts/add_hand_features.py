from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text

from app.core.config import settings


HAND_RASTER_PATH = Path("data/raw/maubin_hand_100m.tif")

HAND_SOURCE_KEY = "hand:global:100m:maubin:v1"
HAND_SOURCE_NAME = "Global HAND 100 m — Maubin"
HAND_DATASET_ID = "maubin-global-hand-100m-v1"
HAND_RESOLUTION_M = 100

HAND_LICENSE_NOTICE = (
    "Global HAND dataset accessed through Google Earth Engine. "
    "Review and preserve the original dataset attribution and licence "
    "before public or production use."
)


LOAD_HAND_RASTER_SQL = text(
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
        ST_FromGDALRaster(:raster_bytes, 4326),
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


CREATE_HAND_TILES_SQL = text(
    """
    CREATE TEMP TABLE prepared_hand_tiles
    ON COMMIT DROP
    AS
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
    WHERE source.source_key = :source_key
    """
)


INDEX_HAND_TILES_SQL = text(
    """
    CREATE INDEX prepared_hand_tiles_footprint_gix
    ON prepared_hand_tiles
    USING gist (footprint)
    """
)


ANALYZE_HAND_TILES_SQL = text(
    """
    ANALYZE prepared_hand_tiles
    """
)


HAND_MAX_VALID_M = 5000.0
FLOAT_NODATA_SENTINEL = -3.402823466385289e38


SET_HAND_NODATA_SQL = text(
    """
    UPDATE terrain_rasters
    SET rast = ST_SetBandNoDataValue(rast, 1, :nodata_value)
    WHERE source_key = :source_key
      AND ST_BandNoDataValue(rast, 1) IS NULL
    """
)


CLEAR_INVALID_HAND_SQL = text(
    """
    UPDATE geo_assets
    SET
        properties = properties
            - 'hand_dataset_id'
            - 'hand_source_resolution_m'
            - 'hand_sample_count'
            - 'hand_mean_m'
            - 'hand_min_m'
            - 'hand_max_m'
            - 'hand_stddev_m',
        updated_at = now()
    WHERE asset_type = 'terrain_cell'
      AND properties ? 'hand_mean_m'
      AND (
        (properties->>'hand_mean_m')::double precision < 0
        OR (properties->>'hand_mean_m')::double precision > :hand_max_valid_m
        OR (properties->>'hand_min_m')::double precision < 0
      )
    """
)


UPDATE_HAND_FEATURES_SQL = text(
    """
    WITH clipped AS (
        SELECT
            cell.id,
            ST_Clip(
                hand_tile.rast,
                1,
                cell.geometry,
                true
            ) AS clipped_rast
        FROM geo_assets AS cell
        JOIN prepared_hand_tiles AS hand_tile
          ON ST_Intersects(
              hand_tile.footprint,
              cell.geometry
          )
        WHERE cell.asset_type = 'terrain_cell'
    ),
    merged AS (
        SELECT
            id,
            ST_Union(clipped_rast) AS clipped_rast
        FROM clipped
        WHERE clipped_rast IS NOT NULL
        GROUP BY id
    ),
    summarized AS (
        SELECT
            id,
            (
                ST_SummaryStats(
                    clipped_rast,
                    1,
                    true
                )
            ).*
        FROM merged
        WHERE clipped_rast IS NOT NULL
    )
    UPDATE geo_assets AS asset
    SET
        properties = COALESCE(
            asset.properties,
            '{}'::jsonb
        ) || jsonb_build_object(
            'hand_dataset_id',
            CAST(:dataset_id AS text),

            'hand_source_resolution_m',
            CAST(:resolution_m AS integer),

            'hand_sample_count',
            summarized.count,

            'hand_mean_m',
            round(summarized.mean::numeric, 3),

            'hand_min_m',
            round(summarized.min::numeric, 3),

            'hand_max_m',
            round(summarized.max::numeric, 3),

            'hand_stddev_m',
            round(summarized.stddev::numeric, 3)
        ),
        updated_at = now()
    FROM summarized
    WHERE asset.id = summarized.id
      AND summarized.count > 0
      AND summarized.mean IS NOT NULL
      AND summarized.mean >= 0
      AND summarized.mean <= :hand_max_valid_m
      AND summarized.min >= 0
    """
)




SUMMARY_SQL = text(
    """
    SELECT
        count(*) AS cell_count,

        min(
            (properties->>'hand_min_m')::double precision
        ) AS min_hand_m,

        max(
            (properties->>'hand_max_m')::double precision
        ) AS max_hand_m,

        avg(
            (properties->>'hand_mean_m')::double precision
        ) AS mean_hand_m

    FROM geo_assets
    WHERE asset_type = 'terrain_cell'
      AND properties ? 'hand_mean_m'
      AND (properties->>'hand_mean_m')::double precision >= 0
      AND (properties->>'hand_mean_m')::double precision <= :hand_max_valid_m
    """
)


RASTER_INFO_SQL = text(
    """
    SELECT
        ST_Width(rast) AS width,
        ST_Height(rast) AS height,
        ST_SRID(rast) AS srid,
        ST_NumBands(rast) AS band_count,
        ST_UpperLeftX(rast) AS upper_left_x,
        ST_UpperLeftY(rast) AS upper_left_y,
        ST_ScaleX(rast) AS scale_x,
        ST_ScaleY(rast) AS scale_y
    FROM terrain_rasters
    WHERE source_key = :source_key
    """
)


VALID_TIFF_SIGNATURES = {
    b"II*\x00": "little-endian classic TIFF",
    b"MM\x00*": "big-endian classic TIFF",
    b"II+\x00": "little-endian BigTIFF",
    b"MM\x00+": "big-endian BigTIFF",
}


def validate_geotiff(path: Path) -> bytes:
    resolved_path = path.resolve()

    if not path.exists():
        raise FileNotFoundError(
            f"HAND GeoTIFF not found: {resolved_path}"
        )

    if not path.is_file():
        raise ValueError(
            f"HAND raster path is not a file: {resolved_path}"
        )

    file_size = path.stat().st_size

    if file_size < 16:
        raise ValueError(
            f"HAND raster is too small to be a valid TIFF: "
            f"{resolved_path} ({file_size} bytes)"
        )

    with path.open("rb") as raster_file:
        header = raster_file.read(16)

    signature = header[:4]
    tiff_type = VALID_TIFF_SIGNATURES.get(signature)

    if tiff_type is None:
        raise ValueError(
            f"{resolved_path} is not a valid TIFF or BigTIFF file. "
            f"Detected header: {signature.hex(' ')}"
        )

    if signature in {b"II+\x00", b"MM\x00+"}:
        byte_order = (
            "little"
            if signature.startswith(b"II")
            else "big"
        )

        offset_size = int.from_bytes(
            header[4:6],
            byteorder=byte_order,
        )

        reserved_value = int.from_bytes(
            header[6:8],
            byteorder=byte_order,
        )

        if offset_size != 8 or reserved_value != 0:
            raise ValueError(
                f"{resolved_path} has an invalid BigTIFF header. "
                f"Offset size: {offset_size}; "
                f"reserved value: {reserved_value}"
            )

    print("HAND raster validation passed.")
    print(f"Path: {resolved_path}")
    print(f"Format: {tiff_type}")
    print(f"Header: {header[:8].hex(' ')}")
    print(f"File size: {file_size:,} bytes")

    return path.read_bytes()


def print_raster_info(raster_info: dict[str, object]) -> None:
    print("\nRaster stored successfully in PostGIS.")
    print(
        f"Raster size: "
        f"{raster_info['width']} x "
        f"{raster_info['height']}"
    )
    print(f"Raster SRID: {raster_info['srid']}")
    print(f"Raster bands: {raster_info['band_count']}")
    print(
        f"Pixel scale: "
        f"{raster_info['scale_x']}, "
        f"{raster_info['scale_y']}"
    )
    print(
        f"Upper-left coordinate: "
        f"{raster_info['upper_left_x']}, "
        f"{raster_info['upper_left_y']}"
    )


def print_summary(summary: dict[str, object]) -> None:
    cell_count = int(summary["cell_count"] or 0)

    if cell_count == 0:
        print(
            "\nHAND raster was loaded successfully, "
            "but no terrain cells received HAND values."
        )
        print(
            "Check whether the raster overlaps the terrain cells "
            "and whether both datasets use SRID 4326."
        )
        return

    min_hand_m = summary["min_hand_m"]
    max_hand_m = summary["max_hand_m"]
    mean_hand_m = summary["mean_hand_m"]

    if (
        min_hand_m is None
        or max_hand_m is None
        or mean_hand_m is None
    ):
        print(
            f"\nUpdated {cell_count} terrain cells, "
            "but summary values were null."
        )
        return

    print(
        "\nAdded HAND features to "
        f"{cell_count} terrain cells; "
        f"HAND range {float(min_hand_m):.2f}-"
        f"{float(max_hand_m):.2f} m "
        f"(mean {float(mean_hand_m):.2f} m)."
    )


def main() -> None:
    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is required. "
            "Check your backend .env file."
        )

    raster_bytes = validate_geotiff(HAND_RASTER_PATH)

    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
    )

    try:
        with engine.begin() as connection:
            print("\nEnabling PostGIS GDAL GTiff driver...")

            connection.execute(
                text(
                    """
                    SET LOCAL postgis.gdal_enabled_drivers = 'GTiff'
                    """
                )
            )

            print("Loading HAND raster into terrain_rasters...")

            connection.execute(
                LOAD_HAND_RASTER_SQL,
                {
                    "source_key": HAND_SOURCE_KEY,
                    "source_name": HAND_SOURCE_NAME,
                    "resolution_m": HAND_RESOLUTION_M,
                    "license_notice": HAND_LICENSE_NOTICE,
                    "raster_bytes": raster_bytes,
                },
            )

            raster_info_result = connection.execute(
                RASTER_INFO_SQL,
                {
                    "source_key": HAND_SOURCE_KEY,
                },
            ).mappings().one_or_none()

            if raster_info_result is None:
                raise RuntimeError(
                    "HAND raster was not found in terrain_rasters "
                    "after insertion."
                )

            print_raster_info(dict(raster_info_result))

            connection.execute(
                SET_HAND_NODATA_SQL,
                {
                    "source_key": HAND_SOURCE_KEY,
                    "nodata_value": FLOAT_NODATA_SENTINEL,
                },
            )

            cleared = connection.execute(
                CLEAR_INVALID_HAND_SQL,
                {"hand_max_valid_m": HAND_MAX_VALID_M},
            )
            if cleared.rowcount:
                print(
                    f"Cleared invalid HAND values from {cleared.rowcount} cells."
                )

            print("\nCreating temporary 256 x 256 raster tiles...")

            connection.execute(
                CREATE_HAND_TILES_SQL,
                {
                    "source_key": HAND_SOURCE_KEY,
                },
            )

            print("Creating spatial index for raster tiles...")

            connection.execute(INDEX_HAND_TILES_SQL)
            connection.execute(ANALYZE_HAND_TILES_SQL)

            print("Calculating HAND values for terrain cells...")

            update_result = connection.execute(
                UPDATE_HAND_FEATURES_SQL,
                {
                    "dataset_id": HAND_DATASET_ID,
                    "resolution_m": HAND_RESOLUTION_M,
                    "hand_max_valid_m": HAND_MAX_VALID_M,
                },
            )

            print(
                "Terrain cells updated in this run: "
                f"{update_result.rowcount}"
            )

            summary_result = connection.execute(
                SUMMARY_SQL,
                {"hand_max_valid_m": HAND_MAX_VALID_M},
            ).mappings().one()

            summary = dict(summary_result)

        print_summary(summary)

    except Exception as exc:
        raise RuntimeError(
            "Failed to add HAND features. "
            f"Original error: {exc}"
        ) from exc

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

