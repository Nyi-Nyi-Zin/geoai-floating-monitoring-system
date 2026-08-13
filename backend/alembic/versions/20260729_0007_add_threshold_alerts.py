"""Add deterministic threshold alerts and acknowledgement audit fields.

Revision ID: 20260729_0007
Revises: 20260729_0006
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260729_0007"
down_revision = "20260729_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_sensor_stations_thresholds_all_or_none",
        "sensor_stations",
        "num_nonnulls(warning_level_cm, danger_level_cm, "
        "critical_level_cm) IN (0, 3)",
    )
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station_id", sa.String(length=100), nullable=False),
        sa.Column(
            "observation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("water_level_cm", sa.Float(), nullable=False),
        sa.Column("threshold_cm", sa.Float(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="open",
            nullable=False,
        ),
        sa.Column("acknowledged_by", sa.String(length=255), nullable=True),
        sa.Column(
            "acknowledged_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("acknowledgement_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "risk_level IN ('MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_alerts_risk_level",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'acknowledged')",
            name="ck_alerts_status",
        ),
        sa.ForeignKeyConstraint(
            ["station_id"],
            ["sensor_stations.station_id"],
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["hydro_observations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_station_id", "alerts", ["station_id"])
    op.create_index("ix_alerts_risk_level", "alerts", ["risk_level"])
    op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_index(
        "uq_alerts_observation_id",
        "alerts",
        ["observation_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_alerts_observation_id", table_name="alerts")
    op.drop_index("ix_alerts_status", table_name="alerts")
    op.drop_index("ix_alerts_risk_level", table_name="alerts")
    op.drop_index("ix_alerts_station_id", table_name="alerts")
    op.drop_table("alerts")
    op.drop_constraint(
        "ck_sensor_stations_thresholds_all_or_none",
        "sensor_stations",
        type_="check",
    )
