from __future__ import annotations

import hashlib
import json
import sysconfig
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID, uuid5

from agas_domain import (
    AccountRole,
    AssessmentReviewDecision,
    CapabilityDomain,
    ComparisonDirection,
    CompetencyFloor,
    CompetencyFloorReview,
    DecisionRecord,
    EvidenceClaim,
    EvidenceClaimReview,
    EvidenceReviewDecision,
    EvidenceSource,
)
from agas_domain.models import VersionedRecord
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agas_api.evidence_governance import (
    EvidenceAuthorityEvaluationError,
    EvidenceAuthorityEvaluator,
    EvidenceAuthorityNotReadyError,
)
from agas_api.identity import AuthorizedRole

CANDIDATE_VERSION = "competency-floor-candidate@1.1.0"
BATCH_VERSION = "competency-floor-candidate-batch@1.0.0"
BATCH_NAMESPACE = UUID("98400000-0000-4000-8000-000000000100")
NonEmptyText = Annotated[str, Field(min_length=1)]


class CompetencyFloorEvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: NonEmptyText
    source_url: NonEmptyText
    population: NonEmptyText
    finding: NonEmptyText
    limitations: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    conflict_disclosure: NonEmptyText


class CompetencyFloorAuthorityBasis(BaseModel):
    """Discloses where the number came from and who made it operational."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    numeric_value_origin: Literal[
        "direct_study_result",
        "derived_from_study",
        "professional_judgment",
        "personal_calibration",
    ]
    operational_use_origin: Literal[
        "evidence_validated",
        "evidence_informed_engineering_judgment",
        "professional_judgment",
        "personal_calibration",
    ]
    numeric_value_explanation: NonEmptyText
    operational_use_explanation: NonEmptyText


class CompetencyFloorCandidate(BaseModel):
    """Immutable owner-readable presentation of a prepared competency floor."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["competency-floor-candidate@1.1.0"]
    candidate_id: UUID
    slug: NonEmptyText
    release_label: NonEmptyText
    prepared_at: datetime
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    summary: NonEmptyText
    authority_basis: CompetencyFloorAuthorityBasis
    domain: CapabilityDomain
    estimate_scope: NonEmptyText
    unit_or_scale: NonEmptyText
    threshold: float
    comparison_direction: ComparisonDirection
    minimum_age_years: int
    maximum_age_years: int
    governs: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    does_not_establish: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    unresolved_limitations: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    evidence: Annotated[tuple[CompetencyFloorEvidenceSummary, ...], Field(min_length=1)]


class CompetencyFloorCandidateItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate: CompetencyFloorCandidate
    status: Literal["available", "ratified", "conflict"]
    ratified_at: datetime | None = None
    issues: tuple[str, ...] = ()


class CompetencyFloorCandidateReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: UUID
    candidate_version: Literal["competency-floor-candidate@1.1.0"]
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class CompetencyFloorCandidateBatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    batch_version: Literal["competency-floor-candidate-batch@1.0.0"]
    batch_id: UUID
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    candidates: Annotated[tuple[CompetencyFloorCandidateReference, ...], Field(min_length=1)]


class CompetencyFloorCandidateProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    projected_at: datetime
    items: tuple[CompetencyFloorCandidateItem, ...]
    batch: CompetencyFloorCandidateBatch
    projection_version: str = "competency-floor-candidates@1.1.0"


class RatifyCompetencyFloorCandidateCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["competency-floor-candidate@1.1.0"]
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    approval_attestation: Literal[True]


class PreparedCompetencyFloorRelease(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    release_id: UUID
    release_label: NonEmptyText
    prepared_at: datetime
    source: EvidenceSource
    claim: EvidenceClaim
    evidence_review_id: UUID
    evidence_review_content: dict[str, str]
    floor: CompetencyFloor
    floor_review_id: UUID
    floor_review_content: dict[str, str]
    release_rationale: NonEmptyText
    release_uncertainty: NonEmptyText


class PreparedCompetencyFloorCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    presentation: CompetencyFloorCandidate
    release: PreparedCompetencyFloorRelease
    accepted_historical_content_digests: tuple[str, ...] = ()


class RatifyCompetencyFloorCandidateBatchCommand(CompetencyFloorCandidateBatch):
    approval_attestation: Literal[True]


class CompetencyFloorCandidateDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    document_schema_version: Literal["competency-floor-candidate-document@1.0.0"]
    candidate_version: Literal["competency-floor-candidate@1.1.0"]
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    accepted_historical_content_digests: tuple[
        Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")], ...
    ] = ()
    presentation: dict[str, Any]
    release: PreparedCompetencyFloorRelease

    @model_validator(mode="after")
    def validate_release_alignment(self) -> CompetencyFloorCandidateDocument:
        presentation = CompetencyFloorCandidate(
            candidate_version=self.candidate_version,
            content_digest=self.content_digest,
            **self.presentation,
        )
        release = self.release
        if presentation.candidate_id != release.release_id:
            raise ValueError("candidate and release identities must match")
        if presentation.release_label != release.release_label:
            raise ValueError("candidate and release labels must match")
        if presentation.prepared_at != release.prepared_at:
            raise ValueError("candidate and release preparation times must match")
        floor = release.floor
        if (
            presentation.domain != floor.domain
            or presentation.estimate_scope != floor.estimate_scope
            or presentation.unit_or_scale != floor.unit_or_scale
            or presentation.threshold != floor.threshold
            or presentation.comparison_direction != floor.comparison_direction
            or presentation.minimum_age_years != floor.minimum_age_years
            or presentation.maximum_age_years != floor.maximum_age_years
        ):
            raise ValueError("candidate presentation and competency floor must match exactly")
        if release.claim.id not in floor.evidence_claim_ids:
            raise ValueError("competency floor must cite the candidate evidence claim")
        if release.source.id not in release.claim.source_record_ids:
            raise ValueError("candidate claim must cite its exact source snapshot")
        if len(set(self.accepted_historical_content_digests)) != len(
            self.accepted_historical_content_digests
        ):
            raise ValueError("historical content digests must be unique")
        return self


class CompetencyFloorRatificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    release_id: UUID
    release_version: str = "competency-floor-ratification@1.0.0"
    candidate_content_digest: str
    authority_account_id: UUID
    authority_assignment_id: UUID
    created_source: bool
    created_claim: bool
    created_evidence_review: bool
    created_floor: bool
    created_floor_review: bool
    decision_record_created: bool
    floor: CompetencyFloor
    floor_review: CompetencyFloorReview


class CompetencyFloorCandidateBatchRatificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    batch: CompetencyFloorCandidateBatch
    authority_account_id: UUID
    authority_assignment_id: UUID
    candidate_results: Annotated[tuple[CompetencyFloorRatificationResult, ...], Field(min_length=1)]
    batch_decision_record_created: bool
    ratification_version: str = "competency-floor-batch-ratification@1.0.0"


class CompetencyFloorCandidateConflictError(RuntimeError):
    pass


class CompetencyFloorCandidateValidationError(RuntimeError):
    pass


def list_competency_floor_candidates(
    session: Session, *, projected_at: datetime | None = None
) -> CompetencyFloorCandidateProjection:
    instant = projected_at or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("candidate projection time must include a timezone")
    repository = DomainRepository(session)
    items: list[CompetencyFloorCandidateItem] = []
    for prepared in _candidate_registry().values():
        decision = repository.get_decision_record(prepared.release.release_id)
        if decision is None:
            status: Literal["available", "ratified", "conflict"] = "available"
            ratified_at = None
            issues: tuple[str, ...] = ()
        elif _decision_candidate_digest(decision) in _accepted_candidate_digests(prepared):
            status = "ratified"
            ratified_at = decision.created_at
            issues = ()
        else:
            status = "conflict"
            ratified_at = decision.created_at
            issues = ("The candidate release identity is occupied by different immutable content.",)
        items.append(
            CompetencyFloorCandidateItem(
                candidate=prepared.presentation,
                status=status,
                ratified_at=ratified_at,
                issues=issues,
            )
        )
    return CompetencyFloorCandidateProjection(
        projected_at=instant,
        items=tuple(items),
        batch=competency_floor_candidate_batch(),
    )


@lru_cache
def competency_floor_candidate_batch() -> CompetencyFloorCandidateBatch:
    references = tuple(
        CompetencyFloorCandidateReference(
            candidate_id=prepared.presentation.candidate_id,
            candidate_version=prepared.presentation.candidate_version,
            content_digest=prepared.presentation.content_digest,
        )
        for prepared in sorted(
            _candidate_registry().values(), key=lambda item: str(item.presentation.candidate_id)
        )
    )
    canonical = json.dumps(
        {
            "batch_version": BATCH_VERSION,
            "candidates": [item.model_dump(mode="json") for item in references],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    digest = f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
    return CompetencyFloorCandidateBatch(
        batch_version=BATCH_VERSION,
        batch_id=uuid5(BATCH_NAMESPACE, digest),
        content_digest=digest,
        candidates=references,
    )


def ratify_competency_floor_candidate(
    session: Session,
    candidate_id: UUID,
    command: RatifyCompetencyFloorCandidateCommand,
    authority: AuthorizedRole,
    *,
    ratified_at: datetime | None = None,
) -> CompetencyFloorRatificationResult:
    prepared = _validated_candidate(candidate_id, command.candidate_version, command.content_digest)
    instant = _validated_ratification_time(authority, prepared.release.prepared_at, ratified_at)
    try:
        result = _persist_candidate(session, prepared, authority, instant)
        session.commit()
    except CompetencyFloorCandidateConflictError:
        session.rollback()
        raise
    except (
        DomainIntegrityError,
        EvidenceAuthorityEvaluationError,
        EvidenceAuthorityNotReadyError,
        IntegrityError,
    ) as error:
        session.rollback()
        raise CompetencyFloorCandidateConflictError(str(error)) from error
    except Exception:
        session.rollback()
        raise
    return result


def ratify_competency_floor_candidate_batch(
    session: Session,
    command: RatifyCompetencyFloorCandidateBatchCommand,
    authority: AuthorizedRole,
    *,
    ratified_at: datetime | None = None,
) -> CompetencyFloorCandidateBatchRatificationResult:
    expected = competency_floor_candidate_batch()
    supplied = CompetencyFloorCandidateBatch.model_validate(
        command.model_dump(exclude={"approval_attestation"})
    )
    if supplied != expected:
        raise CompetencyFloorCandidateConflictError(
            "candidate batch changed; refresh and review the exact current manifest"
        )
    registry = _candidate_registry()
    prepared_items = tuple(registry[item.candidate_id] for item in expected.candidates)
    latest_prepared_at = max(item.release.prepared_at for item in prepared_items)
    instant = _validated_ratification_time(authority, latest_prepared_at, ratified_at)
    repository = DomainRepository(session)
    existing_batch_decision = repository.get_decision_record(expected.batch_id)
    if existing_batch_decision is not None:
        return _existing_batch_result(repository, expected, prepared_items, existing_batch_decision)

    try:
        results = tuple(
            _persist_candidate(session, prepared, authority, instant) for prepared in prepared_items
        )
        batch_decision = DecisionRecord(
            id=expected.batch_id,
            created_at=instant,
            decision="Ratified exact competency-floor candidate batch",
            reason=(
                "Approve one content-addressed manifest while retaining each candidate's own "
                "immutable digest, evidence chain, floor review, and decision record."
            ),
            alternatives_considered=(
                "Require a separate network request and attestation for every floor.",
                "Approve a batch without preserving per-artifact digests.",
                "Allow a partially successful batch.",
            ),
            evidence=(
                f"batch_content_digest:{expected.content_digest}",
                f"authority_account_id:{authority.account_id}",
                f"authority_assignment_id:{authority.assignment_id}",
                *(
                    f"candidate_content_digest:{item.candidate_id}={item.content_digest}"
                    for item in expected.candidates
                ),
            ),
            uncertainty=(
                "One attestation reduces repetitive transport; it does not establish that every "
                "floor has strong evidence or broad athlete applicability."
            ),
            decision_version="competency-floor-batch-ratification@1.0.0",
            decided_on=instant.date(),
        )
        batch_created = _ensure_exact(
            label="candidate batch decision",
            expected=batch_decision,
            existing=repository.get_decision_record(batch_decision.id),
            add=repository.add_decision_record,
        )
        session.commit()
    except CompetencyFloorCandidateConflictError:
        session.rollback()
        raise
    except (
        DomainIntegrityError,
        EvidenceAuthorityEvaluationError,
        EvidenceAuthorityNotReadyError,
        IntegrityError,
    ) as error:
        session.rollback()
        raise CompetencyFloorCandidateConflictError(str(error)) from error
    except Exception:
        session.rollback()
        raise

    return CompetencyFloorCandidateBatchRatificationResult(
        batch=expected,
        authority_account_id=authority.account_id,
        authority_assignment_id=authority.assignment_id,
        candidate_results=results,
        batch_decision_record_created=batch_created,
    )


def _validated_candidate(
    candidate_id: UUID, candidate_version: str, content_digest: str
) -> PreparedCompetencyFloorCandidate:
    try:
        prepared = _candidate_registry()[candidate_id]
    except KeyError as error:
        raise KeyError("competency-floor candidate does not exist") from error
    if candidate_version != prepared.presentation.candidate_version:
        raise CompetencyFloorCandidateValidationError(
            "candidate version does not match the prepared release"
        )
    if content_digest != prepared.presentation.content_digest:
        raise CompetencyFloorCandidateConflictError(
            "candidate content changed; refresh and review the exact current release"
        )
    return prepared


def _validated_ratification_time(
    authority: AuthorizedRole,
    prepared_at: datetime,
    ratified_at: datetime | None,
) -> datetime:
    if authority.role is not AccountRole.PLANNING_REVIEWER:
        raise CompetencyFloorCandidateValidationError(
            "competency-floor ratification requires planning_reviewer authority"
        )
    instant = ratified_at or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("ratification time must include a timezone")
    if instant < prepared_at:
        raise CompetencyFloorCandidateValidationError(
            "ratification cannot predate prepared content"
        )
    if instant < authority.assigned_at:
        raise CompetencyFloorCandidateValidationError(
            "ratification cannot predate the reviewer role assignment"
        )
    if instant > datetime.now(UTC) + timedelta(minutes=5):
        raise CompetencyFloorCandidateValidationError("ratification cannot be in the future")
    return instant


def _persist_candidate(
    session: Session,
    prepared: PreparedCompetencyFloorCandidate,
    authority: AuthorizedRole,
    instant: datetime,
) -> CompetencyFloorRatificationResult:
    repository = DomainRepository(session)
    existing_decision = repository.get_decision_record(prepared.release.release_id)
    if existing_decision is not None:
        return _existing_result(repository, prepared, existing_decision)

    release = prepared.release
    reviewer = f"account:{authority.account_id}"
    evidence_review = EvidenceClaimReview(
        id=release.evidence_review_id,
        created_at=instant,
        evidence_claim_id=release.claim.id,
        decision=EvidenceReviewDecision.APPROVED,
        sequence_number=1,
        reviewed_at=instant,
        reviewer=reviewer,
        **release.evidence_review_content,
    )
    floor_review = CompetencyFloorReview(
        id=release.floor_review_id,
        created_at=instant,
        competency_floor_id=release.floor.id,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=1,
        evidence_claim_ids=(release.claim.id,),
        reviewed_at=instant,
        reviewed_by=reviewer,
        **release.floor_review_content,
    )
    decision = DecisionRecord(
        id=release.release_id,
        created_at=instant,
        decision=f"Ratified competency-floor candidate: {release.release_label}",
        reason=release.release_rationale,
        alternatives_considered=(
            "Leave initial planning blocked until a broader reference source is reviewed.",
            "Ask the owner to invent a threshold without traceable evidence.",
            "Misrepresent the cohort median as a minimum competency floor.",
        ),
        evidence=(
            f"candidate_content_digest:{prepared.presentation.content_digest}",
            f"authority_account_id:{authority.account_id}",
            f"authority_assignment_id:{authority.assignment_id}",
            f"evidence_claim_id:{release.claim.id}",
            f"competency_floor_id:{release.floor.id}",
            f"competency_floor_review_id:{floor_review.id}",
        ),
        uncertainty=release.release_uncertainty,
        decision_version="competency-floor-ratification@1.0.0",
        decided_on=instant.date(),
    )

    created_source = _ensure_exact(
        label="evidence source",
        expected=release.source,
        existing=repository.get_evidence_source(release.source.id),
        add=repository.add_evidence_source,
    )
    session.flush()
    created_claim = _ensure_exact(
        label="evidence claim",
        expected=release.claim,
        existing=repository.get_evidence_claim(release.claim.id),
        add=repository.add_evidence_claim,
    )
    session.flush()
    created_evidence_review = _ensure_exact(
        label="evidence review",
        expected=evidence_review,
        existing=repository.get_evidence_claim_review(evidence_review.id),
        add=repository.add_evidence_claim_review,
    )
    session.flush()
    EvidenceAuthorityEvaluator(session).require_ready((release.claim.id,), instant)
    created_floor = _ensure_exact(
        label="competency floor",
        expected=release.floor,
        existing=repository.get_competency_floor(release.floor.id),
        add=repository.add_competency_floor,
    )
    session.flush()
    created_floor_review = _ensure_exact(
        label="competency floor review",
        expected=floor_review,
        existing=repository.get_competency_floor_review(floor_review.id),
        add=repository.add_competency_floor_review,
    )
    session.flush()
    decision_record_created = _ensure_exact(
        label="decision record",
        expected=decision,
        existing=repository.get_decision_record(decision.id),
        add=repository.add_decision_record,
    )

    return CompetencyFloorRatificationResult(
        release_id=release.release_id,
        candidate_content_digest=prepared.presentation.content_digest,
        authority_account_id=authority.account_id,
        authority_assignment_id=authority.assignment_id,
        created_source=created_source,
        created_claim=created_claim,
        created_evidence_review=created_evidence_review,
        created_floor=created_floor,
        created_floor_review=created_floor_review,
        decision_record_created=decision_record_created,
        floor=release.floor,
        floor_review=floor_review,
    )


def _existing_result(
    repository: DomainRepository,
    prepared: PreparedCompetencyFloorCandidate,
    decision: DecisionRecord,
) -> CompetencyFloorRatificationResult:
    values = {
        key: value
        for item in decision.evidence
        if ":" in item
        for key, value in (item.split(":", 1),)
    }
    persisted_digest = values.get("candidate_content_digest")
    if persisted_digest not in _accepted_candidate_digests(prepared):
        raise CompetencyFloorCandidateConflictError(
            "candidate release identity is occupied by different immutable content"
        )
    try:
        account_id = UUID(values["authority_account_id"])
        assignment_id = UUID(values["authority_assignment_id"])
    except (KeyError, ValueError) as error:
        raise CompetencyFloorCandidateConflictError(
            "persisted candidate decision has incomplete authority provenance"
        ) from error
    floor = repository.get_competency_floor(prepared.release.floor.id)
    review = repository.get_competency_floor_review(prepared.release.floor_review_id)
    if floor != prepared.release.floor or review is None:
        raise CompetencyFloorCandidateConflictError(
            "persisted candidate decision has incomplete competency-floor lineage"
        )
    return CompetencyFloorRatificationResult(
        release_id=prepared.release.release_id,
        candidate_content_digest=persisted_digest,
        authority_account_id=account_id,
        authority_assignment_id=assignment_id,
        created_source=False,
        created_claim=False,
        created_evidence_review=False,
        created_floor=False,
        created_floor_review=False,
        decision_record_created=False,
        floor=floor,
        floor_review=review,
    )


def _existing_batch_result(
    repository: DomainRepository,
    batch: CompetencyFloorCandidateBatch,
    prepared_items: tuple[PreparedCompetencyFloorCandidate, ...],
    decision: DecisionRecord,
) -> CompetencyFloorCandidateBatchRatificationResult:
    values = {
        key: value
        for item in decision.evidence
        if ":" in item
        for key, value in (item.split(":", 1),)
        if key != "candidate_content_digest"
    }
    if values.get("batch_content_digest") != batch.content_digest:
        raise CompetencyFloorCandidateConflictError(
            "candidate batch identity is occupied by different immutable content"
        )
    expected_candidates = {
        f"{item.candidate_id}={item.content_digest}" for item in batch.candidates
    }
    actual_candidates = {
        item.split(":", 1)[1]
        for item in decision.evidence
        if item.startswith("candidate_content_digest:")
    }
    if actual_candidates != expected_candidates:
        raise CompetencyFloorCandidateConflictError(
            "persisted batch decision has incomplete candidate-digest provenance"
        )
    try:
        account_id = UUID(values["authority_account_id"])
        assignment_id = UUID(values["authority_assignment_id"])
    except (KeyError, ValueError) as error:
        raise CompetencyFloorCandidateConflictError(
            "persisted batch decision has incomplete authority provenance"
        ) from error
    results = []
    for prepared in prepared_items:
        candidate_decision = repository.get_decision_record(prepared.release.release_id)
        if candidate_decision is None:
            raise CompetencyFloorCandidateConflictError(
                "persisted batch decision has incomplete candidate lineage"
            )
        results.append(_existing_result(repository, prepared, candidate_decision))
    return CompetencyFloorCandidateBatchRatificationResult(
        batch=batch,
        authority_account_id=account_id,
        authority_assignment_id=assignment_id,
        candidate_results=tuple(results),
        batch_decision_record_created=False,
    )


def _decision_candidate_digest(decision: DecisionRecord) -> str | None:
    prefix = "candidate_content_digest:"
    return next(
        (item.removeprefix(prefix) for item in decision.evidence if item.startswith(prefix)),
        None,
    )


def _accepted_candidate_digests(
    prepared: PreparedCompetencyFloorCandidate,
) -> set[str]:
    return {
        prepared.presentation.content_digest,
        *prepared.accepted_historical_content_digests,
    }


@lru_cache
def _candidate_registry(
    data_root: Path | None = None,
) -> dict[UUID, PreparedCompetencyFloorCandidate]:
    root = data_root or _default_candidate_data_root()
    paths = sorted(root.glob("*.json"))
    if not paths:
        raise CompetencyFloorCandidateValidationError(
            f"no competency-floor candidate documents found in {root}"
        )

    registry: dict[UUID, PreparedCompetencyFloorCandidate] = {}
    for path in paths:
        raw = _read_candidate_json(path)
        try:
            document = CompetencyFloorCandidateDocument.model_validate(raw)
        except ValueError as error:
            raise CompetencyFloorCandidateValidationError(
                f"invalid competency-floor candidate document {path.name}: {error}"
            ) from error
        canonical = json.dumps(
            {
                "candidate_version": raw["candidate_version"],
                "presentation": raw["presentation"],
                "release": raw["release"],
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        actual_digest = f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
        if actual_digest != document.content_digest:
            raise CompetencyFloorCandidateValidationError(
                f"competency-floor candidate document {path.name} has a stale content digest"
            )
        presentation = CompetencyFloorCandidate(
            candidate_version=document.candidate_version,
            content_digest=document.content_digest,
            **document.presentation,
        )
        if presentation.candidate_id in registry:
            raise CompetencyFloorCandidateValidationError(
                f"duplicate competency-floor candidate id {presentation.candidate_id}"
            )
        registry[presentation.candidate_id] = PreparedCompetencyFloorCandidate(
            presentation=presentation,
            release=document.release,
            accepted_historical_content_digests=document.accepted_historical_content_digests,
        )
    return registry


def _default_candidate_data_root() -> Path:
    repository_data = (
        Path(__file__).resolve().parents[4] / "data" / "governance_candidates" / "competency_floors"
    )
    if repository_data.is_dir():
        return repository_data
    return (
        Path(sysconfig.get_path("data"))
        / "share"
        / "agas"
        / "data"
        / "governance_candidates"
        / "competency_floors"
    )


def _read_candidate_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as file:
            raw = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise CompetencyFloorCandidateValidationError(
            f"unable to read competency-floor candidate document {path.name}: {error}"
        ) from error
    if not isinstance(raw, dict):
        raise CompetencyFloorCandidateValidationError(
            f"competency-floor candidate document {path.name} must be an object"
        )
    return raw


def _ensure_exact[Record: VersionedRecord](
    *, label: str, expected: Record, existing: Record | None, add: Callable[[Record], None]
) -> bool:
    if existing is None:
        add(expected)
        return True
    if existing != expected:
        raise CompetencyFloorCandidateConflictError(
            f"persisted {label} {expected.id} differs from candidate content"
        )
    return False
