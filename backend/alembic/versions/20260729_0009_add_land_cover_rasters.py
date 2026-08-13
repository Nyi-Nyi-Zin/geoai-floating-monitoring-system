"""Add PostGIS raster storage for clipped land-cover source data.

Revision ID: 20260729_0009
Revises: 20260729_0008
Create Date: 2026-07-29
"""

from alembic import op

revision = "20260729_0009"
down_revision = "20260729_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE land_cover_rasters (
            source_key varchar(255) PRIMARY KEY,
            source_name varchar(255) NOT NULL,
            reference_year integer NOT NULL,
            resolution_m integer NOT NULL,
            license_notice text NOT NULL,
            class_legend jsonb NOT NULL,
            rast raster NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS land_cover_rasters")
