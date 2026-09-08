from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from agas_domain import (
    AssessmentDefinition,
    AssessmentDefinitionReview,
    AssessmentMeasurementSchema,
    AssessmentReviewDecision,
    CapabilityDomain,
    CapabilityEstimationPolicy,
    DecisionRecord,
    Equipment,
    EvidenceClaim,
    EvidenceClaimReview,
    EvidenceReviewDecision,
    EvidenceSource,
)
from agas_domain.models import VersionedRecord
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agas_api.assessment_governance import (
    AssessmentGovernanceItem,
    AssessmentGovernanceProjectionError,
    AssessmentGovernanceProjector,
)
from agas_api.evidence_governance import (
    EvidenceAuthorityEvaluationError,
    EvidenceAuthorityEvaluator,
    EvidenceAuthorityNotReadyError,
)
from agas_api.evidence_governance_admin import EvidenceGovernanceBundle
from agas_api.identity import AuthorizedRole

RELEASE_VERSION = "assessment-governance-release@1.0.0"
NonEmptyText = Annotated[str, Field(min_length=1)]


class EvidenceClaimReviewDraft(BaseModel):
    """Scientific review content without caller-controlled authority or decision fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    evidence_claim_id: UUID
    sequence_number: int = Field(ge=1)
    supersedes_review_id: UUID | None = None
    source_verification_rationale: NonEmptyText
    extraction_rationale: NonEmptyText
    evidence_strength_rationale: NonEmptyText
    applicability_rationale: NonEmptyText
    uncertainty: NonEmptyText
    conflict_disclosure: NonEmptyText
    review_version: NonEmptyText

    @model_validator(mode="after")
    def validate_review_lineage(self) -> EvidenceClaimReviewDraft:
        if self.sequence_number == 1 and self.supersedes_review_id is not None:
            raise ValueError("the first evidence review cannot supersede another record")
        if self.sequence_number > 1 and self.supersedes_review_id is None:
            raise ValueError("later evidence reviews must reference their predecessor")
        if self.supersedes_review_id == self.id:
            raise ValueError("an evidence review cannot supersede itself")
        return self


class AssessmentDefinitionReviewDraft(BaseModel):
    """Protocol-review content whose approval identity is bound by the API."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    assessment_definition_id: UUID
    sequence_number: int = Field(ge=1)
    supersedes_review_id: UUID | None = None
    protocol_instructions: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    result_entry_instructions: NonEmptyText
    measurement_schema: AssessmentMeasurementSchema
    recommended_reassessment_days: int = Field(ge=1)
    self_administered: Literal[True]
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    applicability_notes: NonEmptyText
    uncertainty: NonEmptyText
    review_version: NonEmptyText

    @model_validator(mode="after")
    def reject_duplicate_protocol_content(self) -> AssessmentDefinitionReviewDraft:
        if len(set(self.protocol_instructions)) != len(self.protocol_instructions):
            raise ValueError("protocol_instructions must not contain duplicates")
        if len(set(self.evidence_claim_ids)) != len(self.evidence_claim_ids):
            raise ValueError("evidence_claim_ids must not contain duplicates")
        if self.sequence_number == 1 and self.supersedes_review_id is not None:
            raise ValueError("the first assessment review cannot supersede another record")
        if self.sequence_number > 1 and self.supersedes_review_id is None:
            raise ValueError("later assessment reviews must reference their predecessor")
        if self.supersedes_review_id == self.id:
            raise ValueError("an assessment review cannot supersede itself")
        return self


class CapabilityEstimationPolicyDraft(BaseModel):
    """Estimation-policy content without caller-controlled authority or decision fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    assessment_definition_id: UUID
    assessment_definition_review_id: UUID
    sequence_number: int = Field(ge=1)
    supersedes_policy_id: UUID | None = None
    domain: CapabilityDomain
    observation_type: NonEmptyText
    unit_or_scale: NonEmptyText
    calculation_method: NonEmptyText
    valid_for_days: int = Field(ge=1)
    multi_observation_window_days: int = Field(default=90, ge=1)
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    applicability_notes: NonEmptyText
    uncertainty: NonEmptyText
    rule_version: NonEmptyText

    @model_validator(mode="after")
    def reject_duplicate_evidence(self) -> CapabilityEstimationPolicyDraft:
        if len(set(self.evidence_claim_ids)) != len(self.evidence_claim_ids):
            raise ValueError("evidence_claim_ids must not contain duplicates")
        if self.sequence_number == 1 and self.supersedes_policy_id is not None:
            raise ValueError("the first capability estimation policy cannot supersede another")
        if self.sequence_number > 1 and self.supersedes_policy_id is None:
            raise ValueError(
                "later capability estimation policies must reference their predecessor"
            )
        if self.supersedes_policy_id == self.id:
            raise ValueError("a capability estimation policy cannot supersede itself")
        return self


class AssessmentGovernanceReleaseRequest(BaseModel):
    """One exact, human-ratified scientific chain prepared outside runtime planning."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    release_version: Literal["assessment-governance-release@1.0.0"]
    release_id: UUID
    release_label: NonEmptyText
    candidate_content_digest: Annotated[str | None, Field(pattern=r"^sha256:[0-9a-f]{64}$")] = None
    prepared_at: datetime
    ratified_at: datetime
    sources: Annotated[tuple[EvidenceSource, ...], Field(min_length=1)]
    supporting_equipment: tuple[Equipment, ...] = ()
    claims: Annotated[tuple[EvidenceClaim, ...], Field(min_length=1)]
    evidence_reviews: Annotated[tuple[EvidenceClaimReviewDraft, ...], Field(min_length=1)]
    definition: AssessmentDefinition
    protocol_review: AssessmentDefinitionReviewDraft
    estimation_policy: CapabilityEstimationPolicyDraft
    release_rationale: NonEmptyText
    release_uncertainty: NonEmptyText
    approval_attestation: Literal[True]

    @field_validator("prepared_at", "ratified_at")
    @classmethod
    def require_aware_times(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("governance release timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_release_chain(self) -> AssessmentGovernanceReleaseRequest:
        if self.ratified_at < self.prepared_at:
            raise ValueError("ratified_at cannot predate prepared_at")

        EvidenceGovernanceBundle(
            bundle_version="evidence-governance-bundle@2.0.0",
            sources=self.sources,
            claims=self.claims,
        )
        claim_ids = {claim.id for claim in self.claims}
        equipment_ids = tuple(item.id for item in self.supporting_equipment)
        if len(set(equipment_ids)) != len(equipment_ids):
            raise ValueError("supporting equipment must have unique ids")
        review_claim_ids = tuple(review.evidence_claim_id for review in self.evidence_reviews)
        if len(set(review_claim_ids)) != len(review_claim_ids):
            raise ValueError("a release must contain exactly one review for each evidence claim")
        if set(review_claim_ids) != claim_ids:
            raise ValueError("a release must review every bundled evidence claim exactly once")
        if self.protocol_review.assessment_definition_id != self.definition.id:
            raise ValueError("protocol review must govern the bundled assessment definition")
        if self.estimation_policy.assessment_definition_id != self.definition.id:
            raise ValueError("estimation policy must govern the bundled assessment definition")
        if self.estimation_policy.assessment_definition_review_id != self.protocol_review.id:
            raise ValueError("estimation policy must target the bundled protocol review")
        referenced_claim_ids = set(self.protocol_review.evidence_claim_ids).union(
            self.estimation_policy.evidence_claim_ids
        )
        if not referenced_claim_ids.issubset(claim_ids):
            raise ValueError("assessment authority must cite only bundled evidence claims")
        if self.estimation_policy.domain != self.definition.domain:
            raise ValueError("estimation policy domain must match the bundled definition")
        if self.estimation_policy.observation_type != self.definition.observation_type:
            raise ValueError("estimation policy observation type must match the bundled definition")
        if self.estimation_policy.unit_or_scale != self.definition.unit_or_scale:
            raise ValueError("estimation policy unit must match the bundled definition")
        records: tuple[VersionedRecord, ...] = (
            *self.sources,
            *self.supporting_equipment,
            *self.claims,
            self.definition,
        )
        if any(record.created_at > self.prepared_at for record in records):
            raise ValueError("prepared content cannot be timestamped after prepared_at")
        return self


class AssessmentGovernanceReleaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    release_id: UUID
    release_version: str
    content_digest: str
    authority_account_id: UUID
    authority_assignment_id: UUID
    created_source_ids: tuple[UUID, ...]
    created_equipment_ids: tuple[UUID, ...] = ()
    created_claim_ids: tuple[UUID, ...]
    created_evidence_review_ids: tuple[UUID, ...]
    definition_created: bool
    protocol_review_created: bool
    estimation_policy_created: bool
    decision_record_created: bool
    assessment: AssessmentGovernanceItem


class AssessmentGovernanceReleaseConflictError(RuntimeError):
    pass


class AssessmentGovernanceReleaseValidationError(RuntimeError):
    pass


def ratify_assessment_governance_release(
    session: Session,
    request: AssessmentGovernanceReleaseRequest,
    authority: AuthorizedRole,
    *,
    recorded_at: datetime | None = None,
) -> AssessmentGovernanceReleaseResult:
    """Atomically ratify exact evidence, protocol, and estimation records."""

    instant = recorded_at or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("release recording time must include a timezone")
    if request.ratified_at < authority.assigned_at:
        raise AssessmentGovernanceReleaseValidationError(
            "governance release cannot predate the reviewer role assignment"
        )
    if request.ratified_at > instant + timedelta(minutes=5):
        raise AssessmentGovernanceReleaseValidationError(
            "governance release ratification cannot be in the future"
        )

    repository = DomainRepository(session)
    reviewer = f"account:{authority.account_id}"
    evidence_reviews = tuple(
        EvidenceClaimReview(
            **draft.model_dump(),
            decision=EvidenceReviewDecision.APPROVED,
            created_at=request.ratified_at,
            reviewed_at=request.ratified_at,
            reviewer=reviewer,
        )
        for draft in request.evidence_reviews
    )
    protocol_review = AssessmentDefinitionReview(
        **request.protocol_review.model_dump(),
        decision=AssessmentReviewDecision.APPROVED,
        created_at=request.ratified_at,
        reviewed_at=request.ratified_at,
        reviewer=reviewer,
    )
    estimation_policy = CapabilityEstimationPolicy(
        **request.estimation_policy.model_dump(),
        decision=AssessmentReviewDecision.APPROVED,
        created_at=request.ratified_at,
        reviewed_at=request.ratified_at,
        reviewed_by=reviewer,
    )
    content_digest = _content_digest(request)
    decision = DecisionRecord(
        id=request.release_id,
        created_at=request.ratified_at,
        decision=f"Ratified assessment-governance release: {request.release_label}",
        reason=request.release_rationale,
        alternatives_considered=(
            "Leave the assessment chain blocked until a later review.",
            "Import approved records automatically without an authenticated ratification.",
            "Require the owner to author raw scientific and protocol records manually.",
        ),
        evidence=(
            f"content_digest:{content_digest}",
            *(
                (f"candidate_content_digest:{request.candidate_content_digest}",)
                if request.candidate_content_digest is not None
                else ()
            ),
            f"authority_account_id:{authority.account_id}",
            f"authority_assignment_id:{authority.assignment_id}",
            *(f"evidence_claim_id:{claim.id}" for claim in request.claims),
            *(f"supporting_equipment_id:{item.id}" for item in request.supporting_equipment),
        ),
        uncertainty=request.release_uncertainty,
        decision_version=f"{request.release_version}:ratification@1.0.0",
        decided_on=request.ratified_at.date(),
    )

    created_source_ids: list[UUID] = []
    created_equipment_ids: list[UUID] = []
    created_claim_ids: list[UUID] = []
    created_evidence_review_ids: list[UUID] = []
    try:
        for source in sorted(
            request.sources,
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

        for claim in request.claims:
            if _ensure_exact(
                label="evidence claim",
                expected=claim,
                existing=repository.get_evidence_claim(claim.id),
                add=repository.add_evidence_claim,
            ):
                created_claim_ids.append(claim.id)
            session.flush()

        for equipment in request.supporting_equipment:
            if _ensure_exact(
                label="supporting equipment",
                expected=equipment,
                existing=repository.get_equipment(equipment.id),
                add=repository.add_equipment,
            ):
                created_equipment_ids.append(equipment.id)
            session.flush()

        for review in sorted(
            evidence_reviews,
            key=lambda item: (item.sequence_number, item.reviewed_at, str(item.id)),
        ):
            if _ensure_exact(
                label="evidence claim review",
                expected=review,
                existing=repository.get_evidence_claim_review(review.id),
                add=repository.add_evidence_claim_review,
            ):
                created_evidence_review_ids.append(review.id)
            session.flush()

        definition_created = _ensure_exact(
            label="assessment definition",
            expected=request.definition,
            existing=repository.get_assessment_definition(request.definition.id),
            add=repository.add_assessment_definition,
        )
        session.flush()
        EvidenceAuthorityEvaluator(session).require_ready(
            protocol_review.evidence_claim_ids, protocol_review.reviewed_at
        )
        protocol_review_created = _ensure_exact(
            label="assessment definition review",
            expected=protocol_review,
            existing=repository.get_assessment_definition_review(protocol_review.id),
            add=repository.add_assessment_definition_review,
        )
        session.flush()
        EvidenceAuthorityEvaluator(session).require_ready(
            estimation_policy.evidence_claim_ids, estimation_policy.reviewed_at
        )
        estimation_policy_created = _ensure_exact(
            label="capability estimation policy",
            expected=estimation_policy,
            existing=repository.get_capability_estimation_policy(estimation_policy.id),
            add=repository.add_capability_estimation_policy,
        )
        session.flush()
        decision_record_created = _ensure_exact(
            label="release decision record",
            expected=decision,
            existing=repository.get_decision_record(decision.id),
            add=repository.add_decision_record,
        )
        session.flush()
        projection = AssessmentGovernanceProjector(session).project(request.ratified_at)
        assessment = next(
            (item for item in projection.items if item.definition.id == request.definition.id),
            None,
        )
        if assessment is None or assessment.readiness != "ready":
            issues = "assessment is absent" if assessment is None else "; ".join(assessment.issues)
            raise AssessmentGovernanceReleaseValidationError(
                f"ratified release did not produce an operational assessment chain: {issues}"
            )
        session.commit()
    except AssessmentGovernanceReleaseValidationError:
        session.rollback()
        raise
    except (
        AssessmentGovernanceProjectionError,
        DomainIntegrityError,
        EvidenceAuthorityEvaluationError,
        EvidenceAuthorityNotReadyError,
        IntegrityError,
    ) as error:
        session.rollback()
        raise AssessmentGovernanceReleaseConflictError(str(error)) from error
    except Exception:
        session.rollback()
        raise

    return AssessmentGovernanceReleaseResult(
        release_id=request.release_id,
        release_version=request.release_version,
        content_digest=content_digest,
        authority_account_id=authority.account_id,
        authority_assignment_id=authority.assignment_id,
        created_source_ids=tuple(created_source_ids),
        created_equipment_ids=tuple(created_equipment_ids),
        created_claim_ids=tuple(created_claim_ids),
        created_evidence_review_ids=tuple(created_evidence_review_ids),
        definition_created=definition_created,
        protocol_review_created=protocol_review_created,
        estimation_policy_created=estimation_policy_created,
        decision_record_created=decision_record_created,
        assessment=assessment,
    )


def _content_digest(request: AssessmentGovernanceReleaseRequest) -> str:
    payload = request.model_dump(mode="json", exclude={"approval_attestation"})
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


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
        raise AssessmentGovernanceReleaseConflictError(
            f"persisted {label} {expected.id} differs from ratified immutable content"
        )
    return False
