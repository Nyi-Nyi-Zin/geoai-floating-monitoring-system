"""Add individual flood event identity and date range.

Revision ID: 20260801_0013
Revises: 20260801_0012
"""

from alembic import op
import sqlalchemy as sa

revision = "20260801_0013"
down_revision = "20260801_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("flood_extents", sa.Column("event_id", sa.String(120)))
    op.add_column("flood_extents", sa.Column("observed_start_date", sa.Date()))
    op.add_column("flood_extents", sa.Column("observed_end_date", sa.Date()))
    op.create_index("ix_flood_extents_event_id", "flood_extents", ["event_id"])
    op.create_index(
        "ix_flood_extents_observed_start_date",
        "flood_extents",
        ["observed_start_date"],
    )
    op.create_index(
        "ix_flood_extents_observed_end_date",
        "flood_extents",
        ["observed_end_date"],
    )
    op.create_check_constraint(
        "ck_flood_extents_event_dates",
        "flood_extents",
        "observed_end_date IS NULL OR observed_start_date IS NULL "
        "OR observed_end_date >= observed_start_date",
    )
    op.execute(
        """
        UPDATE flood_extents
        SET observed_start_date = DATE '2000-02-17',
            observed_end_date = DATE '2018-12-10'
        WHERE source_key LIKE 'maubin:gfd:history:2000-2018:%'
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_flood_extents_event_dates", "flood_extents", type_="check"
    )
    op.drop_index("ix_flood_extents_observed_end_date", table_name="flood_extents")
    op.drop_index("ix_flood_extents_observed_start_date", table_name="flood_extents")
    op.drop_index("ix_flood_extents_event_id", table_name="flood_extents")
    op.drop_column("flood_extents", "observed_end_date")
    op.drop_column("flood_extents", "observed_start_date")
    op.drop_column("flood_extents", "event_id")
