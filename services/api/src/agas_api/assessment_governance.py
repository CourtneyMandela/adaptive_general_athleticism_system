from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from agas_domain import (
    AssessmentDefinition,
    AssessmentDefinitionReview,
    AssessmentReviewDecision,
    CapabilityEstimationPolicy,
    EvidenceClaim,
)
from agas_domain.persistence.repository import DomainRepository
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from agas_api.evidence_governance import (
    EvidenceAuthorityEvaluation,
    EvidenceAuthorityEvaluator,
)


class AssessmentGovernanceItem(BaseModel):
    """Current protocol/policy state plus the immutable history that produced it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    definition: AssessmentDefinition
    status: Literal["unreviewed", "approved", "needs_revision", "rejected"]
    readiness: Literal["ready", "blocked"]
    current_review: AssessmentDefinitionReview | None
    review_history: tuple[AssessmentDefinitionReview, ...]
    current_estimation_policy: CapabilityEstimationPolicy | None
    estimation_policy_history: tuple[CapabilityEstimationPolicy, ...]
    evidence_claims: tuple[EvidenceClaim, ...]
    review_evidence_governance: EvidenceAuthorityEvaluation | None
    estimation_policy_evidence_governance: EvidenceAuthorityEvaluation | None
    issues: tuple[str, ...]


class AssessmentGovernanceProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    projected_at: datetime
    items: tuple[AssessmentGovernanceItem, ...]
    projection_version: str = "assessment-governance-workbench@1.1.0"


class AssessmentGovernanceProjectionError(RuntimeError):
    pass


class AssessmentGovernanceProjector:
    """Project governed assessment readiness without creating scientific approvals."""

    def __init__(self, session: Session) -> None:
        self.repository = DomainRepository(session)
        self.evidence_evaluator = EvidenceAuthorityEvaluator(session)

    def project(self, projected_at: datetime | None = None) -> AssessmentGovernanceProjection:
        instant = projected_at or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("assessment-governance projection time must include a timezone")

        items = []
        for definition in self.repository.list_assessment_definitions():
            if definition.created_at > instant:
                continue
            reviews = tuple(
                review
                for review in self.repository.list_assessment_definition_reviews(definition.id)
                if review.reviewed_at <= instant and review.created_at <= instant
            )
            policies = tuple(
                policy
                for policy in self.repository.list_capability_estimation_policies(definition.id)
                if policy.reviewed_at <= instant and policy.created_at <= instant
            )
            current_review = reviews[-1] if reviews else None
            current_policy = policies[-1] if policies else None
            issues = list(self._issues(current_review, current_policy))
            review_evidence = (
                self.evidence_evaluator.evaluate(
                    current_review.evidence_claim_ids, current_review.reviewed_at
                )
                if current_review
                else None
            )
            policy_evidence = (
                self.evidence_evaluator.evaluate(
                    current_policy.evidence_claim_ids, current_policy.reviewed_at
                )
                if current_policy
                else None
            )
            if (
                current_review is not None
                and current_review.decision is AssessmentReviewDecision.APPROVED
                and review_evidence is not None
                and review_evidence.readiness == "blocked"
            ):
                issues.extend(
                    f"protocol-review evidence was not ready at its review time: {issue}"
                    for issue in review_evidence.issues
                )
            if (
                current_policy is not None
                and current_policy.decision is AssessmentReviewDecision.APPROVED
                and policy_evidence is not None
                and policy_evidence.readiness == "blocked"
            ):
                issues.extend(
                    f"estimation-policy evidence was not ready at its review time: {issue}"
                    for issue in policy_evidence.issues
                )
            evidence_ids = dict.fromkeys(
                evidence_id for review in reviews for evidence_id in review.evidence_claim_ids
            )
            evidence_ids.update(
                dict.fromkeys(
                    evidence_id for policy in policies for evidence_id in policy.evidence_claim_ids
                )
            )
            evidence_claims = []
            for evidence_id in evidence_ids:
                claim = self.repository.get_evidence_claim(evidence_id)
                if claim is None or claim.created_at > instant:
                    raise AssessmentGovernanceProjectionError(
                        f"referenced evidence claim {evidence_id} is not available at the "
                        "projection time"
                    )
                evidence_claims.append(claim)
            items.append(
                AssessmentGovernanceItem(
                    definition=definition,
                    status=(current_review.decision.value if current_review else "unreviewed"),
                    readiness="blocked" if issues else "ready",
                    current_review=current_review,
                    review_history=reviews,
                    current_estimation_policy=current_policy,
                    estimation_policy_history=policies,
                    evidence_claims=tuple(evidence_claims),
                    review_evidence_governance=review_evidence,
                    estimation_policy_evidence_governance=policy_evidence,
                    issues=tuple(issues),
                )
            )
        return AssessmentGovernanceProjection(projected_at=instant, items=tuple(items))

    @staticmethod
    def _issues(
        review: AssessmentDefinitionReview | None,
        policy: CapabilityEstimationPolicy | None,
    ) -> tuple[str, ...]:
        issues: list[str] = []
        if review is None:
            issues.append("assessment definition has no protocol review history")
        elif review.decision is not AssessmentReviewDecision.APPROVED:
            issues.append(f"current protocol review decision is {review.decision.value}")
        else:
            if review.measurement_schema is None:
                issues.append("current approved protocol review has no measurement schema")
            if not review.self_administered:
                issues.append("current approved protocol is not authorized for self-administration")

        if policy is None:
            issues.append("no capability-estimation policy exists for this definition")
        else:
            if policy.decision is not AssessmentReviewDecision.APPROVED:
                issues.append(
                    f"current capability-estimation policy decision is {policy.decision.value}"
                )
            if review is None or policy.assessment_definition_review_id != review.id:
                issues.append(
                    "current capability-estimation policy does not target the current "
                    "protocol review"
                )
        return tuple(issues)
