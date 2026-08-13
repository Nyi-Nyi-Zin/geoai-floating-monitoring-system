"""Add time-stamped hydrometeorology observations.

Revision ID: 20260729_0004
Revises: 20260729_0003
Create Date: 2026-07-29
"""

from alembic import op
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260729_0004"
down_revision = "20260729_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hydro_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", sa.String(length=100), nullable=False),
        sa.Column("station_name", sa.String(length=255), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rainfall_mm", sa.Float(), nullable=True),
        sa.Column("water_level_m", sa.Float(), nullable=True),
        sa.Column("discharge_m3s", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column(
            "quality_status",
            sa.String(length=20),
            server_default="unverified",
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rainfall_mm IS NOT NULL OR water_level_m IS NOT NULL "
            "OR discharge_m3s IS NOT NULL",
            name="ck_hydro_observations_has_measurement",
        ),
        sa.CheckConstraint(
            "rainfall_mm IS NULL OR rainfall_mm >= 0",
            name="ck_hydro_observations_rainfall_nonnegative",
        ),
        sa.CheckConstraint(
            "discharge_m3s IS NULL OR discharge_m3s >= 0",
            name="ck_hydro_observations_discharge_nonnegative",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hydro_observations_station_id",
        "hydro_observations",
        ["station_id"],
    )
    op.create_index(
        "ix_hydro_observations_observed_at",
        "hydro_observations",
        ["observed_at"],
    )
    op.create_index(
        "ix_hydro_observations_quality_status",
        "hydro_observations",
        ["quality_status"],
    )
    op.create_index(
        "ix_hydro_observations_geometry_gist",
        "hydro_observations",
        ["geometry"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_hydro_observations_geometry_gist",
        table_name="hydro_observations",
        postgresql_using="gist",
    )
    op.drop_index(
        "ix_hydro_observations_quality_status",
        table_name="hydro_observations",
    )
    op.drop_index(
        "ix_hydro_observations_observed_at",
        table_name="hydro_observations",
    )
    op.drop_index(
        "ix_hydro_observations_station_id",
        table_name="hydro_observations",
    )
    op.drop_table("hydro_observations")
