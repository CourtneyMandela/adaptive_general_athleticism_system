from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from agas_api.assessment_governance_candidates import (
    RatifyAssessmentGovernanceCandidateCommand,
    list_assessment_governance_candidates,
    ratify_assessment_governance_candidate,
)
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
    CANDIDATE_ID as RESOURCE_CANDIDATE_ID,
)
from agas_api.resource_governance_candidates import (
    CANDIDATE_VERSION as RESOURCE_CANDIDATE_VERSION,
)
from agas_api.resource_governance_candidates import (
    PUSHUP_CANDIDATE_ID as PUSHUP_RESOURCE_CANDIDATE_ID,
)
from agas_api.resource_governance_candidates import (
    RatifyResourceGovernanceCandidateCommand,
    list_resource_governance_candidates,
    ratify_resource_governance_candidate,
)
from agas_api.training_construction_candidates import (
    CANDIDATE_ID,
    CANDIDATE_VERSION,
    JUMP_EXPOSURE_CANDIDATE_ID,
    PUSHUP_CANDIDATE_ID,
    RatifyTrainingConstructionCandidateCommand,
    TrainingConstructionCandidateConflictError,
    list_training_construction_candidates,
    ratify_training_construction_candidate,
)
from agas_domain import AccountRole, AccountRoleStatus
from agas_domain.persistence.repository import DomainRepository
from agas_seed_data import SeedCatalogImporter, load_seed_catalog
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

NOW = datetime(2026, 9, 11, 12, 0, tzinfo=UTC)
JUMP_NOW = datetime(2026, 9, 21, 13, 0, tzinfo=UTC)


def _authority() -> AuthorizedRole:
    return AuthorizedRole(
        account_id=UUID("10000000-0000-4000-8000-000000000007"),
        assignment_id=UUID("20000000-0000-4000-8000-000000000007"),
        role=AccountRole.PLANNING_REVIEWER,
        assigned_at=NOW - timedelta(days=2),
    )


def _persist_prerequisites(session: Session, authority: AuthorizedRole) -> None:
    SeedCatalogImporter(DomainRepository(session)).import_catalog(
        load_seed_catalog(), imported_at=NOW - timedelta(days=1)
    )
    session.commit()
    planning = next(
        item
        for item in list_planning_governance_candidates(session, projected_at=NOW).items
        if item.candidate.slug == "owner_alpha_deficit_only_initial_policy"
    )
    ratify_planning_governance_candidate(
        session,
        planning.candidate.candidate_id,
        RatifyPlanningGovernanceCandidateCommand(
            candidate_version=PLANNING_CANDIDATE_VERSION,
            content_digest=planning.candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=NOW - timedelta(minutes=3),
    )
    resource = list_resource_governance_candidates(
        session, projected_at=NOW - timedelta(minutes=2)
    ).items[0]
    ratify_resource_governance_candidate(
        session,
        RESOURCE_CANDIDATE_ID,
        RatifyResourceGovernanceCandidateCommand(
            candidate_version=RESOURCE_CANDIDATE_VERSION,
            content_digest=resource.candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=NOW - timedelta(minutes=2),
    )


def _command(session: Session) -> RatifyTrainingConstructionCandidateCommand:
    candidate = list_training_construction_candidates(session, projected_at=NOW).items[0].candidate
    return RatifyTrainingConstructionCandidateCommand(
        candidate_version=CANDIDATE_VERSION,
        content_digest=candidate.content_digest,
        approval_attestation=True,
    )


def test_candidate_is_blocked_until_resource_bundle_is_ratified(session: Session) -> None:
    blocked = list_training_construction_candidates(session, projected_at=NOW)

    assert blocked.items[0].status == "blocked"
    assert "resource-governance" in blocked.items[0].issues[0]

    _persist_prerequisites(session, _authority())
    available = list_training_construction_candidates(session, projected_at=NOW)

    assert available.items[0].status == "available"
    assert "engineering prior" in (
        available.items[0].candidate.authority_basis.engineering_prior.casefold()
    )
    assert any(
        "does not validate" in item.unsupported_specifics
        for item in available.items[0].candidate.evidence
    )


def test_exact_construction_bundle_is_atomic_and_idempotent(session: Session) -> None:
    authority = _authority()
    _persist_prerequisites(session, authority)
    command = _command(session)

    first = ratify_training_construction_candidate(
        session, CANDIDATE_ID, command, authority, ratified_at=NOW
    )
    second = ratify_training_construction_candidate(
        session, CANDIDATE_ID, command, authority, ratified_at=NOW + timedelta(minutes=1)
    )
    repository = DomainRepository(session)

    assert first.created_weekly_scheduling_policy is True
    assert first.created_weekly_scheduling_policy_review is True
    assert first.created_progression_policy is True
    assert first.created_repetition_dose_policy is True
    assert first.created_session_safety_policy is True
    assert first.decision_record_created is True
    assert second.decision_record_created is False
    assert first.repetition_dose_policy is not None
    assert first.repetition_dose_policy.target_fraction_of_estimate == 0.5
    assert first.repetition_dose_policy.progression_policy_id == first.progression_policy.id
    assert first.weekly_scheduling_policy_review.decision.value == "approved"
    assert repository.get_repetition_dose_policy(first.repetition_dose_policy.id) == (
        first.repetition_dose_policy
    )
    assert (
        list_training_construction_candidates(session, projected_at=NOW + timedelta(minutes=2))
        .items[0]
        .status
        == "ratified"
    )


def test_pushup_construction_bundle_uses_matching_resource_and_scope(session: Session) -> None:
    authority = _authority()
    _persist_prerequisites(session, authority)
    resource = next(
        item
        for item in list_resource_governance_candidates(
            session, projected_at=datetime(2026, 9, 17, 12, 5, tzinfo=UTC)
        ).items
        if item.candidate.candidate_id == PUSHUP_RESOURCE_CANDIDATE_ID
    )
    ratify_resource_governance_candidate(
        session,
        PUSHUP_RESOURCE_CANDIDATE_ID,
        RatifyResourceGovernanceCandidateCommand(
            candidate_version=RESOURCE_CANDIDATE_VERSION,
            content_digest=resource.candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=datetime(2026, 9, 17, 12, 10, tzinfo=UTC),
    )
    candidate = next(
        item.candidate
        for item in list_training_construction_candidates(
            session, projected_at=datetime(2026, 9, 17, 12, 35, tzinfo=UTC)
        ).items
        if item.candidate.candidate_id == PUSHUP_CANDIDATE_ID
    )

    result = ratify_training_construction_candidate(
        session,
        PUSHUP_CANDIDATE_ID,
        RatifyTrainingConstructionCandidateCommand(
            candidate_version=CANDIDATE_VERSION,
            content_digest=candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=datetime(2026, 9, 17, 12, 40, tzinfo=UTC),
    )

    assert result.repetition_dose_policy is not None
    assert result.repetition_dose_policy.estimate_scope == (
        "assessment_specific:maximum_consecutive_standard_pushup_repetitions"
    )
    assert result.repetition_dose_policy.target_fraction_of_estimate == 0.4
    assert result.repetition_dose_policy.maximum_repetitions_per_set == 10
    assert result.repetition_dose_policy.rest_seconds == 120


def test_introductory_jump_bundle_is_blocked_until_assessment_evidence_is_reviewed(
    session: Session,
) -> None:
    SeedCatalogImporter(DomainRepository(session)).import_catalog(
        load_seed_catalog(), imported_at=JUMP_NOW - timedelta(days=1)
    )
    session.commit()

    item = next(
        item
        for item in list_training_construction_candidates(session, projected_at=JUMP_NOW).items
        if item.candidate.candidate_id == JUMP_EXPOSURE_CANDIDATE_ID
    )

    assert item.status == "blocked"
    assert any("evidence claim" in issue for issue in item.issues)


def test_introductory_jump_bundle_persists_typed_engineering_authorities(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    SeedCatalogImporter(repository).import_catalog(
        load_seed_catalog(), imported_at=JUMP_NOW - timedelta(days=1)
    )
    session.commit()
    assessment = next(
        item.candidate
        for item in list_assessment_governance_candidates(
            session, projected_at=JUMP_NOW - timedelta(minutes=20)
        ).items
        if item.candidate.slug == "countermovement_vertical_jump"
    )
    assessment_authority = AuthorizedRole(
        account_id=UUID("10000000-0000-4000-8000-000000000020"),
        assignment_id=UUID("20000000-0000-4000-8000-000000000020"),
        role=AccountRole.ASSESSMENT_REVIEWER,
        assigned_at=JUMP_NOW - timedelta(days=1),
    )
    ratify_assessment_governance_candidate(
        session,
        assessment.candidate_id,
        RatifyAssessmentGovernanceCandidateCommand(
            candidate_version=assessment.candidate_version,
            content_digest=assessment.content_digest,
            approval_attestation=True,
        ),
        assessment_authority,
        ratified_at=JUMP_NOW - timedelta(minutes=15),
    )
    candidate = next(
        item
        for item in list_training_construction_candidates(session, projected_at=JUMP_NOW).items
        if item.candidate.candidate_id == JUMP_EXPOSURE_CANDIDATE_ID
    )
    authority = AuthorizedRole(
        account_id=UUID("10000000-0000-4000-8000-000000000021"),
        assignment_id=UUID("20000000-0000-4000-8000-000000000021"),
        role=AccountRole.PLANNING_REVIEWER,
        assigned_at=JUMP_NOW - timedelta(days=1),
    )

    first = ratify_training_construction_candidate(
        session,
        JUMP_EXPOSURE_CANDIDATE_ID,
        RatifyTrainingConstructionCandidateCommand(
            candidate_version=candidate.candidate.candidate_version,
            content_digest=candidate.candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=JUMP_NOW,
    )
    second = ratify_training_construction_candidate(
        session,
        JUMP_EXPOSURE_CANDIDATE_ID,
        RatifyTrainingConstructionCandidateCommand(
            candidate_version=candidate.candidate.candidate_version,
            content_digest=candidate.candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=JUMP_NOW + timedelta(minutes=1),
    )

    assert first.repetition_dose_policy is None
    assert first.introductory_exposure_dose_policy is not None
    assert first.introductory_exposure_dose_policy.numeric_value_origin == "engineering_judgment"
    assert (
        first.introductory_exposure_dose_policy.sets
        * first.introductory_exposure_dose_policy.dose_per_set
        == 6
    )
    assert first.introductory_exposure_dose_policy.evidence_claim_ids == ()
    assert first.exposure_definition is not None
    assert first.exposure_definition.exercise_id == UUID(
        "b0000000-0000-4000-8000-000000000012"
    )
    assert first.exposure_progression_policy is not None
    assert first.exposure_progression_policy.maximum_initial_dose == 6
    assert repository.get_introductory_exposure_dose_policy(
        first.introductory_exposure_dose_policy.id
    ) == first.introductory_exposure_dose_policy
    assert first.created_introductory_exposure_dose_policy is True
    assert first.created_exposure_definition is True
    assert first.created_exposure_progression_policy is True
    assert second.decision_record_created is False


def test_stale_digest_persists_none_of_the_construction_bundle(session: Session) -> None:
    authority = _authority()
    _persist_prerequisites(session, authority)
    command = _command(session).model_copy(update={"content_digest": f"sha256:{'0' * 64}"})

    with pytest.raises(TrainingConstructionCandidateConflictError, match="refresh and review"):
        ratify_training_construction_candidate(
            session, CANDIDATE_ID, command, authority, ratified_at=NOW
        )

    repository = DomainRepository(session)
    assert repository.get_decision_record(CANDIDATE_ID) is None
    assert (
        repository.get_repetition_dose_policy(UUID("98940000-0000-4000-8000-000000000001")) is None
    )


def test_endpoints_require_role_and_ratify_one_batch(session: Session) -> None:
    account, assignment, _, _ = set_account_role(
        session,
        issuer="urn:agas:development",
        subject="construction-reviewer",
        role=AccountRole.PLANNING_REVIEWER,
        status=AccountRoleStatus.ACTIVE,
        assigned_at=NOW - timedelta(days=2),
        rationale="Training-construction endpoint test.",
    )
    authority = AuthorizedRole(
        account_id=account.id,
        assignment_id=assignment.id,
        role=assignment.role,
        assigned_at=assignment.assigned_at,
    )
    _persist_prerequisites(session, authority)

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    try:
        client = TestClient(app)
        unauthenticated = client.get("/v1/operator/training-construction-candidates")
        projected = client.get(
            "/v1/operator/training-construction-candidates",
            headers={"Authorization": "Bearer dev.construction-reviewer"},
        )
        candidate = projected.json()["items"][0]["candidate"]
        ratified = client.post(
            f"/v1/operator/training-construction-candidates/{candidate['candidate_id']}/ratifications",
            headers={"Authorization": "Bearer dev.construction-reviewer"},
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
    assert ratified.json()["repetition_dose_policy"]["sets"] == 2
