"""add account identity and athlete ownership

Revision ID: e8a1c4f7b2d9
Revises: d6f0a4b8c2e7
Create Date: 2026-08-22 20:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e8a1c4f7b2d9"
down_revision: str | None = "d6f0a4b8c2e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("issuer", sa.String(length=300), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("issuer", "subject", name="uq_account_issuer_subject"),
    )
    op.create_table(
        "athlete_ownerships",
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("athlete_id", sa.Uuid(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("grant_method", sa.String(length=120), nullable=False),
        sa.Column("rule_version", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("athlete_id", name="uq_athlete_owner"),
    )
    op.create_index(
        "ix_athlete_ownerships_account_id", "athlete_ownerships", ["account_id"], unique=False
    )
    op.create_index(
        "ix_athlete_ownerships_athlete_id", "athlete_ownerships", ["athlete_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_athlete_ownerships_athlete_id", table_name="athlete_ownerships")
    op.drop_index("ix_athlete_ownerships_account_id", table_name="athlete_ownerships")
    op.drop_table("athlete_ownerships")
    op.drop_table("accounts")
