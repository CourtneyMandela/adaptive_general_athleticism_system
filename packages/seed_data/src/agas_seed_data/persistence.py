from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from typing import TypeVar
from uuid import NAMESPACE_URL, UUID, uuid5

from agas_domain import CatalogImport
from agas_domain.models import VersionedRecord, utc_now
from agas_domain.persistence.repository import DomainRepository
from pydantic import BaseModel, ConfigDict

from agas_seed_data.catalog import SeedCatalog

IMPORTER_VERSION = "seed-catalog-importer@1.0.0"
_Record = TypeVar("_Record", bound=VersionedRecord)


class SeedCatalogImportError(ValueError):
    """Raised when catalog content conflicts with immutable persisted records."""


class SeedCatalogImportResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    catalog_import: CatalogImport
    created: bool
    inserted_evidence_claims: int = 0
    inserted_adaptations: int = 0
    inserted_equipment: int = 0
    inserted_exercises: int = 0


class SeedCatalogImporter:
    """Atomically stage one validated catalog in an existing database transaction."""

    def __init__(self, repository: DomainRepository) -> None:
        self.repository = repository

    def import_catalog(
        self, catalog: SeedCatalog, *, imported_at: datetime | None = None
    ) -> SeedCatalogImportResult:
        digest = _catalog_digest(catalog)
        expected = _catalog_import(catalog, digest, imported_at or utc_now())
        existing_import = self.repository.get_catalog_import_by_version(
            catalog.manifest.catalog_version
        )
        if existing_import is not None:
            if existing_import.content_digest != digest or _catalog_ids(existing_import) != (
                tuple(item.id for item in catalog.evidence_claims),
                tuple(item.id for item in catalog.adaptations),
                tuple(item.id for item in catalog.equipment),
                tuple(item.id for item in catalog.exercises),
            ):
                raise SeedCatalogImportError(
                    "catalog version already exists with different immutable content"
                )
            self._verify_existing_content(catalog)
            return SeedCatalogImportResult(catalog_import=existing_import, created=False)

        counts = [0, 0, 0, 0]
        with self.repository.session.begin_nested():
            counts[0] = self._import_records(
                "evidence claim",
                catalog.evidence_claims,
                self.repository.get_evidence_claim,
                self.repository.add_evidence_claim,
            )
            self.repository.session.flush()
            counts[1] = self._import_records(
                "adaptation",
                catalog.adaptations,
                self.repository.get_adaptation,
                self.repository.add_adaptation,
            )
            counts[2] = self._import_records(
                "equipment",
                catalog.equipment,
                self.repository.get_equipment,
                self.repository.add_equipment,
            )
            self.repository.session.flush()
            counts[3] = self._import_records(
                "exercise",
                catalog.exercises,
                self.repository.get_exercise,
                self.repository.add_exercise,
            )
            self.repository.session.flush()
            self.repository.add_catalog_import(expected)
            self.repository.session.flush()
        return SeedCatalogImportResult(
            catalog_import=expected,
            created=True,
            inserted_evidence_claims=counts[0],
            inserted_adaptations=counts[1],
            inserted_equipment=counts[2],
            inserted_exercises=counts[3],
        )

    def _verify_existing_content(self, catalog: SeedCatalog) -> None:
        self._verify_records(
            "evidence claim", catalog.evidence_claims, self.repository.get_evidence_claim
        )
        self._verify_records("adaptation", catalog.adaptations, self.repository.get_adaptation)
        self._verify_records("equipment", catalog.equipment, self.repository.get_equipment)
        self._verify_records("exercise", catalog.exercises, self.repository.get_exercise)

    @staticmethod
    def _verify_records(
        label: str,
        records: tuple[_Record, ...],
        getter: Callable[[UUID], _Record | None],
    ) -> None:
        for record in records:
            if getter(record.id) != record:
                raise SeedCatalogImportError(
                    f"persisted {label} {record.id} differs from catalog content"
                )

    @staticmethod
    def _import_records(
        label: str,
        records: tuple[_Record, ...],
        getter: Callable[[UUID], _Record | None],
        adder: Callable[[_Record], None],
    ) -> int:
        inserted = 0
        for record in records:
            existing = getter(record.id)
            if existing is None:
                adder(record)
                inserted += 1
            elif existing != record:
                raise SeedCatalogImportError(
                    f"persisted {label} {record.id} differs from catalog content"
                )
        return inserted


def _catalog_digest(catalog: SeedCatalog) -> str:
    payload = json.dumps(
        catalog.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    ).encode()
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _catalog_import(catalog: SeedCatalog, digest: str, imported_at: datetime) -> CatalogImport:
    manifest = catalog.manifest
    return CatalogImport(
        id=uuid5(NAMESPACE_URL, f"agas:seed-catalog:{manifest.catalog_version}"),
        created_at=imported_at,
        catalog_version=manifest.catalog_version,
        review_status=manifest.review_status.value,
        reviewed_by=manifest.reviewed_by,
        reviewed_at=manifest.reviewed_at,
        scope=manifest.scope,
        notes=manifest.notes,
        content_digest=digest,
        evidence_claim_ids=tuple(item.id for item in catalog.evidence_claims),
        adaptation_ids=tuple(item.id for item in catalog.adaptations),
        equipment_ids=tuple(item.id for item in catalog.equipment),
        exercise_ids=tuple(item.id for item in catalog.exercises),
        imported_at=imported_at,
        importer_version=IMPORTER_VERSION,
    )


def _catalog_ids(
    catalog_import: CatalogImport,
) -> tuple[tuple[UUID, ...], tuple[UUID, ...], tuple[UUID, ...], tuple[UUID, ...]]:
    return (
        catalog_import.evidence_claim_ids,
        catalog_import.adaptation_ids,
        catalog_import.equipment_ids,
        catalog_import.exercise_ids,
    )
