from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from agas_api.evidence_governance_admin import (
    EVIDENCE_GOVERNANCE_BUNDLE_VERSION,
    EvidenceGovernanceBundle,
    LocalEvidenceGovernanceImportError,
    import_evidence_governance_bundle,
)
from agas_api.settings import Settings
from agas_domain import (
    Applicability,
    EvidenceClaim,
    EvidenceSource,
    EvidenceSourceIdentifier,
    EvidenceStrength,
)
from agas_domain.persistence.repository import DomainRepository
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


def _bundle(source: EvidenceSource, claim: EvidenceClaim) -> EvidenceGovernanceBundle:
    return EvidenceGovernanceBundle(
        bundle_version=EVIDENCE_GOVERNANCE_BUNDLE_VERSION,
        sources=(source,),
        claims=(claim,),
    )


def test_evidence_bundle_requires_exact_source_records_for_every_claim() -> None:
    source = _source()
    claim = _claim(source).model_copy(update={"source_record_ids": (uuid4(),)})

    with pytest.raises(ValidationError, match="unbundled source records"):
        _bundle(source, claim)


def test_local_evidence_bundle_import_is_atomic_idempotent_and_round_trips(
    session: Session,
) -> None:
    source = _source()
    claim = _claim(source)
    bundle = _bundle(source, claim)

    first = import_evidence_governance_bundle(session, bundle, settings=_settings())
    second = import_evidence_governance_bundle(session, bundle, settings=_settings())
    repository = DomainRepository(session)

    assert first.created_source_ids == (source.id,)
    assert first.created_claim_ids == (claim.id,)
    assert second.created_source_ids == ()
    assert second.created_claim_ids == ()
    assert repository.get_evidence_source(source.id) == source
    assert repository.get_evidence_claim(claim.id) == claim


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
                database_url="sqlite+pysqlite:///:memory:",
            ),
        )

    assert DomainRepository(session).get_evidence_source(source.id) is None
