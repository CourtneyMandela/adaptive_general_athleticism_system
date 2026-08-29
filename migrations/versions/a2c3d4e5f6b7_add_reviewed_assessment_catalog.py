"""add reviewed assessment catalog

Revision ID: a2c3d4e5f6b7
Revises: f1b2c3d4e5a6
Create Date: 2026-08-22 23:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql

revision: str = "a2c3d4e5f6b7"
down_revision: str | None = "f1b2c3d4e5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql")
    op.create_table(
        "assessment_definition_reviews",
        sa.Column("assessment_definition_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("supersedes_review_id", sa.Uuid(), nullable=True),
        sa.Column("protocol_instructions", json_type, nullable=False),
        sa.Column("result_entry_instructions", sa.Text(), nullable=False),
        sa.Column("recommended_reassessment_days", sa.Integer(), nullable=True),
        sa.Column("self_administered", sa.Boolean(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewer", sa.String(length=160), nullable=False),
        sa.Column("applicability_notes", sa.Text(), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=False),
        sa.Column("review_version", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "decision IN ('approved', 'needs_revision', 'rejected')",
            name="ck_assessment_review_decision",
        ),
        sa.CheckConstraint("sequence_number >= 1", name="ck_assessment_review_sequence_positive"),
        sa.CheckConstraint(
            "recommended_reassessment_days IS NULL OR recommended_reassessment_days >= 1",
            name="ck_assessment_review_reassessment_positive",
        ),
        sa.CheckConstraint(
            "decision != 'approved' OR recommended_reassessment_days IS NOT NULL",
            name="ck_approved_assessment_has_reassessment_interval",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_definition_id"], ["assessment_definitions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_review_id"],
            ["assessment_definition_reviews.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assessment_definition_id",
            "sequence_number",
            name="uq_assessment_review_definition_sequence",
        ),
        sa.UniqueConstraint("supersedes_review_id", name="uq_assessment_review_superseded_once"),
    )
    op.create_index(
        "ix_assessment_definition_reviews_assessment_definition_id",
        "assessment_definition_reviews",
        ["assessment_definition_id"],
        unique=False,
    )
    op.create_index(
        "ix_assessment_definition_reviews_decision",
        "assessment_definition_reviews",
        ["decision"],
        unique=False,
    )
    op.create_index(
        "ix_assessment_definition_reviews_supersedes_review_id",
        "assessment_definition_reviews",
        ["supersedes_review_id"],
        unique=False,
    )
    op.create_index(
        "ix_assessment_definition_reviews_reviewed_at",
        "assessment_definition_reviews",
        ["reviewed_at"],
        unique=False,
    )
    op.create_table(
        "assessment_definition_review_evidence_claims",
        sa.Column("assessment_review_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_claim_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["assessment_review_id"], ["assessment_definition_reviews.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["evidence_claim_id"], ["evidence_claims.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("assessment_review_id", "evidence_claim_id"),
        sa.UniqueConstraint(
            "assessment_review_id", "position", name="uq_assessment_review_evidence_order"
        ),
    )
    with op.batch_alter_table("assessment_selections") as batch_op:
        batch_op.add_column(sa.Column("assessment_definition_review_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_assessment_selection_definition_review",
            "assessment_definition_reviews",
            ["assessment_definition_review_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(
            "ix_assessment_selections_assessment_definition_review_id",
            ["assessment_definition_review_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("assessment_selections") as batch_op:
        batch_op.drop_index("ix_assessment_selections_assessment_definition_review_id")
        batch_op.drop_constraint("fk_assessment_selection_definition_review", type_="foreignkey")
        batch_op.drop_column("assessment_definition_review_id")
    op.drop_table("assessment_definition_review_evidence_claims")
    op.drop_index(
        "ix_assessment_definition_reviews_reviewed_at",
        table_name="assessment_definition_reviews",
    )
    op.drop_index(
        "ix_assessment_definition_reviews_supersedes_review_id",
        table_name="assessment_definition_reviews",
    )
    op.drop_index(
        "ix_assessment_definition_reviews_decision",
        table_name="assessment_definition_reviews",
    )
    op.drop_index(
        "ix_assessment_definition_reviews_assessment_definition_id",
        table_name="assessment_definition_reviews",
    )
    op.drop_table("assessment_definition_reviews")
