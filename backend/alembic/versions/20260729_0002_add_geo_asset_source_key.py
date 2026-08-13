"""Add a stable source key for idempotent spatial dataset imports.

Revision ID: 20260729_0002
Revises: 20260726_0001
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa

revision = "20260729_0002"
down_revision = "20260726_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "geo_assets",
        sa.Column("source_key", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "uq_geo_assets_source_key",
        "geo_assets",
        ["source_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_geo_assets_source_key", table_name="geo_assets")
    op.drop_column("geo_assets", "source_key")
