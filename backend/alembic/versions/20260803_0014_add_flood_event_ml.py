"""Add persisted event-model metadata and historical hindcast predictions.

Revision ID: 20260803_0014
Revises: 20260801_0013
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260803_0014"
down_revision = "20260801_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "flood_event_ml_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("model_version", sa.String(120), nullable=False, unique=True),
        sa.Column("algorithm", sa.String(120), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="experimental"),
        sa.Column("target_name", sa.String(120), nullable=False),
        sa.Column("target_threshold", sa.Float(), nullable=False),
        sa.Column("decision_threshold", sa.Float(), nullable=False),
        sa.Column("dataset_rows", sa.Integer(), nullable=False),
        sa.Column("train_rows", sa.Integer(), nullable=False),
        sa.Column("positive_rows", sa.Integer(), nullable=False),
        sa.Column("negative_rows", sa.Integer(), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("feature_names", postgresql.JSONB(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("feature_importance", postgresql.JSONB(), nullable=False),
        sa.Column("split_events", postgresql.JSONB(), nullable=False),
        sa.Column("methodology", postgresql.JSONB(), nullable=False),
        sa.Column("artifact_path", sa.Text()),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "dataset_rows > 0 AND train_rows > 0 AND event_count >= 4",
            name="ck_flood_event_ml_models_counts",
        ),
        sa.CheckConstraint(
            "positive_rows >= 0 AND negative_rows >= 0 "
            "AND positive_rows + negative_rows = dataset_rows",
            name="ck_flood_event_ml_models_class_counts",
        ),
        sa.CheckConstraint(
            "target_threshold >= 0 AND target_threshold <= 1 "
            "AND decision_threshold >= 0 AND decision_threshold <= 1",
            name="ck_flood_event_ml_models_thresholds",
        ),
    )
    op.create_table(
        "flood_event_ml_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "model_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("flood_event_ml_models.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_id", sa.String(120), nullable=False),
        sa.Column("event_start_date", sa.Date(), nullable=False),
        sa.Column("split", sa.String(20), nullable=False),
        sa.Column(
            "geo_asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("geo_assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("predicted_label", sa.Boolean(), nullable=False),
        sa.Column("flooded_fraction", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "model_id",
            "event_id",
            "geo_asset_id",
            name="uq_flood_event_ml_predictions_model_event_asset",
        ),
        sa.CheckConstraint(
            "probability >= 0 AND probability <= 1 "
            "AND flooded_fraction >= 0 AND flooded_fraction <= 1",
            name="ck_flood_event_ml_predictions_probabilities",
        ),
        sa.CheckConstraint(
            "split IN ('validation', 'test')",
            name="ck_flood_event_ml_predictions_split",
        ),
    )
    op.create_index(
        "ix_flood_event_ml_predictions_model_id",
        "flood_event_ml_predictions",
        ["model_id"],
    )
    op.create_index(
        "ix_flood_event_ml_predictions_event_id",
        "flood_event_ml_predictions",
        ["event_id"],
    )
    op.create_index(
        "ix_flood_event_ml_predictions_geo_asset_id",
        "flood_event_ml_predictions",
        ["geo_asset_id"],
    )
    op.create_index(
        "ix_flood_event_ml_predictions_split",
        "flood_event_ml_predictions",
        ["split"],
    )


def downgrade() -> None:
    op.drop_table("flood_event_ml_predictions")
    op.drop_table("flood_event_ml_models")
