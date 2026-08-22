"""add athlete safety policy assignments

Revision ID: f1b2c3d4e5a6
Revises: e8a1c4f7b2d9
Create Date: 2026-08-22 22:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f1b2c3d4e5a6"
down_revision: str | None = "e8a1c4f7b2d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "athlete_safety_policy_assignments",
        sa.Column("athlete_id", sa.Uuid(), nullable=False),
        sa.Column("safety_policy_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("supersedes_assignment_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assigned_by", sa.String(length=160), nullable=False),
        sa.Column("applicability_rationale", sa.Text(), nullable=False),
        sa.Column("rule_version", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sequence_number >= 1", name="ck_safety_assignment_sequence_positive"),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["safety_policy_id"], ["session_safety_policies.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_assignment_id"],
            ["athlete_safety_policy_assignments.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "athlete_id", "sequence_number", name="uq_athlete_safety_assignment_sequence"
        ),
        sa.UniqueConstraint(
            "supersedes_assignment_id", name="uq_safety_assignment_superseded_once"
        ),
    )
    op.create_index(
        "ix_athlete_safety_policy_assignments_athlete_id",
        "athlete_safety_policy_assignments",
        ["athlete_id"],
        unique=False,
    )
    op.create_index(
        "ix_athlete_safety_policy_assignments_safety_policy_id",
        "athlete_safety_policy_assignments",
        ["safety_policy_id"],
        unique=False,
    )
    op.create_index(
        "ix_athlete_safety_policy_assignments_supersedes_assignment_id",
        "athlete_safety_policy_assignments",
        ["supersedes_assignment_id"],
        unique=False,
    )
    op.create_index(
        "ix_athlete_safety_policy_assignments_assigned_at",
        "athlete_safety_policy_assignments",
        ["assigned_at"],
        unique=False,
    )
    with op.batch_alter_table("session_safety_decisions") as batch_op:
        batch_op.add_column(sa.Column("safety_policy_assignment_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_safety_decision_policy_assignment",
            "athlete_safety_policy_assignments",
            ["safety_policy_assignment_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(
            "ix_session_safety_decisions_safety_policy_assignment_id",
            ["safety_policy_assignment_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("session_safety_decisions") as batch_op:
        batch_op.drop_index("ix_session_safety_decisions_safety_policy_assignment_id")
        batch_op.drop_constraint("fk_safety_decision_policy_assignment", type_="foreignkey")
        batch_op.drop_column("safety_policy_assignment_id")
    op.drop_index(
        "ix_athlete_safety_policy_assignments_assigned_at",
        table_name="athlete_safety_policy_assignments",
    )
    op.drop_index(
        "ix_athlete_safety_policy_assignments_supersedes_assignment_id",
        table_name="athlete_safety_policy_assignments",
    )
    op.drop_index(
        "ix_athlete_safety_policy_assignments_safety_policy_id",
        table_name="athlete_safety_policy_assignments",
    )
    op.drop_index(
        "ix_athlete_safety_policy_assignments_athlete_id",
        table_name="athlete_safety_policy_assignments",
    )
    op.drop_table("athlete_safety_policy_assignments")
