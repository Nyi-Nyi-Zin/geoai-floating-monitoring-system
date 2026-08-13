"""Add auditable geospatial data-layer catalog.

Revision ID: 20260729_0008
Revises: 20260729_0007
Create Date: 2026-07-29
"""

from alembic import op
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260729_0008"
down_revision = "20260729_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_layers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("layer_key", sa.String(length=150), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("data_kind", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("license_name", sa.String(length=255), nullable=False),
        sa.Column("license_url", sa.Text(), nullable=True),
        sa.Column("attribution", sa.Text(), nullable=False),
        sa.Column("usage_constraints", sa.Text(), nullable=True),
        sa.Column(
            "coverage",
            geoalchemy2.types.Geometry(
                geometry_type="GEOMETRY",
                srid=4326,
                spatial_index=False,
            ),
            nullable=True,
        ),
        sa.Column("spatial_resolution_m", sa.Float(), nullable=True),
        sa.Column(
            "temporal_coverage_start",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "temporal_coverage_end",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("update_frequency", sa.String(length=255), nullable=True),
        sa.Column("quality_status", sa.String(length=20), nullable=False),
        sa.Column("quality_notes", sa.Text(), nullable=False),
        sa.Column(
            "provenance",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
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
            "data_kind IN ('raster', 'vector', 'timeseries', 'service')",
            name="ck_data_layers_kind",
        ),
        sa.CheckConstraint(
            "quality_status IN "
            "('verified', 'limited', 'unreviewed', 'deprecated')",
            name="ck_data_layers_quality_status",
        ),
        sa.CheckConstraint(
            "spatial_resolution_m IS NULL OR spatial_resolution_m > 0",
            name="ck_data_layers_resolution_positive",
        ),
        sa.CheckConstraint(
            "temporal_coverage_start IS NULL "
            "OR temporal_coverage_end IS NULL "
            "OR temporal_coverage_start <= temporal_coverage_end",
            name="ck_data_layers_temporal_order",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("layer_key"),
    )
    op.create_index("ix_data_layers_category", "data_layers", ["category"])
    op.create_index(
        "ix_data_layers_quality_status",
        "data_layers",
        ["quality_status"],
    )
    op.create_index("ix_data_layers_is_active", "data_layers", ["is_active"])
    op.create_index(
        "ix_data_layers_coverage_gist",
        "data_layers",
        ["coverage"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_data_layers_coverage_gist",
        table_name="data_layers",
        postgresql_using="gist",
    )
    op.drop_index("ix_data_layers_is_active", table_name="data_layers")
    op.drop_index("ix_data_layers_quality_status", table_name="data_layers")
    op.drop_index("ix_data_layers_category", table_name="data_layers")
    op.drop_table("data_layers")
