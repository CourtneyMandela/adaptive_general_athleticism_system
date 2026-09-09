"""add structured competency-floor age bounds

Revision ID: b0c9d8e7f6a5
Revises: a9b8c7d6e5f4
Create Date: 2026-09-09 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b0c9d8e7f6a5"
down_revision: str | None = "a9b8c7d6e5f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("competency_floors") as batch_op:
        batch_op.add_column(sa.Column("minimum_age_years", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("maximum_age_years", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            "ck_competency_floor_minimum_age",
            "minimum_age_years IS NULL OR (minimum_age_years >= 0 AND minimum_age_years <= 130)",
        )
        batch_op.create_check_constraint(
            "ck_competency_floor_maximum_age",
            "maximum_age_years IS NULL OR (maximum_age_years >= 0 AND maximum_age_years <= 130)",
        )
        batch_op.create_check_constraint(
            "ck_competency_floor_age_order",
            "minimum_age_years IS NULL OR maximum_age_years IS NULL OR "
            "minimum_age_years <= maximum_age_years",
        )


def downgrade() -> None:
    with op.batch_alter_table("competency_floors") as batch_op:
        batch_op.drop_constraint("ck_competency_floor_age_order", type_="check")
        batch_op.drop_constraint("ck_competency_floor_maximum_age", type_="check")
        batch_op.drop_constraint("ck_competency_floor_minimum_age", type_="check")
        batch_op.drop_column("maximum_age_years")
        batch_op.drop_column("minimum_age_years")
