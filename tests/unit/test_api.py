from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

from agas_api.database import database_session_dependency
from agas_api.main import app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_health_reports_service_version() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "agas-api", "version": "0.1.0"}


def test_replanning_endpoint_reports_missing_review_without_creating_state(
    session: Session,
) -> None:
    def override_session() -> Iterator[Session]:
        yield session

    request_body = {
        "candidate_contexts": [
            {
                "adaptation_id": str(uuid4()),
                "competency_floor_id": str(uuid4()),
                "capability_estimate_id": str(uuid4()),
                "general_relevance": 0.5,
                "goal_relevance": 0.5,
                "prerequisite_value": 0.5,
                "expected_trainability": 0.5,
                "transfer_value": 0.5,
                "fatigue_cost": 0.5,
                "time_cost": 0.5,
                "interference_cost": 0.5,
            }
        ],
        "generated_at": datetime(2026, 8, 22, tzinfo=UTC).isoformat(),
        "review_after_days": 42,
    }
    app.dependency_overrides[database_session_dependency] = override_session
    try:
        response = TestClient(app).post(
            f"/v1/block-reviews/{uuid4()}/replan",
            json=request_body,
        )
        naive_time_response = TestClient(app).post(
            f"/v1/block-reviews/{uuid4()}/replan",
            json={**request_body, "generated_at": "2026-08-22T00:00:00"},
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "block review does not exist"}
    assert naive_time_response.status_code == 422


def test_block_creation_endpoint_reports_missing_strategy_and_rejects_naive_time(
    session: Session,
) -> None:
    def override_session() -> Iterator[Session]:
        yield session

    strategy_id = uuid4()
    request_body = {
        "resource_demand_ids": [str(uuid4())],
        "resource_allocation_policy_id": str(uuid4()),
        "weekly_budget_minutes": 120,
        "starts_on": "2026-08-24",
        "duration_weeks": 4,
        "constraints": ["fixture constraint"],
        "generated_at": datetime(2026, 8, 22, tzinfo=UTC).isoformat(),
    }
    app.dependency_overrides[database_session_dependency] = override_session
    try:
        response = TestClient(app).post(
            f"/v1/strategies/{strategy_id}/blocks",
            json=request_body,
        )
        naive_time_response = TestClient(app).post(
            f"/v1/strategies/{strategy_id}/blocks",
            json={**request_body, "generated_at": "2026-08-22T00:00:00"},
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "long-range strategy does not exist"}
    assert naive_time_response.status_code == 422


def test_resource_preparation_endpoint_validates_transport_before_persistence(
    session: Session,
) -> None:
    def override_session() -> Iterator[Session]:
        yield session

    strategy_id = uuid4()
    priority_id = uuid4()
    exercise_id = uuid4()
    request_body = {
        "mode": "active",
        "environment_id": str(uuid4()),
        "exercise_candidate_ids": [str(exercise_id)],
        "exercise_resolver_policy_id": str(uuid4()),
        "stimulus_specification": {
            "movement_patterns": ["knee_dominant"],
            "allowed_loading_types": ["external_load"],
            "allowed_lateralities": ["bilateral"],
            "minimum_loadability": "high",
            "required_velocity_characteristics": ["controlled"],
            "maximum_skill_complexity": "moderate",
            "maximum_impact_level": "low",
            "maximum_stability_demand": "moderate",
            "maximum_fatigue_cost": "moderate",
            "maximum_soreness_cost": "moderate",
            "source_observation_ids": [str(uuid4())],
            "evidence_claim_ids": [str(uuid4())],
            "rationale": "Synthetic transport fixture.",
        },
        "minimum_weekly_minutes": 30,
        "target_weekly_minutes": 60,
        "sessions_per_week": 2,
        "demand_rationale": "Synthetic transport fixture.",
        "demand_version": "fixture@1.0.0",
        "prepared_at": datetime(2026, 8, 22, tzinfo=UTC).isoformat(),
    }
    path = f"/v1/strategies/{strategy_id}/priorities/{priority_id}/resource-demands"
    app.dependency_overrides[database_session_dependency] = override_session
    try:
        missing_strategy_response = TestClient(app).post(path, json=request_body)
        naive_time_response = TestClient(app).post(
            path, json={**request_body, "prepared_at": "2026-08-22T00:00:00"}
        )
        duplicate_candidate_response = TestClient(app).post(
            path,
            json={
                **request_body,
                "exercise_candidate_ids": [str(exercise_id), str(exercise_id)],
            },
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert missing_strategy_response.status_code == 404
    assert missing_strategy_response.json() == {"detail": "long-range strategy does not exist"}
    assert naive_time_response.status_code == 422
    assert duplicate_candidate_response.status_code == 422


def test_weekly_plan_endpoint_reports_missing_block_and_rejects_naive_time(
    session: Session,
) -> None:
    def override_session() -> Iterator[Session]:
        yield session

    allocation_id = uuid4()
    source_observation_id = uuid4()
    evidence_claim_id = uuid4()
    request_body = {
        "prescriptions": [
            {
                "resource_allocation_id": str(allocation_id),
                "reason_for_inclusion": "Synthetic transport fixture.",
                "sets": 3,
                "repetitions_per_set": 5,
                "intensity_targets": [{"kind": "effort_rpe", "minimum": 6, "maximum": 8}],
                "rest_seconds": 120,
                "progression_rule_reference": "fixture:no-progression@1.0.0",
                "substitution_class": "fixture",
                "planned_duration_minutes": 30,
                "fatigue_cost": "moderate",
                "source_observation_ids": [str(source_observation_id)],
                "evidence_claim_ids": [str(evidence_claim_id)],
                "rule_version": "fixture@1.0.0",
            }
        ],
        "session_templates": [
            {
                "name": "Synthetic session",
                "items": [
                    {
                        "resource_allocation_id": str(allocation_id),
                        "order_index": 1,
                        "section": "primary",
                    }
                ],
                "sessions_per_week": 1,
                "planned_duration_minutes": 30,
                "fatigue_cost": "moderate",
                "source_observation_ids": [str(source_observation_id)],
                "evidence_claim_ids": [str(evidence_claim_id)],
                "rule_version": "fixture@1.0.0",
            }
        ],
        "availability": {
            "week_start": "2026-08-24",
            "windows": [],
            "source_observation_ids": [str(source_observation_id)],
            "rule_version": "fixture@1.0.0",
        },
        "scheduling_policy_id": str(uuid4()),
        "prepared_at": datetime(2026, 8, 22, tzinfo=UTC).isoformat(),
    }
    block_id = uuid4()
    path = f"/v1/blocks/{block_id}/weekly-plans"
    app.dependency_overrides[database_session_dependency] = override_session
    try:
        missing_block_response = TestClient(app).post(path, json=request_body)
        naive_time_response = TestClient(app).post(
            path, json={**request_body, "prepared_at": "2026-08-22T00:00:00"}
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert missing_block_response.status_code == 404
    assert missing_block_response.json() == {"detail": "block plan does not exist"}
    assert naive_time_response.status_code == 422


def test_progression_endpoint_reports_missing_execution_and_rejects_naive_time(
    session: Session,
) -> None:
    def override_session() -> Iterator[Session]:
        yield session

    execution_id = uuid4()
    prescription_id = uuid4()
    path = f"/v1/session-executions/{execution_id}/prescriptions/{prescription_id}/progression"
    request_body = {
        "progression_policy_id": str(uuid4()),
        "decided_at": datetime(2026, 8, 22, tzinfo=UTC).isoformat(),
    }
    app.dependency_overrides[database_session_dependency] = override_session
    try:
        missing_execution_response = TestClient(app).post(path, json=request_body)
        naive_time_response = TestClient(app).post(
            path, json={**request_body, "decided_at": "2026-08-22T00:00:00"}
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert missing_execution_response.status_code == 404
    assert missing_execution_response.json() == {"detail": "session execution does not exist"}
    assert naive_time_response.status_code == 422


def test_block_review_endpoint_reports_missing_block_and_rejects_naive_time(
    session: Session,
) -> None:
    def override_session() -> Iterator[Session]:
        yield session

    block_id = uuid4()
    prescription_id = uuid4()
    response_draft = {
        "adaptation_id": str(uuid4()),
        "prescription_ids": [str(prescription_id)],
        "baseline_capability_estimate_id": str(uuid4()),
        "followup_capability_estimate_id": str(uuid4()),
        "intervention_summary": "Synthetic transport fixture.",
        "measurement_uncertainty": "No operational measurement claim.",
        "contextual_factors": ["synthetic fixture"],
        "comparison_direction": "higher_is_better",
        "minimum_meaningful_change": 5,
    }
    request_body = {
        "block_review_policy_id": str(uuid4()),
        "response_drafts": [response_draft],
        "responses_calculated_at": datetime(2026, 9, 21, 14, 1, tzinfo=UTC).isoformat(),
        "reviewed_at": datetime(2026, 9, 21, 14, 2, tzinfo=UTC).isoformat(),
    }
    path = f"/v1/blocks/{block_id}/reviews"
    app.dependency_overrides[database_session_dependency] = override_session
    try:
        missing_block_response = TestClient(app).post(path, json=request_body)
        naive_time_response = TestClient(app).post(
            path, json={**request_body, "reviewed_at": "2026-09-21T14:02:00"}
        )
        duplicate_partition_response = TestClient(app).post(
            path,
            json={
                **request_body,
                "response_drafts": [
                    response_draft,
                    {**response_draft, "adaptation_id": str(uuid4())},
                ],
            },
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert missing_block_response.status_code == 404
    assert missing_block_response.json() == {"detail": "block plan does not exist"}
    assert naive_time_response.status_code == 422
    assert duplicate_partition_response.status_code == 422
