from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest
from agas_api.database import database_session_dependency
from agas_api.identity import AuthorizedRole, authenticated_principal_dependency
from agas_api.identity_admin import set_account_role
from agas_api.main import app
from agas_api.planning_governance_candidates import prepared_acsm_resistance_training_source
from agas_api.prepared_resource_demand import (
    CANDIDATE_VERSION,
    PreparedResourceDemandConflictError,
    PreparedResourceDemandProjector,
    RatifyPreparedResourceDemandCommand,
    ratify_prepared_resource_demand,
)
from agas_api.resource_governance_candidates import (
    CANDIDATE_ID as RESOURCE_AUTHORITY_CANDIDATE_ID,
)
from agas_api.resource_governance_candidates import (
    prepared_resource_governance_candidate,
)
from agas_domain import (
    AccountRole,
    AccountRoleStatus,
    Adaptation,
    AdaptationPlanningCandidate,
    Applicability,
    Athlete,
    CapabilityDomain,
    CapabilityEstimate,
    ComparisonDirection,
    CompetencyFloor,
    Confidence,
    DecisionRecord,
    Environment,
    EquipmentAvailability,
    EvidenceClaim,
    EvidenceClaimReview,
    EvidenceReviewDecision,
    EvidenceSourceIdentifier,
    EvidenceStrength,
    LongRangeStrategy,
    Observation,
    ObservationSource,
    PriorityPolicy,
    Provenance,
)
from agas_domain.persistence.models import AdaptationResourceDemandRecord
from agas_domain.persistence.repository import DomainRepository
from agas_planner import CompetencyFloorDetector, LongRangeStrategyPlanner
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

NOW = datetime.now(UTC).replace(microsecond=0)
ADAPTATION_ID = UUID("a0000000-0000-4000-8000-000000000004")


def _persist_ready_strategy(
    session: Session, *, chair_available: bool = True, floor_area_m2: float | None = 4
) -> tuple[LongRangeStrategy, AuthorizedRole]:
    repository = DomainRepository(session)
    athlete = Athlete(
        created_at=NOW - timedelta(days=2),
        display_name="Prepared resource athlete",
        date_of_birth=date(1991, 1, 1),
    )
    fixture_claim = EvidenceClaim(
        created_at=NOW - timedelta(days=2),
        claim="Software fixture for strategy persistence.",
        domain="software_test",
        population="synthetic fixture",
        intervention="not applicable",
        outcome="application behavior",
        study_design="software fixture",
        uncertainty="Not scientific evidence.",
        limitations=("Not operational evidence.",),
        evidence_strength=EvidenceStrength.INSUFFICIENT,
        athlete_applicability=Applicability.UNKNOWN,
        applicability_notes="Tests exact provenance only.",
        source_identifiers=(
            EvidenceSourceIdentifier(scheme="other", value="fixture:prepared-resource"),
        ),
        reviewer="automated-test",
        claim_version="fixture@1.0.0",
    )
    observation = Observation(
        created_at=NOW - timedelta(hours=2),
        athlete_id=athlete.id,
        observed_at=NOW - timedelta(hours=2),
        observation_type="thirty_second_chair_stand_repetitions",
        measurement=10,
        unit="repetitions",
        source=ObservationSource.TEST_RESULT,
        reliability=Confidence.LOW,
        context={"fixture": True},
        provenance=Provenance(
            recorded_by="automated-test",
            source_system="pytest",
            ingestion_method="fixture",
        ),
    )
    estimate = CapabilityEstimate(
        created_at=NOW - timedelta(hours=1),
        athlete_id=athlete.id,
        domain=CapabilityDomain.MUSCULAR_ENDURANCE,
        estimate=10,
        unit_or_scale="repetitions",
        estimate_scope="assessment_specific:thirty_second_chair_stand_repetitions",
        confidence=Confidence.LOW,
        calculation_method="latest-matching-observation",
        source_observation_ids=(observation.id,),
        estimated_at=NOW - timedelta(hours=1),
        valid_until=NOW + timedelta(days=28),
        rule_version="fixture-chair-stand-estimate@1.0.0",
    )
    floor = CompetencyFloor(
        created_at=NOW - timedelta(days=1),
        domain=CapabilityDomain.MUSCULAR_ENDURANCE,
        estimate_scope=estimate.estimate_scope,
        unit_or_scale="repetitions",
        threshold=11,
        comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
        population="Synthetic fixture.",
        applicability_notes="Software test only.",
        uncertainty="Not an operational floor.",
        evidence_claim_ids=(fixture_claim.id,),
        floor_version="fixture-floor@1.0.0",
    )
    adaptation = Adaptation(
        id=ADAPTATION_ID,
        created_at=NOW - timedelta(days=2),
        name="Muscular endurance",
        domain=CapabilityDomain.MUSCULAR_ENDURANCE,
    )
    policy = PriorityPolicy(
        created_at=NOW - timedelta(days=1),
        deficit_weight=1,
        general_relevance_weight=0,
        goal_relevance_weight=0,
        prerequisite_value_weight=0,
        expected_trainability_weight=0,
        transfer_value_weight=0,
        fatigue_cost_weight=0,
        time_cost_weight=0,
        interference_cost_weight=0,
        cost_penalty=0,
        confidence_multipliers={
            Confidence.UNKNOWN: 0,
            Confidence.LOW: 0.5,
            Confidence.MODERATE: 0.75,
            Confidence.HIGH: 1,
        },
        develop_score_threshold=0.01,
        comparative_advantage_threshold=1,
        severe_deficit_threshold=0.5,
        max_develop_adaptations=1,
        policy_version="fixture-deficit-only@1.0.0",
    )
    repository.add_athlete(athlete)
    repository.add_evidence_claim(fixture_claim)
    repository.add_observation(observation)
    session.flush()
    repository.add_capability_estimate(estimate)
    repository.add_competency_floor(floor)
    repository.add_adaptation(adaptation)
    repository.add_priority_policy(policy)
    session.flush()
    need = CompetencyFloorDetector().identify(
        athlete_id=athlete.id,
        floor=floor,
        estimate=estimate,
        identified_at=NOW - timedelta(minutes=30),
    )
    strategy = LongRangeStrategyPlanner().build(
        athlete_id=athlete.id,
        adaptations=(adaptation,),
        needs=(need,),
        candidates=(
            AdaptationPlanningCandidate(
                adaptation_id=adaptation.id,
                capability_need_id=need.id,
                general_relevance=0,
                goal_relevance=0,
                prerequisite_value=0,
                expected_trainability=0,
                transfer_value=0,
                fatigue_cost=0,
                time_cost=0,
                interference_cost=0,
                safe_to_train=True,
                source_observation_ids=(observation.id,),
                evidence_claim_ids=(fixture_claim.id,),
            ),
        ),
        policy=policy,
        generated_at=NOW - timedelta(minutes=30),
        horizon_months=12,
        review_after_days=28,
    )
    repository.add_capability_need(need)
    session.flush()
    repository.add_long_range_strategy(strategy)

    resource = prepared_resource_governance_candidate()
    release = resource.release
    repository.add_evidence_source(prepared_acsm_resistance_training_source())
    repository.add_evidence_claim(release.claim)
    session.flush()
    repository.add_evidence_claim_review(
        EvidenceClaimReview(
            created_at=NOW - timedelta(minutes=20),
            evidence_claim_id=release.claim.id,
            decision=EvidenceReviewDecision.APPROVED,
            sequence_number=1,
            reviewed_at=NOW - timedelta(minutes=20),
            reviewer="automated-test",
            **release.evidence_review_content,
        )
    )
    repository.add_equipment(release.equipment)
    session.flush()
    repository.add_exercise(release.exercise)
    repository.add_exercise_resolver_policy(release.resolver_policy)
    repository.add_resource_allocation_policy(release.allocation_policy)
    repository.add_decision_record(
        DecisionRecord(
            id=RESOURCE_AUTHORITY_CANDIDATE_ID,
            created_at=NOW - timedelta(minutes=20),
            decision="Ratified exact resource fixture.",
            reason="Prepared resource-demand integration fixture.",
            alternatives_considered=("No fixture.",),
            evidence=(f"candidate_content_digest:{resource.presentation.content_digest}",),
            uncertainty="Software test only.",
            decision_version="fixture-resource-authority@1.0.0",
            decided_on=NOW.date(),
        )
    )
    environment = Environment(
        created_at=NOW - timedelta(days=1),
        athlete_id=athlete.id,
        name="Home",
        space_constraints=({"floor_area_m2": floor_area_m2} if floor_area_m2 is not None else {}),
    )
    repository.add_environment(environment)
    session.flush()
    repository.add_equipment_availability(
        EquipmentAvailability(
            created_at=NOW - timedelta(minutes=10),
            environment_id=environment.id,
            equipment_id=release.equipment.id,
            is_available=chair_available,
            effective_from=NOW - timedelta(minutes=10),
            reason="Synthetic current availability.",
        )
    )
    session.commit()
    account, assignment, _, _ = set_account_role(
        session,
        issuer="urn:agas:development",
        subject="prepared-resource-reviewer",
        role=AccountRole.PLANNING_REVIEWER,
        status=AccountRoleStatus.ACTIVE,
        assigned_at=NOW - timedelta(days=1),
        rationale="Authorize prepared-resource testing.",
    )
    authority = AuthorizedRole(
        account_id=account.id,
        assignment_id=assignment.id,
        role=assignment.role,
        assigned_at=assignment.assigned_at,
    )
    return strategy, authority


def test_projection_blocks_unknown_or_insufficient_environment_facts(session: Session) -> None:
    strategy, authority = _persist_ready_strategy(
        session, chair_available=False, floor_area_m2=None
    )

    projection = PreparedResourceDemandProjector(session).project(strategy.id, authority, NOW)

    assert projection.status == "blocked"
    assert any("stable chair" in item for item in projection.blockers)
    assert any("2 m²" in item for item in projection.blockers)


def test_candidate_is_exact_content_addressed_and_not_a_dose(session: Session) -> None:
    strategy, authority = _persist_ready_strategy(session)

    first = PreparedResourceDemandProjector(session).project(strategy.id, authority, NOW)
    second = PreparedResourceDemandProjector(session).project(
        strategy.id, authority, NOW + timedelta(seconds=5)
    )

    assert first.status == "available"
    candidate = first.candidates[0]
    assert second.candidates[0].candidate_id == candidate.candidate_id
    assert second.candidates[0].content_digest == candidate.content_digest
    assert candidate.expected_resolution_status.value == "full"
    assert candidate.exercise_name == "Chair sit-to-stand"
    assert candidate.sessions_per_week == 2
    assert candidate.per_session_scheduling_minutes == 5
    assert "not an exercise prescription" in candidate.dose_boundary
    assert "session still requires" in candidate.safety_boundary


def test_ratification_is_idempotent_and_preserves_exact_lineage(session: Session) -> None:
    strategy, authority = _persist_ready_strategy(session)
    candidate = (
        PreparedResourceDemandProjector(session).project(strategy.id, authority, NOW).candidates[0]
    )
    command = RatifyPreparedResourceDemandCommand(
        candidate_version=CANDIDATE_VERSION,
        content_digest=candidate.content_digest,
        approval_attestation=True,
    )

    first = ratify_prepared_resource_demand(
        session, strategy.id, candidate.candidate_id, command, authority
    )
    second = ratify_prepared_resource_demand(
        session, strategy.id, candidate.candidate_id, command, authority
    )

    assert first.created is True
    assert second.created is False
    assert first.result == second.result
    assert first.result.resource_demand.id == candidate.identities.resource_demand_id
    assert first.result.stimulus_requirement is not None
    assert first.result.exercise_resolution is not None
    assert first.result.exercise_resolution.status.value == "full"
    assert candidate.content_digest in first.result.decision_record.reason
    assert session.scalar(select(func.count()).select_from(AdaptationResourceDemandRecord)) == 1


def test_stale_digest_cannot_create_resource_history(session: Session) -> None:
    strategy, authority = _persist_ready_strategy(session)
    candidate = (
        PreparedResourceDemandProjector(session).project(strategy.id, authority, NOW).candidates[0]
    )

    with pytest.raises(PreparedResourceDemandConflictError, match="content changed"):
        ratify_prepared_resource_demand(
            session,
            strategy.id,
            candidate.candidate_id,
            RatifyPreparedResourceDemandCommand(
                candidate_version=CANDIDATE_VERSION,
                content_digest=f"sha256:{'0' * 64}",
                approval_attestation=True,
            ),
            authority,
        )

    assert session.scalar(select(func.count()).select_from(AdaptationResourceDemandRecord)) == 0


def test_endpoints_require_reviewer_and_accept_digest_only(session: Session) -> None:
    strategy, _authority = _persist_ready_strategy(session)

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    try:
        client = TestClient(app)
        unauthenticated = client.get(
            f"/v1/operator/strategies/{strategy.id}/prepared-resource-demands"
        )
        projected = client.get(
            f"/v1/operator/strategies/{strategy.id}/prepared-resource-demands",
            params={"at": NOW.isoformat()},
            headers={"Authorization": "Bearer dev.prepared-resource-reviewer"},
        )
        candidate = projected.json()["candidates"][0]
        ratified = client.post(
            f"/v1/operator/strategies/{strategy.id}/prepared-resource-demands/"
            f"{candidate['candidate_id']}/ratifications",
            headers={"Authorization": "Bearer dev.prepared-resource-reviewer"},
            json={
                "candidate_version": candidate["candidate_version"],
                "content_digest": candidate["content_digest"],
                "approval_attestation": True,
            },
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert unauthenticated.status_code == 401
    assert projected.status_code == 200
    assert ratified.status_code == 201
    assert ratified.json()["result"]["resource_demand"]["sessions_per_week"] == 2
