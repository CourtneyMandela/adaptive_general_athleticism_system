"""add evidence claim reviews

Revision ID: d7e9f1a3b5c8
Revises: c6d8e0f2a4b7
Create Date: 2026-08-31 14:00:00
"""

from collections.abc import Sequence

import agas_domain.persistence.types
import sqlalchemy as sa
from alembic import op

revision: str = "d7e9f1a3b5c8"
down_revision: str | None = "c6d8e0f2a4b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_claim_reviews",
        sa.Column("evidence_claim_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("supersedes_review_id", sa.Uuid(), nullable=True),
        sa.Column(
            "reviewed_at",
            agas_domain.persistence.types.UTCDateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("reviewer", sa.String(length=160), nullable=False),
        sa.Column("source_verification_rationale", sa.Text(), nullable=False),
        sa.Column("extraction_rationale", sa.Text(), nullable=False),
        sa.Column("evidence_strength_rationale", sa.Text(), nullable=False),
        sa.Column("applicability_rationale", sa.Text(), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=False),
        sa.Column("conflict_disclosure", sa.Text(), nullable=False),
        sa.Column("review_version", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at",
            agas_domain.persistence.types.UTCDateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "decision IN ('approved', 'needs_revision', 'rejected')",
            name="ck_evidence_claim_review_decision",
        ),
        sa.CheckConstraint(
            "sequence_number >= 1", name="ck_evidence_claim_review_sequence_positive"
        ),
        sa.ForeignKeyConstraint(["evidence_claim_id"], ["evidence_claims.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["supersedes_review_id"], ["evidence_claim_reviews.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evidence_claim_id",
            "sequence_number",
            name="uq_evidence_claim_review_claim_sequence",
        ),
        sa.UniqueConstraint(
            "supersedes_review_id", name="uq_evidence_claim_review_superseded_once"
        ),
    )
    op.create_index(
        op.f("ix_evidence_claim_reviews_evidence_claim_id"),
        "evidence_claim_reviews",
        ["evidence_claim_id"],
    )
    op.create_index(
        op.f("ix_evidence_claim_reviews_decision"),
        "evidence_claim_reviews",
        ["decision"],
    )
    op.create_index(
        op.f("ix_evidence_claim_reviews_reviewed_at"),
        "evidence_claim_reviews",
        ["reviewed_at"],
    )
    op.create_index(
        op.f("ix_evidence_claim_reviews_supersedes_review_id"),
        "evidence_claim_reviews",
        ["supersedes_review_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_evidence_claim_reviews_supersedes_review_id"),
        table_name="evidence_claim_reviews",
    )
    op.drop_index(
        op.f("ix_evidence_claim_reviews_reviewed_at"),
        table_name="evidence_claim_reviews",
    )
    op.drop_index(
        op.f("ix_evidence_claim_reviews_decision"),
        table_name="evidence_claim_reviews",
    )
    op.drop_index(
        op.f("ix_evidence_claim_reviews_evidence_claim_id"),
        table_name="evidence_claim_reviews",
    )
    op.drop_table("evidence_claim_reviews")
