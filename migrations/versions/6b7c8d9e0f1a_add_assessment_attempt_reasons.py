"""add controlled non-diagnostic assessment attempt reasons

Revision ID: 6b7c8d9e0f1a
Revises: 5a6b7c8d9e0f
Create Date: 2026-09-25 22:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6b7c8d9e0f1a"
down_revision: str | None = "5a6b7c8d9e0f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("assessment_attempts") as batch_op:
        batch_op.add_column(
            sa.Column(
                "reason",
                sa.String(length=60),
                nullable=False,
                server_default="legacy_unspecified",
            )
        )
    op.execute(
        "UPDATE assessment_attempts SET reason = 'listed_stop_condition' "
        "WHERE status = 'safety_stopped'"
    )
    with op.batch_alter_table("assessment_attempts") as batch_op:
        batch_op.alter_column("reason", server_default=None)
        batch_op.create_check_constraint(
            "ck_assessment_attempt_reason",
            "reason IN ('setup_or_equipment_issue', 'measurement_or_route_issue', "
            "'instructions_unclear', 'external_interruption', "
            "'voluntary_non_safety_stop', 'other_non_safety_reason', "
            "'listed_stop_condition', 'legacy_unspecified')",
        )
        batch_op.create_check_constraint(
            "ck_assessment_attempt_status_reason",
            "(status = 'safety_stopped' AND reason = 'listed_stop_condition') OR "
            "(status = 'incomplete' AND reason <> 'listed_stop_condition')",
        )
        batch_op.create_index("ix_assessment_attempts_reason", ["reason"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("assessment_attempts") as batch_op:
        batch_op.drop_index("ix_assessment_attempts_reason")
        batch_op.drop_constraint("ck_assessment_attempt_status_reason", type_="check")
        batch_op.drop_constraint("ck_assessment_attempt_reason", type_="check")
        batch_op.drop_column("reason")
