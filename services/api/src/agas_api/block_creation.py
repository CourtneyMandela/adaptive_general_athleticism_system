from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from agas_domain import BlockPlan, DecisionRecord
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
    reviewed_by: NonEmptyText
    applicability_rationale: NonEmptyText
    uncertainty: NonEmptyText

    @field_validator("generated_at")
    @classmethod
    def require_aware_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at must include a timezone")
        return value

    @field_validator("reviewed_by", "applicability_rationale", "uncertainty")
    @classmethod
    def require_meaningful_review_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("operator review metadata must not be blank")
        return normalized


class BlockPlanCreationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    block_plan: BlockPlan
    decision_record: DecisionRecord


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

    def execute(
        self, strategy_id: UUID, command: CreateBlockPlanCommand
    ) -> BlockPlanCreationResult:
        try:
            block = self._build_block(strategy_id, command)
            self.repository.add_block_plan(block)
            decision_record = self._decision_record(block, command)
            self.repository.add_decision_record(decision_record)
            self.session.commit()
            return BlockPlanCreationResult(
                block_plan=block,
                decision_record=decision_record,
            )
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

    @staticmethod
    def _decision_record(block: BlockPlan, command: CreateBlockPlanCommand) -> DecisionRecord:
        values = [
            f"long_range_strategy:{block.long_range_strategy_id}",
            *(f"adaptation_resource_demand:{item}" for item in command.resource_demand_ids),
            f"resource_allocation_policy:{command.resource_allocation_policy_id}",
            *(f"resource_allocation:{item.id}" for item in block.allocations),
            *(
                f"exercise_resolution:{item.exercise_resolution_id}"
                for item in block.allocations
                if item.exercise_resolution_id is not None
            ),
            *(f"observation:{item}" for item in block.source_observation_ids),
            *(f"evidence_claim:{item}" for item in block.evidence_claim_ids),
            f"block_plan:{block.id}",
        ]
        return DecisionRecord(
            decision=f"Create block plan {block.id} for strategy {block.long_range_strategy_id}.",
            reason=f"Reviewed by {command.reviewed_by}. {command.applicability_rationale}",
            alternatives_considered=(
                "Defer block creation until different reviewed demands, allocation policy, "
                "resource budget, dates, duration, or constraints are available.",
            ),
            evidence=tuple(dict.fromkeys(values)),
            uncertainty=command.uncertainty,
            decision_version=f"block-operator-review@1.0.0;planner={block.rule_version}",
            decided_on=command.generated_at.date(),
        )
