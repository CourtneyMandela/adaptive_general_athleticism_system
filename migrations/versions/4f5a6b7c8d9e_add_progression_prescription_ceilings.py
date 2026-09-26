"""add typed progression prescription ceilings

Revision ID: 4f5a6b7c8d9e
Revises: 3e4f5a6b7c8d
Create Date: 2026-09-25 10:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4f5a6b7c8d9e"
down_revision: str | None = "3e4f5a6b7c8d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("progression_policies") as batch_op:
        batch_op.add_column(
            sa.Column("maximum_prescription_value", sa.Float(), nullable=True),
        )
        batch_op.add_column(
            sa.Column("maximum_prescription_value_unit", sa.String(length=80), nullable=True),
        )
        batch_op.create_check_constraint(
            "ck_progression_policy_ceiling_pair",
            "(maximum_prescription_value IS NULL AND maximum_prescription_value_unit IS NULL) OR "
            "(maximum_prescription_value > 0 AND maximum_prescription_value_unit IS NOT NULL)",
        )


def downgrade() -> None:
    with op.batch_alter_table("progression_policies") as batch_op:
        batch_op.drop_constraint("ck_progression_policy_ceiling_pair", type_="check")
        batch_op.drop_column("maximum_prescription_value_unit")
        batch_op.drop_column("maximum_prescription_value")
