"""add assessment reviewer role

Revision ID: b5c7d9e1f3a5
Revises: a4b6c8d0e2f4
Create Date: 2026-08-30 15:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "b5c7d9e1f3a5"
down_revision: str | None = "a4b6c8d0e2f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("account_role_assignments") as batch_op:
        batch_op.drop_constraint("ck_account_role_assignment_role", type_="check")
        batch_op.create_check_constraint(
            "ck_account_role_assignment_role",
            "role IN ('planning_reviewer', 'assessment_reviewer')",
        )


def downgrade() -> None:
    with op.batch_alter_table("account_role_assignments") as batch_op:
        batch_op.drop_constraint("ck_account_role_assignment_role", type_="check")
        batch_op.create_check_constraint(
            "ck_account_role_assignment_role",
            "role IN ('planning_reviewer')",
        )
