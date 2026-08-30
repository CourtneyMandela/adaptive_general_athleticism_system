from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from agas_api.identity import AuthorizedRole
from agas_api.weekly_planning import (
    CreateWeeklyPlanCommand,
    PersistedWeeklyPlanService,
    SessionPrescriptionDraft,
    SessionTemplateDraft,
    WeeklyAvailabilityDraft,
    WeeklyPlanCreationResult,
)

NonEmptyText = Annotated[str, Field(min_length=1)]


class OperatorWeeklyPlanRequest(BaseModel):
    """Untrusted dose and calendar inputs; reviewer identity is server-owned."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    prescriptions: Annotated[tuple[SessionPrescriptionDraft, ...], Field(min_length=1)]
    session_templates: Annotated[tuple[SessionTemplateDraft, ...], Field(min_length=1)]
    availability: WeeklyAvailabilityDraft
    scheduling_policy_id: UUID
    scheduling_policy_review_id: UUID
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
    def normalize_review_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("operator review metadata must not be blank")
        return normalized


def execute_operator_weekly_plan_creation(
    session: Session,
    block_id: UUID,
    request: OperatorWeeklyPlanRequest,
    authority: AuthorizedRole,
) -> WeeklyPlanCreationResult:
    command = CreateWeeklyPlanCommand(
        **request.model_dump(),
        reviewed_by=f"account:{authority.account_id}",
        review_authority_assignment_id=authority.assignment_id,
    )
    return PersistedWeeklyPlanService(session).execute(block_id, command)
