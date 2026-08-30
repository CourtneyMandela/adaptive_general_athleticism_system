from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from agas_domain import InitialPlanningCandidateContext
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from agas_api.identity import AuthorizedRole
from agas_api.initial_planning import (
    CreateInitialStrategyCommand,
    InitialPlanningValidationError,
    InitialStrategyCreationResult,
    PersistedInitialPlanningService,
)

NonEmptyText = Annotated[str, Field(min_length=1)]


class OperatorInitialStrategyRequest(BaseModel):
    """Untrusted planning input; authenticated reviewer identity is server-owned."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    priority_policy_id: UUID
    priority_policy_review_id: UUID
    candidate_contexts: Annotated[tuple[InitialPlanningCandidateContext, ...], Field(min_length=1)]
    generated_at: datetime
    horizon_months: int = Field(ge=6, le=24)
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
    def require_meaningful_review_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("operator review metadata must not be blank")
        return normalized

    @model_validator(mode="after")
    def require_one_context_per_adaptation(self) -> OperatorInitialStrategyRequest:
        adaptation_ids = tuple(item.adaptation_id for item in self.candidate_contexts)
        if len(set(adaptation_ids)) != len(adaptation_ids):
            raise ValueError("candidate_contexts must contain each adaptation once")
        return self


def execute_operator_initial_strategy(
    session: Session,
    athlete_id: UUID,
    request: OperatorInitialStrategyRequest,
    authority: AuthorizedRole,
) -> InitialStrategyCreationResult:
    if request.generated_at < authority.assigned_at:
        raise InitialPlanningValidationError(
            "initial strategy cannot predate the reviewer role assignment"
        )
    command = CreateInitialStrategyCommand(
        **request.model_dump(),
        reviewed_by=f"account:{authority.account_id}",
        review_authority_assignment_id=authority.assignment_id,
    )
    return PersistedInitialPlanningService(session).execute(athlete_id, command)
