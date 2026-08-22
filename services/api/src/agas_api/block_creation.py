from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from agas_domain import BlockPlan
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import BlockPlanner, BlockPlanningError
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

NonEmptyText = Annotated[str, Field(min_length=1)]


class CreateBlockPlanCommand(BaseModel):
    """Explicit, already-governed inputs for one deterministic block plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    resource_demand_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    resource_allocation_policy_id: UUID
    weekly_budget_minutes: int = Field(gt=0)
    starts_on: date
    duration_weeks: int = Field(ge=4, le=6)
    constraints: tuple[NonEmptyText, ...] = ()
    generated_at: datetime

    @field_validator("generated_at")
    @classmethod
    def require_aware_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at must include a timezone")
        return value


class BlockCreationUseCaseError(RuntimeError):
    """Base error for the persisted block-creation use case."""


class BlockCreationNotFoundError(BlockCreationUseCaseError):
    pass


class BlockCreationConflictError(BlockCreationUseCaseError):
    pass


class BlockCreationValidationError(BlockCreationUseCaseError):
    pass


class PersistedBlockCreationService:
    """Load governed planning inputs and append one block in an owned transaction."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(self, strategy_id: UUID, command: CreateBlockPlanCommand) -> BlockPlan:
        try:
            block = self._build_block(strategy_id, command)
            self.repository.add_block_plan(block)
            self.session.commit()
            return block
        except BlockCreationUseCaseError:
            self.session.rollback()
            raise
        except (BlockPlanningError, DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise BlockCreationValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise BlockCreationConflictError(
                "the block plan conflicts with persisted planning state"
            ) from error

    def _build_block(self, strategy_id: UUID, command: CreateBlockPlanCommand) -> BlockPlan:
        strategy = self.repository.get_long_range_strategy(strategy_id)
        if strategy is None:
            raise BlockCreationNotFoundError("long-range strategy does not exist")

        demands = []
        for demand_id in command.resource_demand_ids:
            demand = self.repository.get_adaptation_resource_demand(demand_id)
            if demand is None:
                raise BlockCreationNotFoundError(f"resource demand {demand_id} does not exist")
            demands.append(demand)

        policy = self.repository.get_resource_allocation_policy(
            command.resource_allocation_policy_id
        )
        if policy is None:
            raise BlockCreationNotFoundError("resource-allocation policy does not exist")

        resolution_ids = tuple(
            dict.fromkeys(
                demand.exercise_resolution_id
                for demand in demands
                if demand.exercise_resolution_id is not None
            )
        )
        resolutions = []
        for resolution_id in resolution_ids:
            resolution = self.repository.get_exercise_resolution(resolution_id)
            if resolution is None:
                raise BlockCreationNotFoundError(
                    f"exercise resolution {resolution_id} does not exist"
                )
            resolutions.append(resolution)

        return BlockPlanner().build(
            strategy=strategy,
            demands=demands,
            resolutions=resolutions,
            policy=policy,
            weekly_budget_minutes=command.weekly_budget_minutes,
            starts_on=command.starts_on,
            duration_weeks=command.duration_weeks,
            constraints=command.constraints,
            generated_at=command.generated_at,
        )
