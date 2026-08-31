"""add versioned evidence sources

Revision ID: c6d8e0f2a4b7
Revises: b5c7d9e1f3a5
Create Date: 2026-08-31 10:00:00
"""

from collections.abc import Sequence

import agas_domain.persistence.types
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.sqltypes import Text

revision: str = "c6d8e0f2a4b7"
down_revision: str | None = "b5c7d9e1f3a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql")
    op.create_table(
        "evidence_sources",
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("authors", json_type, nullable=False),
        sa.Column("journal", sa.Text(), nullable=True),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("publication_types", json_type, nullable=False),
        sa.Column("primary_identifier_scheme", sa.String(length=40), nullable=False),
        sa.Column("primary_identifier_value", sa.String(length=300), nullable=False),
        sa.Column("source_identifiers", json_type, nullable=False),
        sa.Column("metadata_provider", sa.String(length=40), nullable=False),
        sa.Column("retrieval_uri", sa.Text(), nullable=False),
        sa.Column("retrieval_query", sa.Text(), nullable=True),
        sa.Column(
            "retrieved_at",
            agas_domain.persistence.types.UTCDateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("metadata_version", sa.String(length=120), nullable=False),
        sa.Column("provenance_notes", json_type, nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("supersedes_source_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at",
            agas_domain.persistence.types.UTCDateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint("sequence_number >= 1", name="ck_evidence_source_sequence_positive"),
        sa.ForeignKeyConstraint(
            ["supersedes_source_id"], ["evidence_sources.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "primary_identifier_scheme",
            "primary_identifier_value",
            "sequence_number",
            name="uq_evidence_source_identity_sequence",
        ),
        sa.UniqueConstraint("supersedes_source_id", name="uq_evidence_source_superseded_once"),
    )
    op.create_index(
        op.f("ix_evidence_sources_primary_identifier_scheme"),
        "evidence_sources",
        ["primary_identifier_scheme"],
    )
    op.create_index(
        op.f("ix_evidence_sources_primary_identifier_value"),
        "evidence_sources",
        ["primary_identifier_value"],
    )
    op.create_index(op.f("ix_evidence_sources_retrieved_at"), "evidence_sources", ["retrieved_at"])
    op.create_index(
        op.f("ix_evidence_sources_supersedes_source_id"),
        "evidence_sources",
        ["supersedes_source_id"],
    )
    op.create_table(
        "evidence_claim_sources",
        sa.Column("evidence_claim_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_source_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["evidence_claim_id"], ["evidence_claims.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["evidence_source_id"], ["evidence_sources.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("evidence_claim_id", "evidence_source_id"),
        sa.UniqueConstraint("evidence_claim_id", "position", name="uq_evidence_claim_source_order"),
    )


def downgrade() -> None:
    op.drop_table("evidence_claim_sources")
    op.drop_index(op.f("ix_evidence_sources_supersedes_source_id"), table_name="evidence_sources")
    op.drop_index(op.f("ix_evidence_sources_retrieved_at"), table_name="evidence_sources")
    op.drop_index(
        op.f("ix_evidence_sources_primary_identifier_value"), table_name="evidence_sources"
    )
    op.drop_index(
        op.f("ix_evidence_sources_primary_identifier_scheme"), table_name="evidence_sources"
    )
    op.drop_table("evidence_sources")
