from datetime import UTC, datetime, timedelta
from typing import Any

import agas_api.assessment_estimation as assessment_estimation_module
import agas_api.assessment_performance as assessment_performance_module
import agas_api.assessment_selection as assessment_selection_module
import pytest
from agas_api.assessment_eligibility_admin import record_assessment_eligibility_review
from agas_api.assessment_performance import AssessmentPerformanceResult
from agas_api.assessment_selection import AssessmentSelectionRunResult
from agas_api.assessment_workflow import AssessmentWorkflowProjection
from agas_api.database import database_session_dependency
from agas_api.main import app
from agas_domain import (
    Applicability,
    AssessmentDefinition,
    AssessmentDefinitionReview,
    AssessmentEligibilityOutcome,
    AssessmentEligibilityReview,
    AssessmentIntensity,
    AssessmentMeasurementSchema,
    AssessmentMeasurementType,
    AssessmentReviewDecision,
    Athlete,
    CapabilityDomain,
    CapabilityEstimationPolicy,
    Confidence,
    Environment,
    Equipment,
    EquipmentAvailability,
    EvidenceClaim,
    EvidenceSourceIdentifier,
    EvidenceStrength,
    Observation,
    ObservationSource,
    Provenance,
)
from agas_domain.persistence.models import (
    AssessmentPerformanceRecord,
    AssessmentSelectionRecord,
    AssessmentSelectionRunRecord,
    CapabilityEstimateRecord,
    CapabilityEstimationPolicyRecord,
    ImmutableHistoricalRecordError,
    ObservationRecord,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy import func, select
from sqlalchemy.orm import Session

NOW = datetime(2026, 8, 27, 16, 0, tzinfo=UTC)


def provenance() -> Provenance:
    return Provenance(
        recorded_by="test-athlete",
        source_system="agas-test",
        ingestion_method="assessment-context-fixture",
    )


def source_observation(athlete: Athlete) -> Observation:
    return Observation(
        athlete_id=athlete.id,
        observed_at=NOW - timedelta(days=1),
        observation_type="operator_review_source_fixture",
        measurement={"fixture": True},
        source=ObservationSource.USER_REPORT,
        reliability=Confidence.LOW,
        provenance=provenance(),
    )


def evidence_fixture() -> EvidenceClaim:
    return EvidenceClaim(
        claim="Synthetic software fixture for assessment-run persistence tests.",
        domain="software_test_fixture",
        population="No athlete population; software fixture only.",
        intervention="No intervention.",
        outcome="Assessment-run transaction behavior.",
        study_design="software_test_fixture",
        uncertainty="Not scientific evidence and not operationally applicable.",
        evidence_strength=EvidenceStrength.INSUFFICIENT,
        athlete_applicability=Applicability.UNKNOWN,
        applicability_notes="Not applicable to athletes.",
        source_identifiers=(
            EvidenceSourceIdentifier(scheme="other", value="urn:agas:test:assessment-run"),
        ),
        reviewer="automated-test-fixture",
        claim_version="software-fixture@1.0.0",
    )


def definition(slug: str, *, requires_skill: bool = False) -> AssessmentDefinition:
    return AssessmentDefinition(
        slug=slug,
        name=slug.replace("_", " ").title(),
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        observation_type=f"{slug}_result",
        intensity=AssessmentIntensity.LOW,
        unit_or_scale="test_fixture_unit",
        protocol_version=f"{slug}@1.0.0",
        required_equipment_categories=("cycle_ergometer",),
        required_skill_tags=(("reviewed_fixture_skill",) if requires_skill else ()),
    )


def approve(
    repository: DomainRepository,
    assessment: AssessmentDefinition,
    evidence: EvidenceClaim,
    *,
    self_administered: bool = True,
    include_measurement_schema: bool = True,
) -> AssessmentDefinitionReview:
    review = AssessmentDefinitionReview(
        assessment_definition_id=assessment.id,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=1,
        protocol_instructions=("Follow the isolated software-test fixture protocol.",),
        result_entry_instructions="Enter the synthetic fixture value.",
        measurement_schema=(
            AssessmentMeasurementSchema(
                measurement_type=AssessmentMeasurementType.NUMBER,
                label="Synthetic fixture value",
                minimum=0,
                maximum=100,
                step=0.5,
                measurement_schema_version="fixture-measurement@1.0.0",
            )
            if include_measurement_schema
            else None
        ),
        recommended_reassessment_days=28,
        self_administered=self_administered,
        evidence_claim_ids=(evidence.id,),
        reviewed_at=NOW - timedelta(days=2),
        reviewer="automated-test-reviewer",
        applicability_notes="Software validation only; not applicable to an athlete.",
        uncertainty="This record does not approve a real assessment protocol.",
        review_version="assessment-review-fixture@1.0.0",
    )
    repository.add_assessment_definition_review(review)
    return review


def allow(
    repository: DomainRepository,
    athlete: Athlete,
    source: Observation,
    *,
    outcome: AssessmentEligibilityOutcome = AssessmentEligibilityOutcome.SELECTION_ALLOWED,
    valid_for_days: int = 7,
) -> AssessmentEligibilityReview:
    review = AssessmentEligibilityReview(
        athlete_id=athlete.id,
        outcome=outcome,
        sequence_number=1,
        source_observation_ids=(source.id,),
        reviewed_at=NOW - timedelta(hours=1),
        valid_until=NOW + timedelta(days=valid_for_days),
        reviewed_by="automated-test-reviewer",
        screening_process_reference="software-test-screening@1.0.0",
        rationale="Software fixture only; not an athlete screening decision.",
        uncertainty="This fixture has no operational applicability.",
        rule_version="assessment-eligibility-fixture@1.0.0",
    )
    repository.add_assessment_eligibility_review(review)
    return review


def setup_run_state(
    session: Session,
    *,
    eligibility_outcome: AssessmentEligibilityOutcome = (
        AssessmentEligibilityOutcome.SELECTION_ALLOWED
    ),
    self_administered: bool = True,
    include_measurement_schema: bool = True,
    include_deferred_definition: bool = True,
    eligibility_valid_for_days: int = 7,
) -> tuple[Athlete, Environment, AssessmentEligibilityReview]:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Assessment run athlete")
    environment = Environment(athlete_id=athlete.id, name="Test gym")
    cycle = Equipment(name="Synthetic cycle", category="cycle_ergometer")
    source = source_observation(athlete)
    evidence = evidence_fixture()
    first = definition("available_fixture")
    second = definition("skill_deferred_fixture", requires_skill=True)
    repository.add_athlete(athlete)
    repository.add_environment(environment)
    repository.add_equipment(cycle)
    repository.add_observation(source)
    repository.add_evidence_claim(evidence)
    assessments = (first, second) if include_deferred_definition else (first,)
    for assessment in assessments:
        repository.add_assessment_definition(assessment)
        approve(
            repository,
            assessment,
            evidence,
            self_administered=self_administered,
            include_measurement_schema=include_measurement_schema,
        )
    repository.add_equipment_availability(
        EquipmentAvailability(
            environment_id=environment.id,
            equipment_id=cycle.id,
            is_available=True,
            effective_from=NOW - timedelta(days=1),
            reason="software fixture",
        )
    )
    eligibility = allow(
        repository,
        athlete,
        source,
        outcome=eligibility_outcome,
        valid_for_days=eligibility_valid_for_days,
    )
    session.commit()
    return athlete, environment, eligibility


def request_body(environment: Environment, *, evaluated_at: datetime = NOW) -> dict[str, Any]:
    return {
        "environment_id": str(environment.id),
        "body_mass_kg": 78.5,
        "training_age_months_by_domain": {"aerobic_capacity": 6},
        "exercise_skill_tags": [],
        "recent_exposure_tags": [],
        "evaluated_at": evaluated_at.isoformat(),
        "reliability": "low",
        "provenance": provenance().model_dump(mode="json"),
    }


def test_owned_athlete_creates_a_provenance_complete_assessment_selection_run(
    session: Session,
) -> None:
    athlete, environment, eligibility = setup_run_state(session)
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        response = TestClient(app).post(
            f"/v1/athletes/{athlete.id}/assessment-runs", json=request_body(environment)
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code == 201
    result = AssessmentSelectionRunResult.model_validate(response.json())
    assert result.run.assessment_eligibility_review_id == eligibility.id
    assert result.run.context_observation_id == result.context_observation.id
    assert result.context_observation.source is ObservationSource.USER_REPORT
    availability_ids = [
        str(item.id)
        for item in DomainRepository(session).list_equipment_availability(environment.id)
    ]
    assert result.context_observation.measurement == {
        "body_mass_kg": 78.5,
        "training_age_months_by_domain": {"aerobic_capacity": 6},
        "exercise_skill_tags": [],
        "recent_exposure_tags": [],
        "environment_id": str(environment.id),
        "available_equipment_categories": ["cycle_ergometer"],
        "source_availability_ids": availability_ids,
        "assessment_eligibility_review_id": str(eligibility.id),
    }
    assert tuple(item.selection.decision.value for item in result.decisions) == (
        "selected",
        "deferred",
    )
    assert all(
        item.selection.assessment_eligibility_review_id == eligibility.id
        and item.selection.assessment_definition_review_id == item.definition_review.id
        and result.context_observation.id in item.selection.source_observation_ids
        for item in result.decisions
    )
    repository = DomainRepository(session)
    assert repository.get_assessment_selection_run(result.run.id) == result.run
    for item in result.decisions:
        assert repository.get_assessment_selection(item.selection.id) == item.selection


def test_assessment_workflow_projects_readiness_decisions_and_completion(
    session: Session, monkeypatch: MonkeyPatch
) -> None:
    athlete, environment, _eligibility = setup_run_state(session)
    workflow_path = f"/v1/athletes/{athlete.id}/assessment-workflow"
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        client = TestClient(app)
        ready_response = client.get(workflow_path, params={"at": NOW.isoformat()})
        run_response = client.post(
            f"/v1/athletes/{athlete.id}/assessment-runs", json=request_body(environment)
        )
        run_result = AssessmentSelectionRunResult.model_validate(run_response.json())
        selected = run_result.decisions[0].selection
        projected_response = client.get(workflow_path, params={"at": NOW.isoformat()})
        monkeypatch.setattr(
            assessment_performance_module, "_utc_now", lambda: NOW + timedelta(hours=1)
        )
        result_response = client.post(
            f"/v1/athletes/{athlete.id}/assessment-runs/{run_result.run.id}"
            f"/selections/{selected.id}/result",
            json=result_body(),
        )
        completed_response = client.get(
            workflow_path, params={"at": (NOW + timedelta(minutes=10)).isoformat()}
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert ready_response.status_code == 200
    ready = AssessmentWorkflowProjection.model_validate(ready_response.json())
    assert ready.status == "ready_to_start"
    assert ready.can_start_run is True
    assert ready.latest_run is None
    assert ready.approved_self_administered_protocol_count == 2
    assert run_response.status_code == 201
    assert projected_response.status_code == 200
    projected = AssessmentWorkflowProjection.model_validate(projected_response.json())
    assert projected.status == "result_entry_ready"
    assert projected.can_record_results is True
    assert projected.latest_run is not None
    assert tuple(item.result_status for item in projected.latest_run.decisions) == (
        "ready",
        "not_selected",
    )
    first = projected.latest_run.decisions[0]
    assert first.protocol_instructions == ("Follow the isolated software-test fixture protocol.",)
    assert first.result_entry_instructions == "Enter the synthetic fixture value."
    assert first.measurement_schema is not None
    assert first.measurement_schema.measurement_type is AssessmentMeasurementType.NUMBER
    assert first.evidence_claim_ids
    assert "reviewed_by" not in projected_response.text
    assert "screening_process_reference" not in projected_response.text
    assert result_response.status_code == 201
    assert completed_response.status_code == 200
    completed = AssessmentWorkflowProjection.model_validate(completed_response.json())
    assert completed.status == "reassessment_due"
    assert completed.can_record_results is False
    assert completed.can_start_run is True
    assert completed.due_protocol_count == 1
    assert completed.latest_run is not None
    assert completed.latest_run.decisions[0].result is not None
    assert completed.latest_run.decisions[0].result.measurement == 42.5


def test_completed_assessment_blocks_early_retesting_and_opens_when_due(
    session: Session, monkeypatch: MonkeyPatch
) -> None:
    athlete, environment, _eligibility = setup_run_state(
        session,
        include_deferred_definition=False,
        eligibility_valid_for_days=60,
    )
    monkeypatch.setattr(assessment_selection_module, "_utc_now", lambda: NOW + timedelta(days=60))
    workflow_path = f"/v1/athletes/{athlete.id}/assessment-workflow"
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        client = TestClient(app)
        run_response = client.post(
            f"/v1/athletes/{athlete.id}/assessment-runs", json=request_body(environment)
        )
        run_result = AssessmentSelectionRunResult.model_validate(run_response.json())
        selected = run_result.decisions[0].selection
        performed_at = NOW + timedelta(minutes=10)
        monkeypatch.setattr(
            assessment_performance_module, "_utc_now", lambda: performed_at + timedelta(hours=1)
        )
        result_response = client.post(
            f"/v1/athletes/{athlete.id}/assessment-runs/{run_result.run.id}"
            f"/selections/{selected.id}/result",
            json=result_body(),
        )
        completed_response = client.get(workflow_path, params={"at": performed_at.isoformat()})
        observation_count = session.scalar(select(func.count()).select_from(ObservationRecord))
        assert observation_count is not None
        early_response = client.post(
            f"/v1/athletes/{athlete.id}/assessment-runs",
            json=request_body(environment, evaluated_at=performed_at + timedelta(days=1)),
        )
        after_early_observation_count = session.scalar(
            select(func.count()).select_from(ObservationRecord)
        )
        due_at = performed_at + timedelta(days=28)
        due_workflow_response = client.get(workflow_path, params={"at": due_at.isoformat()})
        reassessment_response = client.post(
            f"/v1/athletes/{athlete.id}/assessment-runs",
            json=request_body(environment, evaluated_at=due_at),
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert run_response.status_code == 201
    assert run_result.run.rule_version == "assessment-selection-run@2.0.0"
    assert result_response.status_code == 201
    completed = AssessmentWorkflowProjection.model_validate(completed_response.json())
    assert completed.status == "reassessment_not_due"
    assert completed.can_start_run is False
    assert completed.due_protocol_count == 0
    assert completed.next_reassessment_at == due_at
    assert completed.latest_run is not None
    assert completed.latest_run.decisions[0].result is not None
    assert completed.latest_run.decisions[0].result.next_reassessment_at == due_at
    assert early_response.status_code == 409
    assert "no governed assessment protocol is due" in early_response.json()["detail"]
    assert after_early_observation_count == observation_count
    assert session.scalar(select(func.count()).select_from(ObservationRecord)) == (
        observation_count + 1
    )
    due_workflow = AssessmentWorkflowProjection.model_validate(due_workflow_response.json())
    assert due_workflow.status == "reassessment_due"
    assert due_workflow.can_start_run is True
    assert due_workflow.due_protocol_count == 1
    assert reassessment_response.status_code == 201
    reassessment = AssessmentSelectionRunResult.model_validate(reassessment_response.json())
    assert tuple(item.definition.id for item in reassessment.decisions) == (
        run_result.decisions[0].definition.id,
    )


def test_new_run_is_blocked_while_a_selected_result_is_pending(session: Session) -> None:
    athlete, environment, _eligibility = setup_run_state(session)
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        client = TestClient(app)
        first = client.post(
            f"/v1/athletes/{athlete.id}/assessment-runs", json=request_body(environment)
        )
        observation_count = session.scalar(select(func.count()).select_from(ObservationRecord))
        duplicate = client.post(
            f"/v1/athletes/{athlete.id}/assessment-runs", json=request_body(environment)
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert "awaiting completion" in duplicate.json()["detail"]
    assert session.scalar(select(func.count()).select_from(ObservationRecord)) == observation_count


def test_future_selection_time_cannot_bypass_reassessment_cadence(
    session: Session, monkeypatch: MonkeyPatch
) -> None:
    athlete, environment, _eligibility = setup_run_state(session, eligibility_valid_for_days=60)
    monkeypatch.setattr(assessment_selection_module, "_utc_now", lambda: NOW)
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        response = TestClient(app).post(
            f"/v1/athletes/{athlete.id}/assessment-runs",
            json=request_body(environment, evaluated_at=NOW + timedelta(days=28)),
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code == 422
    assert response.json()["detail"] == "evaluated_at cannot be in the future"


def test_assessment_workflow_exposes_honest_blocked_and_empty_states(session: Session) -> None:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Assessment workflow empty state")
    environment = Environment(athlete_id=athlete.id, name="Empty environment")
    source = source_observation(athlete)
    repository.add_athlete(athlete)
    repository.add_environment(environment)
    repository.add_observation(source)
    session.commit()
    path = f"/v1/athletes/{athlete.id}/assessment-workflow"
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        client = TestClient(app)
        missing_response = client.get(path, params={"at": NOW.isoformat()})
        allow(repository, athlete, source)
        session.commit()
        empty_response = client.get(path, params={"at": NOW.isoformat()})
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert missing_response.status_code == 200
    assert missing_response.json()["status"] == "eligibility_required"
    assert empty_response.status_code == 200
    assert empty_response.json()["status"] == "protocol_catalog_empty"
    assert empty_response.json()["can_start_run"] is False


def test_schema_less_approvals_are_not_operational_for_self_service(session: Session) -> None:
    athlete, environment, _eligibility = setup_run_state(session, include_measurement_schema=False)
    workflow_path = f"/v1/athletes/{athlete.id}/assessment-workflow"
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        client = TestClient(app)
        workflow_response = client.get(workflow_path, params={"at": NOW.isoformat()})
        run_response = client.post(
            f"/v1/athletes/{athlete.id}/assessment-runs", json=request_body(environment)
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert workflow_response.status_code == 200
    assert workflow_response.json()["status"] == "protocol_catalog_empty"
    assert workflow_response.json()["approved_self_administered_protocol_count"] == 0
    assert run_response.status_code == 409
    assert "measurement schemas" in run_response.json()["detail"]


def create_run(session: Session) -> tuple[Athlete, AssessmentSelectionRunResult]:
    athlete, environment, _eligibility = setup_run_state(session)
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        response = TestClient(app).post(
            f"/v1/athletes/{athlete.id}/assessment-runs", json=request_body(environment)
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)
    assert response.status_code == 201
    return athlete, AssessmentSelectionRunResult.model_validate(response.json())


def result_body(
    *, unit: str = "test_fixture_unit", measurement: int | float = 42.5
) -> dict[str, Any]:
    return {
        "performed_at": (NOW + timedelta(minutes=10)).isoformat(),
        "measurement": measurement,
        "unit": unit,
        "reliability": "moderate",
        "provenance": provenance().model_dump(mode="json"),
    }


def test_selected_assessment_records_one_direct_result_without_creating_an_estimate(
    session: Session, monkeypatch: MonkeyPatch
) -> None:
    athlete, run_result = create_run(session)
    selected = run_result.decisions[0].selection
    monkeypatch.setattr(assessment_performance_module, "_utc_now", lambda: NOW + timedelta(hours=1))
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        response = TestClient(app).post(
            f"/v1/athletes/{athlete.id}/assessment-runs/{run_result.run.id}"
            f"/selections/{selected.id}/result",
            json=result_body(),
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code == 201
    result = AssessmentPerformanceResult.model_validate(response.json())
    assert result.performance.assessment_selection_id == selected.id
    assert result.performance.assessment_definition_review_id == (
        selected.assessment_definition_review_id
    )
    assert result.performance.assessment_eligibility_review_id == (
        selected.assessment_eligibility_review_id
    )
    assert result.result_observation.source is ObservationSource.TEST_RESULT
    assert result.result_observation.measurement == 42.5
    assert result.result_observation.context["assessment_selection_run_id"] == str(
        run_result.run.id
    )
    repository = DomainRepository(session)
    assert repository.get_assessment_performance(result.performance.id) == result.performance
    assert repository.list_assessment_performances(athlete.id) == (result.performance,)
    assert repository.get_observation(result.result_observation.id) == result.result_observation
    assert session.scalar(select(func.count()).select_from(AssessmentPerformanceRecord)) == 1
    assert session.scalar(select(func.count()).select_from(ObservationRecord)) == 3
    performance_record = session.get(AssessmentPerformanceRecord, result.performance.id)
    assert performance_record is not None
    performance_record.rule_version = "silently-rewritten"
    with pytest.raises(ImmutableHistoricalRecordError):
        session.commit()
    session.rollback()
    assert repository.get_assessment_performance(result.performance.id) == result.performance


def test_duplicate_result_rolls_back_its_extra_observation(
    session: Session, monkeypatch: MonkeyPatch
) -> None:
    athlete, run_result = create_run(session)
    selected = run_result.decisions[0].selection
    monkeypatch.setattr(assessment_performance_module, "_utc_now", lambda: NOW + timedelta(hours=1))
    path = (
        f"/v1/athletes/{athlete.id}/assessment-runs/{run_result.run.id}"
        f"/selections/{selected.id}/result"
    )
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        client = TestClient(app)
        first = client.post(path, json=result_body())
        observation_count = session.scalar(select(func.count()).select_from(ObservationRecord))
        duplicate = client.post(path, json=result_body())
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert session.scalar(select(func.count()).select_from(ObservationRecord)) == observation_count
    assert session.scalar(select(func.count()).select_from(AssessmentPerformanceRecord)) == 1


def test_reviewed_policy_creates_one_traceable_capability_estimate(
    session: Session, monkeypatch: MonkeyPatch
) -> None:
    athlete, run_result = create_run(session)
    selected = run_result.decisions[0].selection
    monkeypatch.setattr(assessment_performance_module, "_utc_now", lambda: NOW + timedelta(hours=1))
    result_path = (
        f"/v1/athletes/{athlete.id}/assessment-runs/{run_result.run.id}"
        f"/selections/{selected.id}/result"
    )
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        client = TestClient(app)
        result_response = client.post(result_path, json=result_body())
        assert result_response.status_code == 201
        performance = AssessmentPerformanceResult.model_validate(result_response.json()).performance

        unavailable = client.get(f"/v1/athletes/{athlete.id}/assessment-workflow")
        assert unavailable.status_code == 200
        unavailable_result = unavailable.json()["latest_run"]["decisions"][0]["result"]
        assert unavailable_result["capability_estimate_status"] == "policy_unavailable"
        assert unavailable_result["capability_estimate"] is None

        repository = DomainRepository(session)
        definition_record = repository.get_assessment_definition(selected.assessment_definition_id)
        review = repository.get_current_assessment_definition_review(
            selected.assessment_definition_id
        )
        assert definition_record is not None
        assert review is not None
        policy = CapabilityEstimationPolicy(
            assessment_definition_id=definition_record.id,
            assessment_definition_review_id=review.id,
            decision=AssessmentReviewDecision.APPROVED,
            sequence_number=1,
            domain=definition_record.domain,
            observation_type=definition_record.observation_type,
            unit_or_scale=definition_record.unit_or_scale,
            calculation_method="latest-matching-observation",
            valid_for_days=28,
            multi_observation_window_days=90,
            evidence_claim_ids=review.evidence_claim_ids,
            reviewed_at=NOW,
            reviewed_by="automated-test-reviewer",
            applicability_notes="Software validation only.",
            uncertainty="Not an operational estimation policy.",
            rule_version="latest-matching-observation@1.0.0",
        )
        repository.add_capability_estimation_policy(policy)
        repository.add_observation(
            Observation(
                athlete_id=athlete.id,
                observed_at=NOW,
                observation_type=definition_record.observation_type,
                measurement=99,
                unit=definition_record.unit_or_scale,
                source=ObservationSource.USER_REPORT,
                reliability=Confidence.HIGH,
                provenance=provenance(),
            )
        )
        session.commit()

        ready = client.get(f"/v1/athletes/{athlete.id}/assessment-workflow")
        assert (
            ready.json()["latest_run"]["decisions"][0]["result"]["capability_estimate_status"]
            == "ready"
        )
        monkeypatch.setattr(
            assessment_estimation_module, "_utc_now", lambda: NOW + timedelta(hours=1)
        )
        estimate_path = (
            f"/v1/athletes/{athlete.id}/assessment-performances/{performance.id}"
            "/capability-estimate"
        )
        first = client.post(estimate_path)
        second = client.post(estimate_path)
        completed = client.get(f"/v1/athletes/{athlete.id}/assessment-workflow")
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert second.json()["estimate"]["id"] == first.json()["estimate"]["id"]
    assert first.json()["estimate"]["estimate"] == 42.5
    assert first.json()["estimate"]["confidence"] == "low"
    assert first.json()["estimate"]["source_observation_ids"] == [
        str(performance.result_observation_id)
    ]
    assert first.json()["estimate"]["capability_estimation_policy_id"] == str(policy.id)
    assert first.json()["estimate"]["triggering_assessment_performance_id"] == str(performance.id)
    assert session.scalar(select(func.count()).select_from(CapabilityEstimateRecord)) == 1
    assert session.scalar(select(func.count()).select_from(CapabilityEstimationPolicyRecord)) == 1
    completed_result = completed.json()["latest_run"]["decisions"][0]["result"]
    assert completed_result["measurement"] == 42.5
    assert completed_result["capability_estimate_status"] == "completed"
    assert completed_result["capability_estimate"]["estimate"] == 42.5
    assert completed_result["capability_estimate"]["policy_id"] == str(policy.id)

    policy_record = session.get(CapabilityEstimationPolicyRecord, policy.id)
    assert policy_record is not None
    policy_record.reviewed_by = "silently-rewritten"
    with pytest.raises(ImmutableHistoricalRecordError):
        session.commit()
    session.rollback()

    withdrawn = CapabilityEstimationPolicy(
        assessment_definition_id=policy.assessment_definition_id,
        assessment_definition_review_id=policy.assessment_definition_review_id,
        decision=AssessmentReviewDecision.REJECTED,
        sequence_number=2,
        supersedes_policy_id=policy.id,
        domain=policy.domain,
        observation_type=policy.observation_type,
        unit_or_scale=policy.unit_or_scale,
        calculation_method=policy.calculation_method,
        valid_for_days=policy.valid_for_days,
        multi_observation_window_days=policy.multi_observation_window_days,
        evidence_claim_ids=policy.evidence_claim_ids,
        reviewed_at=NOW + timedelta(hours=2),
        reviewed_by="automated-test-reviewer",
        applicability_notes="Software policy withdrawn for a regression fixture.",
        uncertainty="Not operational.",
        rule_version="latest-matching-observation@2.0.0",
    )
    repository.add_capability_estimation_policy(withdrawn)
    session.commit()
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        client = TestClient(app)
        blocked = client.post(estimate_path)
        withdrawn_projection = client.get(f"/v1/athletes/{athlete.id}/assessment-workflow")
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert blocked.status_code == 409
    assert (
        withdrawn_projection.json()["latest_run"]["decisions"][0]["result"][
            "capability_estimate_status"
        ]
        == "policy_superseded"
    )
    assert session.scalar(select(func.count()).select_from(CapabilityEstimateRecord)) == 1


def test_deferred_assessment_and_wrong_units_fail_without_result_history(
    session: Session, monkeypatch: MonkeyPatch
) -> None:
    athlete, run_result = create_run(session)
    selected = run_result.decisions[0].selection
    deferred = run_result.decisions[1].selection
    monkeypatch.setattr(assessment_performance_module, "_utc_now", lambda: NOW + timedelta(hours=1))
    base = f"/v1/athletes/{athlete.id}/assessment-runs/{run_result.run.id}/selections"
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        client = TestClient(app)
        deferred_response = client.post(f"{base}/{deferred.id}/result", json=result_body())
        wrong_unit_response = client.post(
            f"{base}/{selected.id}/result", json=result_body(unit="unsupported_unit")
        )
        future_body = result_body()
        future_body["performed_at"] = (NOW + timedelta(hours=2)).isoformat()
        future_response = client.post(f"{base}/{selected.id}/result", json=future_body)
        missing_measurement_body = result_body()
        missing_measurement_body["measurement"] = None
        missing_measurement_response = client.post(
            f"{base}/{selected.id}/result", json=missing_measurement_body
        )
        above_maximum_response = client.post(
            f"{base}/{selected.id}/result", json=result_body(measurement=101)
        )
        invalid_step_response = client.post(
            f"{base}/{selected.id}/result", json=result_body(measurement=42.3)
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert deferred_response.status_code == 409
    assert wrong_unit_response.status_code == 422
    assert future_response.status_code == 422
    assert missing_measurement_response.status_code == 422
    assert above_maximum_response.status_code == 422
    assert invalid_step_response.status_code == 422
    assert session.scalar(select(func.count()).select_from(AssessmentPerformanceRecord)) == 0
    assert session.scalar(select(func.count()).select_from(ObservationRecord)) == 2


def test_withdrawn_protocol_fails_closed_before_result_history(
    session: Session, monkeypatch: MonkeyPatch
) -> None:
    athlete, run_result = create_run(session)
    selected = run_result.decisions[0].selection
    repository = DomainRepository(session)
    current = repository.get_current_assessment_definition_review(selected.assessment_definition_id)
    assert current is not None
    repository.add_assessment_definition_review(
        AssessmentDefinitionReview(
            assessment_definition_id=selected.assessment_definition_id,
            decision=AssessmentReviewDecision.REJECTED,
            sequence_number=2,
            supersedes_review_id=current.id,
            protocol_instructions=current.protocol_instructions,
            result_entry_instructions=current.result_entry_instructions,
            measurement_schema=current.measurement_schema,
            self_administered=False,
            evidence_claim_ids=current.evidence_claim_ids,
            reviewed_at=NOW + timedelta(minutes=1),
            reviewer="automated-test-reviewer",
            applicability_notes="Withdrawn software fixture.",
            uncertainty="Not operational.",
            review_version="assessment-review-fixture@2.0.0",
        )
    )
    session.commit()
    monkeypatch.setattr(assessment_performance_module, "_utc_now", lambda: NOW + timedelta(hours=1))
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        response = TestClient(app).post(
            f"/v1/athletes/{athlete.id}/assessment-runs/{run_result.run.id}"
            f"/selections/{selected.id}/result",
            json=result_body(),
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code == 409
    assert session.scalar(select(func.count()).select_from(AssessmentPerformanceRecord)) == 0
    assert session.scalar(select(func.count()).select_from(ObservationRecord)) == 2


@pytest.mark.parametrize(
    "outcome",
    (
        AssessmentEligibilityOutcome.SELECTION_BLOCKED,
        AssessmentEligibilityOutcome.REVIEW_REQUIRED,
    ),
)
def test_non_allowed_eligibility_fails_before_writing_context(
    session: Session, outcome: AssessmentEligibilityOutcome
) -> None:
    athlete, environment, _ = setup_run_state(session, eligibility_outcome=outcome)
    counts_before = (
        session.scalar(select(func.count()).select_from(ObservationRecord)),
        session.scalar(select(func.count()).select_from(AssessmentSelectionRecord)),
        session.scalar(select(func.count()).select_from(AssessmentSelectionRunRecord)),
    )
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        response = TestClient(app).post(
            f"/v1/athletes/{athlete.id}/assessment-runs", json=request_body(environment)
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code == 409
    assert "does not allow" in response.json()["detail"]
    assert counts_before == (
        session.scalar(select(func.count()).select_from(ObservationRecord)),
        session.scalar(select(func.count()).select_from(AssessmentSelectionRecord)),
        session.scalar(select(func.count()).select_from(AssessmentSelectionRunRecord)),
    )


def test_professionally_administered_catalog_fails_closed(session: Session) -> None:
    athlete, environment, _ = setup_run_state(session, self_administered=False)
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        response = TestClient(app).post(
            f"/v1/athletes/{athlete.id}/assessment-runs", json=request_body(environment)
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "no approved self-administered assessment definitions with measurement schemas "
            "are available"
        )
    }


def test_late_run_persistence_failure_rolls_back_observation_and_selections(
    session: Session, monkeypatch: MonkeyPatch
) -> None:
    athlete, environment, _ = setup_run_state(session)
    counts_before = (
        session.scalar(select(func.count()).select_from(ObservationRecord)),
        session.scalar(select(func.count()).select_from(AssessmentSelectionRecord)),
    )

    def reject_run(_repository: DomainRepository, _run: object) -> None:
        raise DomainIntegrityError("synthetic late assessment-run failure")

    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        with monkeypatch.context() as context:
            context.setattr(DomainRepository, "add_assessment_selection_run", reject_run)
            response = TestClient(app).post(
                f"/v1/athletes/{athlete.id}/assessment-runs",
                json=request_body(environment),
            )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code == 422
    assert response.json() == {"detail": "synthetic late assessment-run failure"}
    assert counts_before == (
        session.scalar(select(func.count()).select_from(ObservationRecord)),
        session.scalar(select(func.count()).select_from(AssessmentSelectionRecord)),
    )


def test_operator_eligibility_review_is_idempotent_and_replacement_is_linear(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Eligibility review athlete")
    source = source_observation(athlete)
    repository.add_athlete(athlete)
    repository.add_observation(source)
    session.commit()

    def record(
        outcome: AssessmentEligibilityOutcome, reviewed_at: datetime
    ) -> tuple[AssessmentEligibilityReview, bool]:
        return record_assessment_eligibility_review(
            session,
            athlete_id=athlete.id,
            outcome=outcome,
            source_observation_ids=(source.id,),
            reviewed_at=reviewed_at,
            valid_until=NOW + timedelta(days=7),
            reviewed_by="operator-fixture",
            screening_process_reference="operator-fixture@1.0.0",
            rationale="Software validation only.",
            uncertainty="Not operational.",
        )

    first, created = record(AssessmentEligibilityOutcome.SELECTION_ALLOWED, NOW)
    repeated, repeated_created = record(
        AssessmentEligibilityOutcome.SELECTION_ALLOWED, NOW + timedelta(minutes=1)
    )
    replacement, replacement_created = record(
        AssessmentEligibilityOutcome.REVIEW_REQUIRED, NOW + timedelta(hours=1)
    )

    assert created is True
    assert repeated_created is False
    assert repeated == first
    assert replacement_created is True
    assert replacement.sequence_number == 2
    assert replacement.supersedes_review_id == first.id
    assert repository.get_current_assessment_eligibility_review(athlete.id) == replacement
