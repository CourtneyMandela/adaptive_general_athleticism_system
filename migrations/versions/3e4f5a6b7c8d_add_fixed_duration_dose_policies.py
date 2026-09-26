"""add fixed duration dose policies for governed aerobic work

Revision ID: 3e4f5a6b7c8d
Revises: 2d3e4f5a6b7c
Create Date: 2026-09-25 08:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "3e4f5a6b7c8d"
down_revision: str | None = "2d3e4f5a6b7c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "fixed_duration_dose_policies",
        sa.Column("adaptation_id", sa.Uuid(), nullable=False),
        sa.Column("estimate_scope", sa.String(length=200), nullable=False),
        sa.Column("priority_state", sa.String(length=30), nullable=False),
        sa.Column("sets", sa.Integer(), nullable=False),
        sa.Column("duration_seconds_per_set", sa.Integer(), nullable=False),
        sa.Column("maximum_initial_total_duration_seconds", sa.Integer(), nullable=False),
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
        sa.CheckConstraint("sets >= 1", name="ck_fixed_duration_dose_sets_positive"),
        sa.CheckConstraint(
            "duration_seconds_per_set >= 1 AND maximum_initial_total_duration_seconds >= 1",
            name="ck_fixed_duration_dose_seconds_positive",
        ),
        sa.CheckConstraint(
            "sets * duration_seconds_per_set <= maximum_initial_total_duration_seconds",
            name="ck_fixed_duration_dose_initial_cap",
        ),
        sa.CheckConstraint(
            "rest_seconds >= 0",
            name="ck_fixed_duration_dose_rest_nonnegative",
        ),
        sa.CheckConstraint(
            "effort_rpe_minimum >= 0 AND effort_rpe_maximum <= 10 AND "
            "effort_rpe_maximum >= effort_rpe_minimum",
            name="ck_fixed_duration_dose_rpe_bounds",
        ),
        sa.CheckConstraint(
            "planned_duration_minutes > 0",
            name="ck_fixed_duration_dose_planned_minutes_positive",
        ),
        sa.CheckConstraint(
            "sets * duration_seconds_per_set <= planned_duration_minutes * 60",
            name="ck_fixed_duration_dose_fits_session_envelope",
        ),
        sa.CheckConstraint(
            "numeric_value_origin IN ('engineering_judgment', 'professional_judgment', "
            "'scientific_evidence')",
            name="ck_fixed_duration_dose_numeric_origin",
        ),
        sa.CheckConstraint(
            "priority_state IN ('develop', 'maintain')",
            name="ck_fixed_duration_dose_priority_state",
        ),
        sa.ForeignKeyConstraint(["adaptation_id"], ["adaptations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["progression_policy_id"], ["progression_policies.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("adaptation_id", "estimate_scope", "priority_state", "progression_policy_id"):
        op.create_index(
            f"ix_fixed_duration_dose_policies_{column}",
            "fixed_duration_dose_policies",
            [column],
        )
    op.create_table(
        "fixed_duration_dose_policy_evidence_claims",
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_claim_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["evidence_claim_id"], ["evidence_claims.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["fixed_duration_dose_policies.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("policy_id", "evidence_claim_id"),
        sa.UniqueConstraint(
            "policy_id",
            "position",
            name="uq_fixed_duration_dose_policy_evidence_order",
        ),
    )


def downgrade() -> None:
    op.drop_table("fixed_duration_dose_policy_evidence_claims")
    for column in ("progression_policy_id", "priority_state", "estimate_scope", "adaptation_id"):
        op.drop_index(
            f"ix_fixed_duration_dose_policies_{column}",
            table_name="fixed_duration_dose_policies",
        )
    op.drop_table("fixed_duration_dose_policies")
