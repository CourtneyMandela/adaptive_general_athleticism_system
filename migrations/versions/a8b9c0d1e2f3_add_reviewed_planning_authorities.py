"""add reviewed planning authorities

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-08-27 23:55:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a8b9c0d1e2f3"
down_revision: str | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _review_columns(authority_name: str, authority_table: str) -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            f"{authority_name}_id",
            sa.Uuid(),
            sa.ForeignKey(f"{authority_table}.id", ondelete="RESTRICT"),
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
    ]


def _create_review_tables(*, authority_name: str, authority_table: str, review_table: str) -> None:
    sequence_label = "floor" if authority_name == "competency_floor" else "policy"
    op.create_table(
        review_table,
        *_review_columns(authority_name, authority_table),
        sa.CheckConstraint(
            "decision IN ('approved', 'needs_revision', 'rejected')",
            name=f"ck_{authority_name}_review_decision",
        ),
        sa.CheckConstraint(
            "sequence_number >= 1",
            name=f"ck_{authority_name}_review_sequence_positive",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_review_id"], [f"{review_table}.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            f"{authority_name}_id",
            "sequence_number",
            name=f"uq_{authority_name}_review_{sequence_label}_sequence",
        ),
        sa.UniqueConstraint(
            "supersedes_review_id", name=f"uq_{authority_name}_review_superseded_once"
        ),
    )
    for column_name in (
        f"{authority_name}_id",
        "decision",
        "supersedes_review_id",
        "reviewed_at",
    ):
        op.create_index(
            f"ix_{review_table}_{column_name}", review_table, [column_name], unique=False
        )

    link_table = f"{authority_name}_review_evidence_claims"
    review_id_column = f"{authority_name}_review_id"
    op.create_table(
        link_table,
        sa.Column(
            review_id_column,
            sa.Uuid(),
            sa.ForeignKey(f"{review_table}.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "evidence_claim_id",
            sa.Uuid(),
            sa.ForeignKey("evidence_claims.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint(review_id_column, "evidence_claim_id"),
        sa.UniqueConstraint(
            review_id_column,
            "position",
            name=f"uq_{authority_name}_review_evidence_order",
        ),
    )


def upgrade() -> None:
    _create_review_tables(
        authority_name="competency_floor",
        authority_table="competency_floors",
        review_table="competency_floor_reviews",
    )
    _create_review_tables(
        authority_name="priority_policy",
        authority_table="priority_policies",
        review_table="priority_policy_reviews",
    )


def _drop_review_tables(*, authority_name: str, review_table: str) -> None:
    op.drop_table(f"{authority_name}_review_evidence_claims")
    for column_name in (
        "reviewed_at",
        "supersedes_review_id",
        "decision",
        f"{authority_name}_id",
    ):
        op.drop_index(f"ix_{review_table}_{column_name}", table_name=review_table)
    op.drop_table(review_table)


def downgrade() -> None:
    _drop_review_tables(authority_name="priority_policy", review_table="priority_policy_reviews")
    _drop_review_tables(authority_name="competency_floor", review_table="competency_floor_reviews")
