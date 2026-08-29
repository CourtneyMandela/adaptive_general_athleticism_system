import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from agas_api.database import database_session_dependency
from agas_api.initial_planning import (
    CreateInitialStrategyCommand,
    InitialPlanningCandidateContext,
    InitialPlanningConflictError,
    InitialPlanningNotFoundError,
    InitialPlanningValidationError,
    PersistedInitialPlanningService,
)
from agas_api.initial_planning_admin import load_initial_planning_command
from agas_api.main import app
from agas_api.planning_governance_admin import (
    record_competency_floor_review,
    record_priority_policy_review,
)
from agas_api.planning_status import get_planning_status_projection
from agas_domain import (
    Adaptation,
    Applicability,
    AssessmentReviewDecision,
    Athlete,
    CapabilityDomain,
    CapabilityEstimate,
    ComparisonDirection,
    CompetencyFloor,
    CompetencyFloorReview,
    CompetencyStatus,
    Confidence,
    EvidenceClaim,
    EvidenceSourceIdentifier,
    EvidenceStrength,
    Observation,
    ObservationSource,
    PriorityPolicy,
    PriorityPolicyReview,
    Provenance,
)
from agas_domain.persistence.models import (
    CapabilityNeedRecord,
    CompetencyFloorReviewRecord,
    DecisionRecordRecord,
    ImmutableHistoricalRecordError,
    LongRangeStrategyRecord,
)
from agas_domain.persistence.repository import DomainRepository
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

NOW = datetime(2026, 8, 27, 16, 0, tzinfo=UTC)


def _evidence_claim() -> EvidenceClaim:
    return EvidenceClaim(
        claim="Software fixture: planning inputs retain evidence provenance.",
        domain="software_test",
        population="synthetic test fixture",
        intervention="not applicable",
        outcome="referential integrity",
        study_design="software test fixture",
        uncertainty="This is not a scientific training claim.",
        limitations=("Not operational evidence",),
        evidence_strength=EvidenceStrength.INSUFFICIENT,
        athlete_applicability=Applicability.UNKNOWN,
        applicability_notes="Used only to verify software provenance.",
        source_identifiers=(
            EvidenceSourceIdentifier(scheme="other", value="fixture:initial-planning"),
        ),
        reviewer="automated-test",
        claim_version="fixture@1.0.0",
    )


def _priority_policy() -> PriorityPolicy:
    return PriorityPolicy(
        deficit_weight=4,
        general_relevance_weight=1,
        goal_relevance_weight=1,
        prerequisite_value_weight=1,
        expected_trainability_weight=1,
        transfer_value_weight=1,
        fatigue_cost_weight=1,
        time_cost_weight=1,
        interference_cost_weight=1,
        cost_penalty=0.2,
        confidence_multipliers={
            Confidence.UNKNOWN: 0.0,
            Confidence.LOW: 0.5,
            Confidence.MODERATE: 0.75,
            Confidence.HIGH: 1.0,
        },
        develop_score_threshold=0.3,
        comparative_advantage_threshold=0.5,
        severe_deficit_threshold=0.25,
        max_develop_adaptations=2,
        policy_version="initial-planning-fixture@1.0.0",
    )


def _persist_inputs(
    session: Session,
    *,
    adaptation_domain: CapabilityDomain = CapabilityDomain.MAXIMUM_STRENGTH,
) -> tuple[
    Athlete,
    Observation,
    CapabilityEstimate,
    CompetencyFloor,
    Adaptation,
    PriorityPolicy,
    CompetencyFloorReview,
    PriorityPolicyReview,
]:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Initial planning athlete")
    claim = _evidence_claim()
    observation = Observation(
        athlete_id=athlete.id,
        observed_at=NOW - timedelta(hours=1),
        observation_type="fixture_strength_test",
        measurement=60,
        unit="fixture_unit",
        source=ObservationSource.TEST_RESULT,
        reliability=Confidence.MODERATE,
        context={"fixture": True},
        provenance=Provenance(
            recorded_by="automated-test",
            source_system="pytest",
            ingestion_method="fixture",
        ),
    )
    estimate = CapabilityEstimate(
        athlete_id=athlete.id,
        domain=CapabilityDomain.MAXIMUM_STRENGTH,
        estimate=60,
        unit_or_scale="fixture_unit",
        estimate_scope="assessment_specific:fixture_strength_test",
        confidence=Confidence.MODERATE,
        calculation_method="fixture calculation",
        source_observation_ids=(observation.id,),
        estimated_at=NOW - timedelta(minutes=30),
        valid_until=NOW + timedelta(days=30),
        rule_version="fixture-estimate@1.0.0",
    )
    floor = CompetencyFloor(
        domain=CapabilityDomain.MAXIMUM_STRENGTH,
        estimate_scope=estimate.estimate_scope,
        unit_or_scale=estimate.unit_or_scale,
        threshold=100,
        comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
        population="synthetic test population",
        applicability_notes="Software fixture only.",
        uncertainty="Not an operational scientific threshold.",
        evidence_claim_ids=(claim.id,),
        floor_version="fixture-floor@1.0.0",
    )
    adaptation = Adaptation(name="Fixture adaptation", domain=adaptation_domain)
    policy = _priority_policy()

    repository.add_athlete(athlete)
    repository.add_evidence_claim(claim)
    repository.add_observation(observation)
    session.flush()
    repository.add_capability_estimate(estimate)
    repository.add_competency_floor(floor)
    repository.add_adaptation(adaptation)
    repository.add_priority_policy(policy)
    session.flush()
    floor_review = CompetencyFloorReview(
        competency_floor_id=floor.id,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=1,
        evidence_claim_ids=(claim.id,),
        reviewed_at=NOW - timedelta(minutes=20),
        reviewed_by="automated-test-reviewer",
        applicability_rationale="Reviewed only for software behavior testing.",
        uncertainty="This approval is not operational training guidance.",
        review_version="fixture-floor-review@1.0.0",
    )
    policy_review = PriorityPolicyReview(
        priority_policy_id=policy.id,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=1,
        evidence_claim_ids=(claim.id,),
        reviewed_at=NOW - timedelta(minutes=20),
        reviewed_by="automated-test-reviewer",
        applicability_rationale="Reviewed only for software behavior testing.",
        uncertainty="This approval is not operational training guidance.",
        review_version="fixture-policy-review@1.0.0",
    )
    repository.add_competency_floor_review(floor_review)
    repository.add_priority_policy_review(policy_review)
    session.commit()
    return (
        athlete,
        observation,
        estimate,
        floor,
        adaptation,
        policy,
        floor_review,
        policy_review,
    )


def _command(
    observation: Observation,
    estimate: CapabilityEstimate,
    floor: CompetencyFloor,
    adaptation: Adaptation,
    policy: PriorityPolicy,
    floor_review: CompetencyFloorReview,
    policy_review: PriorityPolicyReview,
) -> CreateInitialStrategyCommand:
    return CreateInitialStrategyCommand(
        priority_policy_id=policy.id,
        priority_policy_review_id=policy_review.id,
        candidate_contexts=(
            InitialPlanningCandidateContext(
                adaptation_id=adaptation.id,
                competency_floor_id=floor.id,
                competency_floor_review_id=floor_review.id,
                capability_estimate_id=estimate.id,
                general_relevance=0.9,
                goal_relevance=0.8,
                prerequisite_value=0.7,
                expected_trainability=0.7,
                transfer_value=0.8,
                fatigue_cost=0.3,
                time_cost=0.3,
                interference_cost=0.2,
                source_observation_ids=(observation.id,),
                evidence_claim_ids=floor.evidence_claim_ids,
            ),
        ),
        generated_at=NOW,
        horizon_months=12,
        review_after_days=42,
        reviewed_by="automated-test-operator",
        applicability_rationale=(
            "Synthetic inputs were reviewed together for transaction and provenance testing."
        ),
        uncertainty="Software fixture values are not operational training guidance.",
    )


def test_operator_initial_planning_persists_need_strategy_and_decision_once(
    session: Session,
) -> None:
    athlete, observation, estimate, floor, adaptation, policy, floor_review, policy_review = (
        _persist_inputs(session)
    )
    command = _command(
        observation, estimate, floor, adaptation, policy, floor_review, policy_review
    )

    result = PersistedInitialPlanningService(session).execute(athlete.id, command)

    assert len(result.capability_needs) == 1
    assert result.capability_needs[0].status is CompetencyStatus.BELOW_FLOOR
    assert result.capability_needs[0].capability_estimate_id == estimate.id
    assert result.strategy.source_observation_ids == (observation.id,)
    assert result.strategy.source_capability_estimate_ids == (estimate.id,)
    assert result.strategy.competency_floor_ids == (floor.id,)
    assert result.strategy.evidence_claim_ids == floor.evidence_claim_ids
    assert result.strategy.supersedes_strategy_id is None
    assert result.strategy.triggering_block_review_id is None
    assert str(result.strategy.id) in result.decision_record.decision
    assert command.reviewed_by in result.decision_record.reason
    assert result.decision_record.uncertainty == command.uncertainty
    assert f"priority_policy:{policy.id}" in result.decision_record.evidence
    assert f"priority_policy_review:{policy_review.id}" in result.decision_record.evidence
    assert f"competency_floor_review:{floor_review.id}" in result.decision_record.evidence
    assert f"capability_estimate:{estimate.id}" in result.decision_record.evidence
    assert f"observation:{observation.id}" in result.decision_record.evidence

    with pytest.raises(InitialPlanningConflictError, match="already has"):
        PersistedInitialPlanningService(session).execute(athlete.id, command)

    assert session.scalar(select(func.count()).select_from(CapabilityNeedRecord)) == 1
    assert session.scalar(select(func.count()).select_from(LongRangeStrategyRecord)) == 1
    assert session.scalar(select(func.count()).select_from(DecisionRecordRecord)) == 1
    stored_decision = session.get(DecisionRecordRecord, result.decision_record.id)
    assert stored_decision is not None
    assert stored_decision.decision == result.decision_record.decision
    assert stored_decision.reason == result.decision_record.reason
    assert stored_decision.evidence == list(result.decision_record.evidence)
    assert stored_decision.uncertainty == command.uncertainty

    restored = DomainRepository(session).get_initial_long_range_strategy(athlete.id)
    assert restored is not None
    assert restored.id == result.strategy.id
    assert restored.source_observation_ids == (observation.id,)
    assert restored.source_capability_estimate_ids == (estimate.id,)


def test_athlete_api_does_not_expose_initial_strategy_writes(session: Session) -> None:
    athlete, observation, estimate, floor, adaptation, policy, floor_review, policy_review = (
        _persist_inputs(session)
    )
    command = _command(
        observation, estimate, floor, adaptation, policy, floor_review, policy_review
    )
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        response = TestClient(app).post(
            f"/v1/athletes/{athlete.id}/initial-strategy",
            json=command.model_dump(mode="json"),
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code == 404
    assert session.scalar(select(func.count()).select_from(CapabilityNeedRecord)) == 0
    assert session.scalar(select(func.count()).select_from(LongRangeStrategyRecord)) == 0
    assert session.scalar(select(func.count()).select_from(DecisionRecordRecord)) == 0


def test_operator_input_file_preserves_review_metadata(session: Session, tmp_path: Path) -> None:
    _, observation, estimate, floor, adaptation, policy, floor_review, policy_review = (
        _persist_inputs(session)
    )
    command = _command(
        observation, estimate, floor, adaptation, policy, floor_review, policy_review
    )
    input_path = tmp_path / "reviewed-initial-planning.json"
    input_path.write_text(json.dumps(command.model_dump(mode="json")), encoding="utf-8")

    restored = load_initial_planning_command(input_path)

    assert restored == command
    assert restored.reviewed_by == "automated-test-operator"
    assert restored.applicability_rationale == command.applicability_rationale
    assert restored.uncertainty == command.uncertainty


def test_operator_input_rejects_blank_review_identity(session: Session) -> None:
    _, observation, estimate, floor, adaptation, policy, floor_review, policy_review = (
        _persist_inputs(session)
    )
    payload = _command(
        observation, estimate, floor, adaptation, policy, floor_review, policy_review
    ).model_dump(mode="json")
    payload["reviewed_by"] = "   "

    with pytest.raises(ValueError, match="must not be blank"):
        CreateInitialStrategyCommand.model_validate(payload)


def test_planning_authority_reviews_round_trip_and_preserve_linear_history(
    session: Session,
) -> None:
    _, _, _, floor, _, policy, first_floor_review, first_policy_review = _persist_inputs(session)

    second_floor_review = record_competency_floor_review(
        session,
        competency_floor_id=floor.id,
        decision=AssessmentReviewDecision.NEEDS_REVISION,
        evidence_claim_ids=floor.evidence_claim_ids,
        reviewed_at=NOW + timedelta(minutes=1),
        reviewed_by="second-reviewer",
        applicability_rationale="The floor needs an applicability revision.",
        uncertainty="The synthetic threshold remains non-operational.",
        review_version="fixture-floor-review@1.1.0",
    )
    second_policy_review = record_priority_policy_review(
        session,
        priority_policy_id=policy.id,
        decision=AssessmentReviewDecision.REJECTED,
        evidence_claim_ids=floor.evidence_claim_ids,
        reviewed_at=NOW + timedelta(minutes=1),
        reviewed_by="second-reviewer",
        applicability_rationale="The policy is rejected for this fixture revision.",
        uncertainty="The synthetic weights remain non-operational.",
        review_version="fixture-policy-review@1.1.0",
    )

    repository = DomainRepository(session)
    assert repository.get_competency_floor_review(first_floor_review.id) == first_floor_review
    assert repository.get_current_competency_floor_review(floor.id) == second_floor_review
    assert repository.get_priority_policy_review(first_policy_review.id) == first_policy_review
    assert repository.get_current_priority_policy_review(policy.id) == second_policy_review
    assert second_floor_review.supersedes_review_id == first_floor_review.id
    assert second_policy_review.supersedes_review_id == first_policy_review.id

    stored = session.get(CompetencyFloorReviewRecord, first_floor_review.id)
    assert stored is not None
    stored.reviewed_by = "mutated-reviewer"
    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.commit()
    session.rollback()


def test_initial_strategy_requires_exact_current_approved_authority_reviews(
    session: Session,
) -> None:
    athlete, observation, estimate, floor, adaptation, policy, floor_review, policy_review = (
        _persist_inputs(session)
    )
    command = _command(
        observation, estimate, floor, adaptation, policy, floor_review, policy_review
    )
    replacement_floor_review = record_competency_floor_review(
        session,
        competency_floor_id=floor.id,
        decision=AssessmentReviewDecision.APPROVED,
        evidence_claim_ids=floor.evidence_claim_ids,
        reviewed_at=NOW - timedelta(minutes=10),
        reviewed_by="replacement-reviewer",
        applicability_rationale="Replacement approval for exact-review behavior testing.",
        uncertainty="Software fixture only.",
        review_version="fixture-floor-review@2.0.0",
    )

    with pytest.raises(InitialPlanningValidationError, match="exact current review"):
        PersistedInitialPlanningService(session).execute(athlete.id, command)

    current_command = command.model_copy(
        update={
            "candidate_contexts": (
                command.candidate_contexts[0].model_copy(
                    update={"competency_floor_review_id": replacement_floor_review.id}
                ),
            )
        }
    )
    rejected_policy_review = record_priority_policy_review(
        session,
        priority_policy_id=policy.id,
        decision=AssessmentReviewDecision.REJECTED,
        evidence_claim_ids=floor.evidence_claim_ids,
        reviewed_at=NOW - timedelta(minutes=5),
        reviewed_by="replacement-reviewer",
        applicability_rationale="Rejected to verify fail-closed initial planning.",
        uncertainty="Software fixture only.",
        review_version="fixture-policy-review@2.0.0",
    )
    current_command = current_command.model_copy(
        update={"priority_policy_review_id": rejected_policy_review.id}
    )

    with pytest.raises(InitialPlanningValidationError, match="approved priority policy"):
        PersistedInitialPlanningService(session).execute(athlete.id, current_command)

    assert session.scalar(select(func.count()).select_from(CapabilityNeedRecord)) == 0
    assert session.scalar(select(func.count()).select_from(LongRangeStrategyRecord)) == 0
    assert session.scalar(select(func.count()).select_from(DecisionRecordRecord)) == 0


def test_initial_strategy_rejects_cross_athlete_estimate_without_partial_writes(
    session: Session,
) -> None:
    athlete, observation, estimate, floor, adaptation, policy, floor_review, policy_review = (
        _persist_inputs(session)
    )
    other_athlete = Athlete(display_name="Other athlete")
    DomainRepository(session).add_athlete(other_athlete)
    session.commit()
    command = _command(
        observation, estimate, floor, adaptation, policy, floor_review, policy_review
    )
    forged = command.model_copy(
        update={
            "candidate_contexts": (
                command.candidate_contexts[0].model_copy(
                    update={"capability_estimate_id": estimate.id}
                ),
            )
        }
    )

    with pytest.raises(InitialPlanningValidationError, match="different athlete"):
        PersistedInitialPlanningService(session).execute(other_athlete.id, forged)

    assert session.scalar(select(func.count()).select_from(CapabilityNeedRecord)) == 0
    assert session.scalar(select(func.count()).select_from(LongRangeStrategyRecord)) == 0
    assert session.scalar(select(func.count()).select_from(DecisionRecordRecord)) == 0
    assert DomainRepository(session).get_initial_long_range_strategy(other_athlete.id) is None
    assert athlete.id != other_athlete.id


def test_initial_strategy_rolls_back_when_adaptation_and_need_domains_disagree(
    session: Session,
) -> None:
    athlete, observation, estimate, floor, adaptation, policy, floor_review, policy_review = (
        _persist_inputs(session, adaptation_domain=CapabilityDomain.AEROBIC_CAPACITY)
    )

    with pytest.raises(InitialPlanningValidationError, match="domains must match"):
        PersistedInitialPlanningService(session).execute(
            athlete.id,
            _command(
                observation,
                estimate,
                floor,
                adaptation,
                policy,
                floor_review,
                policy_review,
            ),
        )

    assert session.scalar(select(func.count()).select_from(CapabilityNeedRecord)) == 0
    assert session.scalar(select(func.count()).select_from(LongRangeStrategyRecord)) == 0
    assert session.scalar(select(func.count()).select_from(DecisionRecordRecord)) == 0


def test_initial_strategy_rejects_unknown_context_provenance_without_writes(
    session: Session,
) -> None:
    athlete, observation, estimate, floor, adaptation, policy, floor_review, policy_review = (
        _persist_inputs(session)
    )
    command = _command(
        observation, estimate, floor, adaptation, policy, floor_review, policy_review
    )
    unknown_evidence = uuid4()
    invalid = command.model_copy(
        update={
            "candidate_contexts": (
                command.candidate_contexts[0].model_copy(
                    update={"evidence_claim_ids": (unknown_evidence,)}
                ),
            )
        }
    )

    with pytest.raises(InitialPlanningNotFoundError, match=str(unknown_evidence)):
        PersistedInitialPlanningService(session).execute(athlete.id, invalid)

    assert session.scalar(select(func.count()).select_from(CapabilityNeedRecord)) == 0
    assert session.scalar(select(func.count()).select_from(LongRangeStrategyRecord)) == 0
    assert session.scalar(select(func.count()).select_from(DecisionRecordRecord)) == 0


def test_planning_status_distinguishes_missing_current_stale_and_created_states(
    session: Session,
) -> None:
    empty_athlete = Athlete(display_name="No estimate athlete")
    DomainRepository(session).add_athlete(empty_athlete)
    session.commit()

    empty = get_planning_status_projection(session, empty_athlete.id, NOW)
    assert empty.status == "capability_estimate_required"
    assert empty.capability_estimate_count == 0
    assert empty.initial_strategy is None

    athlete, observation, estimate, floor, adaptation, policy, floor_review, policy_review = (
        _persist_inputs(session)
    )
    current = get_planning_status_projection(session, athlete.id, NOW)
    assert current.status == "planning_context_review_required"
    assert current.capability_estimate_count == 1
    assert current.current_capability_estimate_count == 1
    assert current.stale_capability_estimate_count == 0
    assert current.approved_priority_policy_count == 1
    assert current.approved_compatible_competency_floor_count == 1
    assert current.covered_current_capability_estimate_count == 1
    assert current.uncovered_current_capability_estimate_count == 0
    assert [requirement.satisfied for requirement in current.requirements] == [True, True, False]

    stale = get_planning_status_projection(session, athlete.id, NOW + timedelta(days=31))
    assert stale.status == "capability_estimate_stale"
    assert stale.current_capability_estimate_count == 0
    assert stale.stale_capability_estimate_count == 1

    result = PersistedInitialPlanningService(session).execute(
        athlete.id,
        _command(
            observation,
            estimate,
            floor,
            adaptation,
            policy,
            floor_review,
            policy_review,
        ),
    )
    created = get_planning_status_projection(session, athlete.id, NOW)
    assert created.status == "resource_demand_preparation_required"
    assert created.initial_strategy is not None
    assert created.initial_strategy.strategy_id == result.strategy.id
    assert created.initial_strategy.priority_count == 1
    assert created.initial_strategy.rule_version == result.strategy.rule_version
    assert created.first_block_readiness is not None
    assert created.first_block_readiness.strategy_priority_count == 1
    assert created.first_block_readiness.priorities_with_resource_demand_count == 0
    assert created.first_block_readiness.block_eligible_priority_count == 0
    assert created.first_block_readiness.block_plan is None
    assert [requirement.satisfied for requirement in created.requirements] == [
        False,
        False,
        False,
        False,
    ]


def test_planning_status_api_is_owned_and_time_explicit(session: Session) -> None:
    athlete, _, _, _, _, _, _, _ = _persist_inputs(session)
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        response = TestClient(app).get(
            f"/v1/athletes/{athlete.id}/planning-status",
            params={"at": NOW.isoformat()},
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["athlete_id"] == str(athlete.id)
    assert payload["as_of"] == NOW.isoformat().replace("+00:00", "Z")
    assert payload["status"] == "planning_context_review_required"
    assert payload["approved_priority_policy_count"] == 1
    assert payload["approved_compatible_competency_floor_count"] == 1
    assert payload["projection_version"] == "athlete-planning-status-projection@1.3.0"


def test_planning_status_fails_closed_when_current_authority_reviews_are_not_approved(
    session: Session,
) -> None:
    athlete, _, _, floor, _, policy, _, _ = _persist_inputs(session)
    record_competency_floor_review(
        session,
        competency_floor_id=floor.id,
        decision=AssessmentReviewDecision.NEEDS_REVISION,
        evidence_claim_ids=floor.evidence_claim_ids,
        reviewed_at=NOW - timedelta(minutes=5),
        reviewed_by="readiness-reviewer",
        applicability_rationale="Withdraw the fixture floor approval for readiness testing.",
        uncertainty="Software fixture only.",
        review_version="fixture-floor-review@readiness-withdrawn",
    )
    record_priority_policy_review(
        session,
        priority_policy_id=policy.id,
        decision=AssessmentReviewDecision.REJECTED,
        evidence_claim_ids=floor.evidence_claim_ids,
        reviewed_at=NOW - timedelta(minutes=5),
        reviewed_by="readiness-reviewer",
        applicability_rationale="Withdraw the fixture policy approval for readiness testing.",
        uncertainty="Software fixture only.",
        review_version="fixture-policy-review@readiness-withdrawn",
    )

    projection = get_planning_status_projection(session, athlete.id, NOW)

    assert projection.status == "planning_authorities_required"
    assert projection.approved_priority_policy_count == 0
    assert projection.approved_compatible_competency_floor_count == 0
    assert projection.covered_current_capability_estimate_count == 0
    assert projection.uncovered_current_capability_estimate_count == 1
    assert [requirement.satisfied for requirement in projection.requirements] == [
        False,
        False,
        False,
    ]


def test_planning_status_does_not_restore_superseded_approval_before_future_review_time(
    session: Session,
) -> None:
    athlete, _, _, floor, _, _, _, _ = _persist_inputs(session)
    record_competency_floor_review(
        session,
        competency_floor_id=floor.id,
        decision=AssessmentReviewDecision.APPROVED,
        evidence_claim_ids=floor.evidence_claim_ids,
        reviewed_at=NOW + timedelta(hours=1),
        reviewed_by="future-reviewer",
        applicability_rationale="Future-dated replacement for temporal projection testing.",
        uncertainty="Software fixture only.",
        review_version="fixture-floor-review@future",
    )

    projection = get_planning_status_projection(session, athlete.id, NOW)

    assert projection.status == "planning_authorities_required"
    assert projection.approved_priority_policy_count == 1
    assert projection.approved_compatible_competency_floor_count == 0
    assert projection.covered_current_capability_estimate_count == 0
    assert projection.uncovered_current_capability_estimate_count == 1
