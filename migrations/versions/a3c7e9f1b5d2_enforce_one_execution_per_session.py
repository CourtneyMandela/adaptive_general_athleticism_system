"""enforce one execution per planned session

Revision ID: a3c7e9f1b5d2
Revises: f2a6d8c4e1b7
Create Date: 2026-08-22 08:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a3c7e9f1b5d2"
down_revision: str | None = "f2a6d8c4e1b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("session_executions") as batch_op:
        batch_op.create_unique_constraint("uq_execution_planned_session", ["planned_session_id"])


def downgrade() -> None:
    with op.batch_alter_table("session_executions") as batch_op:
        batch_op.drop_constraint("uq_execution_planned_session", type_="unique")
