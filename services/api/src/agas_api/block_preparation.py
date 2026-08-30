from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from agas_domain import (
    Adaptation,
    AdaptationPriority,
    AdaptationResourceDemand,
    BlockPlan,
    EvidenceClaim,
    ExerciseResolution,
    LongRangeStrategy,
    Observation,
    ResourceAllocationPolicy,
    StimulusRequirement,
)
from agas_domain.persistence.repository import DomainRepository
from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy.orm import Session


class BlockPreparationNotFoundError(LookupError):
    pass


class BlockPreparationProjectionError(RuntimeError):
    pass


class BlockDemandHistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    resource_demand: AdaptationResourceDemand
    stimulus_requirement: StimulusRequirement | None = None
    exercise_resolution: ExerciseResolution | None = None

    @model_validator(mode="after")
    def preserve_demand_shape(self) -> BlockDemandHistoryItem:
        active = self.resource_demand.stimulus_requirement_id is not None
        if active != (self.stimulus_requirement is not None):
            raise ValueError("active block-demand history requires its stimulus requirement")
        if active != (self.exercise_resolution is not None):
            raise ValueError("active block-demand history requires its exercise resolution")
        return self


class BlockPriorityDemandOption(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    priority: AdaptationPriority
    adaptation: Adaptation
    demand_history: tuple[BlockDemandHistoryItem, ...]


class BlockPreparationProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy: LongRangeStrategy
    projected_at: datetime
    priorities: tuple[BlockPriorityDemandOption, ...]
    resource_allocation_policies: tuple[ResourceAllocationPolicy, ...]
    existing_blocks: tuple[BlockPlan, ...]
    source_observations: tuple[Observation, ...]
    evidence_claims: tuple[EvidenceClaim, ...]
    projection_version: str = "block-preparation@1.0.0"


class BlockPreparationProjector:
    """Expose exact block inputs without selecting history, policy, or context."""

    def __init__(self, session: Session) -> None:
        self.repository = DomainRepository(session)

    def project(
        self, strategy_id: UUID, projected_at: datetime | None = None
    ) -> BlockPreparationProjection:
        strategy = self.repository.get_long_range_strategy(strategy_id)
        if strategy is None:
            raise BlockPreparationNotFoundError("long-range strategy does not exist")
        instant = projected_at or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("block preparation time must include a timezone")
        if instant < strategy.generated_at:
            raise ValueError("block preparation cannot predate its strategy")

        demands = self.repository.list_adaptation_resource_demands_for_strategy(strategy.id)
        priorities = tuple(
            self._priority_option(priority, demands) for priority in strategy.priorities
        )
        observation_ids = self._ordered_union(
            strategy.source_observation_ids,
            *(demand.source_observation_ids for demand in demands),
        )
        evidence_ids = self._ordered_union(
            strategy.evidence_claim_ids,
            *(demand.evidence_claim_ids for demand in demands),
        )
        return BlockPreparationProjection(
            strategy=strategy,
            projected_at=instant,
            priorities=priorities,
            resource_allocation_policies=self.repository.list_resource_allocation_policies(),
            existing_blocks=self.repository.list_block_plans_for_strategy(strategy.id),
            source_observations=tuple(
                self._require_observation(strategy, observation_id)
                for observation_id in observation_ids
            ),
            evidence_claims=tuple(
                self._require_evidence_claim(claim_id) for claim_id in evidence_ids
            ),
        )

    def _priority_option(
        self,
        priority: AdaptationPriority,
        demands: tuple[AdaptationResourceDemand, ...],
    ) -> BlockPriorityDemandOption:
        adaptation = self.repository.get_adaptation(priority.adaptation_id)
        if adaptation is None:
            raise BlockPreparationProjectionError(
                f"priority adaptation {priority.adaptation_id} does not exist"
            )
        return BlockPriorityDemandOption(
            priority=priority,
            adaptation=adaptation,
            demand_history=tuple(
                self._history_item(demand)
                for demand in demands
                if demand.adaptation_priority_id == priority.id
            ),
        )

    def _history_item(self, demand: AdaptationResourceDemand) -> BlockDemandHistoryItem:
        if demand.stimulus_requirement_id is None:
            return BlockDemandHistoryItem(resource_demand=demand)
        requirement = self.repository.get_stimulus_requirement(demand.stimulus_requirement_id)
        if requirement is None:
            raise BlockPreparationProjectionError(
                f"stimulus requirement {demand.stimulus_requirement_id} does not exist"
            )
        if demand.exercise_resolution_id is None:
            raise BlockPreparationProjectionError(
                "active resource demand has no exercise resolution"
            )
        resolution = self.repository.get_exercise_resolution(demand.exercise_resolution_id)
        if resolution is None:
            raise BlockPreparationProjectionError(
                f"exercise resolution {demand.exercise_resolution_id} does not exist"
            )
        return BlockDemandHistoryItem(
            resource_demand=demand,
            stimulus_requirement=requirement,
            exercise_resolution=resolution,
        )

    def _require_observation(
        self, strategy: LongRangeStrategy, observation_id: UUID
    ) -> Observation:
        observation = self.repository.get_observation(observation_id)
        if observation is None:
            raise BlockPreparationProjectionError(
                f"block observation {observation_id} does not exist"
            )
        if observation.athlete_id != strategy.athlete_id:
            raise BlockPreparationProjectionError(
                "block observation belongs to a different athlete"
            )
        return observation

    def _require_evidence_claim(self, claim_id: UUID) -> EvidenceClaim:
        claim = self.repository.get_evidence_claim(claim_id)
        if claim is None:
            raise BlockPreparationProjectionError(f"block evidence claim {claim_id} does not exist")
        return claim

    @staticmethod
    def _ordered_union(*groups: tuple[UUID, ...]) -> tuple[UUID, ...]:
        return tuple(dict.fromkeys(item for group in groups for item in group))
