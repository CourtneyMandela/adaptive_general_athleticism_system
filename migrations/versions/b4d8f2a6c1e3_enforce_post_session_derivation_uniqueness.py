"""enforce post-session derivation uniqueness

Revision ID: b4d8f2a6c1e3
Revises: a3c7e9f1b5d2
Create Date: 2026-08-22 09:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "b4d8f2a6c1e3"
down_revision: str | None = "a3c7e9f1b5d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("session_adherence") as batch_op:
        batch_op.create_unique_constraint(
            "uq_adherence_execution_prescription",
            ["session_execution_id", "prescription_id"],
        )
    with op.batch_alter_table("exposure_entries") as batch_op:
        batch_op.create_unique_constraint(
            "uq_exposure_entry_execution_prescription_definition",
            ["session_execution_id", "prescription_id", "exposure_definition_id"],
        )
    with op.batch_alter_table("progression_decisions") as batch_op:
        batch_op.create_unique_constraint(
            "uq_progression_execution_prescription",
            ["session_execution_id", "prescription_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("progression_decisions") as batch_op:
        batch_op.drop_constraint("uq_progression_execution_prescription", type_="unique")
    with op.batch_alter_table("exposure_entries") as batch_op:
        batch_op.drop_constraint(
            "uq_exposure_entry_execution_prescription_definition", type_="unique"
        )
    with op.batch_alter_table("session_adherence") as batch_op:
        batch_op.drop_constraint("uq_adherence_execution_prescription", type_="unique")
