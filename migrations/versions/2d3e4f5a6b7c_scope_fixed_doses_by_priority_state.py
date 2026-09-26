"""scope fixed repetition doses by priority state

Revision ID: 2d3e4f5a6b7c
Revises: 1c2d3e4f5a6b
Create Date: 2026-09-24 19:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2d3e4f5a6b7c"
down_revision: str | None = "1c2d3e4f5a6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("fixed_repetition_dose_policies") as batch_op:
        batch_op.add_column(
            sa.Column(
                "priority_state",
                sa.String(length=30),
                nullable=False,
                server_default="develop",
            )
        )
        batch_op.create_check_constraint(
            "ck_fixed_repetition_dose_priority_state",
            "priority_state IN ('develop', 'maintain')",
        )
        batch_op.create_index(
            "ix_fixed_repetition_dose_policies_priority_state",
            ["priority_state"],
        )
        batch_op.alter_column("priority_state", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("fixed_repetition_dose_policies") as batch_op:
        batch_op.drop_index("ix_fixed_repetition_dose_policies_priority_state")
        batch_op.drop_constraint("ck_fixed_repetition_dose_priority_state", type_="check")
        batch_op.drop_column("priority_state")
