"""add governed capability estimation

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-08-27 23:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: str | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "capability_estimation_policies",
        sa.Column("assessment_definition_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_definition_review_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("supersedes_policy_id", sa.Uuid(), nullable=True),
        sa.Column("domain", sa.String(length=80), nullable=False),
        sa.Column("observation_type", sa.String(length=120), nullable=False),
        sa.Column("unit_or_scale", sa.String(length=80), nullable=False),
        sa.Column("calculation_method", sa.String(length=160), nullable=False),
        sa.Column("valid_for_days", sa.Integer(), nullable=False),
        sa.Column("multi_observation_window_days", sa.Integer(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", sa.String(length=160), nullable=False),
        sa.Column("applicability_notes", sa.Text(), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=False),
        sa.Column("rule_version", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "decision IN ('approved', 'needs_revision', 'rejected')",
            name="ck_capability_estimation_policy_decision",
        ),
        sa.CheckConstraint(
            "sequence_number >= 1", name="ck_capability_estimation_policy_sequence_positive"
        ),
        sa.CheckConstraint(
            "valid_for_days >= 1", name="ck_capability_estimation_validity_positive"
        ),
        sa.CheckConstraint(
            "multi_observation_window_days >= 1",
            name="ck_capability_estimation_window_positive",
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
            ["supersedes_policy_id"],
            ["capability_estimation_policies.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assessment_definition_id",
            "sequence_number",
            name="uq_capability_estimation_policy_definition_sequence",
        ),
        sa.UniqueConstraint(
            "supersedes_policy_id", name="uq_capability_estimation_policy_superseded_once"
        ),
    )
    policy_indexes = {
        "assessment_definition_id": "ix_cap_estimation_policy_definition",
        "assessment_definition_review_id": "ix_cap_estimation_policy_definition_review",
        "decision": "ix_cap_estimation_policy_decision",
        "supersedes_policy_id": "ix_cap_estimation_policy_supersedes",
        "domain": "ix_cap_estimation_policy_domain",
        "reviewed_at": "ix_cap_estimation_policy_reviewed_at",
    }
    for column_name, index_name in policy_indexes.items():
        op.create_index(
            index_name,
            "capability_estimation_policies",
            [column_name],
            unique=False,
        )
    op.create_table(
        "capability_estimation_policy_evidence_claims",
        sa.Column("capability_estimation_policy_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_claim_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["capability_estimation_policy_id"],
            ["capability_estimation_policies.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["evidence_claim_id"], ["evidence_claims.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("capability_estimation_policy_id", "evidence_claim_id"),
        sa.UniqueConstraint(
            "capability_estimation_policy_id",
            "position",
            name="uq_capability_estimation_policy_evidence_order",
        ),
    )

    with op.batch_alter_table("capability_estimates") as batch_op:
        batch_op.add_column(sa.Column("capability_estimation_policy_id", sa.Uuid(), nullable=True))
        batch_op.add_column(
            sa.Column("triggering_assessment_performance_id", sa.Uuid(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_capability_estimates_policy",
            "capability_estimation_policies",
            ["capability_estimation_policy_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_capability_estimates_triggering_performance",
            "assessment_performances",
            ["triggering_assessment_performance_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_check_constraint(
            "ck_assessment_estimate_lineage_complete",
            "(capability_estimation_policy_id IS NULL) = "
            "(triggering_assessment_performance_id IS NULL)",
        )
        batch_op.create_unique_constraint(
            "uq_assessment_estimate_performance_policy",
            ["triggering_assessment_performance_id", "capability_estimation_policy_id"],
        )
        batch_op.create_index(
            "ix_capability_estimates_capability_estimation_policy_id",
            ["capability_estimation_policy_id"],
        )
        batch_op.create_index(
            "ix_capability_estimates_triggering_assessment_performance_id",
            ["triggering_assessment_performance_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("capability_estimates") as batch_op:
        batch_op.drop_index("ix_capability_estimates_triggering_assessment_performance_id")
        batch_op.drop_index("ix_capability_estimates_capability_estimation_policy_id")
        batch_op.drop_constraint("uq_assessment_estimate_performance_policy", type_="unique")
        batch_op.drop_constraint("ck_assessment_estimate_lineage_complete", type_="check")
        batch_op.drop_constraint(
            "fk_capability_estimates_triggering_performance", type_="foreignkey"
        )
        batch_op.drop_constraint("fk_capability_estimates_policy", type_="foreignkey")
        batch_op.drop_column("triggering_assessment_performance_id")
        batch_op.drop_column("capability_estimation_policy_id")

    op.drop_table("capability_estimation_policy_evidence_claims")
    for index_name in reversed(
        (
            "ix_cap_estimation_policy_definition",
            "ix_cap_estimation_policy_definition_review",
            "ix_cap_estimation_policy_decision",
            "ix_cap_estimation_policy_supersedes",
            "ix_cap_estimation_policy_domain",
            "ix_cap_estimation_policy_reviewed_at",
        )
    ):
        op.drop_index(index_name, table_name="capability_estimation_policies")
    op.drop_table("capability_estimation_policies")
