from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from agas_domain import ReplanningCandidateContext
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from agas_api.block_review_application import (
    BlockReviewCreationResult,
    CreateBlockReviewCommand,
    PersistedBlockReviewService,
    TrainingResponseDraft,
)
from agas_api.identity import AuthorizedRole
from agas_api.replanning import (
    PersistedReplanningService,
    PostBlockReplanningCommand,
    PostBlockReplanningResult,
)

NonEmptyText = Annotated[str, Field(min_length=1)]


class OperatorBlockReviewRequest(BaseModel):
    """Untrusted response interpretation inputs; reviewer identity is server-owned."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    block_review_policy_id: UUID
    response_drafts: Annotated[tuple[TrainingResponseDraft, ...], Field(min_length=1)]
    responses_calculated_at: datetime
    reviewed_at: datetime
    applicability_rationale: NonEmptyText
    uncertainty: NonEmptyText

    @field_validator("responses_calculated_at", "reviewed_at")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("block review timestamps must include a timezone")
        return value

    @field_validator("applicability_rationale", "uncertainty")
    @classmethod
    def normalize_review_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("operator review metadata must not be blank")
        return normalized

    @model_validator(mode="after")
    def require_ordered_times_and_unique_prescriptions(self) -> OperatorBlockReviewRequest:
        if self.reviewed_at < self.responses_calculated_at:
            raise ValueError("block review cannot predate its training responses")
        prescription_ids = tuple(
            prescription_id
            for draft in self.response_drafts
            for prescription_id in draft.prescription_ids
        )
        if len(set(prescription_ids)) != len(prescription_ids):
            raise ValueError("one prescription cannot be assigned to multiple responses")
        return self


class OperatorReplanningRequest(BaseModel):
    """Untrusted successor-strategy inputs; reviewer identity is server-owned."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_contexts: Annotated[tuple[ReplanningCandidateContext, ...], Field(min_length=1)]
    generated_at: datetime
    review_after_days: int = Field(ge=1)
    applicability_rationale: NonEmptyText
    uncertainty: NonEmptyText

    @field_validator("generated_at")
    @classmethod
    def require_aware_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at must include a timezone")
        return value

    @field_validator("applicability_rationale", "uncertainty")
    @classmethod
    def normalize_review_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("operator review metadata must not be blank")
        return normalized


def execute_operator_block_review(
    session: Session,
    block_id: UUID,
    request: OperatorBlockReviewRequest,
    authority: AuthorizedRole,
) -> BlockReviewCreationResult:
    command = CreateBlockReviewCommand(
        **request.model_dump(),
        reviewed_by=f"account:{authority.account_id}",
        review_authority_assignment_id=authority.assignment_id,
    )
    return PersistedBlockReviewService(session).execute(block_id, command)


def execute_operator_replanning(
    session: Session,
    block_review_id: UUID,
    request: OperatorReplanningRequest,
    authority: AuthorizedRole,
) -> PostBlockReplanningResult:
    command = PostBlockReplanningCommand(
        **request.model_dump(),
        reviewed_by=f"account:{authority.account_id}",
        review_authority_assignment_id=authority.assignment_id,
    )
    return PersistedReplanningService(session).execute(block_review_id, command)
