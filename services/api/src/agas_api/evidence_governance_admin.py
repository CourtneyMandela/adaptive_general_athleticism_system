from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from agas_domain import EvidenceClaim, EvidenceSource
from agas_domain.models import VersionedRecord
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agas_api.database import database_session
from agas_api.settings import Settings, get_settings

EVIDENCE_GOVERNANCE_BUNDLE_VERSION = "evidence-governance-bundle@1.0.0"


class EvidenceGovernanceBundle(BaseModel):
    """Exact source snapshots and claims prepared through an external review process."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_version: Literal["evidence-governance-bundle@1.0.0"]
    sources: Annotated[tuple[EvidenceSource, ...], Field(min_length=1)]
    claims: Annotated[tuple[EvidenceClaim, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_references(self) -> EvidenceGovernanceBundle:
        source_ids = [source.id for source in self.sources]
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("bundled evidence sources must have unique ids")
        claim_ids = [claim.id for claim in self.claims]
        if len(set(claim_ids)) != len(claim_ids):
            raise ValueError("bundled evidence claims must have unique ids")

        sources_by_id = {source.id: source for source in self.sources}
        for claim in self.claims:
            if not claim.source_record_ids:
                raise ValueError(
                    f"evidence claim {claim.id} must reference at least one source record"
                )
            unknown = set(claim.source_record_ids) - sources_by_id.keys()
            if unknown:
                raise ValueError(
                    f"evidence claim {claim.id} references unbundled source records: "
                    f"{sorted(map(str, unknown))}"
                )
            claim_identifiers = {
                (identifier.scheme, identifier.value.casefold())
                for identifier in claim.source_identifiers
            }
            linked_identifiers: set[tuple[str, str]] = set()
            for source_id in claim.source_record_ids:
                source = sources_by_id[source_id]
                linked_identifiers.update(
                    (identifier.scheme, identifier.value.casefold())
                    for identifier in source.source_identifiers
                )
                primary = (
                    source.primary_identifier.scheme,
                    source.primary_identifier.value.casefold(),
                )
                if primary not in claim_identifiers:
                    raise ValueError(
                        f"evidence claim {claim.id} omits source {source_id}'s primary identifier"
                    )
            if not claim_identifiers.issubset(linked_identifiers):
                raise ValueError(
                    f"evidence claim {claim.id} contains identifiers absent from its source records"
                )
        return self


class EvidenceGovernanceImportResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_version: str
    source_ids: tuple[UUID, ...]
    claim_ids: tuple[UUID, ...]
    created_source_ids: tuple[UUID, ...]
    created_claim_ids: tuple[UUID, ...]


class LocalEvidenceGovernanceImportError(RuntimeError):
    pass


def import_evidence_governance_bundle(
    session: Session,
    bundle: EvidenceGovernanceBundle,
    *,
    settings: Settings,
) -> EvidenceGovernanceImportResult:
    """Idempotently persist exact immutable source snapshots and their claims."""

    _require_local_development(settings)
    repository = DomainRepository(session)
    created_source_ids: list[UUID] = []
    created_claim_ids: list[UUID] = []
    try:
        for source in sorted(
            bundle.sources,
            key=lambda item: (item.sequence_number, item.created_at, str(item.id)),
        ):
            if _ensure_exact(
                label="evidence source",
                expected=source,
                existing=repository.get_evidence_source(source.id),
                add=repository.add_evidence_source,
            ):
                created_source_ids.append(source.id)
            session.flush()

        for claim in bundle.claims:
            if _ensure_exact(
                label="evidence claim",
                expected=claim,
                existing=repository.get_evidence_claim(claim.id),
                add=repository.add_evidence_claim,
            ):
                created_claim_ids.append(claim.id)
            session.flush()
        session.commit()
    except (
        DomainIntegrityError,
        IntegrityError,
        LocalEvidenceGovernanceImportError,
    ) as error:
        session.rollback()
        if isinstance(error, LocalEvidenceGovernanceImportError):
            raise
        raise LocalEvidenceGovernanceImportError(str(error)) from error
    except Exception:
        session.rollback()
        raise

    return EvidenceGovernanceImportResult(
        bundle_version=bundle.bundle_version,
        source_ids=tuple(source.id for source in bundle.sources),
        claim_ids=tuple(claim.id for claim in bundle.claims),
        created_source_ids=tuple(created_source_ids),
        created_claim_ids=tuple(created_claim_ids),
    )


def _ensure_exact[Record: VersionedRecord](
    *,
    label: str,
    expected: Record,
    existing: Record | None,
    add: Callable[[Record], None],
) -> bool:
    if existing is None:
        add(expected)
        return True
    if existing != expected:
        raise LocalEvidenceGovernanceImportError(
            f"persisted {label} {expected.id} differs from bundled immutable content"
        )
    return False


def _require_local_development(settings: Settings) -> None:
    if settings.environment.casefold() in {"production", "prod"}:
        raise LocalEvidenceGovernanceImportError(
            "local evidence-governance import is disabled in production"
        )
    if settings.auth_mode != "development":
        raise LocalEvidenceGovernanceImportError(
            "local evidence-governance import requires development authentication mode"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect the evidence-governance bundle schema or import exact source and claim "
            "records in local development."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("schema", help="Print the versioned JSON bundle schema")
    import_parser = subparsers.add_parser(
        "import-bundle", help="Import exact scientific source snapshots and claims"
    )
    import_parser.add_argument("--input-file", type=Path, required=True)
    arguments = parser.parse_args()

    if arguments.command == "schema":
        print(json.dumps(EvidenceGovernanceBundle.model_json_schema(), sort_keys=True))
        return
    if arguments.command != "import-bundle":
        parser.error("unsupported evidence-governance administration command")
    try:
        bundle = EvidenceGovernanceBundle.model_validate_json(
            arguments.input_file.read_text(encoding="utf-8")
        )
        with database_session() as session:
            result = import_evidence_governance_bundle(
                session,
                bundle,
                settings=get_settings(),
            )
    except (
        DomainIntegrityError,
        LocalEvidenceGovernanceImportError,
        OSError,
        ValidationError,
        ValueError,
    ) as error:
        parser.error(str(error))
    print(json.dumps(result.model_dump(mode="json"), sort_keys=True))


if __name__ == "__main__":
    main()
