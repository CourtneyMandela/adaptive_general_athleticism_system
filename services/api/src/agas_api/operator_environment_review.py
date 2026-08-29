from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from agas_api.environment_prescription_revision import (
    CreateEnvironmentPrescriptionRevisionsCommand,
    EnvironmentPrescriptionRevisionDraft,
    EnvironmentPrescriptionRevisionResult,
    EnvironmentPrescriptionRevisionValidationError,
    PersistedEnvironmentPrescriptionRevisionService,
)
from agas_api.exercise_reresolution import (
    ExerciseReResolutionResult,
    ExerciseReResolutionValidationError,
    PersistedExerciseReResolutionService,
    ReResolveExerciseCommand,
)
from agas_api.identity import AuthorizedRole

NonEmptyText = Annotated[str, Field(min_length=1)]


class OperatorExerciseReResolutionRequest(BaseModel):
    """Untrusted reviewer input; authenticated reviewer identity is server-owned."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    environment_id: UUID
    exercise_candidate_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    exercise_resolver_policy_id: UUID
    resolved_at: datetime
    applicability_rationale: NonEmptyText
    uncertainty: NonEmptyText

    @field_validator("resolved_at")
    @classmethod
    def require_aware_resolved_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("resolved_at must include a timezone")
        return value

    @field_validator("applicability_rationale", "uncertainty")
    @classmethod
    def require_meaningful_review_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("operator review metadata must not be blank")
        return normalized

    @model_validator(mode="after")
    def reject_duplicate_candidates(self) -> OperatorExerciseReResolutionRequest:
        if len(set(self.exercise_candidate_ids)) != len(self.exercise_candidate_ids):
            raise ValueError("exercise_candidate_ids must not contain duplicates")
        return self


class OperatorEnvironmentPrescriptionRevisionRequest(BaseModel):
    """Untrusted revision input; authenticated reviewer identity is server-owned."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    revisions: Annotated[tuple[EnvironmentPrescriptionRevisionDraft, ...], Field(min_length=1)]
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

    @model_validator(mode="after")
    def reject_duplicate_sources(self) -> OperatorEnvironmentPrescriptionRevisionRequest:
        source_ids = tuple(item.source_prescription_id for item in self.revisions)
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("revision drafts must have unique source prescriptions")
        return self


def execute_operator_exercise_reresolution(
    session: Session,
    stimulus_requirement_id: UUID,
    request: OperatorExerciseReResolutionRequest,
    authority: AuthorizedRole,
) -> ExerciseReResolutionResult:
    if request.resolved_at < authority.assigned_at:
        raise ExerciseReResolutionValidationError(
            "exercise re-resolution cannot predate the reviewer role assignment"
        )
    command = ReResolveExerciseCommand(
        **request.model_dump(),
        reviewed_by=f"account:{authority.account_id}",
        review_authority_assignment_id=authority.assignment_id,
    )
    return PersistedExerciseReResolutionService(session).execute(stimulus_requirement_id, command)


def execute_operator_environment_prescription_revision(
    session: Session,
    source_weekly_plan_id: UUID,
    request: OperatorEnvironmentPrescriptionRevisionRequest,
    authority: AuthorizedRole,
) -> EnvironmentPrescriptionRevisionResult:
    if request.prepared_at < authority.assigned_at:
        raise EnvironmentPrescriptionRevisionValidationError(
            "prescription revision cannot predate the reviewer role assignment"
        )
    command = CreateEnvironmentPrescriptionRevisionsCommand(
        **request.model_dump(),
        reviewed_by=f"account:{authority.account_id}",
        review_authority_assignment_id=authority.assignment_id,
    )
    return PersistedEnvironmentPrescriptionRevisionService(session).execute(
        source_weekly_plan_id, command
    )
