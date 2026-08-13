"""Enable PostGIS and create the generic GeoAsset table.

Revision ID: 20260726_0001
Revises:
Create Date: 2026-07-26
"""

from alembic import op
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260726_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "geo_assets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("asset_type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(
                geometry_type="GEOMETRY",
                srid=4326,
                spatial_index=False,
            ),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_geo_assets_asset_type",
        "geo_assets",
        ["asset_type"],
    )
    op.create_index(
        "ix_geo_assets_geometry_gist",
        "geo_assets",
        ["geometry"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_geo_assets_geometry_gist",
        table_name="geo_assets",
        postgresql_using="gist",
    )
    op.drop_index("ix_geo_assets_asset_type", table_name="geo_assets")
    op.drop_table("geo_assets")
    # PostGIS may be shared by other applications, so the downgrade preserves it.
