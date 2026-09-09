from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from agas_api.database import database_session_dependency
from agas_api.identity import AuthorizedRole, authenticated_principal_dependency
from agas_api.identity_admin import set_account_role
from agas_api.main import app
from agas_api.planning_governance_candidates import (
    CANDIDATE_VERSION,
    PlanningGovernanceCandidateConflictError,
    RatifyPlanningGovernanceCandidateCommand,
    list_planning_governance_candidates,
    ratify_planning_governance_candidate,
)
from agas_domain import AccountRole, AccountRoleStatus, Confidence, PriorityPolicy
from agas_domain.persistence.repository import DomainRepository
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

NOW = datetime(2026, 9, 9, 15, 0, tzinfo=UTC)
ACCOUNT_ID = UUID("10000000-0000-0000-0000-000000000001")
ASSIGNMENT_ID = UUID("20000000-0000-0000-0000-000000000001")


def _authority() -> AuthorizedRole:
    return AuthorizedRole(
        account_id=ACCOUNT_ID,
        assignment_id=ASSIGNMENT_ID,
        role=AccountRole.PLANNING_REVIEWER,
        assigned_at=NOW - timedelta(days=1),
    )


def _command(session: Session) -> tuple[UUID, RatifyPlanningGovernanceCandidateCommand]:
    candidate = list_planning_governance_candidates(session, projected_at=NOW).items[0].candidate
    return candidate.candidate_id, RatifyPlanningGovernanceCandidateCommand(
        candidate_version=CANDIDATE_VERSION,
        content_digest=candidate.content_digest,
        approval_attestation=True,
    )


def test_candidate_exposes_policy_scope_and_uncertainty(session: Session) -> None:
    projection = list_planning_governance_candidates(session, projected_at=NOW)

    assert projection.projection_version == "planning-governance-candidates@1.0.0"
    assert len(projection.items) == 1
    item = projection.items[0]
    assert item.status == "available"
    assert item.candidate.slug == "owner_alpha_conservative_priority_policy"
    assert item.candidate.content_digest.startswith("sha256:")
    assert any("weights" in value for value in item.candidate.does_not_establish)
    assert any("two adaptations" in value for value in item.candidate.operational_choices)
    assert any("competency floor" in value for value in item.candidate.unresolved_limitations)
    assert item.candidate.evidence[0].source_url == ("https://pubmed.ncbi.nlm.nih.gov/41843416/")


def test_exact_candidate_ratification_is_atomic_and_idempotent(session: Session) -> None:
    candidate_id, command = _command(session)

    first = ratify_planning_governance_candidate(
        session, candidate_id, command, _authority(), ratified_at=NOW
    )
    second = ratify_planning_governance_candidate(
        session, candidate_id, command, _authority(), ratified_at=NOW + timedelta(minutes=1)
    )
    repository = DomainRepository(session)
    decision = repository.get_decision_record(candidate_id)
    projection = list_planning_governance_candidates(
        session, projected_at=NOW + timedelta(minutes=1)
    )

    assert first.created_source is True
    assert first.created_claim is True
    assert first.created_evidence_review is True
    assert first.created_policy is True
    assert first.created_policy_review is True
    assert first.decision_record_created is True
    assert first.policy.max_develop_adaptations == 2
    assert first.policy.confidence_multipliers[Confidence.UNKNOWN] == 0
    assert first.policy_review.reviewed_by == f"account:{ACCOUNT_ID}"
    assert second.decision_record_created is False
    assert second.policy == first.policy
    assert projection.items[0].status == "ratified"
    assert projection.items[0].ratified_at == NOW
    assert decision is not None
    assert f"candidate_content_digest:{command.content_digest}" in decision.evidence


def test_candidate_rejects_stale_digest_without_persisting(session: Session) -> None:
    candidate_id, command = _command(session)
    stale = command.model_copy(update={"content_digest": f"sha256:{'0' * 64}"})

    with pytest.raises(PlanningGovernanceCandidateConflictError, match="refresh and review"):
        ratify_planning_governance_candidate(
            session, candidate_id, stale, _authority(), ratified_at=NOW
        )

    assert DomainRepository(session).get_decision_record(candidate_id) is None


def test_ratification_rolls_back_partial_records_on_policy_collision(session: Session) -> None:
    candidate_id, command = _command(session)
    repository = DomainRepository(session)
    repository.add_priority_policy(
        PriorityPolicy(
            id=UUID("98000000-0000-4000-8000-000000000001"),
            created_at=NOW - timedelta(days=2),
            deficit_weight=1,
            general_relevance_weight=1,
            goal_relevance_weight=1,
            prerequisite_value_weight=1,
            expected_trainability_weight=1,
            transfer_value_weight=1,
            fatigue_cost_weight=1,
            time_cost_weight=1,
            interference_cost_weight=1,
            cost_penalty=0,
            confidence_multipliers={level: 1 for level in Confidence},
            develop_score_threshold=0.5,
            comparative_advantage_threshold=0.5,
            severe_deficit_threshold=0.5,
            max_develop_adaptations=1,
            policy_version="conflicting-fixture@1.0.0",
        )
    )
    session.commit()

    with pytest.raises(PlanningGovernanceCandidateConflictError, match="differs"):
        ratify_planning_governance_candidate(
            session, candidate_id, command, _authority(), ratified_at=NOW
        )

    assert repository.get_evidence_source(UUID("90000000-0000-4000-8000-000000000003")) is None
    assert repository.get_evidence_claim(UUID("91000000-0000-4000-8000-000000000003")) is None
    assert repository.get_decision_record(candidate_id) is None


def test_candidate_endpoints_require_planning_reviewer_role(session: Session) -> None:
    for subject, role in (
        ("assessment-only", AccountRole.ASSESSMENT_REVIEWER),
        ("planning-reviewer", AccountRole.PLANNING_REVIEWER),
    ):
        set_account_role(
            session,
            issuer="urn:agas:development",
            subject=subject,
            role=role,
            status=AccountRoleStatus.ACTIVE,
            assigned_at=NOW - timedelta(days=1),
            rationale="Planning candidate authorization.",
        )

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    try:
        client = TestClient(app)
        unauthenticated = client.get("/v1/operator/planning-governance/candidates")
        forbidden = client.get(
            "/v1/operator/planning-governance/candidates",
            headers={"Authorization": "Bearer dev.assessment-only"},
        )
        allowed = client.get(
            "/v1/operator/planning-governance/candidates",
            headers={"Authorization": "Bearer dev.planning-reviewer"},
        )
        item = allowed.json()["items"][0]["candidate"]
        ratified = client.post(
            f"/v1/operator/planning-governance/candidates/{item['candidate_id']}/ratifications",
            headers={"Authorization": "Bearer dev.planning-reviewer"},
            json={
                "candidate_version": item["candidate_version"],
                "content_digest": item["content_digest"],
                "approval_attestation": True,
            },
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert unauthenticated.status_code == 401
    assert forbidden.status_code == 403
    assert allowed.status_code == 200
    assert ratified.status_code == 201
    assert ratified.json()["policy"]["policy_version"] == (
        "owner-alpha-conservative-priority@1.0.0"
    )
