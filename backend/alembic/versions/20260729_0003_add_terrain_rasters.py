"""Add PostGIS raster storage for terrain source data.

Revision ID: 20260729_0003
Revises: 20260729_0002
Create Date: 2026-07-29
"""

from alembic import op

revision = "20260729_0003"
down_revision = "20260729_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis_raster")
    op.execute(
        """
        CREATE TABLE terrain_rasters (
            source_key varchar(255) PRIMARY KEY,
            source_name varchar(255) NOT NULL,
            resolution_m integer NOT NULL,
            license_notice text NOT NULL,
            rast raster NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS terrain_rasters")
