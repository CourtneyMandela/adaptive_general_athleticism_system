from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from agas_domain import (
    AssessmentDefinition,
    AssessmentDefinitionReview,
    AssessmentReviewDecision,
    CapabilityEstimationPolicy,
)
from agas_domain.models import VersionedRecord
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agas_api.assessment_governance import (
    AssessmentGovernanceProjectionError,
    AssessmentGovernanceProjector,
)
from agas_api.database import database_session
from agas_api.evidence_governance import (
    EvidenceAuthorityEvaluationError,
    EvidenceAuthorityEvaluator,
    EvidenceAuthorityNotReadyError,
)
from agas_api.settings import Settings, get_settings

ASSESSMENT_GOVERNANCE_BUNDLE_VERSION = "assessment-governance-bundle@1.0.0"


class AssessmentGovernanceBundle(BaseModel):
    """Exact immutable assessment authority records prepared outside the application."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_version: Literal["assessment-governance-bundle@1.0.0"]
    definition: AssessmentDefinition
    review: AssessmentDefinitionReview | None = None
    estimation_policy: CapabilityEstimationPolicy | None = None

    @model_validator(mode="after")
    def validate_lineage(self) -> AssessmentGovernanceBundle:
        if self.review is not None and self.review.assessment_definition_id != self.definition.id:
            raise ValueError("assessment review must govern the bundled definition")
        if self.estimation_policy is not None:
            if self.review is None:
                raise ValueError("an estimation policy bundle must include its exact review")
            if self.estimation_policy.assessment_definition_id != self.definition.id:
                raise ValueError("estimation policy must govern the bundled definition")
            if self.estimation_policy.assessment_definition_review_id != self.review.id:
                raise ValueError("estimation policy must target the bundled review")
        return self


class AssessmentGovernanceImportResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_version: str
    definition_id: UUID
    review_id: UUID | None
    estimation_policy_id: UUID | None
    definition_created: bool
    review_created: bool
    estimation_policy_created: bool
    readiness: Literal["ready", "blocked"]
    issues: tuple[str, ...]


class LocalAssessmentGovernanceImportError(RuntimeError):
    pass


def import_assessment_governance_bundle(
    session: Session,
    bundle: AssessmentGovernanceBundle,
    *,
    settings: Settings,
    imported_at: datetime | None = None,
) -> AssessmentGovernanceImportResult:
    """Idempotently import exact reviewed records through a local-only transaction."""

    _require_local_development(settings)
    instant = imported_at or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("assessment-governance import time must include a timezone")

    repository = DomainRepository(session)
    evidence_evaluator = EvidenceAuthorityEvaluator(session)
    try:
        definition_created = _ensure_exact(
            label="assessment definition",
            expected=bundle.definition,
            existing=repository.get_assessment_definition(bundle.definition.id),
            add=repository.add_assessment_definition,
        )
        session.flush()

        review_created = False
        if bundle.review is not None:
            existing_review = repository.get_assessment_definition_review(bundle.review.id)
            if (
                existing_review is None
                and bundle.review.decision is AssessmentReviewDecision.APPROVED
            ):
                _require_ready_evidence(
                    evidence_evaluator,
                    label="approved assessment review",
                    evidence_claim_ids=bundle.review.evidence_claim_ids,
                    reviewed_at=bundle.review.reviewed_at,
                )
            review_created = _ensure_exact(
                label="assessment definition review",
                expected=bundle.review,
                existing=existing_review,
                add=repository.add_assessment_definition_review,
            )
            session.flush()

        estimation_policy_created = False
        if bundle.estimation_policy is not None:
            existing_policy = repository.get_capability_estimation_policy(
                bundle.estimation_policy.id
            )
            if (
                existing_policy is None
                and bundle.estimation_policy.decision is AssessmentReviewDecision.APPROVED
            ):
                _require_ready_evidence(
                    evidence_evaluator,
                    label="approved capability-estimation policy",
                    evidence_claim_ids=bundle.estimation_policy.evidence_claim_ids,
                    reviewed_at=bundle.estimation_policy.reviewed_at,
                )
            estimation_policy_created = _ensure_exact(
                label="capability estimation policy",
                expected=bundle.estimation_policy,
                existing=existing_policy,
                add=repository.add_capability_estimation_policy,
            )
            session.flush()

        projection = AssessmentGovernanceProjector(session).project(instant)
        item = next(
            (
                candidate
                for candidate in projection.items
                if candidate.definition.id == bundle.definition.id
            ),
            None,
        )
        if item is None:
            raise LocalAssessmentGovernanceImportError(
                "bundled assessment definition is not visible at the import time"
            )
        session.commit()
    except (
        AssessmentGovernanceProjectionError,
        DomainIntegrityError,
        EvidenceAuthorityEvaluationError,
        EvidenceAuthorityNotReadyError,
        IntegrityError,
        LocalAssessmentGovernanceImportError,
    ) as error:
        session.rollback()
        if isinstance(error, LocalAssessmentGovernanceImportError):
            raise
        raise LocalAssessmentGovernanceImportError(str(error)) from error
    except Exception:
        session.rollback()
        raise

    return AssessmentGovernanceImportResult(
        bundle_version=bundle.bundle_version,
        definition_id=bundle.definition.id,
        review_id=bundle.review.id if bundle.review else None,
        estimation_policy_id=bundle.estimation_policy.id if bundle.estimation_policy else None,
        definition_created=definition_created,
        review_created=review_created,
        estimation_policy_created=estimation_policy_created,
        readiness=item.readiness,
        issues=item.issues,
    )


def _require_ready_evidence(
    evaluator: EvidenceAuthorityEvaluator,
    *,
    label: str,
    evidence_claim_ids: tuple[UUID, ...],
    reviewed_at: datetime,
) -> None:
    try:
        evaluator.require_ready(evidence_claim_ids, reviewed_at)
    except (EvidenceAuthorityEvaluationError, EvidenceAuthorityNotReadyError) as error:
        raise LocalAssessmentGovernanceImportError(
            f"{label} evidence is not ready at its review time: {error}"
        ) from error


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
        raise LocalAssessmentGovernanceImportError(
            f"persisted {label} {expected.id} differs from bundled immutable content"
        )
    return False


def _require_local_development(settings: Settings) -> None:
    if settings.environment.casefold() in {"production", "prod"}:
        raise LocalAssessmentGovernanceImportError(
            "local assessment-governance import is disabled in production"
        )
    if settings.auth_mode != "development":
        raise LocalAssessmentGovernanceImportError(
            "local assessment-governance import requires development authentication mode"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect the assessment-governance bundle schema or import exact immutable records "
            "in local development."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("schema", help="Print the versioned JSON bundle schema")
    import_parser = subparsers.add_parser(
        "import-bundle", help="Import one exact definition/review/policy bundle"
    )
    import_parser.add_argument("--input-file", type=Path, required=True)
    arguments = parser.parse_args()

    if arguments.command == "schema":
        print(json.dumps(AssessmentGovernanceBundle.model_json_schema(), sort_keys=True))
        return
    if arguments.command != "import-bundle":
        parser.error("unsupported assessment-governance administration command")
    try:
        bundle = AssessmentGovernanceBundle.model_validate_json(
            arguments.input_file.read_text(encoding="utf-8")
        )
        with database_session() as session:
            result = import_assessment_governance_bundle(
                session,
                bundle,
                settings=get_settings(),
            )
    except (
        DomainIntegrityError,
        LocalAssessmentGovernanceImportError,
        OSError,
        ValidationError,
        ValueError,
    ) as error:
        parser.error(str(error))
    print(json.dumps(result.model_dump(mode="json"), sort_keys=True))


if __name__ == "__main__":
    main()
