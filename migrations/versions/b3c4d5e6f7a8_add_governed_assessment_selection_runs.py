"""add governed assessment selection runs

Revision ID: b3c4d5e6f7a8
Revises: a2c3d4e5f6b7
Create Date: 2026-08-27 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: str | None = "a2c3d4e5f6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assessment_eligibility_reviews",
        sa.Column("athlete_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("supersedes_review_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", sa.String(length=160), nullable=False),
        sa.Column("screening_process_reference", sa.String(length=160), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=False),
        sa.Column("rule_version", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('selection_allowed', 'selection_blocked', 'review_required')",
            name="ck_assessment_eligibility_outcome",
        ),
        sa.CheckConstraint(
            "sequence_number >= 1", name="ck_assessment_eligibility_sequence_positive"
        ),
        sa.CheckConstraint(
            "valid_until > reviewed_at", name="ck_assessment_eligibility_valid_window"
        ),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["supersedes_review_id"],
            ["assessment_eligibility_reviews.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "athlete_id",
            "sequence_number",
            name="uq_assessment_eligibility_athlete_sequence",
        ),
        sa.UniqueConstraint(
            "supersedes_review_id", name="uq_assessment_eligibility_superseded_once"
        ),
    )
    for column_name in (
        "athlete_id",
        "outcome",
        "supersedes_review_id",
        "reviewed_at",
        "valid_until",
    ):
        op.create_index(
            f"ix_assessment_eligibility_reviews_{column_name}",
            "assessment_eligibility_reviews",
            [column_name],
            unique=False,
        )

    op.create_table(
        "assessment_eligibility_review_observations",
        sa.Column("eligibility_review_id", sa.Uuid(), nullable=False),
        sa.Column("observation_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["eligibility_review_id"],
            ["assessment_eligibility_reviews.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["observation_id"], ["observations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("eligibility_review_id", "observation_id"),
        sa.UniqueConstraint(
            "eligibility_review_id",
            "position",
            name="uq_assessment_eligibility_observation_order",
        ),
    )

    with op.batch_alter_table("assessment_selections") as batch_op:
        batch_op.add_column(sa.Column("assessment_eligibility_review_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_assessment_selection_eligibility_review",
            "assessment_eligibility_reviews",
            ["assessment_eligibility_review_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(
            "ix_assessment_selections_assessment_eligibility_review_id",
            ["assessment_eligibility_review_id"],
            unique=False,
        )

    op.create_table(
        "assessment_selection_runs",
        sa.Column("athlete_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_eligibility_review_id", sa.Uuid(), nullable=False),
        sa.Column("environment_id", sa.Uuid(), nullable=False),
        sa.Column("context_observation_id", sa.Uuid(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rule_version", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["assessment_eligibility_review_id"],
            ["assessment_eligibility_reviews.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["context_observation_id"], ["observations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("context_observation_id", name="uq_assessment_run_context_observation"),
    )
    for column_name in (
        "athlete_id",
        "assessment_eligibility_review_id",
        "environment_id",
        "context_observation_id",
        "evaluated_at",
    ):
        op.create_index(
            f"ix_assessment_selection_runs_{column_name}",
            "assessment_selection_runs",
            [column_name],
            unique=False,
        )

    op.create_table(
        "assessment_selection_run_items",
        sa.Column("assessment_run_id", sa.Uuid(), nullable=False),
        sa.Column("selection_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["assessment_run_id"], ["assessment_selection_runs.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["selection_id"], ["assessment_selections.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("assessment_run_id", "selection_id"),
        sa.UniqueConstraint(
            "assessment_run_id", "position", name="uq_assessment_run_selection_order"
        ),
        sa.UniqueConstraint("selection_id", name="uq_assessment_selection_one_run"),
    )


def downgrade() -> None:
    op.drop_table("assessment_selection_run_items")
    for column_name in (
        "evaluated_at",
        "context_observation_id",
        "environment_id",
        "assessment_eligibility_review_id",
        "athlete_id",
    ):
        op.drop_index(
            f"ix_assessment_selection_runs_{column_name}",
            table_name="assessment_selection_runs",
        )
    op.drop_table("assessment_selection_runs")

    with op.batch_alter_table("assessment_selections") as batch_op:
        batch_op.drop_index("ix_assessment_selections_assessment_eligibility_review_id")
        batch_op.drop_constraint("fk_assessment_selection_eligibility_review", type_="foreignkey")
        batch_op.drop_column("assessment_eligibility_review_id")

    op.drop_table("assessment_eligibility_review_observations")
    for column_name in (
        "valid_until",
        "reviewed_at",
        "supersedes_review_id",
        "outcome",
        "athlete_id",
    ):
        op.drop_index(
            f"ix_assessment_eligibility_reviews_{column_name}",
            table_name="assessment_eligibility_reviews",
        )
    op.drop_table("assessment_eligibility_reviews")
