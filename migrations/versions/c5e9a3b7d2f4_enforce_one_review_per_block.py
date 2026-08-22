"""enforce one completed review per block

Revision ID: c5e9a3b7d2f4
Revises: b4d8f2a6c1e3
Create Date: 2026-08-22 12:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c5e9a3b7d2f4"
down_revision: str | None = "b4d8f2a6c1e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("block_reviews") as batch_op:
        batch_op.create_unique_constraint("uq_block_review_block_plan", ["block_plan_id"])


def downgrade() -> None:
    with op.batch_alter_table("block_reviews") as batch_op:
        batch_op.drop_constraint("uq_block_review_block_plan", type_="unique")
