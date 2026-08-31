from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from agas_api.assessment_catalog import ReviewedAssessmentCatalogItem
from agas_api.database import database_session_dependency
from agas_api.main import app
from agas_domain import (
    Applicability,
    AssessmentDefinition,
    AssessmentDefinitionReview,
    AssessmentIntensity,
    AssessmentMeasurementSchema,
    AssessmentMeasurementType,
    AssessmentReviewDecision,
    CapabilityDomain,
    EvidenceClaim,
    EvidenceClaimReview,
    EvidenceReviewDecision,
    EvidenceSource,
    EvidenceSourceIdentifier,
    EvidenceStrength,
)
from agas_domain.persistence.models import (
    AssessmentDefinitionReviewRecord,
    ImmutableHistoricalRecordError,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

NOW = datetime(2026, 8, 22, 20, 0, tzinfo=UTC)


def evidence_fixture(
    repository: DomainRepository,
    *,
    identifier_value: str = "urn:agas:test:assessment-review",
    ready: bool = True,
) -> EvidenceClaim:
    identifier = EvidenceSourceIdentifier(scheme="other", value=identifier_value)
    source = EvidenceSource(
        created_at=NOW - timedelta(days=3),
        title="Synthetic assessment-review source fixture",
        authors=("Automated Test",),
        publication_year=2026,
        publication_types=("Software fixture",),
        primary_identifier=identifier,
        source_identifiers=(identifier,),
        metadata_provider="manual",
        retrieval_uri=identifier.value,
        retrieved_at=NOW - timedelta(days=3),
        metadata_version="software-fixture@1.0.0",
        provenance_notes=("Not scientific evidence.",),
    )
    evidence = EvidenceClaim(
        created_at=NOW - timedelta(days=2),
        claim="Synthetic claim used only to verify assessment review provenance in software tests.",
        domain="software_test_fixture",
        population="No athlete population; software fixture only.",
        intervention="No intervention.",
        comparator="No comparator.",
        outcome="Persistence and catalog filtering behavior.",
        study_design="software_test_fixture",
        uncertainty="This is not scientific evidence and must never be used operationally.",
        limitations=("Exists only inside an isolated test database.",),
        evidence_strength=EvidenceStrength.INSUFFICIENT,
        athlete_applicability=Applicability.UNKNOWN,
        applicability_notes="Not applicable to athletes.",
        source_identifiers=(identifier,),
        source_record_ids=(source.id,) if ready else (),
        reviewer="automated-test-fixture",
        claim_version="software-fixture@1.0.0",
    )
    if ready:
        repository.add_evidence_source(source)
    repository.add_evidence_claim(evidence)
    if ready:
        repository.add_evidence_claim_review(
            EvidenceClaimReview(
                created_at=NOW - timedelta(days=1),
                evidence_claim_id=evidence.id,
                decision=EvidenceReviewDecision.APPROVED,
                sequence_number=1,
                reviewed_at=NOW - timedelta(days=1),
                reviewer="qualified-reviewer-fixture",
                source_verification_rationale="The exact software fixture source was checked.",
                extraction_rationale="The claim describes software behavior only.",
                evidence_strength_rationale="Insufficient is correct for this fixture.",
                applicability_rationale="No athlete applicability is asserted.",
                uncertainty="This record proves only governance behavior.",
                conflict_disclosure="No conflicts declared for the software fixture.",
                review_version="assessment-catalog-evidence-review-fixture@1.0.0",
            )
        )
    return evidence


def definition(slug: str) -> AssessmentDefinition:
    return AssessmentDefinition(
        slug=slug,
        name=slug.replace("_", " ").title(),
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        observation_type=f"{slug}_result",
        intensity=AssessmentIntensity.LOW,
        unit_or_scale="test_fixture_unit",
        protocol_version=f"{slug}@1.0.0",
    )


def review(
    assessment: AssessmentDefinition,
    evidence: EvidenceClaim,
    decision: AssessmentReviewDecision,
    *,
    sequence_number: int = 1,
    supersedes_review_id: UUID | None = None,
    reviewed_at: datetime = NOW,
    include_measurement_schema: bool = True,
) -> AssessmentDefinitionReview:
    return AssessmentDefinitionReview(
        assessment_definition_id=assessment.id,
        decision=decision,
        sequence_number=sequence_number,
        supersedes_review_id=supersedes_review_id,
        protocol_instructions=("Follow the isolated software-test fixture protocol.",),
        result_entry_instructions="Enter the synthetic fixture value.",
        measurement_schema=(
            AssessmentMeasurementSchema(
                measurement_type=AssessmentMeasurementType.NUMBER,
                label="Synthetic fixture value",
                minimum=0,
                maximum=100,
                step=1,
                measurement_schema_version="fixture-measurement@1.0.0",
            )
            if decision is AssessmentReviewDecision.APPROVED and include_measurement_schema
            else None
        ),
        recommended_reassessment_days=(
            28 if decision is AssessmentReviewDecision.APPROVED else None
        ),
        self_administered=decision is AssessmentReviewDecision.APPROVED,
        evidence_claim_ids=(evidence.id,),
        reviewed_at=reviewed_at,
        reviewer="automated-test-reviewer",
        applicability_notes="Software validation only; not applicable to an athlete.",
        uncertainty="This record does not approve a real assessment protocol.",
        review_version=f"assessment-review-fixture@{sequence_number}.0.0",
    )


def test_catalog_exposes_only_definitions_with_a_current_approved_review(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    evidence = evidence_fixture(repository)
    unready_evidence = evidence_fixture(
        repository,
        identifier_value="urn:agas:test:assessment-review-unready",
        ready=False,
    )
    approved_definition = definition("approved_fixture")
    schema_less_definition = definition("approved_without_schema_fixture")
    evidence_unready_definition = definition("approved_with_unready_evidence_fixture")
    unreviewed_definition = definition("unreviewed_fixture")
    withdrawn_definition = definition("withdrawn_fixture")
    for assessment in (
        approved_definition,
        schema_less_definition,
        evidence_unready_definition,
        unreviewed_definition,
        withdrawn_definition,
    ):
        repository.add_assessment_definition(assessment)
    first_approved = review(approved_definition, evidence, AssessmentReviewDecision.APPROVED)
    schema_less_approved = review(
        schema_less_definition,
        evidence,
        AssessmentReviewDecision.APPROVED,
        include_measurement_schema=False,
    )
    withdrawn_approval = review(withdrawn_definition, evidence, AssessmentReviewDecision.APPROVED)
    evidence_unready_approval = review(
        evidence_unready_definition,
        unready_evidence,
        AssessmentReviewDecision.APPROVED,
    )
    repository.add_assessment_definition_review(first_approved)
    repository.add_assessment_definition_review(schema_less_approved)
    repository.add_assessment_definition_review(withdrawn_approval)
    repository.add_assessment_definition_review(evidence_unready_approval)
    repository.add_assessment_definition_review(
        review(
            withdrawn_definition,
            evidence,
            AssessmentReviewDecision.REJECTED,
            sequence_number=2,
            supersedes_review_id=withdrawn_approval.id,
            reviewed_at=NOW + timedelta(days=1),
        )
    )
    session.commit()
    session.expire_all()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    try:
        response = TestClient(app).get("/v1/assessments/catalog")
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code == 200
    catalog = tuple(ReviewedAssessmentCatalogItem.model_validate(item) for item in response.json())
    assert tuple(item.definition.id for item in catalog) == (
        approved_definition.id,
        schema_less_definition.id,
    )
    assert catalog[0].current_review == first_approved
    assert catalog[0].current_review.evidence_claim_ids == (evidence.id,)
    assert catalog[1].current_review == schema_less_approved
    assert catalog[1].current_review.measurement_schema is None
    assert repository.get_assessment_definition_review(first_approved.id) == first_approved


def test_review_history_must_extend_the_current_definition_review(session: Session) -> None:
    repository = DomainRepository(session)
    evidence = evidence_fixture(repository)
    assessment = definition("linear_history_fixture")
    repository.add_assessment_definition(assessment)
    first = review(assessment, evidence, AssessmentReviewDecision.NEEDS_REVISION)
    repository.add_assessment_definition_review(first)
    session.flush()

    stale_branch = review(
        assessment,
        evidence,
        AssessmentReviewDecision.APPROVED,
        sequence_number=2,
        supersedes_review_id=uuid4(),
        reviewed_at=NOW + timedelta(days=1),
    )
    with pytest.raises(DomainIntegrityError, match="supersede the current review"):
        repository.add_assessment_definition_review(stale_branch)


def test_assessment_review_rows_are_immutable(session: Session) -> None:
    repository = DomainRepository(session)
    evidence = evidence_fixture(repository)
    assessment = definition("immutable_fixture")
    repository.add_assessment_definition(assessment)
    approved = review(assessment, evidence, AssessmentReviewDecision.APPROVED)
    repository.add_assessment_definition_review(approved)
    session.commit()

    record = session.get(AssessmentDefinitionReviewRecord, approved.id)
    assert record is not None
    record.reviewer = "mutating-reviewer"
    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.flush()
