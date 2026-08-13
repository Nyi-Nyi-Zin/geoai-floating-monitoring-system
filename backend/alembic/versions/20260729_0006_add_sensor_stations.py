"""Add sensor registry and idempotent IoT reading fields.

Revision ID: 20260729_0006
Revises: 20260729_0005
Create Date: 2026-07-29
"""

from alembic import op
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260729_0006"
down_revision = "20260729_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sensor_stations",
        sa.Column("station_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("river_name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="offline",
            nullable=False,
        ),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
            ),
            nullable=False,
        ),
        sa.Column("warning_level_cm", sa.Float(), nullable=True),
        sa.Column("danger_level_cm", sa.Float(), nullable=True),
        sa.Column("critical_level_cm", sa.Float(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('active', 'offline', 'maintenance')",
            name="ck_sensor_stations_status",
        ),
        sa.CheckConstraint(
            "warning_level_cm IS NULL OR warning_level_cm >= 0",
            name="ck_sensor_stations_warning_nonnegative",
        ),
        sa.CheckConstraint(
            "danger_level_cm IS NULL OR danger_level_cm >= 0",
            name="ck_sensor_stations_danger_nonnegative",
        ),
        sa.CheckConstraint(
            "critical_level_cm IS NULL OR critical_level_cm >= 0",
            name="ck_sensor_stations_critical_nonnegative",
        ),
        sa.CheckConstraint(
            "warning_level_cm IS NULL OR danger_level_cm IS NULL "
            "OR warning_level_cm < danger_level_cm",
            name="ck_sensor_stations_warning_before_danger",
        ),
        sa.CheckConstraint(
            "danger_level_cm IS NULL OR critical_level_cm IS NULL "
            "OR danger_level_cm < critical_level_cm",
            name="ck_sensor_stations_danger_before_critical",
        ),
        sa.PrimaryKeyConstraint("station_id"),
    )
    op.create_index(
        "ix_sensor_stations_status",
        "sensor_stations",
        ["status"],
    )
    op.create_index(
        "ix_sensor_stations_geometry_gist",
        "sensor_stations",
        ["geometry"],
        postgresql_using="gist",
    )
    op.add_column(
        "hydro_observations",
        sa.Column("soil_moisture_percent", sa.Float(), nullable=True),
    )
    op.add_column(
        "hydro_observations",
        sa.Column("battery_percent", sa.Float(), nullable=True),
    )
    op.add_column(
        "hydro_observations",
        sa.Column("ingestion_key", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "uq_hydro_observations_ingestion_key",
        "hydro_observations",
        ["ingestion_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_hydro_observations_ingestion_key",
        table_name="hydro_observations",
    )
    op.drop_column("hydro_observations", "ingestion_key")
    op.drop_column("hydro_observations", "battery_percent")
    op.drop_column("hydro_observations", "soil_moisture_percent")
    op.drop_index(
        "ix_sensor_stations_geometry_gist",
        table_name="sensor_stations",
        postgresql_using="gist",
    )
    op.drop_index("ix_sensor_stations_status", table_name="sensor_stations")
    op.drop_table("sensor_stations")
