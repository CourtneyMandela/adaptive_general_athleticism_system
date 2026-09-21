"""add introductory exposure dose authorities and derived doses

Revision ID: f9c0d1e2f3a4
Revises: f8b9c0d1e2f3
Create Date: 2026-09-20 21:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from agas_domain.persistence.types import UTCDateTime
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f9c0d1e2f3a4"
down_revision: str | None = "f8b9c0d1e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "introductory_exposure_dose_policies",
        sa.Column("adaptation_id", sa.Uuid(), nullable=False),
        sa.Column("exposure_type", sa.String(length=60), nullable=False),
        sa.Column("target_scope", sa.String(length=200), nullable=False),
        sa.Column("dose_unit", sa.String(length=40), nullable=False),
        sa.Column("sets", sa.Integer(), nullable=False),
        sa.Column("dose_per_set", sa.Float(), nullable=False),
        sa.Column("maximum_total_dose", sa.Float(), nullable=False),
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
        sa.Column("created_at", UTCDateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sets >= 1", name="ck_intro_exposure_policy_sets_positive"),
        sa.CheckConstraint(
            "dose_per_set > 0 AND maximum_total_dose > 0",
            name="ck_intro_exposure_policy_dose_positive",
        ),
        sa.CheckConstraint(
            "sets * dose_per_set <= maximum_total_dose",
            name="ck_intro_exposure_policy_dose_cap",
        ),
        sa.CheckConstraint("rest_seconds >= 0", name="ck_intro_exposure_policy_rest_nonnegative"),
        sa.CheckConstraint(
            "effort_rpe_minimum >= 0 AND effort_rpe_maximum <= 10 AND "
            "effort_rpe_maximum >= effort_rpe_minimum",
            name="ck_intro_exposure_policy_rpe_bounds",
        ),
        sa.CheckConstraint(
            "planned_duration_minutes > 0",
            name="ck_intro_exposure_policy_duration_positive",
        ),
        sa.CheckConstraint(
            "dose_unit IN ('repetitions', 'seconds')",
            name="ck_intro_exposure_policy_dose_unit",
        ),
        sa.CheckConstraint(
            "numeric_value_origin IN ('engineering_judgment', 'professional_judgment', "
            "'scientific_evidence')",
            name="ck_intro_exposure_policy_numeric_origin",
        ),
        sa.ForeignKeyConstraint(["adaptation_id"], ["adaptations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["progression_policy_id"], ["progression_policies.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("adaptation_id", "exposure_type", "target_scope", "progression_policy_id"):
        op.create_index(
            f"ix_intro_exposure_policies_{column}",
            "introductory_exposure_dose_policies",
            [column],
            unique=False,
        )
    op.create_table(
        "introductory_exposure_dose_policy_evidence_claims",
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_claim_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["introductory_exposure_dose_policies.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["evidence_claim_id"], ["evidence_claims.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("policy_id", "evidence_claim_id"),
        sa.UniqueConstraint(
            "policy_id", "position", name="uq_intro_exposure_policy_evidence_order"
        ),
    )
    op.create_table(
        "introductory_exposure_doses",
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("athlete_id", sa.Uuid(), nullable=False),
        sa.Column("exposure_need_id", sa.Uuid(), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("adaptation_id", sa.Uuid(), nullable=False),
        sa.Column("exposure_type", sa.String(length=60), nullable=False),
        sa.Column("target_scope", sa.String(length=200), nullable=False),
        sa.Column("dose_unit", sa.String(length=40), nullable=False),
        sa.Column("sets", sa.Integer(), nullable=False),
        sa.Column("dose_per_set", sa.Float(), nullable=False),
        sa.Column("total_dose", sa.Float(), nullable=False),
        sa.Column("rest_seconds", sa.Integer(), nullable=False),
        sa.Column("effort_rpe_minimum", sa.Float(), nullable=False),
        sa.Column("effort_rpe_maximum", sa.Float(), nullable=False),
        sa.Column("technique_constraints", json_type, nullable=False),
        sa.Column("planned_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("numeric_value_origin", sa.String(length=60), nullable=False),
        sa.Column("authority_reference", sa.String(length=200), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=False),
        sa.Column("derived_at", UTCDateTime(timezone=True), nullable=False),
        sa.Column("rule_version", sa.String(length=160), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", UTCDateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind = 'derived'", name="ck_intro_exposure_dose_derived"),
        sa.CheckConstraint("sets >= 1", name="ck_intro_exposure_dose_sets_positive"),
        sa.CheckConstraint(
            "dose_per_set > 0 AND total_dose > 0", name="ck_intro_exposure_dose_positive"
        ),
        sa.CheckConstraint(
            "ABS(total_dose - sets * dose_per_set) < 0.000000001",
            name="ck_intro_exposure_dose_total",
        ),
        sa.CheckConstraint("rest_seconds >= 0", name="ck_intro_exposure_dose_rest_nonnegative"),
        sa.CheckConstraint(
            "effort_rpe_minimum >= 0 AND effort_rpe_maximum <= 10 AND "
            "effort_rpe_maximum >= effort_rpe_minimum",
            name="ck_intro_exposure_dose_rpe_bounds",
        ),
        sa.CheckConstraint(
            "planned_duration_minutes > 0", name="ck_intro_exposure_dose_duration_positive"
        ),
        sa.CheckConstraint(
            "dose_unit IN ('repetitions', 'seconds')", name="ck_intro_exposure_dose_unit"
        ),
        sa.CheckConstraint(
            "numeric_value_origin IN ('engineering_judgment', 'professional_judgment', "
            "'scientific_evidence')",
            name="ck_intro_exposure_dose_numeric_origin",
        ),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["exposure_need_id"], ["exposure_needs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["introductory_exposure_dose_policies.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["adaptation_id"], ["adaptations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "exposure_need_id", "policy_id", name="uq_intro_exposure_dose_need_policy"
        ),
    )
    for column in ("athlete_id", "exposure_need_id", "policy_id", "adaptation_id", "derived_at"):
        op.create_index(
            f"ix_intro_exposure_doses_{column}",
            "introductory_exposure_doses",
            [column],
            unique=False,
        )
    op.create_table(
        "introductory_exposure_dose_observations",
        sa.Column("dose_id", sa.Uuid(), nullable=False),
        sa.Column("observation_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dose_id"], ["introductory_exposure_doses.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["observation_id"], ["observations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("dose_id", "observation_id"),
        sa.UniqueConstraint("dose_id", "position", name="uq_intro_exposure_dose_observation_order"),
    )
    op.create_table(
        "introductory_exposure_dose_evidence_claims",
        sa.Column("dose_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_claim_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dose_id"], ["introductory_exposure_doses.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["evidence_claim_id"], ["evidence_claims.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("dose_id", "evidence_claim_id"),
        sa.UniqueConstraint("dose_id", "position", name="uq_intro_exposure_dose_evidence_order"),
    )


def downgrade() -> None:
    op.drop_table("introductory_exposure_dose_evidence_claims")
    op.drop_table("introductory_exposure_dose_observations")
    for column in ("derived_at", "adaptation_id", "policy_id", "exposure_need_id", "athlete_id"):
        op.drop_index(f"ix_intro_exposure_doses_{column}", table_name="introductory_exposure_doses")
    op.drop_table("introductory_exposure_doses")
    op.drop_table("introductory_exposure_dose_policy_evidence_claims")
    for column in ("progression_policy_id", "target_scope", "exposure_type", "adaptation_id"):
        op.drop_index(
            f"ix_intro_exposure_policies_{column}",
            table_name="introductory_exposure_dose_policies",
        )
    op.drop_table("introductory_exposure_dose_policies")
