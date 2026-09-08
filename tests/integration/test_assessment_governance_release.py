from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from agas_api.assessment_governance_release import (
    RELEASE_VERSION,
    AssessmentDefinitionReviewDraft,
    AssessmentGovernanceReleaseConflictError,
    AssessmentGovernanceReleaseRequest,
    CapabilityEstimationPolicyDraft,
    EvidenceClaimReviewDraft,
    ratify_assessment_governance_release,
)
from agas_api.database import database_session_dependency
from agas_api.identity import AuthorizedRole, authenticated_principal_dependency
from agas_api.identity_admin import set_account_role
from agas_api.main import app
from agas_domain import (
    AccountRole,
    AccountRoleStatus,
    Applicability,
    AssessmentDefinition,
    AssessmentIntensity,
    AssessmentMeasurementSchema,
    AssessmentMeasurementType,
    CapabilityDomain,
    EvidenceClaim,
    EvidenceSource,
    EvidenceSourceIdentifier,
    EvidenceStrength,
)
from agas_domain.persistence.repository import DomainRepository
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

NOW = datetime(2026, 9, 3, 15, 0, tzinfo=UTC)
ACCOUNT_ID = UUID("10000000-0000-0000-0000-000000000001")
ASSIGNMENT_ID = UUID("20000000-0000-0000-0000-000000000001")


def _authority() -> AuthorizedRole:
    return AuthorizedRole(
        account_id=ACCOUNT_ID,
        assignment_id=ASSIGNMENT_ID,
        role=AccountRole.ASSESSMENT_REVIEWER,
        assigned_at=NOW - timedelta(days=1),
    )


def _release() -> AssessmentGovernanceReleaseRequest:
    source_identifier = EvidenceSourceIdentifier(
        scheme="other", value="urn:agas:test:governance-release-source"
    )
    source = EvidenceSource(
        created_at=NOW - timedelta(hours=4),
        title="Synthetic governance release source",
        authors=("Automated Test",),
        publication_year=2026,
        publication_types=("Software fixture",),
        primary_identifier=source_identifier,
        source_identifiers=(source_identifier,),
        metadata_provider="manual",
        retrieval_uri="urn:agas:test:governance-release-source",
        retrieved_at=NOW - timedelta(hours=4),
        metadata_version="software-fixture@1.0.0",
        provenance_notes=("Not scientific evidence.",),
    )
    claim = EvidenceClaim(
        created_at=NOW - timedelta(hours=3),
        claim="A synthetic release can preserve an exact governance chain.",
        domain="software_test_fixture",
        population="No athlete population; software fixture only.",
        intervention="No intervention.",
        outcome="Atomic governance release behavior.",
        study_design="software_test_fixture",
        uncertainty="This fixture supports no training conclusion.",
        limitations=("Software test only.",),
        evidence_strength=EvidenceStrength.INSUFFICIENT,
        athlete_applicability=Applicability.UNKNOWN,
        applicability_notes="Not applicable to an athlete.",
        source_identifiers=(source_identifier,),
        source_record_ids=(source.id,),
        reviewer="automated-test-author",
        claim_version="governance-release-fixture@1.0.0",
    )
    definition = AssessmentDefinition(
        created_at=NOW - timedelta(hours=2),
        slug="release_fixture",
        name="Release fixture",
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        observation_type="release_fixture_result",
        intensity=AssessmentIntensity.LOW,
        unit_or_scale="count",
        protocol_version="release-fixture@1.0.0",
    )
    protocol_review_id = uuid4()
    return AssessmentGovernanceReleaseRequest(
        release_version=RELEASE_VERSION,
        release_id=uuid4(),
        release_label="Synthetic governance release",
        prepared_at=NOW - timedelta(hours=1),
        ratified_at=NOW,
        sources=(source,),
        claims=(claim,),
        evidence_reviews=(
            EvidenceClaimReviewDraft(
                id=uuid4(),
                evidence_claim_id=claim.id,
                sequence_number=1,
                source_verification_rationale="The exact synthetic source link was checked.",
                extraction_rationale="The claim describes only the tested software behavior.",
                evidence_strength_rationale="Insufficient is correct for the fixture.",
                applicability_rationale="No athlete applicability is asserted.",
                uncertainty="This is not a scientific conclusion.",
                conflict_disclosure="No conflicts declared for the fixture.",
                review_version="governance-release-review-fixture@1.0.0",
            ),
        ),
        definition=definition,
        protocol_review=AssessmentDefinitionReviewDraft(
            id=protocol_review_id,
            assessment_definition_id=definition.id,
            sequence_number=1,
            protocol_instructions=("Follow the isolated software fixture protocol.",),
            result_entry_instructions="Enter the synthetic count.",
            measurement_schema=AssessmentMeasurementSchema(
                measurement_type=AssessmentMeasurementType.INTEGER,
                label="Synthetic count",
                minimum=0,
                maximum=100,
                step=1,
                measurement_schema_version="synthetic-count@1.0.0",
            ),
            recommended_reassessment_days=28,
            self_administered=True,
            evidence_claim_ids=(claim.id,),
            applicability_notes="Software validation only.",
            uncertainty="This does not authorize a real assessment.",
            review_version="release-protocol-review-fixture@1.0.0",
        ),
        estimation_policy=CapabilityEstimationPolicyDraft(
            id=uuid4(),
            assessment_definition_id=definition.id,
            assessment_definition_review_id=protocol_review_id,
            sequence_number=1,
            domain=definition.domain,
            observation_type=definition.observation_type,
            unit_or_scale=definition.unit_or_scale,
            calculation_method="latest-matching-observation",
            valid_for_days=28,
            evidence_claim_ids=(claim.id,),
            applicability_notes="Software validation only.",
            uncertainty="This does not estimate a real capability.",
            rule_version="latest-matching-observation@1.0.0",
        ),
        release_rationale="Exercise the authenticated atomic release boundary.",
        release_uncertainty="The release contains software fixtures only.",
        approval_attestation=True,
    )


def test_ratified_release_is_atomic_idempotent_and_binds_authority(session: Session) -> None:
    request = _release()

    first = ratify_assessment_governance_release(session, request, _authority(), recorded_at=NOW)
    second = ratify_assessment_governance_release(session, request, _authority(), recorded_at=NOW)
    repository = DomainRepository(session)
    evidence_review = repository.get_evidence_claim_review(request.evidence_reviews[0].id)
    protocol_review = repository.get_assessment_definition_review(request.protocol_review.id)
    policy = repository.get_capability_estimation_policy(request.estimation_policy.id)
    decision = repository.get_decision_record(request.release_id)

    assert first.created_source_ids == (request.sources[0].id,)
    assert first.created_claim_ids == (request.claims[0].id,)
    assert first.created_evidence_review_ids == (request.evidence_reviews[0].id,)
    assert first.definition_created is True
    assert first.protocol_review_created is True
    assert first.estimation_policy_created is True
    assert first.decision_record_created is True
    assert first.assessment.readiness == "ready"
    assert second.created_source_ids == ()
    assert second.created_claim_ids == ()
    assert second.created_evidence_review_ids == ()
    assert second.definition_created is False
    assert second.protocol_review_created is False
    assert second.estimation_policy_created is False
    assert second.decision_record_created is False
    assert second.content_digest == first.content_digest
    assert evidence_review is not None
    assert evidence_review.reviewer == f"account:{ACCOUNT_ID}"
    assert protocol_review is not None
    assert protocol_review.reviewer == f"account:{ACCOUNT_ID}"
    assert policy is not None
    assert policy.reviewed_by == f"account:{ACCOUNT_ID}"
    assert decision is not None
    assert f"authority_assignment_id:{ASSIGNMENT_ID}" in decision.evidence


def test_altered_retry_conflicts_without_rewriting_ratified_history(session: Session) -> None:
    request = _release()
    ratify_assessment_governance_release(session, request, _authority(), recorded_at=NOW)
    altered_draft = request.protocol_review.model_copy(
        update={"uncertainty": "Altered after ratification."}
    )
    altered = request.model_copy(update={"protocol_review": altered_draft})

    with pytest.raises(
        AssessmentGovernanceReleaseConflictError, match="differs from ratified immutable content"
    ):
        ratify_assessment_governance_release(session, altered, _authority(), recorded_at=NOW)

    persisted = DomainRepository(session).get_assessment_definition_review(
        request.protocol_review.id
    )
    assert persisted is not None
    assert persisted.uncertainty == request.protocol_review.uncertainty


def test_release_requires_every_bundled_claim_to_receive_one_review() -> None:
    request = _release()
    second_claim = request.claims[0].model_copy(
        update={
            "id": uuid4(),
            "claim": "A second synthetic claim also requires an exact review.",
            "claim_version": "governance-release-fixture@1.0.1",
        }
    )

    with pytest.raises(ValidationError, match="review every bundled evidence claim"):
        AssessmentGovernanceReleaseRequest.model_validate(
            request.model_dump(mode="json")
            | {"claims": [*request.model_dump(mode="json")["claims"], second_claim.model_dump()]}
        )


def test_release_endpoint_requires_assessment_role_and_rejects_spoofed_reviewer(
    session: Session,
) -> None:
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
            rationale="Exercise the release authorization boundary.",
        )

    def override_session() -> Iterator[Session]:
        yield session

    request = _release()
    payload = request.model_dump(mode="json")
    spoofed = request.model_dump(mode="json")
    spoofed["evidence_reviews"][0]["reviewer"] = "caller-controlled"
    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    try:
        client = TestClient(app)
        unauthenticated = client.post("/v1/operator/assessment-governance/releases", json=payload)
        planning_only = client.post(
            "/v1/operator/assessment-governance/releases",
            json=payload,
            headers={"Authorization": "Bearer dev.planning-only"},
        )
        spoof_attempt = client.post(
            "/v1/operator/assessment-governance/releases",
            json=spoofed,
            headers={"Authorization": "Bearer dev.assessment-reviewer"},
        )
        approved = client.post(
            "/v1/operator/assessment-governance/releases",
            json=payload,
            headers={"Authorization": "Bearer dev.assessment-reviewer"},
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert unauthenticated.status_code == 401
    assert planning_only.status_code == 403
    assert spoof_attempt.status_code == 422
    assert approved.status_code == 201
    body = approved.json()
    account = DomainRepository(session).get_account_by_identity(
        "urn:agas:development", "assessment-reviewer"
    )
    assert account is not None
    assert body["authority_account_id"] == str(account.id)
    persisted_review = DomainRepository(session).get_evidence_claim_review(
        request.evidence_reviews[0].id
    )
    assert persisted_review is not None
    assert persisted_review.reviewer == f"account:{account.id}"


def test_release_rolls_back_when_review_lineage_is_invalid(session: Session) -> None:
    request = _release()
    invalid_review = request.evidence_reviews[0].model_copy(
        update={"sequence_number": 2, "supersedes_review_id": uuid4()}
    )
    invalid = request.model_copy(update={"evidence_reviews": (invalid_review,)})

    with pytest.raises(AssessmentGovernanceReleaseConflictError, match="unknown predecessor"):
        ratify_assessment_governance_release(session, invalid, _authority(), recorded_at=NOW)

    repository = DomainRepository(session)
    assert repository.get_evidence_source(request.sources[0].id) is None
    assert repository.get_evidence_claim(request.claims[0].id) is None
    assert repository.get_assessment_definition(request.definition.id) is None
