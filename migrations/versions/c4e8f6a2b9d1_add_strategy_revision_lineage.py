"""add strategy revision lineage

Revision ID: c4e8f6a2b9d1
Revises: 8a7b2d91c4e6
Create Date: 2026-08-21 02:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4e8f6a2b9d1"
down_revision: str | None = "8a7b2d91c4e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("long_range_strategies") as batch_op:
        batch_op.add_column(sa.Column("supersedes_strategy_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("triggering_block_review_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_strategy_supersedes_strategy",
            "long_range_strategies",
            ["supersedes_strategy_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_strategy_triggering_block_review",
            "block_reviews",
            ["triggering_block_review_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_check_constraint(
            "ck_strategy_revision_lineage_pair",
            "(supersedes_strategy_id IS NULL AND triggering_block_review_id IS NULL) "
            "OR (supersedes_strategy_id IS NOT NULL "
            "AND triggering_block_review_id IS NOT NULL)",
        )
        batch_op.create_index(
            "ix_long_range_strategies_supersedes_strategy_id",
            ["supersedes_strategy_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_long_range_strategies_triggering_block_review_id",
            ["triggering_block_review_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("long_range_strategies") as batch_op:
        batch_op.drop_index("ix_long_range_strategies_triggering_block_review_id")
        batch_op.drop_index("ix_long_range_strategies_supersedes_strategy_id")
        batch_op.drop_constraint("ck_strategy_revision_lineage_pair", type_="check")
        batch_op.drop_constraint("fk_strategy_triggering_block_review", type_="foreignkey")
        batch_op.drop_constraint("fk_strategy_supersedes_strategy", type_="foreignkey")
        batch_op.drop_column("triggering_block_review_id")
        batch_op.drop_column("supersedes_strategy_id")
