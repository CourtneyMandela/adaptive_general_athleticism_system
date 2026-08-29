"""link equipment availability observations

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-08-28 23:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c0d1e2f3a4b5"
down_revision: str | None = "b9c0d1e2f3a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("equipment_availability") as batch_op:
        batch_op.add_column(sa.Column("source_observation_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_equipment_availability_source_observation",
            "observations",
            ["source_observation_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(
            "ix_equipment_availability_source_observation_id",
            ["source_observation_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("equipment_availability") as batch_op:
        batch_op.drop_index("ix_equipment_availability_source_observation_id")
        batch_op.drop_constraint("fk_equipment_availability_source_observation", type_="foreignkey")
        batch_op.drop_column("source_observation_id")
