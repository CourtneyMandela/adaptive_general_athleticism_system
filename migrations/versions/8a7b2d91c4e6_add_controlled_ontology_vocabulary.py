"""add controlled ontology vocabulary

Revision ID: 8a7b2d91c4e6
Revises: 3f0613c5f0d3
Create Date: 2026-08-19 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.sqltypes import Text

revision: str = "8a7b2d91c4e6"
down_revision: str | None = "3f0613c5f0d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql")
    op.add_column(
        "exercises",
        sa.Column(
            "laterality",
            sa.String(length=40),
            nullable=False,
            server_default="not_applicable",
        ),
    )
    op.add_column(
        "stimulus_requirements",
        sa.Column(
            "allowed_lateralities",
            json_type,
            nullable=False,
            server_default=sa.text("'[\"not_applicable\"]'"),
        ),
    )
    op.add_column(
        "exercise_resolver_policies",
        sa.Column("laterality_weight", sa.Float(), nullable=False, server_default="1"),
    )
    op.add_column(
        "weekly_scheduling_policies",
        sa.Column(
            "allow_partial_exercise_resolution",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("weekly_scheduling_policies", "allow_partial_exercise_resolution")
    op.drop_column("exercise_resolver_policies", "laterality_weight")
    op.drop_column("stimulus_requirements", "allowed_lateralities")
    op.drop_column("exercises", "laterality")
