from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest
from agas_api.database import database_session_dependency
from agas_api.identity import AuthorizedRole, authenticated_principal_dependency
from agas_api.identity_admin import set_account_role
from agas_api.main import app
from agas_api.prepared_initial_planning_context import (
    CANDIDATE_VERSION,
    PreparedInitialPlanningContextConflictError,
    PreparedInitialPlanningContextProjector,
    RatifyPreparedInitialPlanningContextCommand,
    ratify_prepared_initial_planning_context,
)
from agas_domain import (
    AccountRole,
    AccountRoleStatus,
    Adaptation,
    Applicability,
    AssessmentReviewDecision,
    Athlete,
    CapabilityDomain,
    CapabilityEstimate,
    ComparisonDirection,
    CompetencyFloor,
    CompetencyFloorReview,
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
from agas_domain.persistence.models import InitialPlanningContextDraftRecord
from agas_domain.persistence.repository import DomainRepository
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

NOW = datetime.now(UTC).replace(microsecond=0)
ADAPTATION_ID = UUID("a0000000-0000-4000-8000-000000000004")


def _persist_ready_path(session: Session) -> tuple[Athlete, AuthorizedRole]:
    repository = DomainRepository(session)
    athlete = Athlete(
        created_at=NOW - timedelta(days=2),
        display_name="Prepared context athlete",
        date_of_birth=date(1991, 1, 1),
    )
    claim = EvidenceClaim(
        created_at=NOW - timedelta(days=2),
        claim="Software fixture for a prepared planning path.",
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
            EvidenceSourceIdentifier(scheme="other", value="fixture:prepared-context"),
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
        population="Synthetic age-compatible fixture.",
        minimum_age_years=30,
        maximum_age_years=39,
        applicability_notes="Software test only.",
        uncertainty="Not an operational floor.",
        evidence_claim_ids=(claim.id,),
        floor_version="chair-stand-age-30-39-lower-reference-floor@1.0.0",
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
        policy_version="owner-alpha-deficit-only-priority@1.0.0",
    )
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
        created_at=NOW - timedelta(hours=12),
        competency_floor_id=floor.id,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=1,
        evidence_claim_ids=(claim.id,),
        reviewed_at=NOW - timedelta(hours=12),
        reviewed_by="automated-test",
        applicability_rationale="Synthetic exact floor review.",
        uncertainty="Software test only.",
        review_version="fixture-floor-review@1.0.0",
    )
    policy_review = PriorityPolicyReview(
        created_at=NOW - timedelta(hours=12),
        priority_policy_id=policy.id,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=1,
        evidence_claim_ids=(claim.id,),
        reviewed_at=NOW - timedelta(hours=12),
        reviewed_by="automated-test",
        applicability_rationale="Synthetic exact policy review.",
        uncertainty="Software test only.",
        review_version="fixture-policy-review@1.0.0",
    )
    repository.add_competency_floor_review(floor_review)
    repository.add_priority_policy_review(policy_review)
    session.commit()
    account, assignment, _, _ = set_account_role(
        session,
        issuer="urn:agas:development",
        subject="prepared-context-reviewer",
        role=AccountRole.PLANNING_REVIEWER,
        status=AccountRoleStatus.ACTIVE,
        assigned_at=NOW - timedelta(days=1),
        rationale="Authorize prepared-context testing.",
    )
    return athlete, AuthorizedRole(
        account_id=account.id,
        assignment_id=assignment.id,
        role=assignment.role,
        assigned_at=assignment.assigned_at,
    )


def test_projection_prepares_only_governed_deficit_and_explicit_unused_values(
    session: Session,
) -> None:
    athlete, authority = _persist_ready_path(session)

    projection = PreparedInitialPlanningContextProjector(session).project(
        athlete.id, authority, NOW
    )

    assert projection.status == "available"
    assert projection.blockers == ()
    candidate = projection.candidate
    assert candidate is not None
    assert candidate.expected_priority_state == "develop"
    assert candidate.expected_priority_score == pytest.approx((1 / 11) * 0.5)
    assert candidate.candidate_context.safe_to_train is True
    assert candidate.candidate_context.prerequisites_met is True
    assert candidate.candidate_context.source_observation_ids
    assert all(
        component.value == 0 and component.treatment == "unused"
        for component in candidate.components[:8]
    )
    assert (
        next(
            component.value
            for component in candidate.components
            if component.field == "safe_to_train"
        )
        is True
    )
    assert "not medical clearance" in candidate.safety_boundary
    assert "not because" in candidate.applicability_rationale


def test_ratification_is_content_addressed_and_idempotent(session: Session) -> None:
    athlete, authority = _persist_ready_path(session)
    candidate = (
        PreparedInitialPlanningContextProjector(session)
        .project(athlete.id, authority, NOW)
        .candidate
    )
    assert candidate is not None
    command = RatifyPreparedInitialPlanningContextCommand(
        candidate_version=CANDIDATE_VERSION,
        content_digest=candidate.content_digest,
        approval_attestation=True,
    )

    first = ratify_prepared_initial_planning_context(
        session, athlete.id, candidate.candidate_id, command, authority
    )
    second = ratify_prepared_initial_planning_context(
        session, athlete.id, candidate.candidate_id, command, authority
    )

    assert first.created is True
    assert second.created is False
    assert first.draft.id == candidate.candidate_id
    assert second.draft == first.draft
    assert candidate.content_digest in first.draft.applicability_rationale
    assert first.draft.candidate_contexts == (candidate.candidate_context,)
    assert session.scalar(select(func.count()).select_from(InitialPlanningContextDraftRecord)) == 1


def test_stale_digest_cannot_create_a_draft(session: Session) -> None:
    athlete, authority = _persist_ready_path(session)
    candidate = (
        PreparedInitialPlanningContextProjector(session)
        .project(athlete.id, authority, NOW)
        .candidate
    )
    assert candidate is not None

    with pytest.raises(PreparedInitialPlanningContextConflictError, match="content changed"):
        ratify_prepared_initial_planning_context(
            session,
            athlete.id,
            candidate.candidate_id,
            RatifyPreparedInitialPlanningContextCommand(
                candidate_version=CANDIDATE_VERSION,
                content_digest=f"sha256:{'0' * 64}",
                approval_attestation=True,
            ),
            authority,
        )

    assert session.scalar(select(func.count()).select_from(InitialPlanningContextDraftRecord)) == 0


def test_prepared_context_endpoints_require_role_and_preserve_exact_transport(
    session: Session,
) -> None:
    athlete, _authority = _persist_ready_path(session)

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    try:
        client = TestClient(app)
        unauthenticated = client.get(
            f"/v1/operator/athletes/{athlete.id}/prepared-initial-planning-context"
        )
        projected = client.get(
            f"/v1/operator/athletes/{athlete.id}/prepared-initial-planning-context",
            params={"at": NOW.isoformat()},
            headers={"Authorization": "Bearer dev.prepared-context-reviewer"},
        )
        candidate = projected.json()["candidate"]
        ratified = client.post(
            f"/v1/operator/athletes/{athlete.id}/prepared-initial-planning-context/"
            f"{candidate['candidate_id']}/ratifications",
            headers={"Authorization": "Bearer dev.prepared-context-reviewer"},
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
    assert candidate["candidate_context"]["general_relevance"] == 0
    assert candidate["expected_priority_state"] == "develop"
    assert ratified.status_code == 201
    assert ratified.json()["draft"]["id"] == candidate["candidate_id"]
