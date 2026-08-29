from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from agas_domain import (
    AccountRoleStatus,
    DecisionRecord,
    ExerciseResolution,
    StimulusRequirement,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import EnvironmentSnapshotBuilder, ExerciseResolver, ResolutionError
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

NonEmptyText = Annotated[str, Field(min_length=1)]


class ReResolveExerciseCommand(BaseModel):
    """Reviewed inputs for resolving one existing stimulus in a new environment state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    environment_id: UUID
    exercise_candidate_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    exercise_resolver_policy_id: UUID
    resolved_at: datetime
    reviewed_by: NonEmptyText
    review_authority_assignment_id: UUID | None = None
    applicability_rationale: NonEmptyText
    uncertainty: NonEmptyText

    @field_validator("resolved_at")
    @classmethod
    def require_aware_resolved_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("resolved_at must include a timezone")
        return value

    @field_validator("reviewed_by", "applicability_rationale", "uncertainty")
    @classmethod
    def require_meaningful_review_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("operator review metadata must not be blank")
        return normalized

    @model_validator(mode="after")
    def reject_duplicate_candidates(self) -> ReResolveExerciseCommand:
        if len(set(self.exercise_candidate_ids)) != len(self.exercise_candidate_ids):
            raise ValueError("exercise_candidate_ids must not contain duplicates")
        return self


class ExerciseReResolutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    exercise_resolution: ExerciseResolution
    decision_record: DecisionRecord


class ExerciseReResolutionUseCaseError(RuntimeError):
    """Base error for persisted exercise re-resolution."""


class ExerciseReResolutionNotFoundError(ExerciseReResolutionUseCaseError):
    pass


class ExerciseReResolutionConflictError(ExerciseReResolutionUseCaseError):
    pass


class ExerciseReResolutionValidationError(ExerciseReResolutionUseCaseError):
    pass


class PersistedExerciseReResolutionService:
    """Append one reviewed resolution for an existing immutable stimulus requirement."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(
        self,
        stimulus_requirement_id: UUID,
        command: ReResolveExerciseCommand,
    ) -> ExerciseReResolutionResult:
        try:
            requirement, resolution = self._resolve(stimulus_requirement_id, command)
            self.repository.add_exercise_resolution(resolution)
            decision = self._decision_record(requirement, resolution, command)
            self.repository.add_decision_record(decision)
            self.session.commit()
            return ExerciseReResolutionResult(
                exercise_resolution=resolution,
                decision_record=decision,
            )
        except ExerciseReResolutionUseCaseError:
            self.session.rollback()
            raise
        except (ResolutionError, DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise ExerciseReResolutionValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise ExerciseReResolutionConflictError(
                "exercise re-resolution conflicts with persisted planning state"
            ) from error

    def _resolve(
        self,
        stimulus_requirement_id: UUID,
        command: ReResolveExerciseCommand,
    ) -> tuple[StimulusRequirement, ExerciseResolution]:
        self._validate_review_authority(command)
        requirement = self.repository.get_stimulus_requirement(stimulus_requirement_id)
        if requirement is None:
            raise ExerciseReResolutionNotFoundError("stimulus requirement does not exist")

        environment = self.repository.get_environment(command.environment_id)
        if environment is None:
            raise ExerciseReResolutionNotFoundError("environment does not exist")
        if environment.athlete_id != requirement.athlete_id:
            raise ExerciseReResolutionValidationError(
                "environment belongs to a different athlete than the stimulus requirement"
            )

        policy = self.repository.get_exercise_resolver_policy(command.exercise_resolver_policy_id)
        if policy is None:
            raise ExerciseReResolutionNotFoundError("exercise resolver policy does not exist")

        exercises = []
        for exercise_id in command.exercise_candidate_ids:
            exercise = self.repository.get_exercise(exercise_id)
            if exercise is None:
                raise ExerciseReResolutionNotFoundError(
                    f"exercise candidate {exercise_id} does not exist"
                )
            exercises.append(exercise)

        availability = self.repository.list_equipment_availability(environment.id)
        equipment = []
        for equipment_id in dict.fromkeys(item.equipment_id for item in availability):
            item = self.repository.get_equipment(equipment_id)
            if item is None:
                raise ExerciseReResolutionNotFoundError(
                    f"availability equipment {equipment_id} does not exist"
                )
            equipment.append(item)

        snapshot = EnvironmentSnapshotBuilder().build(
            environment,
            equipment,
            availability,
            command.resolved_at,
        )
        return (
            requirement,
            ExerciseResolver().resolve(
                requirement=requirement,
                environment=snapshot,
                exercises=exercises,
                policy=policy,
                resolved_at=command.resolved_at,
            ),
        )

    def _validate_review_authority(self, command: ReResolveExerciseCommand) -> None:
        assignment_id = command.review_authority_assignment_id
        if assignment_id is None:
            return
        assignment = self.repository.get_account_role_assignment(assignment_id)
        if assignment is None:
            raise ExerciseReResolutionValidationError("review authority assignment does not exist")
        current = self.repository.get_current_account_role_assignment(
            assignment.account_id, assignment.role
        )
        if (
            assignment.status is not AccountRoleStatus.ACTIVE
            or current is None
            or current.id != assignment.id
        ):
            raise ExerciseReResolutionValidationError(
                "review authority assignment is not currently active"
            )
        if command.reviewed_by != f"account:{assignment.account_id}":
            raise ExerciseReResolutionValidationError(
                "reviewed_by does not match the review authority account"
            )
        if command.resolved_at < assignment.assigned_at:
            raise ExerciseReResolutionValidationError(
                "exercise re-resolution cannot predate the reviewer role assignment"
            )

    @staticmethod
    def _decision_record(
        requirement: StimulusRequirement,
        resolution: ExerciseResolution,
        command: ReResolveExerciseCommand,
    ) -> DecisionRecord:
        evidence = (
            f"athlete:{requirement.athlete_id}",
            f"long_range_strategy:{requirement.long_range_strategy_id}",
            f"adaptation_priority:{requirement.adaptation_priority_id}",
            f"adaptation:{requirement.adaptation_id}",
            f"stimulus_requirement:{resolution.stimulus_requirement_id}",
            *(f"observation:{item}" for item in requirement.source_observation_ids),
            *(f"evidence_claim:{item}" for item in requirement.evidence_claim_ids),
            f"environment:{resolution.environment_id}",
            *(f"exercise_candidate:{item}" for item in command.exercise_candidate_ids),
            f"exercise_resolver_policy:{resolution.resolver_policy_id}",
            *(f"equipment_availability:{item}" for item in resolution.source_availability_ids),
            f"exercise_resolution:{resolution.id}",
            *(
                (f"account_role_assignment:{command.review_authority_assignment_id}",)
                if command.review_authority_assignment_id is not None
                else ()
            ),
        )
        return DecisionRecord(
            decision=(
                f"Append {resolution.status.value} exercise resolution {resolution.id} for "
                f"existing stimulus requirement {resolution.stimulus_requirement_id}."
            ),
            reason=f"Reviewed by {command.reviewed_by}. {command.applicability_rationale}",
            alternatives_considered=(
                "Retain the prior exercise resolution and require manual planning review without "
                "asserting that the selected environment can reproduce the stimulus.",
            ),
            evidence=tuple(dict.fromkeys(evidence)),
            uncertainty=command.uncertainty,
            decision_version="exercise-reresolution-operator-review@1.0.0",
            decided_on=command.resolved_at.date(),
        )
