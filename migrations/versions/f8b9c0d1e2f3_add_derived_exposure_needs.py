"""add derived exposure needs

Revision ID: f8b9c0d1e2f3
Revises: e4f5a6b7c8d9
Create Date: 2026-09-20 20:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from agas_domain.persistence.types import UTCDateTime
from alembic import op

revision: str = "f8b9c0d1e2f3"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exposure_needs",
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("athlete_id", sa.Uuid(), nullable=False),
        sa.Column("exposure_type", sa.String(length=60), nullable=False),
        sa.Column("target_scope", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("lookback_days", sa.Integer(), nullable=False),
        sa.Column("minimum_exposure_days", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.String(length=40), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=False),
        sa.Column("authority_reference", sa.String(length=200), nullable=False),
        sa.Column("identified_at", UTCDateTime(timezone=True), nullable=False),
        sa.Column("valid_until", UTCDateTime(timezone=True), nullable=True),
        sa.Column("rule_version", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", UTCDateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind = 'derived'", name="ck_exposure_need_derived"),
        sa.CheckConstraint("lookback_days >= 1", name="ck_exposure_need_lookback_positive"),
        sa.CheckConstraint(
            "minimum_exposure_days >= 1",
            name="ck_exposure_need_minimum_days_positive",
        ),
        sa.CheckConstraint(
            "status IN ('unknown', 'introductory_exposure_needed', 'recent_exposure_confirmed')",
            name="ck_exposure_need_status",
        ),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "athlete_id",
            "exposure_type",
            "target_scope",
            "identified_at",
            name="uq_exposure_need_target_instant",
        ),
    )
    op.create_index("ix_exposure_needs_athlete_id", "exposure_needs", ["athlete_id"], unique=False)
    op.create_index(
        "ix_exposure_needs_exposure_type",
        "exposure_needs",
        ["exposure_type"],
        unique=False,
    )
    op.create_index(
        "ix_exposure_needs_target_scope",
        "exposure_needs",
        ["target_scope"],
        unique=False,
    )
    op.create_index("ix_exposure_needs_status", "exposure_needs", ["status"], unique=False)
    op.create_index(
        "ix_exposure_needs_identified_at",
        "exposure_needs",
        ["identified_at"],
        unique=False,
    )
    op.create_table(
        "exposure_need_observations",
        sa.Column("exposure_need_id", sa.Uuid(), nullable=False),
        sa.Column("observation_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["exposure_need_id"], ["exposure_needs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["observation_id"], ["observations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("exposure_need_id", "observation_id"),
        sa.UniqueConstraint(
            "exposure_need_id",
            "position",
            name="uq_exposure_need_observation_order",
        ),
    )


def downgrade() -> None:
    op.drop_table("exposure_need_observations")
    op.drop_index("ix_exposure_needs_identified_at", table_name="exposure_needs")
    op.drop_index("ix_exposure_needs_status", table_name="exposure_needs")
    op.drop_index("ix_exposure_needs_target_scope", table_name="exposure_needs")
    op.drop_index("ix_exposure_needs_exposure_type", table_name="exposure_needs")
    op.drop_index("ix_exposure_needs_athlete_id", table_name="exposure_needs")
    op.drop_table("exposure_needs")
