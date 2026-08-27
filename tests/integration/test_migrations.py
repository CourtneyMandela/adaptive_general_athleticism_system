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
        assert "accounts" in actual_tables
        assert "athlete_ownerships" in actual_tables
        assert "athlete_safety_policy_assignments" in actual_tables
        assert "assessment_definition_reviews" in actual_tables
        assert "assessment_definition_review_evidence_claims" in actual_tables
        assert "assessment_eligibility_reviews" in actual_tables
        assert "assessment_eligibility_review_observations" in actual_tables
        assert "assessment_selection_runs" in actual_tables
        assert "assessment_selection_run_items" in actual_tables
        assert "assessment_performances" in actual_tables
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
        assert any(
            constraint["name"] == "uq_strategy_triggering_block_review"
            for constraint in inspector.get_unique_constraints("long_range_strategies")
        )
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
