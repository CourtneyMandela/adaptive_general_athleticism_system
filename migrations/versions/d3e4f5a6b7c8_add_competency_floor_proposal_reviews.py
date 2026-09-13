"""add competency-floor proposal reviews

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-09-13 01:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from agas_domain.persistence.types import UTCDateTime
from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: str | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX_NAMES = {
    "proposal_id": "ix_competency_floor_proposal_reviews_proposal_id",
    "proposal_content_digest": "ix_competency_floor_proposal_reviews_proposal_content_digest",
    "batch_id": "ix_competency_floor_proposal_reviews_batch_id",
    "decision": "ix_competency_floor_proposal_reviews_decision",
    "supersedes_review_id": "ix_competency_floor_proposal_reviews_supersedes_review_id",
    "reviewed_at": "ix_competency_floor_proposal_reviews_reviewed_at",
    "reviewer_account_id": "ix_competency_floor_proposal_reviews_reviewer_account_id",
    "reviewer_authority_assignment_id": "ix_floor_proposal_review_assignment",
}


def upgrade() -> None:
    op.create_table(
        "competency_floor_proposal_reviews",
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("proposal_content_digest", sa.String(length=80), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("batch_content_digest", sa.String(length=80), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("supersedes_review_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", UTCDateTime(), nullable=False),
        sa.Column("reviewer_account_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_authority_assignment_id", sa.Uuid(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("attestation", sa.Text(), nullable=False),
        sa.Column("review_version", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.CheckConstraint(
            "decision IN ('advance', 'needs_revision', 'rejected')",
            name="ck_floor_proposal_review_decision",
        ),
        sa.CheckConstraint(
            "sequence_number >= 1",
            name="ck_floor_proposal_review_sequence",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_review_id"],
            ["competency_floor_proposal_reviews.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["reviewer_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["reviewer_authority_assignment_id"],
            ["account_role_assignments.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "proposal_id",
            "sequence_number",
            name="uq_floor_proposal_review_sequence",
        ),
        sa.UniqueConstraint(
            "supersedes_review_id",
            name="uq_floor_proposal_review_superseded_once",
        ),
    )
    for column, index_name in _INDEX_NAMES.items():
        op.create_index(
            index_name,
            "competency_floor_proposal_reviews",
            [column],
            unique=False,
        )


def downgrade() -> None:
    for index_name in reversed(_INDEX_NAMES.values()):
        op.drop_index(
            index_name,
            table_name="competency_floor_proposal_reviews",
        )
    op.drop_table("competency_floor_proposal_reviews")
