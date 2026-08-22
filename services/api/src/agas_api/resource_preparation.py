from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from agas_domain import (
    AdaptationPriority,
    AdaptationResourceDemand,
    ExerciseResolution,
    LongRangeStrategy,
    StimulusRequirement,
    StimulusSpecification,
    TrainingPriorityState,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import (
    EnvironmentSnapshotBuilder,
    ExerciseResolver,
    ResolutionError,
    StimulusRequirementBuilder,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

NonEmptyText = Annotated[str, Field(min_length=1)]


class ActiveResourceDemandCommand(BaseModel):
    """Explicit scientific, environment, and resource inputs for an active priority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

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
    prepared_at: datetime

    @model_validator(mode="after")
    def validate_active_command(self) -> ActiveResourceDemandCommand:
        if len(set(self.exercise_candidate_ids)) != len(self.exercise_candidate_ids):
            raise ValueError("exercise_candidate_ids must not contain duplicates")
        if self.prepared_at.tzinfo is None or self.prepared_at.utcoffset() is None:
            raise ValueError("prepared_at must include a timezone")
        return self


class DeferredResourceDemandCommand(BaseModel):
    """Explicit provenance for a priority that currently receives no training resource."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: Literal["deferred"]
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    demand_rationale: NonEmptyText
    demand_version: NonEmptyText

    @model_validator(mode="after")
    def reject_duplicate_provenance(self) -> DeferredResourceDemandCommand:
        for field_name in ("source_observation_ids", "evidence_claim_ids"):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        return self


ResourceDemandPreparationCommand = Annotated[
    ActiveResourceDemandCommand | DeferredResourceDemandCommand,
    Field(discriminator="mode"),
]


class ResourceDemandPreparationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stimulus_requirement: StimulusRequirement | None = None
    exercise_resolution: ExerciseResolution | None = None
    resource_demand: AdaptationResourceDemand

    @model_validator(mode="after")
    def validate_result_shape(self) -> ResourceDemandPreparationResult:
        active = self.resource_demand.priority_state is not TrainingPriorityState.DEFER
        if active != (self.stimulus_requirement is not None):
            raise ValueError("active results require one stimulus requirement")
        if active != (self.exercise_resolution is not None):
            raise ValueError("active results require one exercise resolution")
        return self


class ResourcePreparationUseCaseError(RuntimeError):
    """Base error for persisted resource-demand preparation."""


class ResourcePreparationNotFoundError(ResourcePreparationUseCaseError):
    pass


class ResourcePreparationConflictError(ResourcePreparationUseCaseError):
    pass


class ResourcePreparationValidationError(ResourcePreparationUseCaseError):
    pass


class PersistedResourcePreparationService:
    """Resolve one strategy priority and append its planning inputs atomically."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(
        self,
        strategy_id: UUID,
        priority_id: UUID,
        command: ResourceDemandPreparationCommand,
    ) -> ResourceDemandPreparationResult:
        try:
            result = self._prepare(strategy_id, priority_id, command)
            if result.stimulus_requirement is not None:
                self.repository.add_stimulus_requirement(result.stimulus_requirement)
                self.session.flush()
            if result.exercise_resolution is not None:
                self.repository.add_exercise_resolution(result.exercise_resolution)
                self.session.flush()
            self.repository.add_adaptation_resource_demand(result.resource_demand)
            self.session.commit()
            return result
        except ResourcePreparationUseCaseError:
            self.session.rollback()
            raise
        except (ResolutionError, DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise ResourcePreparationValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise ResourcePreparationConflictError(
                "resource-demand preparation conflicts with persisted planning state"
            ) from error

    def _prepare(
        self,
        strategy_id: UUID,
        priority_id: UUID,
        command: ResourceDemandPreparationCommand,
    ) -> ResourceDemandPreparationResult:
        strategy = self.repository.get_long_range_strategy(strategy_id)
        if strategy is None:
            raise ResourcePreparationNotFoundError("long-range strategy does not exist")
        priority = next((item for item in strategy.priorities if item.id == priority_id), None)
        if priority is None:
            raise ResourcePreparationNotFoundError(
                "adaptation priority does not belong to the strategy"
            )
        if isinstance(command, DeferredResourceDemandCommand):
            if priority.state is not TrainingPriorityState.DEFER:
                raise ResourcePreparationValidationError(
                    "only a DEFER priority can create a deferred resource demand"
                )
            return ResourceDemandPreparationResult(
                resource_demand=AdaptationResourceDemand(
                    long_range_strategy_id=strategy.id,
                    adaptation_priority_id=priority.id,
                    adaptation_id=priority.adaptation_id,
                    priority_state=priority.state,
                    minimum_weekly_minutes=0,
                    target_weekly_minutes=0,
                    sessions_per_week=0,
                    source_observation_ids=command.source_observation_ids,
                    evidence_claim_ids=command.evidence_claim_ids,
                    rationale=command.demand_rationale,
                    demand_version=command.demand_version,
                )
            )
        if priority.state is TrainingPriorityState.DEFER:
            raise ResourcePreparationValidationError(
                "a DEFER priority cannot create an active stimulus or resource demand"
            )
        return self._prepare_active(strategy, priority, command)

    def _prepare_active(
        self,
        strategy: LongRangeStrategy,
        priority: AdaptationPriority,
        command: ActiveResourceDemandCommand,
    ) -> ResourceDemandPreparationResult:
        adaptation = self.repository.get_adaptation(priority.adaptation_id)
        if adaptation is None:
            raise ResourcePreparationNotFoundError("priority adaptation does not exist")
        environment = self.repository.get_environment(command.environment_id)
        if environment is None:
            raise ResourcePreparationNotFoundError("environment does not exist")
        policy = self.repository.get_exercise_resolver_policy(command.exercise_resolver_policy_id)
        if policy is None:
            raise ResourcePreparationNotFoundError("exercise resolver policy does not exist")

        exercises = []
        for exercise_id in command.exercise_candidate_ids:
            exercise = self.repository.get_exercise(exercise_id)
            if exercise is None:
                raise ResourcePreparationNotFoundError(
                    f"exercise candidate {exercise_id} does not exist"
                )
            exercises.append(exercise)
        availability = self.repository.list_equipment_availability(environment.id)
        equipment = []
        for equipment_id in dict.fromkeys(item.equipment_id for item in availability):
            item = self.repository.get_equipment(equipment_id)
            if item is None:
                raise ResourcePreparationNotFoundError(
                    f"availability equipment {equipment_id} does not exist"
                )
            equipment.append(item)

        snapshot = EnvironmentSnapshotBuilder().build(
            environment, equipment, availability, command.prepared_at
        )
        requirement = StimulusRequirementBuilder().build(
            strategy=strategy,
            priority=priority,
            adaptation=adaptation,
            specification=command.stimulus_specification,
            generated_at=command.prepared_at,
        )
        resolution = ExerciseResolver().resolve(
            requirement=requirement,
            environment=snapshot,
            exercises=exercises,
            policy=policy,
            resolved_at=command.prepared_at,
        )
        demand = AdaptationResourceDemand(
            long_range_strategy_id=strategy.id,
            adaptation_priority_id=priority.id,
            adaptation_id=priority.adaptation_id,
            priority_state=priority.state,
            stimulus_requirement_id=requirement.id,
            exercise_resolution_id=resolution.id,
            minimum_weekly_minutes=command.minimum_weekly_minutes,
            target_weekly_minutes=command.target_weekly_minutes,
            sessions_per_week=command.sessions_per_week,
            source_observation_ids=command.stimulus_specification.source_observation_ids,
            evidence_claim_ids=command.stimulus_specification.evidence_claim_ids,
            rationale=command.demand_rationale,
            demand_version=command.demand_version,
        )
        return ResourceDemandPreparationResult(
            stimulus_requirement=requirement,
            exercise_resolution=resolution,
            resource_demand=demand,
        )
