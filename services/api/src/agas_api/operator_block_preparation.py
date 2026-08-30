from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from agas_api.block_creation import (
    BlockPlanCreationResult,
    CreateBlockPlanCommand,
    PersistedBlockCreationService,
)
from agas_api.identity import AuthorizedRole

NonEmptyText = Annotated[str, Field(min_length=1)]


class OperatorBlockPlanRequest(BaseModel):
    """Untrusted block context; authenticated reviewer identity is server-owned."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    resource_demand_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    resource_allocation_policy_id: UUID
    weekly_budget_minutes: int = Field(gt=0)
    starts_on: date
    duration_weeks: int = Field(ge=4, le=6)
    constraints: tuple[NonEmptyText, ...] = ()
    generated_at: datetime
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

    @field_validator("resource_demand_ids")
    @classmethod
    def reject_duplicate_demands(cls, value: tuple[UUID, ...]) -> tuple[UUID, ...]:
        if len(set(value)) != len(value):
            raise ValueError("resource_demand_ids must not contain duplicates")
        return value

    @field_validator("constraints")
    @classmethod
    def normalize_constraints(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            raise ValueError("constraints must not contain blank values")
        if len(set(normalized)) != len(normalized):
            raise ValueError("constraints must not contain duplicates")
        return normalized


def execute_operator_block_creation(
    session: Session,
    strategy_id: UUID,
    request: OperatorBlockPlanRequest,
    authority: AuthorizedRole,
) -> BlockPlanCreationResult:
    command = CreateBlockPlanCommand(
        **request.model_dump(),
        reviewed_by=f"account:{authority.account_id}",
        review_authority_assignment_id=authority.assignment_id,
    )
    return PersistedBlockCreationService(session).execute(strategy_id, command)
