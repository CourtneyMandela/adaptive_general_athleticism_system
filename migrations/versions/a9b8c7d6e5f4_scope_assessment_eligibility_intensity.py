"""scope assessment eligibility by maximum intensity

Revision ID: a9b8c7d6e5f4
Revises: e1a2b3c4d5f6
Create Date: 2026-09-08 15:15:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a9b8c7d6e5f4"
down_revision: str | None = "e1a2b3c4d5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("assessment_eligibility_reviews") as batch_op:
        batch_op.add_column(
            sa.Column(
                "maximum_assessment_intensity",
                sa.String(length=40),
                nullable=False,
                server_default="maximal",
            )
        )
        batch_op.create_check_constraint(
            "ck_assessment_eligibility_maximum_intensity",
            "maximum_assessment_intensity IN ('low', 'moderate', 'high', 'maximal')",
        )
        batch_op.alter_column("maximum_assessment_intensity", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("assessment_eligibility_reviews") as batch_op:
        batch_op.drop_constraint("ck_assessment_eligibility_maximum_intensity", type_="check")
        batch_op.drop_column("maximum_assessment_intensity")
