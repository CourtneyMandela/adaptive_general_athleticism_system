from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from agas_api.competency_floor_proposals import competency_floor_proposal_batch
from agas_api.database import database_session_dependency
from agas_api.identity import authenticated_principal_dependency
from agas_api.identity_admin import set_account_role
from agas_api.main import app
from agas_domain import AccountRole, AccountRoleStatus
from agas_domain.persistence.models import (
    CompetencyFloorAuthorityRecord,
    CompetencyFloorProposalReviewRecord,
    CompetencyFloorRecord,
    ImmutableHistoricalRecordError,
)
from agas_domain.persistence.repository import DomainRepository
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

NOW = datetime(2026, 9, 13, 1, 0, tzinfo=UTC)


def _client(session: Session) -> TestClient:
    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    return TestClient(app)


def _command(*, decision: str, rationale: str) -> dict[str, object]:
    batch = competency_floor_proposal_batch()
    proposal = batch.proposals[0]
    return {
        "proposal_content_digest": proposal.content_digest,
        "batch_id": str(batch.batch_id),
        "batch_content_digest": batch.content_digest,
        "decision": decision,
        "rationale": rationale,
        "feedback_only_attestation": True,
    }


def test_proposal_feedback_is_append_only_and_cannot_create_training_authority(
    session: Session,
) -> None:
    account, assignment, _, _ = set_account_role(
        session,
        issuer="urn:agas:development",
        subject="proposal-reviewer",
        role=AccountRole.PLANNING_REVIEWER,
        status=AccountRoleStatus.ACTIVE,
        assigned_at=NOW - timedelta(days=1),
        rationale="Review owner-alpha research proposals.",
    )
    batch = competency_floor_proposal_batch()
    proposal = batch.proposals[0]
    client = _client(session)
    try:
        unauthenticated = client.get("/v1/operator/competency-floor-proposal-reviews")
        missing_attestation = client.post(
            f"/v1/operator/competency-floor-proposals/{proposal.proposal_id}/reviews",
            headers={"Authorization": "Bearer dev.proposal-reviewer"},
            json=_command(decision="advance", rationale="Prepare the next artifact.")
            | {"feedback_only_attestation": False},
        )
        stale = client.post(
            f"/v1/operator/competency-floor-proposals/{proposal.proposal_id}/reviews",
            headers={"Authorization": "Bearer dev.proposal-reviewer"},
            json=_command(decision="advance", rationale="Prepare the next artifact.")
            | {"proposal_content_digest": f"sha256:{'0' * 64}"},
        )
        first = client.post(
            f"/v1/operator/competency-floor-proposals/{proposal.proposal_id}/reviews",
            headers={"Authorization": "Bearer dev.proposal-reviewer"},
            json=_command(decision="advance", rationale="Prepare the matching assessment."),
        )
        repeated = client.post(
            f"/v1/operator/competency-floor-proposals/{proposal.proposal_id}/reviews",
            headers={"Authorization": "Bearer dev.proposal-reviewer"},
            json=_command(decision="advance", rationale="Prepare the matching assessment."),
        )
        revised = client.post(
            f"/v1/operator/competency-floor-proposals/{proposal.proposal_id}/reviews",
            headers={"Authorization": "Bearer dev.proposal-reviewer"},
            json=_command(
                decision="needs_revision",
                rationale="Use a practical submaximal field measure instead.",
            ),
        )
        projection = client.get(
            "/v1/operator/competency-floor-proposal-reviews",
            headers={"Authorization": "Bearer dev.proposal-reviewer"},
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert unauthenticated.status_code == 401
    assert missing_attestation.status_code == 422
    assert stale.status_code == 409
    assert first.status_code == 201
    assert first.json()["created"] is True
    assert first.json()["training_authority_created"] is False
    assert repeated.status_code == 201
    assert repeated.json()["created"] is False
    assert revised.status_code == 201
    assert revised.json()["review"]["sequence_number"] == 2
    assert revised.json()["review"]["reviewer_account_id"] == str(account.id)
    assert revised.json()["review"]["reviewer_authority_assignment_id"] == str(assignment.id)
    assert projection.status_code == 200
    item = next(
        value
        for value in projection.json()["items"]
        if value["proposal"]["proposal_id"] == str(proposal.proposal_id)
    )
    assert item["status"] == "needs_revision"
    assert item["current_review"]["rationale"] == (
        "Use a practical submaximal field measure instead."
    )
    assert session.scalar(select(func.count()).select_from(CompetencyFloorRecord)) == 0
    assert session.scalar(select(func.count()).select_from(CompetencyFloorAuthorityRecord)) == 0

    repository = DomainRepository(session)
    current = repository.get_current_competency_floor_proposal_review(proposal.proposal_id)
    assert current is not None
    assert current.sequence_number == 2
    record = session.get(CompetencyFloorProposalReviewRecord, current.id)
    assert record is not None
    record.rationale = "silently changed"
    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.flush()
    session.rollback()


def test_proposal_feedback_rejects_unknown_proposal(session: Session) -> None:
    set_account_role(
        session,
        issuer="urn:agas:development",
        subject="proposal-reviewer",
        role=AccountRole.PLANNING_REVIEWER,
        status=AccountRoleStatus.ACTIVE,
        assigned_at=NOW - timedelta(days=1),
        rationale="Review owner-alpha research proposals.",
    )
    client = _client(session)
    try:
        response = client.post(
            "/v1/operator/competency-floor-proposals/00000000-0000-4000-8000-000000000999/reviews",
            headers={"Authorization": "Bearer dev.proposal-reviewer"},
            json=_command(decision="rejected", rationale="Not applicable."),
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)
    assert response.status_code == 404
