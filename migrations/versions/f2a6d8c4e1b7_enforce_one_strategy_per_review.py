"""enforce one strategy revision per review

Revision ID: f2a6d8c4e1b7
Revises: e7b5c3d1a9f2
Create Date: 2026-08-22 01:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f2a6d8c4e1b7"
down_revision: str | None = "e7b5c3d1a9f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("long_range_strategies") as batch_op:
        batch_op.create_unique_constraint(
            "uq_strategy_triggering_block_review", ["triggering_block_review_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("long_range_strategies") as batch_op:
        batch_op.drop_constraint("uq_strategy_triggering_block_review", type_="unique")
