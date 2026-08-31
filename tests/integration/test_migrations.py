from pathlib import Path
from uuid import uuid4

import pytest
from agas_api.settings import get_settings
from agas_domain.persistence.models import Base
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_baseline_migration_matches_current_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = Path(f".test-migration-{uuid4().hex}.db").resolve()
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("AGAS_DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    engine = create_engine(database_url)
    try:
        command.upgrade(config, "head")

        inspector = inspect(engine)
        expected_tables = set(Base.metadata.tables)
        actual_tables = set(inspector.get_table_names())
        assert actual_tables == expected_tables | {"alembic_version"}
        assert "intensity_targets" in {
            column["name"] for column in inspector.get_columns("session_prescriptions")
        }
        assert "session_template_id" in {
            column["name"] for column in inspector.get_columns("planned_sessions")
        }
        assert "previous_template_id" in {
            column["name"] for column in inspector.get_columns("session_templates")
        }
        assert "previous_weekly_plan_id" in {
            column["name"] for column in inspector.get_columns("weekly_plans")
        }
        assert "scheduling_policy_review_id" in {
            column["name"] for column in inspector.get_columns("weekly_plans")
        }
        assert "session_item_executions" in actual_tables
        assert "laterality" in {column["name"] for column in inspector.get_columns("exercises")}
        assert "allowed_lateralities" in {
            column["name"] for column in inspector.get_columns("stimulus_requirements")
        }
        assert "laterality_weight" in {
            column["name"] for column in inspector.get_columns("exercise_resolver_policies")
        }
        assert "allow_partial_exercise_resolution" in {
            column["name"] for column in inspector.get_columns("weekly_scheduling_policies")
        }
        strategy_columns = {
            column["name"] for column in inspector.get_columns("long_range_strategies")
        }
        assert "supersedes_strategy_id" in strategy_columns
        assert "triggering_block_review_id" in strategy_columns
        assert "catalog_imports" in actual_tables
        assert "evidence_sources" in actual_tables
        assert "evidence_claim_sources" in actual_tables
        assert "accounts" in actual_tables
        assert "account_role_assignments" in actual_tables
        assert "athlete_ownerships" in actual_tables
        assert "athlete_safety_policy_assignments" in actual_tables
        assert "assessment_definition_reviews" in actual_tables
        assert "assessment_definition_review_evidence_claims" in actual_tables
        assert "measurement_schema" in {
            column["name"] for column in inspector.get_columns("assessment_definition_reviews")
        }
        assert "assessment_eligibility_reviews" in actual_tables
        assert "assessment_eligibility_review_observations" in actual_tables
        assert "assessment_selection_runs" in actual_tables
        assert "assessment_selection_run_items" in actual_tables
        assert "assessment_performances" in actual_tables
        assert "capability_estimation_policies" in actual_tables
        assert "capability_estimation_policy_evidence_claims" in actual_tables
        assert "competency_floor_reviews" in actual_tables
        assert "competency_floor_review_evidence_claims" in actual_tables
        assert "priority_policy_reviews" in actual_tables
        assert "priority_policy_review_evidence_claims" in actual_tables
        assert "initial_planning_context_drafts" in actual_tables
        assert "initial_planning_candidate_contexts" in actual_tables
        assert "initial_planning_context_prerequisites" in actual_tables
        assert "initial_planning_context_observations" in actual_tables
        assert "initial_planning_context_evidence_claims" in actual_tables
        assert "initial_planning_context_reviews" in actual_tables
        assert "weekly_scheduling_policy_reviews" in actual_tables
        assert "weekly_scheduling_policy_review_evidence_claims" in actual_tables
        assert "source_observation_id" in {
            column["name"] for column in inspector.get_columns("equipment_availability")
        }
        assert "source_weekly_plan_id" in {
            column["name"] for column in inspector.get_columns("weekly_availabilities")
        }
        assert any(
            constraint["name"] == "uq_weekly_availability_source_plan"
            for constraint in inspector.get_unique_constraints("weekly_availabilities")
        )
        prescription_revision_columns = {
            column["name"] for column in inspector.get_columns("session_prescription_revisions")
        }
        assert "planning_decision_record_id" in prescription_revision_columns
        assert any(
            constraint["name"] == "ck_prescription_revision_one_authorizer"
            for constraint in inspector.get_check_constraints("session_prescription_revisions")
        )
        estimate_columns = {
            column["name"] for column in inspector.get_columns("capability_estimates")
        }
        assert "capability_estimation_policy_id" in estimate_columns
        assert "triggering_assessment_performance_id" in estimate_columns
        assert "safety_policy_assignment_id" in {
            column["name"] for column in inspector.get_columns("session_safety_decisions")
        }
        assert "assessment_definition_review_id" in {
            column["name"] for column in inspector.get_columns("assessment_selections")
        }
        assert "assessment_eligibility_review_id" in {
            column["name"] for column in inspector.get_columns("assessment_selections")
        }
        assert any(
            constraint["name"] == "uq_account_issuer_subject"
            for constraint in inspector.get_unique_constraints("accounts")
        )
        evidence_source_constraints = inspector.get_unique_constraints("evidence_sources")
        assert any(
            constraint["name"] == "uq_evidence_source_identity_sequence"
            for constraint in evidence_source_constraints
        )
        assert any(
            constraint["name"] == "uq_evidence_source_superseded_once"
            for constraint in evidence_source_constraints
        )
        role_constraints = inspector.get_unique_constraints("account_role_assignments")
        assert any(
            constraint["name"] == "uq_account_role_assignment_sequence"
            for constraint in role_constraints
        )
        assert any(
            constraint["name"] == "uq_account_role_assignment_superseded_once"
            for constraint in role_constraints
        )
        assert any(
            "assessment_reviewer" in str(constraint.get("sqltext", ""))
            for constraint in inspector.get_check_constraints("account_role_assignments")
            if constraint["name"] == "ck_account_role_assignment_role"
        )
        assert any(
            constraint["name"] == "uq_athlete_owner"
            for constraint in inspector.get_unique_constraints("athlete_ownerships")
        )
        safety_assignment_constraints = inspector.get_unique_constraints(
            "athlete_safety_policy_assignments"
        )
        assert any(
            constraint["name"] == "uq_athlete_safety_assignment_sequence"
            for constraint in safety_assignment_constraints
        )
        assert any(
            constraint["name"] == "uq_safety_assignment_superseded_once"
            for constraint in safety_assignment_constraints
        )
        assessment_review_constraints = inspector.get_unique_constraints(
            "assessment_definition_reviews"
        )
        assert any(
            constraint["name"] == "uq_assessment_review_definition_sequence"
            for constraint in assessment_review_constraints
        )
        assert any(
            constraint["name"] == "uq_assessment_review_superseded_once"
            for constraint in assessment_review_constraints
        )
        eligibility_constraints = inspector.get_unique_constraints("assessment_eligibility_reviews")
        assert any(
            constraint["name"] == "uq_assessment_eligibility_athlete_sequence"
            for constraint in eligibility_constraints
        )
        assert any(
            constraint["name"] == "uq_assessment_eligibility_superseded_once"
            for constraint in eligibility_constraints
        )
        assert any(
            constraint["name"] == "uq_assessment_run_context_observation"
            for constraint in inspector.get_unique_constraints("assessment_selection_runs")
        )
        performance_constraints = inspector.get_unique_constraints("assessment_performances")
        assert any(
            constraint["name"] == "uq_assessment_performance_selection"
            for constraint in performance_constraints
        )
        assert any(
            constraint["name"] == "uq_assessment_performance_observation"
            for constraint in performance_constraints
        )
        policy_constraints = inspector.get_unique_constraints("capability_estimation_policies")
        assert any(
            constraint["name"] == "uq_capability_estimation_policy_definition_sequence"
            for constraint in policy_constraints
        )
        assert any(
            constraint["name"] == "uq_capability_estimation_policy_superseded_once"
            for constraint in policy_constraints
        )
        floor_review_constraints = inspector.get_unique_constraints("competency_floor_reviews")
        assert any(
            constraint["name"] == "uq_competency_floor_review_floor_sequence"
            for constraint in floor_review_constraints
        )
        assert any(
            constraint["name"] == "uq_competency_floor_review_superseded_once"
            for constraint in floor_review_constraints
        )
        priority_review_constraints = inspector.get_unique_constraints("priority_policy_reviews")
        assert any(
            constraint["name"] == "uq_priority_policy_review_policy_sequence"
            for constraint in priority_review_constraints
        )
        assert any(
            constraint["name"] == "uq_priority_policy_review_superseded_once"
            for constraint in priority_review_constraints
        )
        context_review_constraints = inspector.get_unique_constraints(
            "initial_planning_context_reviews"
        )
        assert any(
            constraint["name"] == "uq_initial_planning_context_review_draft"
            for constraint in context_review_constraints
        )
        scheduling_review_constraints = inspector.get_unique_constraints(
            "weekly_scheduling_policy_reviews"
        )
        assert any(
            constraint["name"] == "uq_weekly_scheduling_policy_review_policy_sequence"
            for constraint in scheduling_review_constraints
        )
        assert any(
            constraint["name"] == "uq_weekly_scheduling_policy_review_superseded_once"
            for constraint in scheduling_review_constraints
        )
        policy_index_names = {
            index["name"] for index in inspector.get_indexes("capability_estimation_policies")
        }
        assert {
            "ix_cap_estimation_policy_definition",
            "ix_cap_estimation_policy_definition_review",
            "ix_cap_estimation_policy_decision",
            "ix_cap_estimation_policy_supersedes",
            "ix_cap_estimation_policy_domain",
            "ix_cap_estimation_policy_reviewed_at",
        }.issubset(policy_index_names)
        assert any(
            constraint["name"] == "uq_assessment_estimate_performance_policy"
            for constraint in inspector.get_unique_constraints("capability_estimates")
        )
        assert any(
            constraint["name"] == "uq_strategy_triggering_block_review"
            for constraint in inspector.get_unique_constraints("long_range_strategies")
        )
        assert "uq_initial_strategy_athlete" in {
            index["name"] for index in inspector.get_indexes("long_range_strategies")
        }
        assert any(
            constraint["name"] == "uq_block_review_block_plan"
            for constraint in inspector.get_unique_constraints("block_reviews")
        )
        assert any(
            constraint["name"] == "uq_session_templates_previous_template"
            for constraint in inspector.get_unique_constraints("session_templates")
        )
        assert any(
            constraint["name"] == "uq_weekly_plans_previous_weekly_plan"
            for constraint in inspector.get_unique_constraints("weekly_plans")
        )

        command.downgrade(config, "base")
        assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    finally:
        engine.dispose()
        get_settings.cache_clear()
        database_path.unlink(missing_ok=True)
