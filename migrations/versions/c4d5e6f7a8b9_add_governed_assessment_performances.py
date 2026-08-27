"""add governed assessment performances

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-08-27 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: str | None = "b3c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assessment_performances",
        sa.Column("athlete_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_selection_run_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_selection_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_definition_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_definition_review_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_eligibility_review_id", sa.Uuid(), nullable=False),
        sa.Column("result_observation_id", sa.Uuid(), nullable=False),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rule_version", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
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
            ["result_observation_id"], ["observations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_selection_id", name="uq_assessment_performance_selection"),
        sa.UniqueConstraint("result_observation_id", name="uq_assessment_performance_observation"),
    )
    for column_name in (
        "athlete_id",
        "assessment_selection_run_id",
        "assessment_selection_id",
        "assessment_definition_id",
        "assessment_definition_review_id",
        "assessment_eligibility_review_id",
        "result_observation_id",
        "performed_at",
    ):
        op.create_index(
            f"ix_assessment_performances_{column_name}",
            "assessment_performances",
            [column_name],
            unique=False,
        )


def downgrade() -> None:
    for column_name in (
        "performed_at",
        "result_observation_id",
        "assessment_eligibility_review_id",
        "assessment_definition_review_id",
        "assessment_definition_id",
        "assessment_selection_id",
        "assessment_selection_run_id",
        "athlete_id",
    ):
        op.drop_index(
            f"ix_assessment_performances_{column_name}",
            table_name="assessment_performances",
        )
    op.drop_table("assessment_performances")
