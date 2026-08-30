from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from agas_domain import (
    Adaptation,
    AdaptationPriority,
    AdaptationResourceDemand,
    Environment,
    EnvironmentSnapshot,
    EvidenceClaim,
    Exercise,
    ExerciseResolution,
    ExerciseResolverPolicy,
    LongRangeStrategy,
    Observation,
    StimulusRequirement,
)
from agas_domain.persistence.repository import DomainRepository
from agas_planner import EnvironmentSnapshotBuilder, ResolutionError
from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy.orm import Session


class ResourceDemandPreparationNotFoundError(LookupError):
    pass


class ResourceDemandPreparationProjectionError(RuntimeError):
    pass


class ResourceDemandHistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    resource_demand: AdaptationResourceDemand
    stimulus_requirement: StimulusRequirement | None = None
    exercise_resolution: ExerciseResolution | None = None

    @model_validator(mode="after")
    def preserve_active_history_shape(self) -> ResourceDemandHistoryItem:
        active = self.resource_demand.stimulus_requirement_id is not None
        if active != (self.stimulus_requirement is not None):
            raise ValueError("active demand history requires its stimulus requirement")
        if active != (self.exercise_resolution is not None):
            raise ValueError("active demand history requires its exercise resolution")
        return self


class ResourceDemandPriorityOption(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    priority: AdaptationPriority
    adaptation: Adaptation
    demand_history: tuple[ResourceDemandHistoryItem, ...]


class ResourceDemandEnvironmentOption(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    environment: Environment
    snapshot: EnvironmentSnapshot


class ResourceDemandPreparationProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy: LongRangeStrategy
    projected_at: datetime
    priorities: tuple[ResourceDemandPriorityOption, ...]
    source_observations: tuple[Observation, ...]
    evidence_claims: tuple[EvidenceClaim, ...]
    environments: tuple[ResourceDemandEnvironmentOption, ...]
    exercise_resolver_policies: tuple[ExerciseResolverPolicy, ...]
    exercise_catalog: tuple[Exercise, ...]
    projection_version: str = "resource-demand-preparation@1.0.0"


class ResourceDemandPreparationProjector:
    """Expose exact persisted inputs without selecting stimulus, dose, or exercises."""

    def __init__(self, session: Session) -> None:
        self.repository = DomainRepository(session)

    def project(
        self, strategy_id: UUID, projected_at: datetime | None = None
    ) -> ResourceDemandPreparationProjection:
        strategy = self.repository.get_long_range_strategy(strategy_id)
        if strategy is None:
            raise ResourceDemandPreparationNotFoundError("long-range strategy does not exist")
        instant = projected_at or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("resource-demand preparation time must include a timezone")
        if instant < strategy.generated_at:
            raise ValueError("resource-demand preparation cannot predate its strategy")

        demand_history = self.repository.list_adaptation_resource_demands_for_strategy(strategy.id)
        priorities = tuple(
            self._priority_option(priority, demand_history) for priority in strategy.priorities
        )
        observations = tuple(
            self._require_observation(strategy, observation_id)
            for observation_id in strategy.source_observation_ids
        )
        evidence = tuple(
            self._require_evidence_claim(claim_id) for claim_id in strategy.evidence_claim_ids
        )
        environments = self._environment_options(strategy, instant)
        return ResourceDemandPreparationProjection(
            strategy=strategy,
            projected_at=instant,
            priorities=priorities,
            source_observations=observations,
            evidence_claims=evidence,
            environments=environments,
            exercise_resolver_policies=self.repository.list_exercise_resolver_policies(),
            exercise_catalog=self.repository.list_exercises(),
        )

    def _priority_option(
        self,
        priority: AdaptationPriority,
        demands: tuple[AdaptationResourceDemand, ...],
    ) -> ResourceDemandPriorityOption:
        adaptation = self.repository.get_adaptation(priority.adaptation_id)
        if adaptation is None:
            raise ResourceDemandPreparationProjectionError(
                f"priority adaptation {priority.adaptation_id} does not exist"
            )
        history = tuple(
            self._history_item(demand)
            for demand in demands
            if demand.adaptation_priority_id == priority.id
        )
        return ResourceDemandPriorityOption(
            priority=priority,
            adaptation=adaptation,
            demand_history=history,
        )

    def _history_item(self, demand: AdaptationResourceDemand) -> ResourceDemandHistoryItem:
        if demand.stimulus_requirement_id is None:
            return ResourceDemandHistoryItem(resource_demand=demand)
        requirement = self.repository.get_stimulus_requirement(demand.stimulus_requirement_id)
        if requirement is None:
            raise ResourceDemandPreparationProjectionError(
                f"stimulus requirement {demand.stimulus_requirement_id} does not exist"
            )
        if demand.exercise_resolution_id is None:
            raise ResourceDemandPreparationProjectionError(
                "active resource demand has no exercise resolution"
            )
        resolution = self.repository.get_exercise_resolution(demand.exercise_resolution_id)
        if resolution is None:
            raise ResourceDemandPreparationProjectionError(
                f"exercise resolution {demand.exercise_resolution_id} does not exist"
            )
        return ResourceDemandHistoryItem(
            resource_demand=demand,
            stimulus_requirement=requirement,
            exercise_resolution=resolution,
        )

    def _environment_options(
        self, strategy: LongRangeStrategy, instant: datetime
    ) -> tuple[ResourceDemandEnvironmentOption, ...]:
        equipment = self.repository.list_equipment()
        options = []
        for environment in self.repository.list_environments(strategy.athlete_id):
            availability = self.repository.list_equipment_availability(environment.id)
            try:
                snapshot = EnvironmentSnapshotBuilder().build(
                    environment,
                    equipment,
                    availability,
                    instant,
                )
            except ResolutionError as error:
                raise ResourceDemandPreparationProjectionError(str(error)) from error
            options.append(
                ResourceDemandEnvironmentOption(
                    environment=environment,
                    snapshot=snapshot,
                )
            )
        return tuple(options)

    def _require_observation(
        self, strategy: LongRangeStrategy, observation_id: UUID
    ) -> Observation:
        observation = self.repository.get_observation(observation_id)
        if observation is None:
            raise ResourceDemandPreparationProjectionError(
                f"strategy observation {observation_id} does not exist"
            )
        if observation.athlete_id != strategy.athlete_id:
            raise ResourceDemandPreparationProjectionError(
                "strategy observation belongs to a different athlete"
            )
        return observation

    def _require_evidence_claim(self, claim_id: UUID) -> EvidenceClaim:
        claim = self.repository.get_evidence_claim(claim_id)
        if claim is None:
            raise ResourceDemandPreparationProjectionError(
                f"strategy evidence claim {claim_id} does not exist"
            )
        return claim
