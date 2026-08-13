"""Add versioned flood ML models and terrain-cell predictions.

Revision ID: 20260801_0012
Revises: 20260801_0011
Create Date: 2026-08-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260801_0012"
down_revision = "20260801_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "flood_ml_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_version", sa.String(length=120), nullable=False),
        sa.Column("algorithm", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="trained", nullable=False),
        sa.Column("target_name", sa.String(length=120), nullable=False),
        sa.Column("target_threshold", sa.Float(), nullable=False),
        sa.Column("training_rows", sa.Integer(), nullable=False),
        sa.Column("positive_rows", sa.Integer(), nullable=False),
        sa.Column("negative_rows", sa.Integer(), nullable=False),
        sa.Column("feature_names", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("feature_importance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("methodology", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column("trained_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("training_rows > 0 AND positive_rows >= 0 AND negative_rows >= 0", name="ck_flood_ml_models_training_counts"),
        sa.CheckConstraint("positive_rows + negative_rows = training_rows", name="ck_flood_ml_models_class_counts"),
        sa.CheckConstraint("target_threshold >= 0 AND target_threshold <= 1", name="ck_flood_ml_models_target_threshold"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_version", name="uq_flood_ml_models_model_version"),
    )
    op.create_table(
        "flood_ml_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("geo_asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("risk_band", sa.String(length=20), nullable=False),
        sa.Column("predicted_label", sa.Boolean(), nullable=False),
        sa.Column("flooded_fraction", sa.Float(), nullable=False),
        sa.Column("historical_event_count", sa.Integer(), nullable=False),
        sa.Column("historical_event_density", sa.Float(), nullable=False),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("probability >= 0 AND probability <= 1", name="ck_flood_ml_predictions_probability"),
        sa.CheckConstraint("risk_band IN ('LOW', 'MODERATE', 'HIGH', 'VERY_HIGH')", name="ck_flood_ml_predictions_risk_band"),
        sa.CheckConstraint("flooded_fraction >= 0 AND flooded_fraction <= 1", name="ck_flood_ml_predictions_flooded_fraction"),
        sa.CheckConstraint("historical_event_count >= 0 AND historical_event_density >= 0", name="ck_flood_ml_predictions_historical_labels"),
        sa.ForeignKeyConstraint(["geo_asset_id"], ["geo_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["model_id"], ["flood_ml_models.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_id", "geo_asset_id", name="uq_flood_ml_predictions_model_asset"),
    )
    op.create_index("ix_flood_ml_predictions_model_id", "flood_ml_predictions", ["model_id"])
    op.create_index("ix_flood_ml_predictions_geo_asset_id", "flood_ml_predictions", ["geo_asset_id"])
    op.create_index("ix_flood_ml_predictions_risk_band", "flood_ml_predictions", ["risk_band"])


def downgrade() -> None:
    op.drop_index("ix_flood_ml_predictions_risk_band", table_name="flood_ml_predictions")
    op.drop_index("ix_flood_ml_predictions_geo_asset_id", table_name="flood_ml_predictions")
    op.drop_index("ix_flood_ml_predictions_model_id", table_name="flood_ml_predictions")
    op.drop_table("flood_ml_predictions")
    op.drop_table("flood_ml_models")
