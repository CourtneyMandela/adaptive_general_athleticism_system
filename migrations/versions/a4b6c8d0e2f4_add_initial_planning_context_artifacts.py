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
    for column in (
        "athlete_id",
        "priority_policy_id",
        "priority_policy_review_id",
        "authored_by_account_id",
        "author_authority_assignment_id",
        "authored_at",
    ):
        op.create_index(
            f"ix_initial_planning_context_drafts_{column}",
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
    for column in (
        "draft_id",
        "adaptation_id",
        "competency_floor_id",
        "competency_floor_review_id",
        "capability_estimate_id",
    ):
        op.create_index(
            f"ix_initial_planning_candidate_contexts_{column}",
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
    for column in (
        "draft_id",
        "decision",
        "reviewed_by_account_id",
        "review_authority_assignment_id",
        "reviewed_at",
    ):
        op.create_index(
            f"ix_initial_planning_context_reviews_{column}",
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
    for column in (
        "reviewed_at",
        "review_authority_assignment_id",
        "reviewed_by_account_id",
        "decision",
        "draft_id",
    ):
        op.drop_index(
            f"ix_initial_planning_context_reviews_{column}",
            table_name="initial_planning_context_reviews",
        )
    op.drop_table("initial_planning_context_reviews")
    op.drop_table("initial_planning_context_evidence_claims")
    op.drop_table("initial_planning_context_observations")
    op.drop_table("initial_planning_context_prerequisites")
    for column in (
        "capability_estimate_id",
        "competency_floor_review_id",
        "competency_floor_id",
        "adaptation_id",
        "draft_id",
    ):
        op.drop_index(
            f"ix_initial_planning_candidate_contexts_{column}",
            table_name="initial_planning_candidate_contexts",
        )
    op.drop_table("initial_planning_candidate_contexts")
    for column in (
        "authored_at",
        "author_authority_assignment_id",
        "authored_by_account_id",
        "priority_policy_review_id",
        "priority_policy_id",
        "athlete_id",
    ):
        op.drop_index(
            f"ix_initial_planning_context_drafts_{column}",
            table_name="initial_planning_context_drafts",
        )
    op.drop_table("initial_planning_context_drafts")
