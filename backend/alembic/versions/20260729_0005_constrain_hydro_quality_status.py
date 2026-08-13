"""Constrain hydrology observation quality flags.

Revision ID: 20260729_0005
Revises: 20260729_0004
Create Date: 2026-07-29
"""

from alembic import op

revision = "20260729_0005"
down_revision = "20260729_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_hydro_observations_quality_status",
        "hydro_observations",
        "quality_status IN "
        "('unverified', 'provisional', 'verified', 'rejected')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_hydro_observations_quality_status",
        "hydro_observations",
        type_="check",
    )
