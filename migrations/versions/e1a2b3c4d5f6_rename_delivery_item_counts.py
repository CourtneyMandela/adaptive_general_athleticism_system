"""rename delivery item counts

Revision ID: e1a2b3c4d5f6
Revises: d7e9f1a3b5c8
Create Date: 2026-09-01 19:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e1a2b3c4d5f6"
down_revision: str | None = "d7e9f1a3b5c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table_name in ("training_responses", "block_reviews"):
        op.alter_column(
            table_name,
            "prescribed_sessions",
            new_column_name="prescribed_item_count",
            existing_type=sa.Integer(),
            existing_nullable=False,
        )
        op.alter_column(
            table_name,
            "completed_sessions",
            new_column_name="completed_item_count",
            existing_type=sa.Integer(),
            existing_nullable=False,
        )


def downgrade() -> None:
    for table_name in ("training_responses", "block_reviews"):
        op.alter_column(
            table_name,
            "prescribed_item_count",
            new_column_name="prescribed_sessions",
            existing_type=sa.Integer(),
            existing_nullable=False,
        )
        op.alter_column(
            table_name,
            "completed_item_count",
            new_column_name="completed_sessions",
            existing_type=sa.Integer(),
            existing_nullable=False,
        )
