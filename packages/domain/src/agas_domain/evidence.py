from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from agas_domain.enums import EvidenceReviewDecision
from agas_domain.models import EvidenceClaim, EvidenceClaimReview, EvidenceSource


@dataclass(frozen=True)
class EvidenceClaimAuthorityState:
    """Point-in-time scientific-governance state for one exact claim."""

    claim: EvidenceClaim
    sources: tuple[EvidenceSource, ...]
    current_review: EvidenceClaimReview | None
    review_history: tuple[EvidenceClaimReview, ...]
    issues: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return not self.issues


def evaluate_evidence_claim_authority(
    claim: EvidenceClaim,
    sources_by_id: Mapping[UUID, EvidenceSource],
    reviews: Iterable[EvidenceClaimReview],
    evaluated_at: datetime,
) -> EvidenceClaimAuthorityState:
    """Evaluate only records that actually existed by the authority decision time."""

    if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
        raise ValueError("evidence-authority evaluation time must include a timezone")

    issues: list[str] = []
    if claim.created_at > evaluated_at:
        issues.append("claim did not exist at the evaluation time")

    available_sources: list[EvidenceSource] = []
    if not claim.source_record_ids:
        issues.append("claim has no exact evidence-source snapshot links")
    for source_id in claim.source_record_ids:
        source = sources_by_id.get(source_id)
        if source is None:
            issues.append(f"linked evidence source {source_id} does not exist")
        elif source.created_at > evaluated_at or source.retrieved_at > evaluated_at:
            issues.append(
                f"linked evidence source {source_id} was unavailable at the evaluation time"
            )
        else:
            available_sources.append(source)

    all_reviews = tuple(reviews)
    if any(review.evidence_claim_id != claim.id for review in all_reviews):
        raise ValueError("evidence review does not govern the evaluated claim")
    review_history = tuple(
        sorted(
            (
                review
                for review in all_reviews
                if review.created_at <= evaluated_at and review.reviewed_at <= evaluated_at
            ),
            key=lambda review: (
                review.sequence_number,
                review.reviewed_at,
                str(review.id),
            ),
        )
    )
    current_review = review_history[-1] if review_history else None
    if current_review is None:
        issues.append("claim had no scientific review at the evaluation time")
    elif current_review.decision is not EvidenceReviewDecision.APPROVED:
        issues.append(
            "current evidence review decision at the evaluation time was "
            f"{current_review.decision.value}"
        )

    return EvidenceClaimAuthorityState(
        claim=claim,
        sources=tuple(available_sources),
        current_review=current_review,
        review_history=review_history,
        issues=tuple(issues),
    )
