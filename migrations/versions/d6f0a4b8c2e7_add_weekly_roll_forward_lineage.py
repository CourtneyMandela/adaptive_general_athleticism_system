"""add weekly roll-forward lineage

Revision ID: d6f0a4b8c2e7
Revises: c5e9a3b7d2f4
Create Date: 2026-08-22 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d6f0a4b8c2e7"
down_revision: str | None = "c5e9a3b7d2f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("session_templates") as batch_op:
        batch_op.add_column(sa.Column("previous_template_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_session_templates_previous_template",
            "session_templates",
            ["previous_template_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_unique_constraint(
            "uq_session_templates_previous_template", ["previous_template_id"]
        )
        batch_op.create_index("ix_session_templates_previous_template_id", ["previous_template_id"])
    with op.batch_alter_table("weekly_plans") as batch_op:
        batch_op.add_column(sa.Column("previous_weekly_plan_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_weekly_plans_previous_weekly_plan",
            "weekly_plans",
            ["previous_weekly_plan_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_unique_constraint(
            "uq_weekly_plans_previous_weekly_plan", ["previous_weekly_plan_id"]
        )
        batch_op.create_index(
            "ix_weekly_plans_previous_weekly_plan_id", ["previous_weekly_plan_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("weekly_plans") as batch_op:
        batch_op.drop_index("ix_weekly_plans_previous_weekly_plan_id")
        batch_op.drop_constraint("uq_weekly_plans_previous_weekly_plan", type_="unique")
        batch_op.drop_constraint("fk_weekly_plans_previous_weekly_plan", type_="foreignkey")
        batch_op.drop_column("previous_weekly_plan_id")
    with op.batch_alter_table("session_templates") as batch_op:
        batch_op.drop_index("ix_session_templates_previous_template_id")
        batch_op.drop_constraint("uq_session_templates_previous_template", type_="unique")
        batch_op.drop_constraint("fk_session_templates_previous_template", type_="foreignkey")
        batch_op.drop_column("previous_template_id")
