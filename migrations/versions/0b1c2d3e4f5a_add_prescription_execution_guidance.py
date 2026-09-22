"""add immutable prescription execution guidance snapshots

Revision ID: 0b1c2d3e4f5a
Revises: 0a1b2c3d4e5f
Create Date: 2026-09-22 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0b1c2d3e4f5a"
down_revision: str | None = "0a1b2c3d4e5f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.add_column(
        "session_prescriptions",
        sa.Column("execution_guidance", json_type, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("session_prescriptions", "execution_guidance")
