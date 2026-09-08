from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from agas_api.assessment_governance_candidates import (
    CANDIDATE_VERSION,
    RatifyAssessmentGovernanceCandidateCommand,
    list_assessment_governance_candidates,
    ratify_assessment_governance_candidate,
)
from agas_api.assessment_governance_release import AssessmentGovernanceReleaseConflictError
from agas_api.database import database_session_dependency
from agas_api.identity import AuthorizedRole, authenticated_principal_dependency
from agas_api.identity_admin import set_account_role
from agas_api.main import app
from agas_domain import AccountRole, AccountRoleStatus
from agas_domain.persistence.repository import DomainRepository
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

NOW = datetime(2026, 9, 8, 15, 0, tzinfo=UTC)
ACCOUNT_ID = UUID("10000000-0000-0000-0000-000000000001")
ASSIGNMENT_ID = UUID("20000000-0000-0000-0000-000000000001")


def _authority() -> AuthorizedRole:
    return AuthorizedRole(
        account_id=ACCOUNT_ID,
        assignment_id=ASSIGNMENT_ID,
        role=AccountRole.ASSESSMENT_REVIEWER,
        assigned_at=NOW - timedelta(days=1),
    )


def _command(session: Session) -> tuple[UUID, RatifyAssessmentGovernanceCandidateCommand]:
    candidate = list_assessment_governance_candidates(session, projected_at=NOW).items[0].candidate
    return candidate.candidate_id, RatifyAssessmentGovernanceCandidateCommand(
        candidate_version=CANDIDATE_VERSION,
        content_digest=candidate.content_digest,
        approval_attestation=True,
    )


def test_candidate_presents_narrow_meaning_protocol_and_source_limitations(
    session: Session,
) -> None:
    projection = list_assessment_governance_candidates(session, projected_at=NOW)

    assert projection.projection_version == "assessment-governance-candidates@1.0.0"
    assert len(projection.items) == 1
    item = projection.items[0]
    assert item.status == "available"
    assert item.candidate.slug == "thirty_second_chair_stand"
    assert item.candidate.content_digest.startswith("sha256:")
    assert "Maximum strength" in item.candidate.does_not_measure[0]
    assert any("43-45 cm" in value for value in item.candidate.setup_requirements)
    assert any("pain" in value for value in item.candidate.stop_conditions)
    assert len(item.candidate.evidence) == 2
    assert {source.source_url for source in item.candidate.evidence} == {
        "https://pubmed.ncbi.nlm.nih.gov/35949374/",
        "https://pubmed.ncbi.nlm.nih.gov/40330808/",
    }
    assert any("1.5 repetitions" in value for value in item.candidate.unresolved_limitations)


def test_exact_candidate_ratification_is_atomic_and_idempotent(session: Session) -> None:
    candidate_id, command = _command(session)

    first = ratify_assessment_governance_candidate(
        session, candidate_id, command, _authority(), ratified_at=NOW
    )
    second = ratify_assessment_governance_candidate(
        session, candidate_id, command, _authority(), ratified_at=NOW + timedelta(minutes=1)
    )
    projection = list_assessment_governance_candidates(
        session, projected_at=NOW + timedelta(minutes=1)
    )
    repository = DomainRepository(session)
    decision = repository.get_decision_record(candidate_id)

    assert first.assessment.readiness == "ready"
    assert first.assessment.definition.required_equipment_categories == ("chair",)
    assert first.assessment.current_estimation_policy is not None
    assert first.assessment.current_estimation_policy.calculation_method == (
        "latest-matching-observation"
    )
    assert first.created_equipment_ids == (UUID("97000000-0000-4000-8000-000000000001"),)
    assert first.decision_record_created is True
    assert second.decision_record_created is False
    assert second.content_digest == first.content_digest
    assert projection.items[0].status == "ratified"
    assert projection.items[0].ratified_at == NOW
    assert decision is not None
    assert f"candidate_content_digest:{command.content_digest}" in decision.evidence
    assert repository.get_evidence_source(UUID("90000000-0000-4000-8000-000000000001")) is not None
    assert repository.get_equipment(UUID("97000000-0000-4000-8000-000000000001")) is not None


def test_candidate_rejects_a_stale_digest_without_persisting_content(session: Session) -> None:
    candidate_id, command = _command(session)
    stale = command.model_copy(update={"content_digest": f"sha256:{'0' * 64}"})

    with pytest.raises(AssessmentGovernanceReleaseConflictError, match="refresh and review"):
        ratify_assessment_governance_candidate(
            session, candidate_id, stale, _authority(), ratified_at=NOW
        )

    assert DomainRepository(session).get_decision_record(candidate_id) is None


def test_candidate_endpoints_require_assessment_reviewer_role(session: Session) -> None:
    for subject, role in (
        ("planning-only", AccountRole.PLANNING_REVIEWER),
        ("assessment-reviewer", AccountRole.ASSESSMENT_REVIEWER),
    ):
        set_account_role(
            session,
            issuer="urn:agas:development",
            subject=subject,
            role=role,
            status=AccountRoleStatus.ACTIVE,
            assigned_at=NOW - timedelta(days=1),
            rationale="Exercise candidate authorization.",
        )

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    try:
        client = TestClient(app)
        unauthenticated = client.get("/v1/operator/assessment-governance/candidates")
        forbidden = client.get(
            "/v1/operator/assessment-governance/candidates",
            headers={"Authorization": "Bearer dev.planning-only"},
        )
        allowed = client.get(
            "/v1/operator/assessment-governance/candidates",
            headers={"Authorization": "Bearer dev.assessment-reviewer"},
        )
        item = allowed.json()["items"][0]["candidate"]
        ratified = client.post(
            f"/v1/operator/assessment-governance/candidates/{item['candidate_id']}/ratifications",
            headers={"Authorization": "Bearer dev.assessment-reviewer"},
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
    assert ratified.json()["assessment"]["definition"]["slug"] == ("thirty_second_chair_stand")
