from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from agas_api.database import database_session_dependency
from agas_api.evidence_governance import EvidenceGovernanceProjector
from agas_api.evidence_governance_admin import (
    EVIDENCE_GOVERNANCE_BUNDLE_VERSION,
    EvidenceGovernanceBundle,
    LocalEvidenceGovernanceImportError,
    import_evidence_governance_bundle,
)
from agas_api.identity import authenticated_principal_dependency
from agas_api.identity_admin import set_account_role
from agas_api.main import app
from agas_api.settings import Settings
from agas_domain import (
    AccountRole,
    AccountRoleStatus,
    Applicability,
    EvidenceClaim,
    EvidenceClaimReview,
    EvidenceReviewDecision,
    EvidenceSource,
    EvidenceSourceIdentifier,
    EvidenceStrength,
)
from agas_domain.persistence.models import (
    EvidenceClaimReviewRecord,
    ImmutableHistoricalRecordError,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

NOW = datetime(2026, 8, 31, 14, 0, tzinfo=UTC)


def _settings() -> Settings:
    return Settings(
        environment="development",
        auth_mode="development",
        database_url="sqlite+pysqlite:///:memory:",
    )


def _source() -> EvidenceSource:
    pmid = EvidenceSourceIdentifier(scheme="pmid", value="12345678")
    doi = EvidenceSourceIdentifier(scheme="doi", value="10.0000/software-fixture")
    return EvidenceSource(
        created_at=NOW,
        title="Evidence governance software fixture",
        authors=("Test Author",),
        journal="Software Test Journal",
        publication_year=2026,
        abstract="Synthetic metadata used only to exercise software provenance behavior.",
        publication_types=("Test Fixture",),
        primary_identifier=pmid,
        source_identifiers=(pmid, doi),
        metadata_provider="pubmed",
        retrieval_uri="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        retrieval_query="12345678[pmid]",
        retrieved_at=NOW,
        metadata_version="pubmed-xml@1",
        provenance_notes=("Synthetic fixture; not scientific evidence.",),
    )


def _claim(source: EvidenceSource) -> EvidenceClaim:
    return EvidenceClaim(
        created_at=NOW,
        claim="Exact source snapshots remain linked through persistence.",
        domain="software_test",
        population="not applicable",
        intervention="not applicable",
        outcome="provenance round trip",
        study_design="test fixture",
        uncertainty="This is not a scientific training claim.",
        limitations=("Synthetic fixture only.",),
        evidence_strength=EvidenceStrength.INSUFFICIENT,
        athlete_applicability=Applicability.UNKNOWN,
        applicability_notes="Not applicable to an athlete.",
        source_identifiers=source.source_identifiers,
        source_record_ids=(source.id,),
        reviewer="automated-test",
        claim_version="fixture@1.0.0",
    )


def _review(claim: EvidenceClaim) -> EvidenceClaimReview:
    return EvidenceClaimReview(
        created_at=NOW + timedelta(hours=1),
        evidence_claim_id=claim.id,
        decision=EvidenceReviewDecision.APPROVED,
        sequence_number=1,
        reviewed_at=NOW + timedelta(hours=1),
        reviewer="qualified-reviewer-fixture",
        source_verification_rationale="The exact synthetic source snapshot was checked.",
        extraction_rationale="The claim mirrors the software-only fixture behavior.",
        evidence_strength_rationale="Insufficient is correct for a software fixture.",
        applicability_rationale="The fixture has no athlete applicability.",
        uncertainty="No scientific conclusion is represented.",
        conflict_disclosure="No conflicts declared for this software fixture.",
        review_version="fixture-review@1.0.0",
    )


def _bundle(
    source: EvidenceSource,
    claim: EvidenceClaim,
    reviews: tuple[EvidenceClaimReview, ...] = (),
) -> EvidenceGovernanceBundle:
    return EvidenceGovernanceBundle(
        bundle_version=EVIDENCE_GOVERNANCE_BUNDLE_VERSION,
        sources=(source,),
        claims=(claim,),
        reviews=reviews,
    )


def test_evidence_bundle_requires_exact_source_records_for_every_claim() -> None:
    source = _source()
    claim = _claim(source).model_copy(update={"source_record_ids": (uuid4(),)})

    with pytest.raises(ValidationError, match="unbundled source records"):
        _bundle(source, claim)


def test_claim_cannot_predate_the_source_snapshot_it_interprets(session: Session) -> None:
    source = _source()
    claim = _claim(source).model_copy(update={"created_at": NOW - timedelta(seconds=1)})
    repository = DomainRepository(session)
    repository.add_evidence_source(source)
    session.flush()

    with pytest.raises(DomainIntegrityError, match="cannot predate linked source snapshot"):
        repository.add_evidence_claim(claim)


def test_local_evidence_bundle_import_is_atomic_idempotent_and_round_trips(
    session: Session,
) -> None:
    source = _source()
    claim = _claim(source)
    review = _review(claim)
    bundle = _bundle(source, claim, (review,))

    first = import_evidence_governance_bundle(session, bundle, settings=_settings())
    second = import_evidence_governance_bundle(session, bundle, settings=_settings())
    repository = DomainRepository(session)

    assert first.created_source_ids == (source.id,)
    assert first.created_claim_ids == (claim.id,)
    assert first.created_review_ids == (review.id,)
    assert second.created_source_ids == ()
    assert second.created_claim_ids == ()
    assert second.created_review_ids == ()
    assert repository.get_evidence_source(source.id) == source
    assert repository.get_evidence_claim(claim.id) == claim
    assert repository.get_evidence_claim_review(review.id) == review


def test_evidence_governance_projection_separates_claim_storage_from_approval(
    session: Session,
) -> None:
    source = _source()
    claim = _claim(source)
    review = _review(claim)
    import_evidence_governance_bundle(
        session, _bundle(source, claim, (review,)), settings=_settings()
    )

    before_review = EvidenceGovernanceProjector(session).project(NOW + timedelta(minutes=30))
    after_review = EvidenceGovernanceProjector(session).project(NOW + timedelta(hours=2))

    assert before_review.items[0].status == "unreviewed"
    assert before_review.items[0].readiness == "blocked"
    assert before_review.items[0].current_review is None
    assert after_review.items[0].status == "approved"
    assert after_review.items[0].readiness == "ready"
    assert after_review.items[0].sources == (source,)
    assert after_review.items[0].review_history == (review,)


def test_legacy_claim_without_source_snapshots_remains_visibly_blocked(
    session: Session,
) -> None:
    source = _source()
    claim = _claim(source).model_copy(update={"source_record_ids": ()})
    repository = DomainRepository(session)
    repository.add_evidence_claim(claim)
    session.commit()

    item = EvidenceGovernanceProjector(session).project(NOW + timedelta(hours=2)).items[0]

    assert item.status == "unreviewed"
    assert item.readiness == "blocked"
    assert "claim has no exact evidence-source snapshot links" in item.issues
    assert "claim had no scientific review at the evaluation time" in item.issues


def test_evidence_review_lineage_rejects_cross_claim_predecessor(session: Session) -> None:
    source = _source()
    first_claim = _claim(source)
    second_claim = _claim(source).model_copy(update={"id": uuid4()})
    first_review = _review(first_claim)
    repository = DomainRepository(session)
    repository.add_evidence_source(source)
    repository.add_evidence_claim(first_claim)
    repository.add_evidence_claim(second_claim)
    repository.add_evidence_claim_review(first_review)
    session.flush()
    invalid_successor = _review(second_claim).model_copy(
        update={
            "id": uuid4(),
            "sequence_number": 2,
            "supersedes_review_id": first_review.id,
            "reviewed_at": first_review.reviewed_at + timedelta(hours=1),
            "created_at": first_review.created_at + timedelta(hours=1),
        }
    )

    with pytest.raises(DomainIntegrityError, match="same claim"):
        repository.add_evidence_claim_review(invalid_successor)


def test_evidence_review_history_cannot_be_rewritten(session: Session) -> None:
    source = _source()
    claim = _claim(source)
    review = _review(claim)
    import_evidence_governance_bundle(
        session, _bundle(source, claim, (review,)), settings=_settings()
    )
    persisted = session.get(EvidenceClaimReviewRecord, review.id)
    assert persisted is not None
    persisted.uncertainty = "Silently rewritten uncertainty."

    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.commit()
    session.rollback()

    assert DomainRepository(session).get_evidence_claim_review(review.id) == review


def test_evidence_governance_reuses_read_only_scientific_governance_role(
    session: Session,
) -> None:
    for subject, role in (
        ("planning-only", AccountRole.PLANNING_REVIEWER),
        ("scientific-governance", AccountRole.ASSESSMENT_REVIEWER),
    ):
        set_account_role(
            session,
            issuer="urn:agas:development",
            subject=subject,
            role=role,
            status=AccountRoleStatus.ACTIVE,
            assigned_at=NOW,
            rationale="Exercise the read-only evidence-governance authorization boundary.",
        )

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    try:
        unauthenticated = TestClient(app).get("/v1/operator/evidence-governance")
        planning_only = TestClient(app).get(
            "/v1/operator/evidence-governance",
            headers={"Authorization": "Bearer dev.planning-only"},
        )
        authorized = TestClient(app).get(
            "/v1/operator/evidence-governance",
            headers={"Authorization": "Bearer dev.scientific-governance"},
            params={"at": (NOW + timedelta(minutes=1)).isoformat()},
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert unauthenticated.status_code == 401
    assert planning_only.status_code == 403
    assert planning_only.json() == {"detail": "active assessment_reviewer role required"}
    assert authorized.status_code == 200
    assert authorized.json()["items"] == []


def test_local_evidence_bundle_rejects_immutable_content_collision(session: Session) -> None:
    source = _source()
    claim = _claim(source)
    import_evidence_governance_bundle(session, _bundle(source, claim), settings=_settings())
    conflicting_source = source.model_copy(update={"title": "Silently rewritten title"})

    with pytest.raises(LocalEvidenceGovernanceImportError, match="immutable content"):
        import_evidence_governance_bundle(
            session,
            _bundle(conflicting_source, claim),
            settings=_settings(),
        )

    assert DomainRepository(session).get_evidence_source(source.id) == source


def test_local_evidence_bundle_rolls_back_when_source_lineage_is_unknown(
    session: Session,
) -> None:
    first = _source()
    later = EvidenceSource(
        title=first.title,
        authors=first.authors,
        journal=first.journal,
        publication_year=first.publication_year,
        abstract=first.abstract,
        publication_types=first.publication_types,
        primary_identifier=first.primary_identifier,
        source_identifiers=first.source_identifiers,
        metadata_provider=first.metadata_provider,
        retrieval_uri=first.retrieval_uri,
        retrieval_query=first.retrieval_query,
        retrieved_at=first.retrieved_at + timedelta(days=1),
        metadata_version="pubmed-xml@2",
        provenance_notes=first.provenance_notes,
        sequence_number=2,
        supersedes_source_id=uuid4(),
    )
    claim = _claim(later)

    with pytest.raises(LocalEvidenceGovernanceImportError, match="unknown predecessor"):
        import_evidence_governance_bundle(
            session,
            _bundle(later, claim),
            settings=_settings(),
        )

    repository = DomainRepository(session)
    assert repository.get_evidence_source(later.id) is None
    assert repository.get_evidence_claim(claim.id) is None


def test_local_evidence_bundle_fails_closed_outside_development(session: Session) -> None:
    source = _source()
    claim = _claim(source)

    with pytest.raises(LocalEvidenceGovernanceImportError, match="disabled in production"):
        import_evidence_governance_bundle(
            session,
            _bundle(source, claim),
            settings=Settings(
                environment="production",
                auth_mode="external",
                external_auth_issuer="https://issuer.example/",
                external_auth_audience="https://api.agas.example",
                external_auth_jwks_url="https://issuer.example/.well-known/jwks.json",
                database_url="sqlite+pysqlite:///:memory:",
            ),
        )

    assert DomainRepository(session).get_evidence_source(source.id) is None
