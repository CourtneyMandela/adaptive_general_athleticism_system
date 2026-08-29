from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from agas_domain import (
    AdaptationPriority,
    AdaptationResourceDemand,
    DecisionRecord,
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
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

NonEmptyText = Annotated[str, Field(min_length=1)]


class ReviewedResourceDemandCommand(BaseModel):
    """Review metadata shared by active and deferred resource decisions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    prepared_at: datetime
    reviewed_by: NonEmptyText
    applicability_rationale: NonEmptyText
    uncertainty: NonEmptyText

    @field_validator("prepared_at")
    @classmethod
    def require_aware_prepared_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("prepared_at must include a timezone")
        return value

    @field_validator("reviewed_by", "applicability_rationale", "uncertainty")
    @classmethod
    def require_meaningful_review_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("operator review metadata must not be blank")
        return normalized


class ActiveResourceDemandCommand(ReviewedResourceDemandCommand):
    """Explicit scientific, environment, and resource inputs for an active priority."""

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
    def validate_active_command(self) -> ActiveResourceDemandCommand:
        if len(set(self.exercise_candidate_ids)) != len(self.exercise_candidate_ids):
            raise ValueError("exercise_candidate_ids must not contain duplicates")
        return self


class DeferredResourceDemandCommand(ReviewedResourceDemandCommand):
    """Explicit provenance for a priority that currently receives no training resource."""

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
    decision_record: DecisionRecord

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
            self.repository.add_decision_record(result.decision_record)
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
            demand = AdaptationResourceDemand(
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
            return self._result(
                strategy=strategy,
                priority=priority,
                command=command,
                resource_demand=demand,
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
        return self._result(
            strategy=strategy,
            priority=priority,
            command=command,
            stimulus_requirement=requirement,
            exercise_resolution=resolution,
            resource_demand=demand,
        )

    @staticmethod
    def _result(
        *,
        strategy: LongRangeStrategy,
        priority: AdaptationPriority,
        command: ActiveResourceDemandCommand | DeferredResourceDemandCommand,
        resource_demand: AdaptationResourceDemand,
        stimulus_requirement: StimulusRequirement | None = None,
        exercise_resolution: ExerciseResolution | None = None,
    ) -> ResourceDemandPreparationResult:
        values = [
            f"long_range_strategy:{strategy.id}",
            f"adaptation_priority:{priority.id}",
            f"adaptation:{priority.adaptation_id}",
            *(f"observation:{item}" for item in resource_demand.source_observation_ids),
            *(f"evidence_claim:{item}" for item in resource_demand.evidence_claim_ids),
        ]
        if isinstance(command, ActiveResourceDemandCommand):
            values.extend(
                [
                    f"environment:{command.environment_id}",
                    *(
                        f"exercise_candidate:{exercise_id}"
                        for exercise_id in command.exercise_candidate_ids
                    ),
                    f"exercise_resolver_policy:{command.exercise_resolver_policy_id}",
                ]
            )
        if stimulus_requirement is not None:
            values.append(f"stimulus_requirement:{stimulus_requirement.id}")
        if exercise_resolution is not None:
            values.extend(
                [
                    *(
                        f"equipment_availability:{item}"
                        for item in exercise_resolution.source_availability_ids
                    ),
                    f"exercise_resolution:{exercise_resolution.id}",
                ]
            )
        values.append(f"adaptation_resource_demand:{resource_demand.id}")
        decision = DecisionRecord(
            decision=(
                f"Prepare {command.mode} resource demand {resource_demand.id} for strategy "
                f"priority {priority.id}."
            ),
            reason=f"Reviewed by {command.reviewed_by}. {command.applicability_rationale}",
            alternatives_considered=(
                "Defer resource-demand preparation until different reviewed stimulus, exercise, "
                "environment, resource, or provenance inputs are available.",
            ),
            evidence=tuple(dict.fromkeys(values)),
            uncertainty=command.uncertainty,
            decision_version=(
                f"resource-demand-operator-review@1.0.0;demand={resource_demand.demand_version}"
            ),
            decided_on=command.prepared_at.date(),
        )
        return ResourceDemandPreparationResult(
            stimulus_requirement=stimulus_requirement,
            exercise_resolution=exercise_resolution,
            resource_demand=resource_demand,
            decision_record=decision,
        )
