"""add account role assignments

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-08-29 09:15:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3a4b5c6d7e8"
down_revision: str | None = "e2f3a4b5c6d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "account_role_assignments",
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("supersedes_assignment_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assigned_by", sa.String(length=160), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("rule_version", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('planning_reviewer')",
            name="ck_account_role_assignment_role",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'revoked')",
            name="ck_account_role_assignment_status",
        ),
        sa.CheckConstraint(
            "sequence_number >= 1",
            name="ck_account_role_assignment_sequence_positive",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_assignment_id"],
            ["account_role_assignments.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "role",
            "sequence_number",
            name="uq_account_role_assignment_sequence",
        ),
        sa.UniqueConstraint(
            "supersedes_assignment_id",
            name="uq_account_role_assignment_superseded_once",
        ),
    )
    op.create_index(
        "ix_account_role_assignments_account_id",
        "account_role_assignments",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        "ix_account_role_assignments_assigned_at",
        "account_role_assignments",
        ["assigned_at"],
        unique=False,
    )
    op.create_index(
        "ix_account_role_assignments_role",
        "account_role_assignments",
        ["role"],
        unique=False,
    )
    op.create_index(
        "ix_account_role_assignments_status",
        "account_role_assignments",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_account_role_assignments_supersedes_assignment_id",
        "account_role_assignments",
        ["supersedes_assignment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_account_role_assignments_supersedes_assignment_id",
        table_name="account_role_assignments",
    )
    op.drop_index(
        "ix_account_role_assignments_status",
        table_name="account_role_assignments",
    )
    op.drop_index(
        "ix_account_role_assignments_role",
        table_name="account_role_assignments",
    )
    op.drop_index(
        "ix_account_role_assignments_assigned_at",
        table_name="account_role_assignments",
    )
    op.drop_index(
        "ix_account_role_assignments_account_id",
        table_name="account_role_assignments",
    )
    op.drop_table("account_role_assignments")
