"""add immutable introductory exposure executions

Revision ID: 0a1b2c3d4e5f
Revises: f9c0d1e2f3a4
Create Date: 2026-09-21 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from agas_domain.persistence.types import UTCDateTime
from alembic import op

revision: str = "0a1b2c3d4e5f"
down_revision: str | None = "f9c0d1e2f3a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "introductory_exposure_executions",
        sa.Column("athlete_id", sa.Uuid(), nullable=False),
        sa.Column("exposure_need_id", sa.Uuid(), nullable=False),
        sa.Column("introductory_exposure_dose_id", sa.Uuid(), nullable=False),
        sa.Column("exposure_definition_id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("environment_id", sa.Uuid(), nullable=False),
        sa.Column("performance_observation_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("actual_sets", sa.Integer(), nullable=False),
        sa.Column("actual_dose", sa.Float(), nullable=False),
        sa.Column("dose_unit", sa.String(length=40), nullable=False),
        sa.Column("session_rpe", sa.Float(), nullable=True),
        sa.Column("pre_session_ready", sa.Boolean(), nullable=False),
        sa.Column("controlled_technique", sa.Boolean(), nullable=False),
        sa.Column("stop_condition_occurred", sa.Boolean(), nullable=False),
        sa.Column("qualifies_as_exposure_day", sa.Boolean(), nullable=False),
        sa.Column("started_at", UTCDateTime(timezone=True), nullable=False),
        sa.Column("ended_at", UTCDateTime(timezone=True), nullable=False),
        sa.Column("rule_version", sa.String(length=160), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", UTCDateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('completed', 'partial', 'stopped_safety')",
            name="ck_intro_exposure_execution_status",
        ),
        sa.CheckConstraint(
            "actual_sets >= 0 AND actual_dose >= 0",
            name="ck_intro_exposure_execution_actuals_nonnegative",
        ),
        sa.CheckConstraint(
            "session_rpe IS NULL OR (session_rpe >= 0 AND session_rpe <= 10)",
            name="ck_intro_exposure_execution_rpe_bounds",
        ),
        sa.CheckConstraint(
            "dose_unit IN ('repetitions', 'seconds')",
            name="ck_intro_exposure_execution_dose_unit",
        ),
        sa.CheckConstraint("ended_at >= started_at", name="ck_intro_exposure_execution_time_order"),
        sa.CheckConstraint(
            "qualifies_as_exposure_day = (status = 'completed' AND pre_session_ready "
            "AND controlled_technique AND NOT stop_condition_occurred)",
            name="ck_intro_exposure_execution_qualification",
        ),
        sa.CheckConstraint(
            "status != 'stopped_safety' OR stop_condition_occurred",
            name="ck_intro_exposure_execution_safety_stop",
        ),
        sa.CheckConstraint(
            "status != 'completed' OR (actual_dose > 0 AND session_rpe IS NOT NULL)",
            name="ck_intro_exposure_execution_completed_actuals",
        ),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["exposure_need_id"], ["exposure_needs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["introductory_exposure_dose_id"],
            ["introductory_exposure_doses.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["exposure_definition_id"], ["exposure_definitions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["performance_observation_id"], ["observations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "performance_observation_id", name="uq_intro_exposure_execution_observation"
        ),
    )
    for column in (
        "athlete_id",
        "exposure_need_id",
        "introductory_exposure_dose_id",
        "exposure_definition_id",
        "exercise_id",
        "environment_id",
        "performance_observation_id",
        "qualifies_as_exposure_day",
        "started_at",
        "ended_at",
    ):
        op.create_index(
            f"ix_intro_exposure_executions_{column}",
            "introductory_exposure_executions",
            [column],
            unique=False,
        )


def downgrade() -> None:
    for column in (
        "ended_at",
        "started_at",
        "qualifies_as_exposure_day",
        "performance_observation_id",
        "environment_id",
        "exercise_id",
        "exposure_definition_id",
        "introductory_exposure_dose_id",
        "exposure_need_id",
        "athlete_id",
    ):
        op.drop_index(
            f"ix_intro_exposure_executions_{column}",
            table_name="introductory_exposure_executions",
        )
    op.drop_table("introductory_exposure_executions")
