from __future__ import annotations

from sqlalchemy import create_engine, text

from app.core.config import settings


UPDATE_WATERWAY_FEATURES_SQL = text(
    """
    WITH terrain_cells AS (
        SELECT
            id,
            ST_Centroid(geometry) AS centroid
        FROM geo_assets
        WHERE asset_type = 'terrain_cell'
    ),
    nearest_distances AS (
        SELECT
            cell.id,

            (
                SELECT ST_Distance(
                    cell.centroid::geography,
                    river.geometry::geography
                )
                FROM geo_assets AS river
                WHERE river.asset_type = 'river_segment'
                ORDER BY cell.centroid <-> river.geometry
                LIMIT 1
            ) AS distance_to_river_m,

            (
                SELECT ST_Distance(
                    cell.centroid::geography,
                    canal.geometry::geography
                )
                FROM geo_assets AS canal
                WHERE canal.asset_type = 'canal_segment'
                ORDER BY cell.centroid <-> canal.geometry
                LIMIT 1
            ) AS distance_to_canal_m

        FROM terrain_cells AS cell
    )
    UPDATE geo_assets AS asset
    SET
        properties = COALESCE(asset.properties, '{}'::jsonb)
            || jsonb_build_object(
                'distance_to_river_m',
                round(
                    nearest.distance_to_river_m::numeric,
                    2
                ),

                'distance_to_canal_m',
                round(
                    nearest.distance_to_canal_m::numeric,
                    2
                ),

                'distance_to_waterway_m',
                round(
                    LEAST(
                        nearest.distance_to_river_m,
                        nearest.distance_to_canal_m
                    )::numeric,
                    2
                )
            ),
        updated_at = now()
    FROM nearest_distances AS nearest
    WHERE asset.id = nearest.id
    """
)


SUMMARY_SQL = text(
    """
    SELECT
        count(*) AS cell_count,

        min(
            (properties->>'distance_to_river_m')::double precision
        ) AS min_river_distance_m,

        max(
            (properties->>'distance_to_river_m')::double precision
        ) AS max_river_distance_m,

        avg(
            (properties->>'distance_to_river_m')::double precision
        ) AS mean_river_distance_m,

        min(
            (properties->>'distance_to_canal_m')::double precision
        ) AS min_canal_distance_m,

        max(
            (properties->>'distance_to_canal_m')::double precision
        ) AS max_canal_distance_m,

        avg(
            (properties->>'distance_to_canal_m')::double precision
        ) AS mean_canal_distance_m,

        min(
            (properties->>'distance_to_waterway_m')::double precision
        ) AS min_waterway_distance_m,

        max(
            (properties->>'distance_to_waterway_m')::double precision
        ) AS max_waterway_distance_m,

        avg(
            (properties->>'distance_to_waterway_m')::double precision
        ) AS mean_waterway_distance_m

    FROM geo_assets
    WHERE asset_type = 'terrain_cell'
      AND properties ? 'distance_to_waterway_m'
    """
)


SOURCE_COUNTS_SQL = text(
    """
    SELECT
        count(*) FILTER (
            WHERE asset_type = 'terrain_cell'
        ) AS terrain_cell_count,

        count(*) FILTER (
            WHERE asset_type = 'river_segment'
        ) AS river_segment_count,

        count(*) FILTER (
            WHERE asset_type = 'canal_segment'
        ) AS canal_segment_count

    FROM geo_assets
    WHERE asset_type IN (
        'terrain_cell',
        'river_segment',
        'canal_segment'
    )
    """
)


def require_positive_count(
    source_name: str,
    value: object,
) -> int:
    count = int(value or 0)

    if count == 0:
        raise RuntimeError(
            f"No {source_name} records were found in geo_assets."
        )

    return count


def main() -> None:
    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is required. "
            "Check the backend .env file."
        )

    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
    )

    try:
        with engine.begin() as connection:
            source_counts = connection.execute(
                SOURCE_COUNTS_SQL
            ).mappings().one()

            terrain_cell_count = require_positive_count(
                "terrain_cell",
                source_counts["terrain_cell_count"],
            )

            river_segment_count = require_positive_count(
                "river_segment",
                source_counts["river_segment_count"],
            )

            canal_segment_count = require_positive_count(
                "canal_segment",
                source_counts["canal_segment_count"],
            )

            print(
                f"Terrain cells: {terrain_cell_count}"
            )
            print(
                f"River segments: {river_segment_count}"
            )
            print(
                f"Canal segments: {canal_segment_count}"
            )

            print(
                "\nCalculating nearest river and canal distances..."
            )

            update_result = connection.execute(
                UPDATE_WATERWAY_FEATURES_SQL
            )

            print(
                "Terrain cells updated in this run: "
                f"{update_result.rowcount}"
            )

            summary = connection.execute(
                SUMMARY_SQL
            ).mappings().one()

        cell_count = int(summary["cell_count"] or 0)

        if cell_count == 0:
            raise RuntimeError(
                "No terrain cells received waterway-distance features."
            )

        print(
            "\nAdded waterway-distance features to "
            f"{cell_count} terrain cells."
        )

        print(
            "River distance: "
            f"{float(summary['min_river_distance_m']):.2f}-"
            f"{float(summary['max_river_distance_m']):.2f} m "
            f"(mean "
            f"{float(summary['mean_river_distance_m']):.2f} m)"
        )

        print(
            "Canal distance: "
            f"{float(summary['min_canal_distance_m']):.2f}-"
            f"{float(summary['max_canal_distance_m']):.2f} m "
            f"(mean "
            f"{float(summary['mean_canal_distance_m']):.2f} m)"
        )

        print(
            "Nearest waterway distance: "
            f"{float(summary['min_waterway_distance_m']):.2f}-"
            f"{float(summary['max_waterway_distance_m']):.2f} m "
            f"(mean "
            f"{float(summary['mean_waterway_distance_m']):.2f} m)"
        )

    except Exception as exc:
        raise RuntimeError(
            "Failed to add waterway-distance features. "
            f"Original error: {exc}"
        ) from exc

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()