"""add planning-authorized prescription revisions

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-08-28 23:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: str | None = "c0d1e2f3a4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("session_prescription_revisions") as batch_op:
        batch_op.alter_column(
            "progression_decision_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )
        batch_op.add_column(sa.Column("planning_decision_record_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_prescription_revision_planning_decision",
            "decision_records",
            ["planning_decision_record_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(
            "ix_session_prescription_revisions_planning_decision_record_id",
            ["planning_decision_record_id"],
            unique=False,
        )
        batch_op.create_check_constraint(
            "ck_prescription_revision_one_authorizer",
            "(progression_decision_id IS NOT NULL AND planning_decision_record_id IS NULL) OR "
            "(progression_decision_id IS NULL AND planning_decision_record_id IS NOT NULL)",
        )


def downgrade() -> None:
    with op.batch_alter_table("session_prescription_revisions") as batch_op:
        batch_op.drop_constraint("ck_prescription_revision_one_authorizer", type_="check")
        batch_op.drop_index("ix_session_prescription_revisions_planning_decision_record_id")
        batch_op.drop_constraint(
            "fk_prescription_revision_planning_decision",
            type_="foreignkey",
        )
        batch_op.drop_column("planning_decision_record_id")
        batch_op.alter_column(
            "progression_decision_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )
