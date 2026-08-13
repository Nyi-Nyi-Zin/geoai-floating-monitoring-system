"""Add provenance-aware historical flood extent labels.

Revision ID: 20260801_0011
Revises: 20260730_0010
Create Date: 2026-08-01
"""

from alembic import op
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260801_0011"
down_revision = "20260730_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "flood_extents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_key", sa.String(length=255), nullable=False),
        sa.Column("event_name", sa.String(length=255), nullable=False),
        sa.Column("observed_date", sa.Date(), nullable=False),
        sa.Column("sensor", sa.String(length=100), nullable=False),
        sa.Column("classification", sa.String(length=30), nullable=False),
        sa.Column(
            "confidence",
            sa.String(length=20),
            server_default="unknown",
            nullable=False,
        ),
        sa.Column(
            "field_validated",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("license_name", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                spatial_index=False,
            ),
            nullable=False,
        ),
        sa.Column("area_km2", sa.Float(), nullable=False),
        sa.Column(
            "properties",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
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
            "classification IN ('flood', 'possible_flood')",
            name="ck_flood_extents_classification",
        ),
        sa.CheckConstraint(
            "confidence IN ('high', 'moderate', 'low', 'unknown')",
            name="ck_flood_extents_confidence",
        ),
        sa.CheckConstraint(
            "area_km2 > 0",
            name="ck_flood_extents_area_positive",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key", name="uq_flood_extents_source_key"),
    )
    op.create_index(
        "ix_flood_extents_observed_date",
        "flood_extents",
        ["observed_date"],
    )
    op.create_index(
        "ix_flood_extents_classification",
        "flood_extents",
        ["classification"],
    )
    op.create_index(
        "ix_flood_extents_geometry_gist",
        "flood_extents",
        ["geometry"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_flood_extents_geometry_gist",
        table_name="flood_extents",
        postgresql_using="gist",
    )
    op.drop_index(
        "ix_flood_extents_classification",
        table_name="flood_extents",
    )
    op.drop_index(
        "ix_flood_extents_observed_date",
        table_name="flood_extents",
    )
    op.drop_table("flood_extents")
