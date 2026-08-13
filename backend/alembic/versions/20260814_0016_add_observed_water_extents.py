"""Add observed_water_extents for dynamic satellite water snapshots.

Revision ID: 20260814_0016
Revises: 20260811_0015
"""

from alembic import op
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260814_0016"
down_revision = "20260811_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "observed_water_extents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_key", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("observed_at", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("method", sa.String(length=255), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("event_id", sa.String(length=120), nullable=True),
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
                from_text="ST_GeomFromEWKT",
                name="geometry",
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
        sa.CheckConstraint("area_km2 > 0", name="ck_observed_water_extents_area_positive"),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_observed_water_extents_confidence_range",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key"),
    )
    op.create_index(
        "ix_observed_water_extents_observed_at",
        "observed_water_extents",
        ["observed_at"],
    )
    op.create_index(
        "ix_observed_water_extents_source",
        "observed_water_extents",
        ["source"],
    )
    op.create_index(
        "ix_observed_water_extents_event_id",
        "observed_water_extents",
        ["event_id"],
    )
    op.create_index(
        "ix_observed_water_extents_geometry",
        "observed_water_extents",
        ["geometry"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_observed_water_extents_geometry",
        table_name="observed_water_extents",
    )
    op.drop_index(
        "ix_observed_water_extents_event_id",
        table_name="observed_water_extents",
    )
    op.drop_index(
        "ix_observed_water_extents_source",
        table_name="observed_water_extents",
    )
    op.drop_index(
        "ix_observed_water_extents_observed_at",
        table_name="observed_water_extents",
    )
    op.drop_table("observed_water_extents")
