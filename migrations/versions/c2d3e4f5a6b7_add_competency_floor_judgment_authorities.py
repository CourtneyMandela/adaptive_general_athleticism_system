"""add competency-floor judgment authorities

Revision ID: c2d3e4f5a6b7
Revises: c1d2e3f4a5b6
Create Date: 2026-09-12 17:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from agas_domain.persistence.types import UTCDateTime
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c2d3e4f5a6b7"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "competency_floor_authorities",
        sa.Column("authority_kind", sa.String(length=60), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("scope", sa.String(length=200), nullable=False),
        sa.Column("population", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("applicability_notes", sa.Text(), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=False),
        sa.Column("limitations", json_type, nullable=False),
        sa.Column("authored_by", sa.String(length=160), nullable=False),
        sa.Column("qualification_context", sa.Text(), nullable=False),
        sa.Column("content_digest", sa.String(length=80), nullable=False),
        sa.Column("authority_version", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.CheckConstraint(
            "authority_kind IN ('professional_judgment', 'personal_calibration')",
            name="ck_competency_floor_authority_kind",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_digest", name="uq_competency_floor_authority_digest"),
    )
    op.create_index(
        "ix_competency_floor_authorities_authority_kind",
        "competency_floor_authorities",
        ["authority_kind"],
        unique=False,
    )
    op.create_table(
        "competency_floor_authority_evidence_claims",
        sa.Column("authority_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_claim_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["authority_id"], ["competency_floor_authorities.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["evidence_claim_id"], ["evidence_claims.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("authority_id", "evidence_claim_id"),
        sa.UniqueConstraint("authority_id", "position", name="uq_floor_authority_evidence_order"),
    )
    op.create_table(
        "competency_floor_authority_reviews",
        sa.Column("authority_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("supersedes_review_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", UTCDateTime(), nullable=False),
        sa.Column("reviewed_by", sa.String(length=160), nullable=False),
        sa.Column("attestation", sa.Text(), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=False),
        sa.Column("review_version", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.CheckConstraint(
            "decision IN ('approved', 'needs_revision', 'rejected')",
            name="ck_floor_authority_review_decision",
        ),
        sa.CheckConstraint("sequence_number >= 1", name="ck_floor_authority_review_sequence"),
        sa.ForeignKeyConstraint(
            ["authority_id"], ["competency_floor_authorities.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_review_id"],
            ["competency_floor_authority_reviews.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "authority_id", "sequence_number", name="uq_floor_authority_review_sequence"
        ),
        sa.UniqueConstraint(
            "supersedes_review_id", name="uq_floor_authority_review_superseded_once"
        ),
    )
    for column in ("authority_id", "decision", "supersedes_review_id", "reviewed_at"):
        op.create_index(
            f"ix_competency_floor_authority_reviews_{column}",
            "competency_floor_authority_reviews",
            [column],
            unique=False,
        )
    op.create_table(
        "competency_floor_authority_links",
        sa.Column("competency_floor_id", sa.Uuid(), nullable=False),
        sa.Column("authority_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["competency_floor_id"], ["competency_floors.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["authority_id"], ["competency_floor_authorities.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("competency_floor_id", "authority_id"),
        sa.UniqueConstraint(
            "competency_floor_id", "position", name="uq_floor_authority_order"
        ),
    )
    op.create_table(
        "competency_floor_review_authority_links",
        sa.Column("competency_floor_review_id", sa.Uuid(), nullable=False),
        sa.Column("authority_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["competency_floor_review_id"],
            ["competency_floor_reviews.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["authority_id"], ["competency_floor_authorities.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("competency_floor_review_id", "authority_id"),
        sa.UniqueConstraint(
            "competency_floor_review_id",
            "position",
            name="uq_floor_review_authority_order",
        ),
    )


def downgrade() -> None:
    op.drop_table("competency_floor_review_authority_links")
    op.drop_table("competency_floor_authority_links")
    for column in ("reviewed_at", "supersedes_review_id", "decision", "authority_id"):
        op.drop_index(
            f"ix_competency_floor_authority_reviews_{column}",
            table_name="competency_floor_authority_reviews",
        )
    op.drop_table("competency_floor_authority_reviews")
    op.drop_table("competency_floor_authority_evidence_claims")
    op.drop_index(
        "ix_competency_floor_authorities_authority_kind",
        table_name="competency_floor_authorities",
    )
    op.drop_table("competency_floor_authorities")
