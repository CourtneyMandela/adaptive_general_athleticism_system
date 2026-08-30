from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from agas_domain import StimulusSpecification
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from agas_api.identity import AuthorizedRole
from agas_api.resource_preparation import (
    ActiveResourceDemandCommand,
    DeferredResourceDemandCommand,
    PersistedResourcePreparationService,
    ResourceDemandPreparationCommand,
    ResourceDemandPreparationResult,
    ResourcePreparationValidationError,
)

NonEmptyText = Annotated[str, Field(min_length=1)]


class OperatorReviewedResourceDemandRequest(BaseModel):
    """Untrusted review input; authenticated reviewer identity is server-owned."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    prepared_at: datetime
    applicability_rationale: NonEmptyText
    uncertainty: NonEmptyText

    @field_validator("prepared_at")
    @classmethod
    def require_aware_prepared_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("prepared_at must include a timezone")
        return value

    @field_validator("applicability_rationale", "uncertainty")
    @classmethod
    def require_meaningful_review_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("operator review metadata must not be blank")
        return normalized


class OperatorActiveResourceDemandRequest(OperatorReviewedResourceDemandRequest):
    mode: Literal["active"]
    environment_id: UUID
    exercise_candidate_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    exercise_resolver_policy_id: UUID
    stimulus_specification: StimulusSpecification
    minimum_weekly_minutes: int = Field(gt=0)
    target_weekly_minutes: int = Field(gt=0)
    sessions_per_week: int = Field(gt=0)
    demand_rationale: NonEmptyText
    demand_version: NonEmptyText

    @model_validator(mode="after")
    def reject_duplicate_candidates(self) -> OperatorActiveResourceDemandRequest:
        if len(set(self.exercise_candidate_ids)) != len(self.exercise_candidate_ids):
            raise ValueError("exercise_candidate_ids must not contain duplicates")
        return self


class OperatorDeferredResourceDemandRequest(OperatorReviewedResourceDemandRequest):
    mode: Literal["deferred"]
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    demand_rationale: NonEmptyText
    demand_version: NonEmptyText

    @model_validator(mode="after")
    def reject_duplicate_provenance(self) -> OperatorDeferredResourceDemandRequest:
        for field_name in ("source_observation_ids", "evidence_claim_ids"):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        return self


OperatorResourceDemandRequest = Annotated[
    OperatorActiveResourceDemandRequest | OperatorDeferredResourceDemandRequest,
    Field(discriminator="mode"),
]


def execute_operator_resource_preparation(
    session: Session,
    strategy_id: UUID,
    priority_id: UUID,
    request: OperatorResourceDemandRequest,
    authority: AuthorizedRole,
) -> ResourceDemandPreparationResult:
    if request.prepared_at < authority.assigned_at:
        raise ResourcePreparationValidationError(
            "resource-demand preparation cannot predate the reviewer role assignment"
        )
    authority_fields = {
        "reviewed_by": f"account:{authority.account_id}",
        "review_authority_assignment_id": authority.assignment_id,
    }
    command: ResourceDemandPreparationCommand
    if isinstance(request, OperatorActiveResourceDemandRequest):
        command = ActiveResourceDemandCommand(
            **request.model_dump(),
            **authority_fields,
        )
    else:
        command = DeferredResourceDemandCommand(
            **request.model_dump(),
            **authority_fields,
        )
    return PersistedResourcePreparationService(session).execute(
        strategy_id,
        priority_id,
        command,
    )
