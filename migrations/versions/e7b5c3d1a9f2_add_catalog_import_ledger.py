"""add catalog import ledger

Revision ID: e7b5c3d1a9f2
Revises: c4e8f6a2b9d1
Create Date: 2026-08-21 03:00:00
"""

from collections.abc import Sequence

import agas_domain.persistence.types
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.sqltypes import Text

revision: str = "e7b5c3d1a9f2"
down_revision: str | None = "c4e8f6a2b9d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql")
    op.create_table(
        "catalog_imports",
        sa.Column("catalog_version", sa.String(length=80), nullable=False),
        sa.Column("review_status", sa.String(length=80), nullable=False),
        sa.Column("reviewed_by", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.Date(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("notes", json_type, nullable=False),
        sa.Column("content_digest", sa.String(length=80), nullable=False),
        sa.Column(
            "imported_at",
            agas_domain.persistence.types.UTCDateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("importer_version", sa.String(length=80), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at",
            agas_domain.persistence.types.UTCDateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("catalog_version"),
        sa.UniqueConstraint("content_digest"),
    )
    op.create_table(
        "catalog_import_evidence_claims",
        sa.Column("catalog_import_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_claim_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["catalog_import_id"], ["catalog_imports.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evidence_claim_id"], ["evidence_claims.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("catalog_import_id", "evidence_claim_id"),
        sa.UniqueConstraint(
            "catalog_import_id", "position", name="uq_catalog_import_evidence_order"
        ),
    )
    op.create_table(
        "catalog_import_adaptations",
        sa.Column("catalog_import_id", sa.Uuid(), nullable=False),
        sa.Column("adaptation_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["adaptation_id"], ["adaptations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["catalog_import_id"], ["catalog_imports.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("catalog_import_id", "adaptation_id"),
        sa.UniqueConstraint(
            "catalog_import_id", "position", name="uq_catalog_import_adaptation_order"
        ),
    )
    op.create_table(
        "catalog_import_equipment",
        sa.Column("catalog_import_id", sa.Uuid(), nullable=False),
        sa.Column("equipment_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["catalog_import_id"], ["catalog_imports.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("catalog_import_id", "equipment_id"),
        sa.UniqueConstraint(
            "catalog_import_id", "position", name="uq_catalog_import_equipment_order"
        ),
    )
    op.create_table(
        "catalog_import_exercises",
        sa.Column("catalog_import_id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["catalog_import_id"], ["catalog_imports.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("catalog_import_id", "exercise_id"),
        sa.UniqueConstraint(
            "catalog_import_id", "position", name="uq_catalog_import_exercise_order"
        ),
    )


def downgrade() -> None:
    op.drop_table("catalog_import_exercises")
    op.drop_table("catalog_import_equipment")
    op.drop_table("catalog_import_adaptations")
    op.drop_table("catalog_import_evidence_claims")
    op.drop_table("catalog_imports")
