import hashlib
import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import agas_api.competency_floor_candidates as floor_candidates
import pytest
from agas_api.competency_floor_candidates import (
    CANDIDATE_VERSION,
    CompetencyFloorCandidateConflictError,
    CompetencyFloorCandidateValidationError,
    RatifyCompetencyFloorCandidateBatchCommand,
    RatifyCompetencyFloorCandidateCommand,
    _candidate_registry,
    competency_floor_candidate_batch,
    list_competency_floor_candidates,
    ratify_competency_floor_candidate,
    ratify_competency_floor_candidate_batch,
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
from agas_domain.persistence.models import DecisionRecordRecord
from agas_domain.persistence.repository import DomainRepository
from fastapi.testclient import TestClient
from sqlalchemy import update
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

    assert projection.projection_version == "competency-floor-candidates@1.1.0"
    assert len(projection.items) == 1
    assert projection.batch.candidates[0].candidate_id == projection.items[0].candidate.candidate_id
    assert projection.batch.content_digest.startswith("sha256:")
    candidate = projection.items[0].candidate
    assert projection.items[0].status == "available"
    assert candidate.threshold == 11
    assert candidate.minimum_age_years == 30
    assert candidate.maximum_age_years == 39
    assert candidate.domain is CapabilityDomain.MUSCULAR_ENDURANCE
    assert candidate.comparison_direction is ComparisonDirection.HIGHER_IS_BETTER
    assert candidate.estimate_scope == ("assessment_specific:thirty_second_chair_stand_repetitions")
    assert candidate.authority_basis.numeric_value_origin == "direct_study_result"
    assert (
        candidate.authority_basis.operational_use_origin == "evidence_informed_engineering_judgment"
    )
    assert "did not validate" in candidate.authority_basis.operational_use_explanation
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


def test_exact_batch_ratification_is_atomic_idempotent_and_audited(session: Session) -> None:
    batch = competency_floor_candidate_batch()
    command = RatifyCompetencyFloorCandidateBatchCommand(
        **batch.model_dump(), approval_attestation=True
    )

    first = ratify_competency_floor_candidate_batch(session, command, _authority(), ratified_at=NOW)
    second = ratify_competency_floor_candidate_batch(
        session, command, _authority(), ratified_at=NOW + timedelta(minutes=1)
    )
    decision = DomainRepository(session).get_decision_record(batch.batch_id)

    assert first.batch_decision_record_created is True
    assert len(first.candidate_results) == len(batch.candidates)
    assert second.batch_decision_record_created is False
    assert all(not item.decision_record_created for item in second.candidate_results)
    assert decision is not None
    assert f"batch_content_digest:{batch.content_digest}" in decision.evidence
    assert {
        item.removeprefix("candidate_content_digest:")
        for item in decision.evidence
        if item.startswith("candidate_content_digest:")
    } == {f"{item.candidate_id}={item.content_digest}" for item in batch.candidates}


def test_historical_canonicalization_digest_remains_readable_and_idempotent(
    session: Session,
) -> None:
    candidate_id, command = _command(session)
    ratify_competency_floor_candidate(session, candidate_id, command, _authority(), ratified_at=NOW)
    prepared = _candidate_registry()[candidate_id]
    historical_digest = prepared.accepted_historical_content_digests[0]
    record = session.get(DecisionRecordRecord, candidate_id)
    assert record is not None
    historical_evidence = [
        f"candidate_content_digest:{historical_digest}"
        if value.startswith("candidate_content_digest:")
        else value
        for value in record.evidence
    ]
    # Simulate the row already present before the canonicalization fix. Core SQL deliberately
    # bypasses the ORM's append-only guard; production code never rewrites decision history.
    session.execute(
        update(DecisionRecordRecord)
        .where(DecisionRecordRecord.id == candidate_id)
        .values(evidence=historical_evidence)
    )
    session.commit()
    session.expire_all()

    projection = list_competency_floor_candidates(session, projected_at=NOW + timedelta(minutes=1))
    repeated = ratify_competency_floor_candidate(
        session,
        candidate_id,
        command,
        _authority(),
        ratified_at=NOW + timedelta(minutes=1),
    )

    assert projection.items[0].status == "ratified"
    assert repeated.candidate_content_digest == historical_digest
    assert repeated.decision_record_created is False


def test_batch_rolls_back_every_new_candidate_when_one_conflicts(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = next(iter(_candidate_registry().values()))
    second_candidate_id = uuid4()
    second_floor_id = uuid4()
    second = original.model_copy(
        deep=True,
        update={
            "presentation": original.presentation.model_copy(
                update={
                    "candidate_id": second_candidate_id,
                    "release_label": "Synthetic second batch floor",
                    "content_digest": f"sha256:{'b' * 64}",
                }
            ),
            "release": original.release.model_copy(
                deep=True,
                update={
                    "release_id": second_candidate_id,
                    "release_label": "Synthetic second batch floor",
                    "floor": original.release.floor.model_copy(update={"id": second_floor_id}),
                    "floor_review_id": uuid4(),
                },
            ),
            "accepted_historical_content_digests": (),
        },
    )
    registry = {
        original.presentation.candidate_id: original,
        second.presentation.candidate_id: second,
    }
    monkeypatch.setattr(floor_candidates, "_candidate_registry", lambda: registry)
    competency_floor_candidate_batch.cache_clear()
    batch = competency_floor_candidate_batch()
    repository = DomainRepository(session)
    repository.add_evidence_source(second.release.source)
    session.flush()
    repository.add_evidence_claim(second.release.claim)
    session.flush()
    repository.add_competency_floor(second.release.floor.model_copy(update={"threshold": 12}))
    session.commit()

    with pytest.raises(CompetencyFloorCandidateConflictError, match="differs"):
        ratify_competency_floor_candidate_batch(
            session,
            RatifyCompetencyFloorCandidateBatchCommand(
                **batch.model_dump(), approval_attestation=True
            ),
            _authority(),
            ratified_at=NOW,
        )

    assert repository.get_decision_record(original.release.release_id) is None
    assert repository.get_competency_floor(original.release.floor.id) is None
    assert repository.get_decision_record(batch.batch_id) is None
    competency_floor_candidate_batch.cache_clear()


def test_data_loaded_candidate_rejects_stale_digest_and_cross_field_drift(tmp_path: Path) -> None:
    source_path = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "governance_candidates"
        / "competency_floors"
        / "chair_stand_age_30_39.json"
    )
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    payload["presentation"]["summary"] = "Changed without refreshing the digest."
    (tmp_path / "stale.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CompetencyFloorCandidateValidationError, match="stale content digest"):
        _candidate_registry(tmp_path)

    _candidate_registry.cache_clear()
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    payload["release"]["floor"]["threshold"] = 12
    canonical = json.dumps(
        {
            "candidate_version": payload["candidate_version"],
            "presentation": payload["presentation"],
            "release": payload["release"],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    payload["content_digest"] = f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
    (tmp_path / "stale.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CompetencyFloorCandidateValidationError, match="must match exactly"):
        _candidate_registry(tmp_path)
    _candidate_registry.cache_clear()


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
        batch = allowed.json()["batch"]
        forbidden_batch = client.post(
            "/v1/operator/competency-floor-candidate-batches/ratifications",
            headers={"Authorization": "Bearer dev.assessment-only"},
            json={**batch, "approval_attestation": True},
        )
        ratified = client.post(
            f"/v1/operator/competency-floor-candidates/{item['candidate_id']}/ratifications",
            headers={"Authorization": "Bearer dev.planning-reviewer"},
            json={
                "candidate_version": item["candidate_version"],
                "content_digest": item["content_digest"],
                "approval_attestation": True,
            },
        )
        batch_ratified = client.post(
            "/v1/operator/competency-floor-candidate-batches/ratifications",
            headers={"Authorization": "Bearer dev.planning-reviewer"},
            json={**batch, "approval_attestation": True},
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert unauthenticated.status_code == 401
    assert forbidden.status_code == 403
    assert allowed.status_code == 200
    assert forbidden_batch.status_code == 403
    assert ratified.status_code == 201
    assert ratified.json()["floor"]["threshold"] == 11
    assert ratified.json()["floor"]["minimum_age_years"] == 30
    assert batch_ratified.status_code == 201
    assert batch_ratified.json()["batch"]["content_digest"] == batch["content_digest"]
    assert len(batch_ratified.json()["candidate_results"]) == 1
