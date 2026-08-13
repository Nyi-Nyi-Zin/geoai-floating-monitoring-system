"""Add township-scale historical rainfall aggregates.

Revision ID: 20260730_0010
Revises: 20260729_0009
Create Date: 2026-07-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260730_0010"
down_revision = "20260729_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rainfall_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("source_key", sa.String(length=120), nullable=False),
        sa.Column("observed_date", sa.Date(), nullable=False),
        sa.Column("mean_precipitation_mm", sa.Float(), nullable=False),
        sa.Column("max_precipitation_mm", sa.Float(), nullable=False),
        sa.Column("p90_precipitation_mm", sa.Float(), nullable=False),
        sa.Column("accumulation_3d_mm", sa.Float(), nullable=False),
        sa.Column("accumulation_7d_mm", sa.Float(), nullable=False),
        sa.Column("accumulation_30d_mm", sa.Float(), nullable=False),
        sa.Column("grid_cell_count", sa.Integer(), nullable=False),
        sa.Column("source_resolution_m", sa.Integer(), nullable=False),
        sa.Column(
            "quality_status",
            sa.String(length=20),
            server_default="reanalysis",
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
            "mean_precipitation_mm >= 0 "
            "AND max_precipitation_mm >= mean_precipitation_mm",
            name="ck_rainfall_history_precipitation_valid",
        ),
        sa.CheckConstraint(
            "p90_precipitation_mm >= 0",
            name="ck_rainfall_history_p90_nonnegative",
        ),
        sa.CheckConstraint(
            "accumulation_3d_mm >= 0 AND accumulation_7d_mm >= 0 "
            "AND accumulation_30d_mm >= 0",
            name="ck_rainfall_history_accumulations_nonnegative",
        ),
        sa.CheckConstraint(
            "grid_cell_count > 0",
            name="ck_rainfall_history_grid_count_positive",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_key",
            "observed_date",
            name="uq_rainfall_history_source_date",
        ),
    )
    op.create_index(
        "ix_rainfall_history_observed_date",
        "rainfall_history",
        ["observed_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rainfall_history_observed_date",
        table_name="rainfall_history",
    )
    op.drop_table("rainfall_history")
