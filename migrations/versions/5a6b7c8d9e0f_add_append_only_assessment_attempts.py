"""add append-only incomplete assessment attempts

Revision ID: 5a6b7c8d9e0f
Revises: 4f5a6b7c8d9e
Create Date: 2026-09-25 21:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5a6b7c8d9e0f"
down_revision: str | None = "4f5a6b7c8d9e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assessment_attempts",
        sa.Column("athlete_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_selection_run_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_selection_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_definition_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_definition_review_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_eligibility_review_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_observation_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rule_version", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('incomplete', 'safety_stopped')",
            name="ck_assessment_attempt_status",
        ),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["assessment_selection_run_id"],
            ["assessment_selection_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_selection_id"], ["assessment_selections.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["assessment_definition_id"], ["assessment_definitions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["assessment_definition_review_id"],
            ["assessment_definition_reviews.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_eligibility_review_id"],
            ["assessment_eligibility_reviews.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["attempt_observation_id"], ["observations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_observation_id", name="uq_assessment_attempt_observation"),
    )
    for column_name in (
        "athlete_id",
        "assessment_selection_run_id",
        "assessment_selection_id",
        "assessment_definition_id",
        "assessment_definition_review_id",
        "assessment_eligibility_review_id",
        "attempt_observation_id",
        "status",
        "attempted_at",
    ):
        op.create_index(
            f"ix_assessment_attempts_{column_name}",
            "assessment_attempts",
            [column_name],
            unique=False,
        )


def downgrade() -> None:
    for column_name in (
        "attempted_at",
        "status",
        "attempt_observation_id",
        "assessment_eligibility_review_id",
        "assessment_definition_review_id",
        "assessment_definition_id",
        "assessment_selection_id",
        "assessment_selection_run_id",
        "athlete_id",
    ):
        op.drop_index(f"ix_assessment_attempts_{column_name}", table_name="assessment_attempts")
    op.drop_table("assessment_attempts")
