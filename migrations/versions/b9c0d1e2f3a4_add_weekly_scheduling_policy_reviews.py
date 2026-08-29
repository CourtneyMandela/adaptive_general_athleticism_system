"""add weekly scheduling policy reviews

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-08-28 02:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b9c0d1e2f3a4"
down_revision: str | None = "a8b9c0d1e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "weekly_scheduling_policy_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "weekly_scheduling_policy_id",
            sa.Uuid(),
            sa.ForeignKey("weekly_scheduling_policies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("supersedes_review_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", sa.String(length=160), nullable=False),
        sa.Column("applicability_rationale", sa.Text(), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=False),
        sa.Column("review_version", sa.String(length=120), nullable=False),
        sa.CheckConstraint(
            "decision IN ('approved', 'needs_revision', 'rejected')",
            name="ck_weekly_scheduling_policy_review_decision",
        ),
        sa.CheckConstraint(
            "sequence_number >= 1",
            name="ck_weekly_scheduling_policy_review_sequence_positive",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_review_id"],
            ["weekly_scheduling_policy_reviews.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "weekly_scheduling_policy_id",
            "sequence_number",
            name="uq_weekly_scheduling_policy_review_policy_sequence",
        ),
        sa.UniqueConstraint(
            "supersedes_review_id",
            name="uq_weekly_scheduling_policy_review_superseded_once",
        ),
    )
    for column_name in (
        "weekly_scheduling_policy_id",
        "decision",
        "supersedes_review_id",
        "reviewed_at",
    ):
        op.create_index(
            f"ix_weekly_scheduling_policy_reviews_{column_name}",
            "weekly_scheduling_policy_reviews",
            [column_name],
            unique=False,
        )

    op.create_table(
        "weekly_scheduling_policy_review_evidence_claims",
        sa.Column(
            "weekly_scheduling_policy_review_id",
            sa.Uuid(),
            sa.ForeignKey("weekly_scheduling_policy_reviews.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "evidence_claim_id",
            sa.Uuid(),
            sa.ForeignKey("evidence_claims.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("weekly_scheduling_policy_review_id", "evidence_claim_id"),
        sa.UniqueConstraint(
            "weekly_scheduling_policy_review_id",
            "position",
            name="uq_weekly_scheduling_policy_review_evidence_order",
        ),
    )

    with op.batch_alter_table("weekly_plans") as batch_op:
        batch_op.add_column(sa.Column("scheduling_policy_review_id", sa.Uuid(), nullable=True))
        batch_op.create_index(
            "ix_weekly_plans_scheduling_policy_review_id",
            ["scheduling_policy_review_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_weekly_plan_scheduling_policy_review",
            "weekly_scheduling_policy_reviews",
            ["scheduling_policy_review_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("weekly_plans") as batch_op:
        batch_op.drop_constraint("fk_weekly_plan_scheduling_policy_review", type_="foreignkey")
        batch_op.drop_index("ix_weekly_plans_scheduling_policy_review_id")
        batch_op.drop_column("scheduling_policy_review_id")

    op.drop_table("weekly_scheduling_policy_review_evidence_claims")
    for column_name in (
        "reviewed_at",
        "supersedes_review_id",
        "decision",
        "weekly_scheduling_policy_id",
    ):
        op.drop_index(
            f"ix_weekly_scheduling_policy_reviews_{column_name}",
            table_name="weekly_scheduling_policy_reviews",
        )
    op.drop_table("weekly_scheduling_policy_reviews")
