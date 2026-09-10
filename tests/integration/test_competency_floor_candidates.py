from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from agas_api.competency_floor_candidates import (
    CANDIDATE_VERSION,
    CompetencyFloorCandidateConflictError,
    RatifyCompetencyFloorCandidateCommand,
    _candidate_registry,
    list_competency_floor_candidates,
    ratify_competency_floor_candidate,
)
from agas_api.database import database_session_dependency
from agas_api.identity import AuthorizedRole, authenticated_principal_dependency
from agas_api.identity_admin import set_account_role
from agas_api.main import app
from agas_domain import (
    AccountRole,
    AccountRoleStatus,
    CapabilityDomain,
    ComparisonDirection,
)
from agas_domain.persistence.repository import DomainRepository
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

NOW = datetime(2026, 9, 10, 15, 0, tzinfo=UTC)
ACCOUNT_ID = UUID("10000000-0000-0000-0000-000000000001")
ASSIGNMENT_ID = UUID("20000000-0000-0000-0000-000000000001")


def _authority() -> AuthorizedRole:
    return AuthorizedRole(
        account_id=ACCOUNT_ID,
        assignment_id=ASSIGNMENT_ID,
        role=AccountRole.PLANNING_REVIEWER,
        assigned_at=NOW - timedelta(days=1),
    )


def _command(session: Session) -> tuple[UUID, RatifyCompetencyFloorCandidateCommand]:
    candidate = list_competency_floor_candidates(session, projected_at=NOW).items[0].candidate
    return candidate.candidate_id, RatifyCompetencyFloorCandidateCommand(
        candidate_version=CANDIDATE_VERSION,
        content_digest=candidate.content_digest,
        approval_attestation=True,
    )


def test_candidate_exposes_exact_floor_and_population_limitations(session: Session) -> None:
    projection = list_competency_floor_candidates(session, projected_at=NOW)

    assert projection.projection_version == "competency-floor-candidates@1.0.0"
    assert len(projection.items) == 1
    candidate = projection.items[0].candidate
    assert projection.items[0].status == "available"
    assert candidate.threshold == 11
    assert candidate.minimum_age_years == 30
    assert candidate.maximum_age_years == 39
    assert candidate.domain is CapabilityDomain.MUSCULAR_ENDURANCE
    assert candidate.comparison_direction is ComparisonDirection.HIGHER_IS_BETTER
    assert candidate.estimate_scope == ("assessment_specific:thirty_second_chair_stand_repetitions")
    assert any("not a validated minimum" in value for value in candidate.unresolved_limitations)
    assert candidate.evidence[0].source_url == (
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC13193711/"
    )


def test_exact_floor_ratification_is_atomic_idempotent_and_provenanced(session: Session) -> None:
    candidate_id, command = _command(session)

    first = ratify_competency_floor_candidate(
        session, candidate_id, command, _authority(), ratified_at=NOW
    )
    second = ratify_competency_floor_candidate(
        session, candidate_id, command, _authority(), ratified_at=NOW + timedelta(minutes=1)
    )
    repository = DomainRepository(session)
    persisted = repository.get_competency_floor(first.floor.id)
    decision = repository.get_decision_record(candidate_id)

    assert first.created_source is True
    assert first.created_claim is True
    assert first.created_evidence_review is True
    assert first.created_floor is True
    assert first.created_floor_review is True
    assert first.decision_record_created is True
    assert first.floor.minimum_age_years == 30
    assert first.floor.maximum_age_years == 39
    assert first.floor_review.reviewed_by == f"account:{ACCOUNT_ID}"
    assert persisted == first.floor
    assert second.decision_record_created is False
    assert second.floor == first.floor
    assert decision is not None
    assert f"candidate_content_digest:{command.content_digest}" in decision.evidence


def test_stale_digest_cannot_persist_partial_authority(session: Session) -> None:
    candidate_id, command = _command(session)
    stale = command.model_copy(update={"content_digest": f"sha256:{'0' * 64}"})

    with pytest.raises(CompetencyFloorCandidateConflictError, match="refresh and review"):
        ratify_competency_floor_candidate(
            session, candidate_id, stale, _authority(), ratified_at=NOW
        )

    repository = DomainRepository(session)
    assert repository.get_decision_record(candidate_id) is None
    assert repository.get_competency_floor(UUID("98500000-0000-4000-8000-000000000001")) is None


def test_ratification_rolls_back_review_when_floor_identity_conflicts(session: Session) -> None:
    candidate_id, command = _command(session)
    release = _candidate_registry()[candidate_id].release
    repository = DomainRepository(session)
    repository.add_evidence_source(release.source)
    session.flush()
    repository.add_evidence_claim(release.claim)
    session.flush()
    repository.add_competency_floor(release.floor.model_copy(update={"threshold": 12}))
    session.commit()

    with pytest.raises(CompetencyFloorCandidateConflictError, match="differs"):
        ratify_competency_floor_candidate(
            session, candidate_id, command, _authority(), ratified_at=NOW
        )

    assert repository.get_evidence_claim_review(release.evidence_review_id) is None
    assert repository.get_competency_floor_review(release.floor_review_id) is None
    assert repository.get_decision_record(candidate_id) is None


def test_floor_candidate_endpoints_require_planning_reviewer_role(session: Session) -> None:
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
            rationale="Competency-floor candidate authorization.",
        )

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    try:
        client = TestClient(app)
        unauthenticated = client.get("/v1/operator/competency-floor-candidates")
        forbidden = client.get(
            "/v1/operator/competency-floor-candidates",
            headers={"Authorization": "Bearer dev.assessment-only"},
        )
        allowed = client.get(
            "/v1/operator/competency-floor-candidates",
            headers={"Authorization": "Bearer dev.planning-reviewer"},
        )
        item = allowed.json()["items"][0]["candidate"]
        ratified = client.post(
            f"/v1/operator/competency-floor-candidates/{item['candidate_id']}/ratifications",
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
    assert ratified.json()["floor"]["threshold"] == 11
    assert ratified.json()["floor"]["minimum_age_years"] == 30
