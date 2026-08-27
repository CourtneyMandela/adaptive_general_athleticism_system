"""add assessment measurement schemas

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-08-27 21:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    schema_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    with op.batch_alter_table("assessment_definition_reviews") as batch_op:
        batch_op.add_column(sa.Column("measurement_schema", schema_type, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("assessment_definition_reviews") as batch_op:
        batch_op.drop_column("measurement_schema")
