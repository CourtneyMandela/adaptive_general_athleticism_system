from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

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


class EvidenceGovernanceProjector:
    """Project review readiness without granting or creating scientific authority."""

    def __init__(self, session: Session) -> None:
        self.repository = DomainRepository(session)

    def project(self, projected_at: datetime | None = None) -> EvidenceGovernanceProjection:
        instant = projected_at or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("evidence-governance projection time must include a timezone")

        items: list[EvidenceGovernanceItem] = []
        for claim in self.repository.list_evidence_claims():
            if claim.created_at > instant:
                continue
            sources = self._sources_at(claim, instant)
            reviews = tuple(
                review
                for review in self.repository.list_evidence_claim_reviews(claim.id)
                if review.created_at <= instant and review.reviewed_at <= instant
            )
            current_review = reviews[-1] if reviews else None
            issues = self._issues(claim, sources, current_review)
            items.append(
                EvidenceGovernanceItem(
                    claim=claim,
                    status=current_review.decision.value if current_review else "unreviewed",
                    readiness="blocked" if issues else "ready",
                    sources=sources,
                    current_review=current_review,
                    review_history=reviews,
                    issues=issues,
                )
            )
        return EvidenceGovernanceProjection(projected_at=instant, items=tuple(items))

    def _sources_at(self, claim: EvidenceClaim, instant: datetime) -> tuple[EvidenceSource, ...]:
        sources: list[EvidenceSource] = []
        for source_id in claim.source_record_ids:
            source = self.repository.get_evidence_source(source_id)
            if source is None or source.created_at > instant or source.retrieved_at > instant:
                raise EvidenceGovernanceProjectionError(
                    f"claim {claim.id} references source {source_id} that is not available "
                    "at the projection time"
                )
            sources.append(source)
        return tuple(sources)

    @staticmethod
    def _issues(
        claim: EvidenceClaim,
        sources: tuple[EvidenceSource, ...],
        current_review: EvidenceClaimReview | None,
    ) -> tuple[str, ...]:
        issues: list[str] = []
        if not claim.source_record_ids:
            issues.append("claim has no exact evidence-source snapshot links")
        elif not sources:
            issues.append("claim has no source snapshots available at this time")
        if current_review is None:
            issues.append("claim has no scientific review history")
        elif current_review.decision is not EvidenceReviewDecision.APPROVED:
            issues.append(f"current evidence review decision is {current_review.decision.value}")
        return tuple(issues)
