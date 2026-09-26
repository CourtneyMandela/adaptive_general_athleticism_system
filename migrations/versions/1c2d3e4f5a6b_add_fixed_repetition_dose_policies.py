"""add fixed repetition dose policies for capability deficits

Revision ID: 1c2d3e4f5a6b
Revises: 0b1c2d3e4f5a
Create Date: 2026-09-23 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "1c2d3e4f5a6b"
down_revision: str | None = "0b1c2d3e4f5a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "fixed_repetition_dose_policies",
        sa.Column("adaptation_id", sa.Uuid(), nullable=False),
        sa.Column("estimate_scope", sa.String(length=200), nullable=False),
        sa.Column("sets", sa.Integer(), nullable=False),
        sa.Column("repetitions_per_set", sa.Integer(), nullable=False),
        sa.Column("maximum_initial_total_repetitions", sa.Integer(), nullable=False),
        sa.Column("rest_seconds", sa.Integer(), nullable=False),
        sa.Column("effort_rpe_minimum", sa.Float(), nullable=False),
        sa.Column("effort_rpe_maximum", sa.Float(), nullable=False),
        sa.Column("technique_constraints", json_type, nullable=False),
        sa.Column("planned_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("progression_policy_id", sa.Uuid(), nullable=False),
        sa.Column("numeric_value_origin", sa.String(length=60), nullable=False),
        sa.Column("authority_reference", sa.String(length=200), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sets >= 1", name="ck_fixed_repetition_dose_sets_positive"),
        sa.CheckConstraint(
            "repetitions_per_set >= 1 AND maximum_initial_total_repetitions >= 1",
            name="ck_fixed_repetition_dose_repetitions_positive",
        ),
        sa.CheckConstraint(
            "sets * repetitions_per_set <= maximum_initial_total_repetitions",
            name="ck_fixed_repetition_dose_initial_cap",
        ),
        sa.CheckConstraint(
            "rest_seconds >= 0",
            name="ck_fixed_repetition_dose_rest_nonnegative",
        ),
        sa.CheckConstraint(
            "effort_rpe_minimum >= 0 AND effort_rpe_maximum <= 10 AND "
            "effort_rpe_maximum >= effort_rpe_minimum",
            name="ck_fixed_repetition_dose_rpe_bounds",
        ),
        sa.CheckConstraint(
            "planned_duration_minutes > 0",
            name="ck_fixed_repetition_dose_duration_positive",
        ),
        sa.CheckConstraint(
            "numeric_value_origin IN ('engineering_judgment', 'professional_judgment', "
            "'scientific_evidence')",
            name="ck_fixed_repetition_dose_numeric_origin",
        ),
        sa.ForeignKeyConstraint(["adaptation_id"], ["adaptations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["progression_policy_id"], ["progression_policies.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fixed_repetition_dose_policies_adaptation_id",
        "fixed_repetition_dose_policies",
        ["adaptation_id"],
    )
    op.create_index(
        "ix_fixed_repetition_dose_policies_estimate_scope",
        "fixed_repetition_dose_policies",
        ["estimate_scope"],
    )
    op.create_index(
        "ix_fixed_repetition_dose_policies_progression_policy_id",
        "fixed_repetition_dose_policies",
        ["progression_policy_id"],
    )
    op.create_table(
        "fixed_repetition_dose_policy_evidence_claims",
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_claim_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["evidence_claim_id"], ["evidence_claims.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["fixed_repetition_dose_policies.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("policy_id", "evidence_claim_id"),
        sa.UniqueConstraint(
            "policy_id",
            "position",
            name="uq_fixed_repetition_dose_policy_evidence_order",
        ),
    )


def downgrade() -> None:
    op.drop_table("fixed_repetition_dose_policy_evidence_claims")
    op.drop_index(
        "ix_fixed_repetition_dose_policies_progression_policy_id",
        table_name="fixed_repetition_dose_policies",
    )
    op.drop_index(
        "ix_fixed_repetition_dose_policies_estimate_scope",
        table_name="fixed_repetition_dose_policies",
    )
    op.drop_index(
        "ix_fixed_repetition_dose_policies_adaptation_id",
        table_name="fixed_repetition_dose_policies",
    )
    op.drop_table("fixed_repetition_dose_policies")
