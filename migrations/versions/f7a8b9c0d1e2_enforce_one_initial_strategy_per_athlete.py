"""enforce one initial strategy per athlete

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-08-27 23:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "e6f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_initial_strategy_athlete",
        "long_range_strategies",
        ["athlete_id"],
        unique=True,
        postgresql_where=sa.text("supersedes_strategy_id IS NULL"),
        sqlite_where=sa.text("supersedes_strategy_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_initial_strategy_athlete", table_name="long_range_strategies")
