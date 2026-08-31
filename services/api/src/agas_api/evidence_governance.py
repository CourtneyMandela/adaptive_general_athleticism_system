from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from agas_domain import (
    EvidenceClaim,
    EvidenceClaimReview,
    EvidenceReviewDecision,
    EvidenceSource,
)
from agas_domain.persistence.repository import DomainRepository
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session


class EvidenceGovernanceItem(BaseModel):
    """One exact claim with its source snapshots and append-only review history."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim: EvidenceClaim
    status: Literal["unreviewed", "approved", "needs_revision", "rejected"]
    readiness: Literal["ready", "blocked"]
    sources: tuple[EvidenceSource, ...]
    current_review: EvidenceClaimReview | None
    review_history: tuple[EvidenceClaimReview, ...]
    issues: tuple[str, ...]


class EvidenceGovernanceProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    projected_at: datetime
    items: tuple[EvidenceGovernanceItem, ...]
    projection_version: str = "evidence-governance-workbench@1.0.0"


class EvidenceGovernanceProjectionError(RuntimeError):
    pass


class EvidenceAuthorityEvaluation(BaseModel):
    """Readiness of exact claims at the time a scientific authority was reviewed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluated_at: datetime
    readiness: Literal["ready", "blocked"]
    claim_results: tuple[EvidenceGovernanceItem, ...]
    issues: tuple[str, ...]
    evaluation_version: str = "evidence-authority-readiness@1.0.0"


class EvidenceAuthorityEvaluationError(RuntimeError):
    pass


class EvidenceAuthorityNotReadyError(RuntimeError):
    pass


class EvidenceAuthorityEvaluator:
    """Evaluate evidence as it existed at an authority's own decision time."""

    def __init__(self, session: Session) -> None:
        self.repository = DomainRepository(session)

    def evaluate(
        self, evidence_claim_ids: tuple[UUID, ...], evaluated_at: datetime
    ) -> EvidenceAuthorityEvaluation:
        if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
            raise ValueError("evidence-authority evaluation time must include a timezone")
        if len(set(evidence_claim_ids)) != len(evidence_claim_ids):
            raise ValueError("evidence-authority claim ids must not contain duplicates")
        if not evidence_claim_ids:
            return EvidenceAuthorityEvaluation(
                evaluated_at=evaluated_at,
                readiness="blocked",
                claim_results=(),
                issues=("authority cites no evidence claims",),
            )

        results: list[EvidenceGovernanceItem] = []
        issues: list[str] = []
        for claim_id in evidence_claim_ids:
            claim = self.repository.get_evidence_claim(claim_id)
            if claim is None:
                raise EvidenceAuthorityEvaluationError(
                    f"authority references unknown evidence claim {claim_id}"
                )
            result = self.evaluate_claim(claim, evaluated_at)
            results.append(result)
            issues.extend(f"evidence claim {claim.id}: {issue}" for issue in result.issues)
        return EvidenceAuthorityEvaluation(
            evaluated_at=evaluated_at,
            readiness="blocked" if issues else "ready",
            claim_results=tuple(results),
            issues=tuple(issues),
        )

    def require_ready(
        self, evidence_claim_ids: tuple[UUID, ...], evaluated_at: datetime
    ) -> EvidenceAuthorityEvaluation:
        evaluation = self.evaluate(evidence_claim_ids, evaluated_at)
        if evaluation.readiness != "ready":
            raise EvidenceAuthorityNotReadyError("; ".join(evaluation.issues))
        return evaluation

    def evaluate_claim(
        self, claim: EvidenceClaim, evaluated_at: datetime
    ) -> EvidenceGovernanceItem:
        issues: list[str] = []
        if claim.created_at > evaluated_at:
            issues.append("claim did not exist at the evaluation time")

        sources: list[EvidenceSource] = []
        if not claim.source_record_ids:
            issues.append("claim has no exact evidence-source snapshot links")
        for source_id in claim.source_record_ids:
            source = self.repository.get_evidence_source(source_id)
            if source is None:
                issues.append(f"linked evidence source {source_id} does not exist")
            elif source.created_at > evaluated_at or source.retrieved_at > evaluated_at:
                issues.append(
                    f"linked evidence source {source_id} was unavailable at the evaluation time"
                )
            else:
                sources.append(source)

        reviews = tuple(
            review
            for review in self.repository.list_evidence_claim_reviews(claim.id)
            if review.created_at <= evaluated_at and review.reviewed_at <= evaluated_at
        )
        current_review = reviews[-1] if reviews else None
        if current_review is None:
            issues.append("claim had no scientific review at the evaluation time")
        elif current_review.decision is not EvidenceReviewDecision.APPROVED:
            issues.append(
                "current evidence review decision at the evaluation time was "
                f"{current_review.decision.value}"
            )

        return EvidenceGovernanceItem(
            claim=claim,
            status=current_review.decision.value if current_review else "unreviewed",
            readiness="blocked" if issues else "ready",
            sources=tuple(sources),
            current_review=current_review,
            review_history=reviews,
            issues=tuple(issues),
        )


class EvidenceGovernanceProjector:
    """Project review readiness without granting or creating scientific authority."""

    def __init__(self, session: Session) -> None:
        self.repository = DomainRepository(session)
        self.evaluator = EvidenceAuthorityEvaluator(session)

    def project(self, projected_at: datetime | None = None) -> EvidenceGovernanceProjection:
        instant = projected_at or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("evidence-governance projection time must include a timezone")

        items: list[EvidenceGovernanceItem] = []
        for claim in self.repository.list_evidence_claims():
            if claim.created_at > instant:
                continue
            items.append(self.evaluator.evaluate_claim(claim, instant))
        return EvidenceGovernanceProjection(projected_at=instant, items=tuple(items))
