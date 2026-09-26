from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from agas_domain import LongRangeStrategy, TrainingPriorityState
from agas_domain.persistence.repository import DomainRepository
from pydantic import BaseModel, ConfigDict


class PreparedPriorPriority(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    adaptation_id: UUID
    adaptation_priority_id: UUID
    capability_need_id: UUID
    state: TrainingPriorityState


class PreparedStrategyCycleLineage(BaseModel):
    """Exact prior-cycle lineage included in prepared planning candidates."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cycle: Literal["initial", "successor"]
    predecessor_strategy_id: UUID | None = None
    triggering_block_review_id: UUID | None = None
    predecessor_block_plan_id: UUID | None = None
    predecessor_block_ends_on: date | None = None
    prior_priorities: tuple[PreparedPriorPriority, ...] = ()


class PreparedStrategyCycleError(RuntimeError):
    pass


def resolve_strategy_cycle_lineage(
    repository: DomainRepository,
    strategy: LongRangeStrategy,
) -> PreparedStrategyCycleLineage:
    """Fail closed unless a successor strategy's immutable review chain is exact."""

    if strategy.supersedes_strategy_id is None:
        if strategy.triggering_block_review_id is not None:
            raise PreparedStrategyCycleError(
                "An initial strategy cannot reference a triggering block review."
            )
        return PreparedStrategyCycleLineage(cycle="initial")

    if strategy.triggering_block_review_id is None:
        raise PreparedStrategyCycleError(
            "A successor strategy requires its triggering block review."
        )
    predecessor = repository.get_long_range_strategy(strategy.supersedes_strategy_id)
    review = repository.get_block_review(strategy.triggering_block_review_id)
    if predecessor is None or predecessor.athlete_id != strategy.athlete_id:
        raise PreparedStrategyCycleError(
            "The successor strategy's predecessor is unavailable or belongs to another athlete."
        )
    if review is None or review.athlete_id != strategy.athlete_id:
        raise PreparedStrategyCycleError(
            "The successor strategy's triggering review is unavailable or belongs to "
            "another athlete."
        )
    predecessor_block = repository.get_block_plan(review.block_plan_id)
    if (
        predecessor_block is None
        or predecessor_block.athlete_id != strategy.athlete_id
        or predecessor_block.long_range_strategy_id != predecessor.id
    ):
        raise PreparedStrategyCycleError(
            "The triggering review does not identify a block from the predecessor strategy."
        )
    if review.reviewed_at > strategy.generated_at:
        raise PreparedStrategyCycleError(
            "The successor strategy predates its triggering block review."
        )

    return PreparedStrategyCycleLineage(
        cycle="successor",
        predecessor_strategy_id=predecessor.id,
        triggering_block_review_id=review.id,
        predecessor_block_plan_id=predecessor_block.id,
        predecessor_block_ends_on=predecessor_block.ends_on,
        prior_priorities=tuple(
            PreparedPriorPriority(
                adaptation_id=priority.adaptation_id,
                adaptation_priority_id=priority.id,
                capability_need_id=priority.capability_need_id,
                state=priority.state,
            )
            for priority in predecessor.priorities
        ),
    )


def prior_state_for_adaptation(
    lineage: PreparedStrategyCycleLineage,
    adaptation_id: UUID,
) -> TrainingPriorityState | None:
    matches = tuple(
        item.state for item in lineage.prior_priorities if item.adaptation_id == adaptation_id
    )
    if len(matches) > 1:
        raise PreparedStrategyCycleError(
            "The predecessor strategy contains duplicate priorities for one adaptation."
        )
    return matches[0] if matches else None
