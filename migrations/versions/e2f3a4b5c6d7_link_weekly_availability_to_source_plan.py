"""link weekly availability to source plan

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-08-29 00:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e2f3a4b5c6d7"
down_revision: str | None = "d1e2f3a4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("weekly_availabilities") as batch_op:
        batch_op.add_column(sa.Column("source_weekly_plan_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_weekly_availability_source_plan",
            "weekly_plans",
            ["source_weekly_plan_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(
            "ix_weekly_availabilities_source_weekly_plan_id",
            ["source_weekly_plan_id"],
            unique=False,
        )
        batch_op.create_unique_constraint(
            "uq_weekly_availability_source_plan",
            ["source_weekly_plan_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("weekly_availabilities") as batch_op:
        batch_op.drop_constraint("uq_weekly_availability_source_plan", type_="unique")
        batch_op.drop_index("ix_weekly_availabilities_source_weekly_plan_id")
        batch_op.drop_constraint("fk_weekly_availability_source_plan", type_="foreignkey")
        batch_op.drop_column("source_weekly_plan_id")
