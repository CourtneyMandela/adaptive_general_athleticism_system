"""add engineering competency-floor authority

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-09-15 20:30:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: str | None = "d3e4f5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("competency_floor_authorities") as batch_op:
        batch_op.drop_constraint("ck_competency_floor_authority_kind", type_="check")
        batch_op.create_check_constraint(
            "ck_competency_floor_authority_kind",
            "authority_kind IN ('engineering_judgment', 'professional_judgment', "
            "'personal_calibration')",
        )


def downgrade() -> None:
    with op.batch_alter_table("competency_floor_authorities") as batch_op:
        batch_op.drop_constraint("ck_competency_floor_authority_kind", type_="check")
        batch_op.create_check_constraint(
            "ck_competency_floor_authority_kind",
            "authority_kind IN ('professional_judgment', 'personal_calibration')",
        )
