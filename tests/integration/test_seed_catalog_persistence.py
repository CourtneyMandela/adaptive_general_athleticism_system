from datetime import UTC, datetime

import pytest
from agas_domain.persistence.models import (
    AthleteRecord,
    CatalogImportRecord,
    ImmutableHistoricalRecordError,
)
from agas_domain.persistence.repository import DomainRepository
from agas_seed_data import (
    SeedCatalog,
    SeedCatalogImporter,
    SeedCatalogImportError,
    load_seed_catalog,
)
from sqlalchemy.orm import Session

IMPORTED_AT = datetime(2026, 8, 21, 3, 0, tzinfo=UTC)


def test_seed_catalog_import_is_audited_idempotent_and_excludes_synthetic_athlete(
    session: Session,
) -> None:
    catalog = load_seed_catalog()
    repository = DomainRepository(session)
    importer = SeedCatalogImporter(repository)

    first = importer.import_catalog(catalog, imported_at=IMPORTED_AT)
    session.commit()
    session.expire_all()

    assert first.created is True
    assert first.inserted_evidence_claims == len(catalog.evidence_claims)
    assert first.inserted_adaptations == len(catalog.adaptations)
    assert first.inserted_equipment == len(catalog.equipment)
    assert first.inserted_exercises == len(catalog.exercises)
    assert repository.get_catalog_import(first.catalog_import.id) == first.catalog_import
    assert session.get(AthleteRecord, catalog.travel_scenario.athlete.id) is None
    assert all(repository.get_evidence_claim(item.id) == item for item in catalog.evidence_claims)
    assert all(repository.get_adaptation(item.id) == item for item in catalog.adaptations)
    assert all(repository.get_equipment(item.id) == item for item in catalog.equipment)
    assert all(repository.get_exercise(item.id) == item for item in catalog.exercises)

    second = importer.import_catalog(catalog, imported_at=IMPORTED_AT)
    assert second.created is False
    assert second.catalog_import == first.catalog_import
    assert second.inserted_evidence_claims == 0
    assert second.inserted_adaptations == 0
    assert second.inserted_equipment == 0
    assert second.inserted_exercises == 0

    import_record = session.get(CatalogImportRecord, first.catalog_import.id)
    assert import_record is not None
    import_record.review_status = "production_approved"
    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.flush()


def test_seed_catalog_import_rolls_back_partial_inserts_on_identity_collision(
    session: Session,
) -> None:
    catalog = load_seed_catalog()
    repository = DomainRepository(session)
    conflicting_equipment = catalog.equipment[0].model_copy(update={"name": "Conflicting item"})
    repository.add_equipment(conflicting_equipment)
    session.commit()

    with pytest.raises(SeedCatalogImportError, match="differs from catalog content"):
        SeedCatalogImporter(repository).import_catalog(catalog, imported_at=IMPORTED_AT)

    assert repository.get_evidence_claim(catalog.evidence_claims[0].id) is None
    assert repository.get_adaptation(catalog.adaptations[0].id) is None
    assert repository.get_catalog_import_by_version(catalog.manifest.catalog_version) is None


def test_seed_catalog_version_cannot_be_reused_for_different_content(session: Session) -> None:
    catalog = load_seed_catalog()
    repository = DomainRepository(session)
    importer = SeedCatalogImporter(repository)
    importer.import_catalog(catalog, imported_at=IMPORTED_AT)
    session.commit()

    changed_exercise = catalog.exercises[0].model_copy(update={"name": "Changed name"})
    changed = SeedCatalog.model_validate(
        {**catalog.model_dump(), "exercises": (changed_exercise, *catalog.exercises[1:])}
    )
    with pytest.raises(SeedCatalogImportError, match="different immutable content"):
        importer.import_catalog(changed, imported_at=IMPORTED_AT)
