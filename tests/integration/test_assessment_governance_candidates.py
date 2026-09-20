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
PUSHUP_RATIFIED_AT = datetime(2026, 9, 15, 10, 0, tzinfo=UTC)
JUMP_RATIFIED_AT = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
ACCOUNT_ID = UUID("10000000-0000-0000-0000-000000000001")
ASSIGNMENT_ID = UUID("20000000-0000-0000-0000-000000000001")


def _authority() -> AuthorizedRole:
    return AuthorizedRole(
        account_id=ACCOUNT_ID,
        assignment_id=ASSIGNMENT_ID,
        role=AccountRole.ASSESSMENT_REVIEWER,
        assigned_at=NOW - timedelta(days=1),
    )


def _command(
    session: Session,
    slug: str = "thirty_second_chair_stand",
) -> tuple[UUID, RatifyAssessmentGovernanceCandidateCommand]:
    candidate = next(
        item.candidate
        for item in list_assessment_governance_candidates(session, projected_at=NOW).items
        if item.candidate.slug == slug
    )
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
    assert len(projection.items) == 3
    item = next(
        item for item in projection.items if item.candidate.slug == "thirty_second_chair_stand"
    )
    assert item.status == "available"
    assert item.candidate.capability_domain.value == "muscular_endurance"
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


def test_standard_pushup_candidate_is_narrow_sex_neutral_and_does_not_import_a_floor(
    session: Session,
) -> None:
    projection = list_assessment_governance_candidates(session, projected_at=NOW)
    item = next(
        item
        for item in projection.items
        if item.candidate.slug == "maximum_consecutive_standard_pushups"
    )

    assert item.status == "available"
    assert item.candidate.setup_requirements[0].startswith("Level nonslip floor")
    assert item.candidate.estimate_scope == (
        "assessment_specific:maximum_consecutive_standard_pushup_repetitions"
    )
    assert any("does not infer sex" in value for value in item.candidate.operational_choices)
    assert any("not activated" in value for value in item.candidate.operational_choices)
    assert any("competency floor" in value for value in item.candidate.unresolved_limitations)
    assert len(item.candidate.evidence) == 1
    assert "ACSM Guidelines" in item.candidate.evidence[0].title


def test_standard_pushup_ratification_persists_textbook_provenance_and_narrow_policy(
    session: Session,
) -> None:
    candidate_id, command = _command(session, "maximum_consecutive_standard_pushups")

    result = ratify_assessment_governance_candidate(
        session,
        candidate_id,
        command,
        _authority(),
        ratified_at=PUSHUP_RATIFIED_AT,
    )
    repository = DomainRepository(session)
    source = repository.get_evidence_source(UUID("90000000-0000-4000-8000-000000000003"))

    assert result.assessment.readiness == "ready"
    assert result.assessment.definition.intensity.value == "high"
    assert result.assessment.definition.required_equipment_categories == ()
    assert result.assessment.current_estimation_policy is not None
    assert result.assessment.current_estimation_policy.calculation_method == (
        "latest-matching-observation"
    )
    assert result.created_equipment_ids == ()
    assert source is not None
    assert source.primary_identifier.scheme == "isbn"
    assert source.primary_identifier.value == "9781975219246"
    assert source.authors[-1] == "Paul M. Gallo"
    assert source.retrieval_uri == "https://www.ncbi.nlm.nih.gov/nlmcatalog/137328"
    assert any("Table 3.11" in note for note in source.provenance_notes)
    assert repository.list_competency_floors() == ()


def test_countermovement_jump_candidate_keeps_norms_contextual_and_requires_exact_setup(
    session: Session,
) -> None:
    projection = list_assessment_governance_candidates(session, projected_at=JUMP_RATIFIED_AT)
    item = next(
        item for item in projection.items if item.candidate.slug == "countermovement_vertical_jump"
    )

    assert item.status == "available"
    assert item.candidate.capability_domain.value == "explosive_power"
    assert item.candidate.estimate_scope == (
        "assessment_specific:countermovement_vertical_jump_height_cm"
    )
    assert any("no age/sex category" in value for value in item.candidate.operational_choices)
    assert any("competency floor" in value for value in item.candidate.unresolved_limitations)
    assert len(item.candidate.evidence) == 2
    assert {source.source_url for source in item.candidate.evidence} == {
        "https://www.ncbi.nlm.nih.gov/nlmcatalog/137328",
        "https://pubmed.ncbi.nlm.nih.gov/11098155/",
    }


def test_countermovement_jump_ratification_preserves_source_lineage_and_narrow_policy(
    session: Session,
) -> None:
    candidate_id, command = _command(session, "countermovement_vertical_jump")

    result = ratify_assessment_governance_candidate(
        session,
        candidate_id,
        command,
        _authority(),
        ratified_at=JUMP_RATIFIED_AT,
    )
    repository = DomainRepository(session)
    first_snapshot = repository.get_evidence_source(UUID("90000000-0000-4000-8000-000000000003"))
    jump_snapshot = repository.get_evidence_source(UUID("90000000-0000-4000-8000-000000000004"))

    assert result.assessment.readiness == "ready"
    assert result.assessment.definition.intensity.value == "high"
    assert result.assessment.definition.required_equipment_categories == (
        "vertical_jump_measurement_setup",
    )
    assert result.assessment.definition.blocked_by_health_screening_flags == (
        "lower_body_or_balance_concern",
        "controlled_jump_landing_not_confirmed",
    )
    assert result.assessment.current_review is not None
    measurement_schema = result.assessment.current_review.measurement_schema
    assert measurement_schema is not None
    assert measurement_schema.step == 0.5
    assert result.assessment.current_estimation_policy is not None
    assert result.assessment.current_estimation_policy.calculation_method == (
        "latest-matching-observation"
    )
    assert result.created_equipment_ids == (UUID("97000000-0000-4000-8000-000000000002"),)
    assert first_snapshot is not None
    assert jump_snapshot is not None
    assert jump_snapshot.sequence_number == 2
    assert jump_snapshot.supersedes_source_id == first_snapshot.id
    assert any("Table 3.12" in note for note in jump_snapshot.provenance_notes)
    assert repository.list_competency_floors() == ()


def test_textbook_snapshot_lineage_allows_pushup_ratification_after_jump(
    session: Session,
) -> None:
    jump_id, jump_command = _command(session, "countermovement_vertical_jump")
    ratify_assessment_governance_candidate(
        session,
        jump_id,
        jump_command,
        _authority(),
        ratified_at=JUMP_RATIFIED_AT,
    )
    pushup_id, pushup_command = _command(session, "maximum_consecutive_standard_pushups")

    pushup = ratify_assessment_governance_candidate(
        session,
        pushup_id,
        pushup_command,
        _authority(),
        ratified_at=JUMP_RATIFIED_AT + timedelta(minutes=1),
    )

    assert pushup.assessment.readiness == "ready"
    assert pushup.created_source_ids == ()


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
    chair_item = next(
        item for item in projection.items if item.candidate.slug == "thirty_second_chair_stand"
    )
    assert chair_item.status == "ratified"
    assert chair_item.ratified_at == NOW
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
        item = next(
            candidate_item["candidate"]
            for candidate_item in allowed.json()["items"]
            if candidate_item["candidate"]["slug"] == "thirty_second_chair_stand"
        )
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
