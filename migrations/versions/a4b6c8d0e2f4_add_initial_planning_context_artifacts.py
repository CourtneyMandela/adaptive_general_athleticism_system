"""add initial planning context artifacts

Revision ID: a4b6c8d0e2f4
Revises: f3a4b5c6d7e8
Create Date: 2026-08-29 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4b6c8d0e2f4"
down_revision: str | None = "f3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DRAFT_INDEX_NAMES = {
    "athlete_id": "ix_initial_planning_context_drafts_athlete_id",
    "priority_policy_id": "ix_initial_planning_context_drafts_priority_policy_id",
    "priority_policy_review_id": "ix_initial_planning_context_drafts_priority_policy_review_id",
    "authored_by_account_id": "ix_initial_planning_context_drafts_authored_by_account_id",
    "author_authority_assignment_id": "ix_initial_plan_draft_authority_assignment",
    "authored_at": "ix_initial_planning_context_drafts_authored_at",
}

_CANDIDATE_INDEX_NAMES = {
    "draft_id": "ix_initial_planning_candidate_contexts_draft_id",
    "adaptation_id": "ix_initial_planning_candidate_contexts_adaptation_id",
    "competency_floor_id": "ix_initial_planning_candidate_contexts_competency_floor_id",
    "competency_floor_review_id": "ix_initial_plan_candidate_floor_review",
    "capability_estimate_id": "ix_initial_planning_candidate_contexts_capability_estimate_id",
}

_REVIEW_INDEX_NAMES = {
    "draft_id": "ix_initial_planning_context_reviews_draft_id",
    "decision": "ix_initial_planning_context_reviews_decision",
    "reviewed_by_account_id": "ix_initial_planning_context_reviews_reviewed_by_account_id",
    "review_authority_assignment_id": "ix_initial_plan_review_authority_assignment",
    "reviewed_at": "ix_initial_planning_context_reviews_reviewed_at",
}


def _version_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "initial_planning_context_drafts",
        *_version_columns(),
        sa.Column("athlete_id", sa.Uuid(), nullable=False),
        sa.Column("priority_policy_id", sa.Uuid(), nullable=False),
        sa.Column("priority_policy_review_id", sa.Uuid(), nullable=False),
        sa.Column("horizon_months", sa.Integer(), nullable=False),
        sa.Column("review_after_days", sa.Integer(), nullable=False),
        sa.Column("authored_by_account_id", sa.Uuid(), nullable=False),
        sa.Column("author_authority_assignment_id", sa.Uuid(), nullable=False),
        sa.Column("authored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applicability_rationale", sa.Text(), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=False),
        sa.Column("draft_version", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["priority_policy_id"], ["priority_policies.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["priority_policy_review_id"],
            ["priority_policy_reviews.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["authored_by_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["author_authority_assignment_id"],
            ["account_role_assignments.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column, index_name in _DRAFT_INDEX_NAMES.items():
        op.create_index(
            index_name,
            "initial_planning_context_drafts",
            [column],
            unique=False,
        )

    op.create_table(
        "initial_planning_candidate_contexts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("draft_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("adaptation_id", sa.Uuid(), nullable=False),
        sa.Column("competency_floor_id", sa.Uuid(), nullable=False),
        sa.Column("competency_floor_review_id", sa.Uuid(), nullable=False),
        sa.Column("capability_estimate_id", sa.Uuid(), nullable=False),
        sa.Column("general_relevance", sa.Float(), nullable=False),
        sa.Column("goal_relevance", sa.Float(), nullable=False),
        sa.Column("prerequisite_value", sa.Float(), nullable=False),
        sa.Column("expected_trainability", sa.Float(), nullable=False),
        sa.Column("transfer_value", sa.Float(), nullable=False),
        sa.Column("fatigue_cost", sa.Float(), nullable=False),
        sa.Column("time_cost", sa.Float(), nullable=False),
        sa.Column("interference_cost", sa.Float(), nullable=False),
        sa.Column("safe_to_train", sa.Boolean(), nullable=False),
        sa.Column("introductory_exposure_needed", sa.Boolean(), nullable=False),
        sa.Column("prerequisites_met", sa.Boolean(), nullable=False),
        sa.Column("cultivate_comparative_advantage", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "general_relevance >= 0 AND general_relevance <= 1 "
            "AND goal_relevance >= 0 AND goal_relevance <= 1 "
            "AND prerequisite_value >= 0 AND prerequisite_value <= 1 "
            "AND expected_trainability >= 0 AND expected_trainability <= 1 "
            "AND transfer_value >= 0 AND transfer_value <= 1 "
            "AND fatigue_cost >= 0 AND fatigue_cost <= 1 "
            "AND time_cost >= 0 AND time_cost <= 1 "
            "AND interference_cost >= 0 AND interference_cost <= 1",
            name="ck_initial_planning_candidate_unit_intervals",
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"], ["initial_planning_context_drafts.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["adaptation_id"], ["adaptations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["competency_floor_id"], ["competency_floors.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["competency_floor_review_id"],
            ["competency_floor_reviews.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["capability_estimate_id"], ["capability_estimates.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draft_id", "position", name="uq_initial_planning_candidate_order"),
        sa.UniqueConstraint(
            "draft_id", "adaptation_id", name="uq_initial_planning_draft_adaptation"
        ),
    )
    for column, index_name in _CANDIDATE_INDEX_NAMES.items():
        op.create_index(
            index_name,
            "initial_planning_candidate_contexts",
            [column],
            unique=False,
        )

    _create_candidate_link(
        "initial_planning_context_prerequisites",
        "adaptation_id",
        "adaptations",
        "uq_initial_context_prerequisite_order",
    )
    _create_candidate_link(
        "initial_planning_context_observations",
        "observation_id",
        "observations",
        "uq_initial_context_observation_order",
    )
    _create_candidate_link(
        "initial_planning_context_evidence_claims",
        "evidence_claim_id",
        "evidence_claims",
        "uq_initial_context_evidence_order",
    )

    op.create_table(
        "initial_planning_context_reviews",
        *_version_columns(),
        sa.Column("draft_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column("reviewed_by_account_id", sa.Uuid(), nullable=False),
        sa.Column("review_authority_assignment_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applicability_rationale", sa.Text(), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=False),
        sa.Column("review_version", sa.String(length=120), nullable=False),
        sa.CheckConstraint(
            "decision IN ('approved', 'needs_revision', 'rejected')",
            name="ck_initial_planning_context_review_decision",
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"], ["initial_planning_context_drafts.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["reviewed_by_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["review_authority_assignment_id"],
            ["account_role_assignments.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draft_id", name="uq_initial_planning_context_review_draft"),
    )
    for column, index_name in _REVIEW_INDEX_NAMES.items():
        op.create_index(
            index_name,
            "initial_planning_context_reviews",
            [column],
            unique=False,
        )


def _create_candidate_link(
    table_name: str,
    target_column: str,
    target_table: str,
    order_constraint: str,
) -> None:
    op.create_table(
        table_name,
        sa.Column("candidate_context_id", sa.Uuid(), nullable=False),
        sa.Column(target_column, sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_context_id"],
            ["initial_planning_candidate_contexts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint([target_column], [f"{target_table}.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("candidate_context_id", target_column),
        sa.UniqueConstraint("candidate_context_id", "position", name=order_constraint),
    )


def downgrade() -> None:
    for index_name in reversed(_REVIEW_INDEX_NAMES.values()):
        op.drop_index(
            index_name,
            table_name="initial_planning_context_reviews",
        )
    op.drop_table("initial_planning_context_reviews")
    op.drop_table("initial_planning_context_evidence_claims")
    op.drop_table("initial_planning_context_observations")
    op.drop_table("initial_planning_context_prerequisites")
    for index_name in reversed(_CANDIDATE_INDEX_NAMES.values()):
        op.drop_index(
            index_name,
            table_name="initial_planning_candidate_contexts",
        )
    op.drop_table("initial_planning_candidate_contexts")
    for index_name in reversed(_DRAFT_INDEX_NAMES.values()):
        op.drop_index(
            index_name,
            table_name="initial_planning_context_drafts",
        )
    op.drop_table("initial_planning_context_drafts")
