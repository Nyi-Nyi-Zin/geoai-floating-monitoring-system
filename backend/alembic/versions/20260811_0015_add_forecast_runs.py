"""Add forecast_runs and forecast_predictions tables.

Revision ID: 20260811_0015
Revises: 20260803_0014
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260811_0015"
down_revision = "20260803_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forecast_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_version", sa.String(120), nullable=False, unique=True),
        sa.Column(
            "model_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("flood_event_ml_models.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status", sa.String(30), nullable=False, server_default="completed"
        ),
        sa.Column(
            "forecast_type",
            sa.String(30),
            nullable=False,
            server_default="scenario_forecast",
        ),
        sa.Column("rainfall_source", sa.String(120), nullable=False),
        sa.Column(
            "rainfall_fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("rainfall_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("forecast_horizon_days", sa.Integer(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("decision_threshold", sa.Float(), nullable=False),
        sa.Column("threshold_mode", sa.String(30), nullable=False),
        sa.Column("cell_count", sa.Integer(), nullable=False),
        sa.Column("flagged_cell_count", sa.Integer(), nullable=False),
        sa.Column("summary_metrics", postgresql.JSONB(), nullable=False),
        sa.Column("limitations", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "forecast_horizon_days >= 1 AND forecast_horizon_days <= 7",
            name="ck_forecast_runs_horizon",
        ),
        sa.CheckConstraint(
            "decision_threshold >= 0 AND decision_threshold <= 1",
            name="ck_forecast_runs_threshold",
        ),
        sa.CheckConstraint(
            "cell_count > 0 AND flagged_cell_count >= 0 "
            "AND flagged_cell_count <= cell_count",
            name="ck_forecast_runs_cell_counts",
        ),
        sa.CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_forecast_runs_status",
        ),
        sa.CheckConstraint(
            "threshold_mode IN ('screening', 'balanced', 'conservative')",
            name="ck_forecast_runs_threshold_mode",
        ),
    )
    op.create_index(
        "ix_forecast_runs_model_id", "forecast_runs", ["model_id"]
    )
    op.create_table(
        "forecast_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("forecast_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "geo_asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("geo_assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("predicted_label", sa.Boolean(), nullable=False),
        sa.Column("risk_band", sa.String(20), nullable=False),
        sa.Column("features", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "run_id",
            "geo_asset_id",
            name="uq_forecast_predictions_run_asset",
        ),
        sa.CheckConstraint(
            "probability >= 0 AND probability <= 1",
            name="ck_forecast_predictions_probability",
        ),
        sa.CheckConstraint(
            "risk_band IN ('LOW', 'MODERATE', 'HIGH', 'VERY_HIGH')",
            name="ck_forecast_predictions_risk_band",
        ),
    )
    op.create_index(
        "ix_forecast_predictions_run_id",
        "forecast_predictions",
        ["run_id"],
    )
    op.create_index(
        "ix_forecast_predictions_geo_asset_id",
        "forecast_predictions",
        ["geo_asset_id"],
    )
    op.create_index(
        "ix_forecast_predictions_risk_band",
        "forecast_predictions",
        ["risk_band"],
    )


def downgrade() -> None:
    op.drop_table("forecast_predictions")
    op.drop_table("forecast_runs")
