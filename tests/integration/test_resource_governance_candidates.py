from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from agas_api.database import database_session_dependency
from agas_api.identity import AuthorizedRole, authenticated_principal_dependency
from agas_api.identity_admin import set_account_role
from agas_api.main import app
from agas_api.planning_governance_candidates import (
    CANDIDATE_VERSION as PLANNING_CANDIDATE_VERSION,
)
from agas_api.planning_governance_candidates import (
    RatifyPlanningGovernanceCandidateCommand,
    list_planning_governance_candidates,
    ratify_planning_governance_candidate,
)
from agas_api.resource_governance_candidates import (
    CANDIDATE_ID,
    CANDIDATE_VERSION,
    RatifyResourceGovernanceCandidateCommand,
    ResourceGovernanceCandidateConflictError,
    list_resource_governance_candidates,
    ratify_resource_governance_candidate,
)
from agas_domain import AccountRole, AccountRoleStatus
from agas_domain.persistence.repository import DomainRepository
from agas_seed_data import SeedCatalogImporter, load_seed_catalog
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

NOW = datetime(2026, 9, 10, 18, 0, tzinfo=UTC)


def _authority() -> AuthorizedRole:
    return AuthorizedRole(
        account_id=UUID("10000000-0000-4000-8000-000000000006"),
        assignment_id=UUID("20000000-0000-4000-8000-000000000006"),
        role=AccountRole.PLANNING_REVIEWER,
        assigned_at=NOW - timedelta(days=1),
    )


def _persist_source_prerequisite(session: Session, authority: AuthorizedRole) -> None:
    SeedCatalogImporter(DomainRepository(session)).import_catalog(
        load_seed_catalog(), imported_at=NOW - timedelta(minutes=1)
    )
    session.commit()
    item = next(
        item
        for item in list_planning_governance_candidates(session, projected_at=NOW).items
        if item.candidate.slug == "owner_alpha_deficit_only_initial_policy"
    )
    ratify_planning_governance_candidate(
        session,
        item.candidate.candidate_id,
        RatifyPlanningGovernanceCandidateCommand(
            candidate_version=PLANNING_CANDIDATE_VERSION,
            content_digest=item.candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=NOW,
    )


def _command(session: Session) -> RatifyResourceGovernanceCandidateCommand:
    candidate = (
        list_resource_governance_candidates(session, projected_at=NOW + timedelta(minutes=1))
        .items[0]
        .candidate
    )
    return RatifyResourceGovernanceCandidateCommand(
        candidate_version=CANDIDATE_VERSION,
        content_digest=candidate.content_digest,
        approval_attestation=True,
    )


def test_candidate_is_blocked_until_exact_shared_source_exists(session: Session) -> None:
    blocked = list_resource_governance_candidates(session, projected_at=NOW)

    assert blocked.items[0].status == "blocked"
    assert "deficit-only" in blocked.items[0].issues[0]

    _persist_source_prerequisite(session, _authority())
    available = list_resource_governance_candidates(
        session, projected_at=NOW + timedelta(minutes=1)
    )

    assert available.items[0].status == "available"
    assert any(
        "Sets, repetitions" in value for value in available.items[0].candidate.does_not_establish
    )
    assert any(
        "stable-chair" in value.casefold()
        for value in available.items[0].candidate.unresolved_limitations
    )


def test_exact_bundle_ratification_is_atomic_and_idempotent(session: Session) -> None:
    authority = _authority()
    _persist_source_prerequisite(session, authority)
    command = _command(session)

    first = ratify_resource_governance_candidate(
        session, CANDIDATE_ID, command, authority, ratified_at=NOW + timedelta(minutes=2)
    )
    second = ratify_resource_governance_candidate(
        session, CANDIDATE_ID, command, authority, ratified_at=NOW + timedelta(minutes=3)
    )
    repository = DomainRepository(session)

    assert first.created_claim is True
    assert first.created_evidence_review is True
    assert first.created_equipment is True
    assert first.created_exercise is True
    assert first.created_resolver_policy is True
    assert first.created_allocation_policy is True
    assert first.decision_record_created is True
    assert second.decision_record_created is False
    assert first.exercise.name == "Chair sit-to-stand"
    assert first.exercise.equipment_requirement_ids == (first.equipment.id,)
    assert first.resolver_policy.partial_match_threshold == 1
    assert first.allocation_policy.allow_partial_exercise_resolution is False
    assert repository.get_exercise(first.exercise.id) == first.exercise
    assert (
        list_resource_governance_candidates(session, projected_at=NOW + timedelta(minutes=4))
        .items[0]
        .status
        == "ratified"
    )


def test_stale_digest_does_not_persist_bundle(session: Session) -> None:
    authority = _authority()
    _persist_source_prerequisite(session, authority)
    command = _command(session).model_copy(update={"content_digest": f"sha256:{'0' * 64}"})

    with pytest.raises(ResourceGovernanceCandidateConflictError, match="refresh and review"):
        ratify_resource_governance_candidate(
            session, CANDIDATE_ID, command, authority, ratified_at=NOW + timedelta(minutes=2)
        )

    repository = DomainRepository(session)
    assert repository.get_decision_record(CANDIDATE_ID) is None
    assert repository.get_exercise(UUID("b1000000-0000-4000-8000-000000000001")) is None


def test_endpoints_require_role_and_accept_only_digest_attestation(session: Session) -> None:
    account, assignment, _, _ = set_account_role(
        session,
        issuer="urn:agas:development",
        subject="resource-reviewer",
        role=AccountRole.PLANNING_REVIEWER,
        status=AccountRoleStatus.ACTIVE,
        assigned_at=NOW - timedelta(days=1),
        rationale="Resource-governance endpoint test.",
    )
    authority = AuthorizedRole(
        account_id=account.id,
        assignment_id=assignment.id,
        role=assignment.role,
        assigned_at=assignment.assigned_at,
    )
    _persist_source_prerequisite(session, authority)

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    try:
        client = TestClient(app)
        unauthenticated = client.get("/v1/operator/resource-governance/candidates")
        projected = client.get(
            "/v1/operator/resource-governance/candidates",
            headers={"Authorization": "Bearer dev.resource-reviewer"},
        )
        candidate = projected.json()["items"][0]["candidate"]
        ratified = client.post(
            f"/v1/operator/resource-governance/candidates/{candidate['candidate_id']}/ratifications",
            headers={"Authorization": "Bearer dev.resource-reviewer"},
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
    assert ratified.json()["exercise"]["name"] == "Chair sit-to-stand"
