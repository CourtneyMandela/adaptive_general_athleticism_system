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


def _evidence() -> EvidenceClaim:
    return EvidenceClaim(
        created_at=NOW,
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
        source_identifiers=(
            EvidenceSourceIdentifier(scheme="other", value="urn:agas:test:governance"),
        ),
        reviewer="automated-test-fixture",
        claim_version="software-fixture@1.0.0",
    )


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
    evidence = _evidence()
    unreviewed = _definition("unreviewed_fixture")
    ready = _definition("ready_fixture")
    review = _approved_review(ready, evidence)
    policy = _approved_policy(ready, review, evidence)
    repository.add_evidence_claim(evidence)
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
    evidence = _evidence()
    definition = _definition("curated_fixture")
    review = _approved_review(definition, evidence)
    policy = _approved_policy(definition, review, evidence)
    repository.add_evidence_claim(evidence)
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

    with pytest.raises(LocalAssessmentGovernanceImportError, match="unknown assessment review"):
        import_assessment_governance_bundle(
            session,
            bundle,
            settings=_development_settings(),
            imported_at=NOW + timedelta(minutes=1),
        )

    repository = DomainRepository(session)
    assert repository.get_assessment_definition(definition.id) is None
    assert repository.get_assessment_definition_review(review.id) is None
