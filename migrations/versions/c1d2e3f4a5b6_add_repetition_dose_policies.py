"""add governed repetition dose policies

Revision ID: c1d2e3f4a5b6
Revises: b0c9d8e7f6a5
Create Date: 2026-09-11 11:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from agas_domain.persistence.types import UTCDateTime
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b0c9d8e7f6a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "repetition_dose_policies",
        sa.Column("adaptation_id", sa.Uuid(), nullable=False),
        sa.Column("estimate_scope", sa.String(length=200), nullable=False),
        sa.Column("unit_or_scale", sa.String(length=80), nullable=False),
        sa.Column("minimum_eligible_estimate", sa.Float(), nullable=False),
        sa.Column("target_fraction_of_estimate", sa.Float(), nullable=False),
        sa.Column("rounding_mode", sa.String(length=20), nullable=False),
        sa.Column("sets", sa.Integer(), nullable=False),
        sa.Column("minimum_repetitions_per_set", sa.Integer(), nullable=False),
        sa.Column("maximum_repetitions_per_set", sa.Integer(), nullable=False),
        sa.Column("rest_seconds", sa.Integer(), nullable=False),
        sa.Column("effort_rpe_minimum", sa.Float(), nullable=False),
        sa.Column("effort_rpe_maximum", sa.Float(), nullable=False),
        sa.Column(
            "technique_constraints",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column("planned_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("progression_policy_id", sa.Uuid(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", UTCDateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "minimum_eligible_estimate >= 0",
            name="ck_repetition_dose_minimum_estimate_nonnegative",
        ),
        sa.CheckConstraint(
            "target_fraction_of_estimate > 0 AND target_fraction_of_estimate <= 1",
            name="ck_repetition_dose_target_fraction",
        ),
        sa.CheckConstraint(
            "rounding_mode = 'floor'",
            name="ck_repetition_dose_rounding_mode",
        ),
        sa.CheckConstraint("sets >= 1", name="ck_repetition_dose_sets_positive"),
        sa.CheckConstraint(
            "minimum_repetitions_per_set >= 1 AND "
            "maximum_repetitions_per_set >= minimum_repetitions_per_set",
            name="ck_repetition_dose_rep_bounds",
        ),
        sa.CheckConstraint(
            "rest_seconds >= 0",
            name="ck_repetition_dose_rest_nonnegative",
        ),
        sa.CheckConstraint(
            "effort_rpe_minimum >= 0 AND effort_rpe_maximum <= 10 AND "
            "effort_rpe_maximum >= effort_rpe_minimum",
            name="ck_repetition_dose_rpe_bounds",
        ),
        sa.CheckConstraint(
            "planned_duration_minutes > 0",
            name="ck_repetition_dose_duration_positive",
        ),
        sa.ForeignKeyConstraint(["adaptation_id"], ["adaptations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["progression_policy_id"],
            ["progression_policies.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_repetition_dose_policies_adaptation_id",
        "repetition_dose_policies",
        ["adaptation_id"],
        unique=False,
    )
    op.create_index(
        "ix_repetition_dose_policies_estimate_scope",
        "repetition_dose_policies",
        ["estimate_scope"],
        unique=False,
    )
    op.create_index(
        "ix_repetition_dose_policies_progression_policy_id",
        "repetition_dose_policies",
        ["progression_policy_id"],
        unique=False,
    )
    op.create_table(
        "repetition_dose_policy_evidence_claims",
        sa.Column("repetition_dose_policy_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_claim_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["evidence_claim_id"], ["evidence_claims.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["repetition_dose_policy_id"],
            ["repetition_dose_policies.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("repetition_dose_policy_id", "evidence_claim_id"),
        sa.UniqueConstraint(
            "repetition_dose_policy_id",
            "position",
            name="uq_repetition_dose_policy_evidence_order",
        ),
    )


def downgrade() -> None:
    op.drop_table("repetition_dose_policy_evidence_claims")
    op.drop_index(
        "ix_repetition_dose_policies_progression_policy_id",
        table_name="repetition_dose_policies",
    )
    op.drop_index(
        "ix_repetition_dose_policies_estimate_scope",
        table_name="repetition_dose_policies",
    )
    op.drop_index(
        "ix_repetition_dose_policies_adaptation_id",
        table_name="repetition_dose_policies",
    )
    op.drop_table("repetition_dose_policies")
