from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from agas_api.assessment_governance import AssessmentGovernanceProjector
from agas_api.assessment_governance_admin import (
    ASSESSMENT_GOVERNANCE_BUNDLE_VERSION,
    AssessmentGovernanceBundle,
    LocalAssessmentGovernanceImportError,
    import_assessment_governance_bundle,
)
from agas_api.database import database_session_dependency
from agas_api.identity import authenticated_principal_dependency
from agas_api.identity_admin import set_account_role
from agas_api.main import app
from agas_api.settings import Settings
from agas_domain import (
    AccountRole,
    AccountRoleStatus,
    Applicability,
    AssessmentDefinition,
    AssessmentDefinitionReview,
    AssessmentIntensity,
    AssessmentMeasurementSchema,
    AssessmentMeasurementType,
    AssessmentReviewDecision,
    CapabilityDomain,
    CapabilityEstimationPolicy,
    EvidenceClaim,
    EvidenceClaimReview,
    EvidenceReviewDecision,
    EvidenceSource,
    EvidenceSourceIdentifier,
    EvidenceStrength,
)
from agas_domain.persistence.repository import DomainRepository
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

NOW = datetime(2026, 8, 30, 16, 0, tzinfo=UTC)


def _development_settings() -> Settings:
    return Settings(
        environment="development",
        auth_mode="development",
        database_url="sqlite+pysqlite:///:memory:",
    )


def _source() -> EvidenceSource:
    identifier = EvidenceSourceIdentifier(
        scheme="other", value="urn:agas:test:assessment-governance-source"
    )
    return EvidenceSource(
        created_at=NOW - timedelta(hours=3),
        title="Synthetic assessment-governance source fixture",
        authors=("Automated Test",),
        publication_year=2026,
        publication_types=("Software fixture",),
        primary_identifier=identifier,
        source_identifiers=(identifier,),
        metadata_provider="manual",
        retrieval_uri="urn:agas:test:assessment-governance-source",
        retrieved_at=NOW - timedelta(hours=3),
        metadata_version="software-fixture@1.0.0",
        provenance_notes=("Not scientific evidence.",),
    )


def _evidence(source: EvidenceSource | None = None) -> EvidenceClaim:
    identifiers = (
        source.source_identifiers
        if source
        else (EvidenceSourceIdentifier(scheme="other", value="urn:agas:test:governance"),)
    )
    return EvidenceClaim(
        created_at=NOW - timedelta(hours=2),
        claim="Synthetic software fixture for assessment-governance projection tests.",
        domain="software_test_fixture",
        population="No athlete population; software fixture only.",
        intervention="No intervention.",
        outcome="Assessment-governance projection behavior.",
        study_design="software_test_fixture",
        uncertainty="Not scientific evidence and not operationally applicable.",
        evidence_strength=EvidenceStrength.INSUFFICIENT,
        athlete_applicability=Applicability.UNKNOWN,
        applicability_notes="Not applicable to athletes.",
        source_identifiers=identifiers,
        source_record_ids=(source.id,) if source else (),
        reviewer="automated-test-fixture",
        claim_version="software-fixture@1.0.0",
    )


def _evidence_review(
    evidence: EvidenceClaim, *, reviewed_at: datetime = NOW - timedelta(hours=1)
) -> EvidenceClaimReview:
    return EvidenceClaimReview(
        created_at=reviewed_at,
        evidence_claim_id=evidence.id,
        decision=EvidenceReviewDecision.APPROVED,
        sequence_number=1,
        reviewed_at=reviewed_at,
        reviewer="qualified-reviewer-fixture",
        source_verification_rationale="The exact software fixture source was checked.",
        extraction_rationale="The claim describes software behavior only.",
        evidence_strength_rationale="Insufficient is correct for this fixture.",
        applicability_rationale="No athlete applicability is asserted.",
        uncertainty="This record proves only governance behavior.",
        conflict_disclosure="No conflicts declared for the software fixture.",
        review_version="assessment-evidence-review-fixture@1.0.0",
    )


def _persist_approved_evidence(session: Session) -> EvidenceClaim:
    source = _source()
    evidence = _evidence(source)
    review = _evidence_review(evidence)
    repository = DomainRepository(session)
    repository.add_evidence_source(source)
    repository.add_evidence_claim(evidence)
    repository.add_evidence_claim_review(review)
    session.flush()
    return evidence


def _definition(slug: str, *, created_at: datetime = NOW) -> AssessmentDefinition:
    return AssessmentDefinition(
        created_at=created_at,
        slug=slug,
        name=slug.replace("_", " ").title(),
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        observation_type=f"{slug}_result",
        intensity=AssessmentIntensity.MODERATE,
        unit_or_scale="w",
        protocol_version=f"{slug}@1.0.0",
    )


def _approved_review(
    definition: AssessmentDefinition, evidence: EvidenceClaim, *, reviewed_at: datetime = NOW
) -> AssessmentDefinitionReview:
    return AssessmentDefinitionReview(
        created_at=reviewed_at,
        assessment_definition_id=definition.id,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=1,
        protocol_instructions=("Follow the isolated software-test fixture protocol.",),
        result_entry_instructions="Enter the synthetic fixture value.",
        measurement_schema=AssessmentMeasurementSchema(
            measurement_type=AssessmentMeasurementType.NUMBER,
            label="Synthetic watts",
            minimum=0,
            maximum=1000,
            step=1,
            measurement_schema_version="fixture-watts@1.0.0",
        ),
        recommended_reassessment_days=28,
        self_administered=True,
        evidence_claim_ids=(evidence.id,),
        reviewed_at=reviewed_at,
        reviewer="automated-test-reviewer",
        applicability_notes="Software validation only.",
        uncertainty="This record does not approve a real assessment protocol.",
        review_version="assessment-review-fixture@1.0.0",
    )


def _approved_policy(
    definition: AssessmentDefinition,
    review: AssessmentDefinitionReview,
    evidence: EvidenceClaim,
    *,
    reviewed_at: datetime = NOW,
) -> CapabilityEstimationPolicy:
    return CapabilityEstimationPolicy(
        created_at=reviewed_at,
        assessment_definition_id=definition.id,
        assessment_definition_review_id=review.id,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=1,
        domain=definition.domain,
        observation_type=definition.observation_type,
        unit_or_scale=definition.unit_or_scale,
        calculation_method="latest-matching-observation",
        valid_for_days=28,
        evidence_claim_ids=(evidence.id,),
        reviewed_at=reviewed_at,
        reviewed_by="automated-test-reviewer",
        applicability_notes="Software validation only.",
        uncertainty="This policy is not operational scientific guidance.",
        rule_version="latest-matching-observation@1.0.0",
    )


def test_governance_projection_exposes_blockers_history_and_evidence(session: Session) -> None:
    repository = DomainRepository(session)
    evidence = _persist_approved_evidence(session)
    unreviewed = _definition("unreviewed_fixture")
    ready = _definition("ready_fixture")
    review = _approved_review(ready, evidence)
    policy = _approved_policy(ready, review, evidence)
    repository.add_assessment_definition(unreviewed)
    repository.add_assessment_definition(ready)
    repository.add_assessment_definition_review(review)
    repository.add_capability_estimation_policy(policy)
    session.commit()

    projection = AssessmentGovernanceProjector(session).project(NOW + timedelta(minutes=1))
    by_slug = {item.definition.slug: item for item in projection.items}

    assert by_slug["unreviewed_fixture"].status == "unreviewed"
    assert by_slug["unreviewed_fixture"].readiness == "blocked"
    assert by_slug["unreviewed_fixture"].issues == (
        "assessment definition has no protocol review history",
        "no capability-estimation policy exists for this definition",
    )
    ready_item = by_slug["ready_fixture"]
    assert ready_item.readiness == "ready"
    assert ready_item.current_review == review
    assert ready_item.review_history == (review,)
    assert ready_item.current_estimation_policy == policy
    assert ready_item.estimation_policy_history == (policy,)
    assert ready_item.evidence_claims == (evidence,)
    assert ready_item.review_evidence_governance is not None
    assert ready_item.review_evidence_governance.readiness == "ready"
    assert ready_item.estimation_policy_evidence_governance is not None
    assert ready_item.estimation_policy_evidence_governance.readiness == "ready"


def test_governance_projection_does_not_reveal_future_records(session: Session) -> None:
    repository = DomainRepository(session)
    evidence = _evidence()
    future = NOW + timedelta(days=1)
    definition = _definition("future_review_fixture", created_at=NOW - timedelta(days=1))
    review = _approved_review(definition, evidence, reviewed_at=future)
    repository.add_evidence_claim(evidence)
    repository.add_assessment_definition(definition)
    repository.add_assessment_definition_review(review)
    session.commit()

    item = AssessmentGovernanceProjector(session).project(NOW).items[0]

    assert item.status == "unreviewed"
    assert item.current_review is None
    assert item.review_history == ()
    assert item.evidence_claims == ()


def test_assessment_governance_requires_its_distinct_role(session: Session) -> None:
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
            assigned_at=NOW,
            rationale="Exercise the distinct assessment-governance authorization boundary.",
        )

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    try:
        unauthenticated = TestClient(app).get("/v1/operator/assessment-governance")
        planning_only = TestClient(app).get(
            "/v1/operator/assessment-governance",
            headers={"Authorization": "Bearer dev.planning-only"},
        )
        authorized = TestClient(app).get(
            "/v1/operator/assessment-governance",
            headers={"Authorization": "Bearer dev.assessment-reviewer"},
            params={"at": (NOW + timedelta(minutes=1)).isoformat()},
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert unauthenticated.status_code == 401
    assert planning_only.status_code == 403
    assert planning_only.json() == {"detail": "active assessment_reviewer role required"}
    assert authorized.status_code == 200
    assert authorized.json()["items"] == []


def test_local_governance_bundle_import_is_atomic_exact_and_idempotent(session: Session) -> None:
    repository = DomainRepository(session)
    evidence = _persist_approved_evidence(session)
    definition = _definition("curated_fixture")
    review = _approved_review(definition, evidence)
    policy = _approved_policy(definition, review, evidence)
    session.commit()
    bundle = AssessmentGovernanceBundle(
        bundle_version=ASSESSMENT_GOVERNANCE_BUNDLE_VERSION,
        definition=definition,
        review=review,
        estimation_policy=policy,
    )

    first = import_assessment_governance_bundle(
        session,
        bundle,
        settings=_development_settings(),
        imported_at=NOW + timedelta(minutes=1),
    )
    second = import_assessment_governance_bundle(
        session,
        bundle,
        settings=_development_settings(),
        imported_at=NOW + timedelta(minutes=2),
    )

    assert first.definition_created is True
    assert first.review_created is True
    assert first.estimation_policy_created is True
    assert first.readiness == "ready"
    assert first.issues == ()
    assert second.definition_created is False
    assert second.review_created is False
    assert second.estimation_policy_created is False
    assert repository.get_assessment_definition(definition.id) == definition
    assert repository.get_assessment_definition_review(review.id) == review
    assert repository.get_capability_estimation_policy(policy.id) == policy

    conflicting_bundle = bundle.model_copy(
        update={
            "review": review.model_copy(
                update={"uncertainty": "Conflicting content under the same immutable identity."}
            )
        }
    )
    with pytest.raises(LocalAssessmentGovernanceImportError, match="differs from bundled"):
        import_assessment_governance_bundle(
            session,
            conflicting_bundle,
            settings=_development_settings(),
            imported_at=NOW + timedelta(minutes=3),
        )
    assert repository.get_assessment_definition_review(review.id) == review


def test_local_governance_bundle_import_fails_closed_outside_development(
    session: Session,
) -> None:
    definition = _definition("production_fixture")
    bundle = AssessmentGovernanceBundle(
        bundle_version=ASSESSMENT_GOVERNANCE_BUNDLE_VERSION,
        definition=definition,
    )

    with pytest.raises(LocalAssessmentGovernanceImportError, match="disabled in production"):
        import_assessment_governance_bundle(
            session,
            bundle,
            settings=Settings(
                environment="production",
                auth_mode="external",
                external_auth_issuer="https://issuer.example/",
                external_auth_audience="https://api.agas.example",
                external_auth_jwks_url="https://issuer.example/.well-known/jwks.json",
                database_url="sqlite+pysqlite:///:memory:",
            ),
            imported_at=NOW,
        )

    assert DomainRepository(session).get_assessment_definition(definition.id) is None


def test_local_governance_bundle_rolls_back_definition_when_evidence_is_unknown(
    session: Session,
) -> None:
    missing_evidence = _evidence()
    definition = _definition("rollback_fixture")
    review = _approved_review(definition, missing_evidence)
    bundle = AssessmentGovernanceBundle(
        bundle_version=ASSESSMENT_GOVERNANCE_BUNDLE_VERSION,
        definition=definition,
        review=review,
    )

    with pytest.raises(LocalAssessmentGovernanceImportError, match="unknown evidence claim"):
        import_assessment_governance_bundle(
            session,
            bundle,
            settings=_development_settings(),
            imported_at=NOW + timedelta(minutes=1),
        )

    repository = DomainRepository(session)
    assert repository.get_assessment_definition(definition.id) is None
    assert repository.get_assessment_definition_review(review.id) is None


def test_local_governance_bundle_rejects_unreviewed_evidence_for_approved_review(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    evidence = _evidence()
    repository.add_evidence_claim(evidence)
    session.commit()
    definition = _definition("unready_review_evidence_fixture")
    review = _approved_review(definition, evidence)
    bundle = AssessmentGovernanceBundle(
        bundle_version=ASSESSMENT_GOVERNANCE_BUNDLE_VERSION,
        definition=definition,
        review=review,
    )

    with pytest.raises(
        LocalAssessmentGovernanceImportError,
        match="approved assessment review evidence is not ready at its review time",
    ):
        import_assessment_governance_bundle(
            session,
            bundle,
            settings=_development_settings(),
            imported_at=NOW + timedelta(minutes=1),
        )

    assert repository.get_assessment_definition(definition.id) is None
    assert repository.get_assessment_definition_review(review.id) is None
    assert repository.get_evidence_claim(evidence.id) == evidence


def test_local_governance_bundle_rejects_unreviewed_evidence_for_approved_policy(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    ready_evidence = _persist_approved_evidence(session)
    unready_evidence = _evidence()
    repository.add_evidence_claim(unready_evidence)
    session.commit()
    definition = _definition("unready_policy_evidence_fixture")
    review = _approved_review(definition, ready_evidence)
    policy = _approved_policy(definition, review, unready_evidence)
    bundle = AssessmentGovernanceBundle(
        bundle_version=ASSESSMENT_GOVERNANCE_BUNDLE_VERSION,
        definition=definition,
        review=review,
        estimation_policy=policy,
    )

    with pytest.raises(
        LocalAssessmentGovernanceImportError,
        match="approved capability-estimation policy evidence is not ready at its review time",
    ):
        import_assessment_governance_bundle(
            session,
            bundle,
            settings=_development_settings(),
            imported_at=NOW + timedelta(minutes=1),
        )

    assert repository.get_assessment_definition(definition.id) is None
    assert repository.get_assessment_definition_review(review.id) is None
    assert repository.get_capability_estimation_policy(policy.id) is None
    assert repository.get_evidence_claim(ready_evidence.id) == ready_evidence
    assert repository.get_evidence_claim(unready_evidence.id) == unready_evidence


def test_later_evidence_approval_does_not_retroactively_authorize_older_assessment(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    source = _source()
    evidence = _evidence(source)
    definition = _definition("nonretroactive_evidence_fixture")
    review = _approved_review(definition, evidence)
    policy = _approved_policy(definition, review, evidence)
    late_evidence_review = _evidence_review(
        evidence,
        reviewed_at=NOW + timedelta(hours=1),
    )
    repository.add_evidence_source(source)
    repository.add_evidence_claim(evidence)
    repository.add_assessment_definition(definition)
    repository.add_assessment_definition_review(review)
    repository.add_capability_estimation_policy(policy)
    repository.add_evidence_claim_review(late_evidence_review)
    session.commit()

    item = AssessmentGovernanceProjector(session).project(NOW + timedelta(hours=2)).items[0]

    assert item.status == "approved"
    assert item.readiness == "blocked"
    assert item.review_evidence_governance is not None
    assert item.review_evidence_governance.evaluated_at == NOW
    assert item.review_evidence_governance.claim_results[0].current_review is None
    assert item.estimation_policy_evidence_governance is not None
    assert item.estimation_policy_evidence_governance.evaluated_at == NOW
    assert item.estimation_policy_evidence_governance.claim_results[0].current_review is None
    assert any("evaluation time" in issue for issue in item.issues)
