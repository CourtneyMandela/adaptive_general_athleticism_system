from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Annotated, TypeVar
from uuid import UUID

from agas_domain import (
    Adaptation,
    CapabilityEstimate,
    ClosedLoopReplanningResult,
    CompetencyFloor,
    ReplanningCandidateContext,
    TrainingResponse,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import ClosedLoopReplanner, ClosedLoopReplanningError
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

_Record = TypeVar("_Record", Adaptation, CapabilityEstimate, CompetencyFloor, TrainingResponse)


class PostBlockReplanningCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_contexts: Annotated[tuple[ReplanningCandidateContext, ...], Field(min_length=1)]
    generated_at: datetime
    review_after_days: int = Field(ge=1)

    @field_validator("generated_at")
    @classmethod
    def require_aware_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at must include a timezone")
        return value


class ReplanningUseCaseError(RuntimeError):
    """Base error for the persisted post-block replanning use case."""


class ReplanningNotFoundError(ReplanningUseCaseError):
    pass


class ReplanningConflictError(ReplanningUseCaseError):
    pass


class ReplanningValidationError(ReplanningUseCaseError):
    pass


class PersistedReplanningService:
    """Load, replan, and append a strategy revision in one owned transaction."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(
        self, block_review_id: UUID, command: PostBlockReplanningCommand
    ) -> ClosedLoopReplanningResult:
        try:
            result = self._build_result(block_review_id, command)
            for need in result.capability_needs:
                self.repository.add_capability_need(need)
            self.session.flush()
            self.repository.add_long_range_strategy(result.strategy)
            self.session.commit()
            return result
        except ReplanningUseCaseError:
            self.session.rollback()
            raise
        except (ClosedLoopReplanningError, DomainIntegrityError) as error:
            self.session.rollback()
            raise ReplanningValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise ReplanningConflictError(
                "the block review already has a strategy revision"
            ) from error

    def _build_result(
        self, block_review_id: UUID, command: PostBlockReplanningCommand
    ) -> ClosedLoopReplanningResult:
        if (
            self.repository.get_long_range_strategy_by_triggering_review(block_review_id)
            is not None
        ):
            raise ReplanningConflictError("the block review already has a strategy revision")
        review = self.repository.get_block_review(block_review_id)
        if review is None:
            raise ReplanningNotFoundError("block review does not exist")
        block = self.repository.get_block_plan(review.block_plan_id)
        if block is None:
            raise ReplanningNotFoundError("reviewed block does not exist")
        previous_strategy = self.repository.get_long_range_strategy(block.long_range_strategy_id)
        if previous_strategy is None:
            raise ReplanningNotFoundError("prior strategy does not exist")
        priority_policy = self.repository.get_priority_policy(previous_strategy.priority_policy_id)
        if priority_policy is None:
            raise ReplanningNotFoundError("priority policy does not exist")

        responses = self._load_records(
            review.training_response_ids,
            self.repository.get_training_response,
            "training response",
        )
        estimate_ids = tuple(
            dict.fromkeys(item.capability_estimate_id for item in command.candidate_contexts)
        )
        estimates = self._load_records(
            estimate_ids,
            self.repository.get_capability_estimate,
            "capability estimate",
        )
        adaptation_ids = tuple(
            dict.fromkeys(item.adaptation_id for item in command.candidate_contexts)
        )
        adaptations = self._load_records(
            adaptation_ids, self.repository.get_adaptation, "adaptation"
        )
        floor_ids = tuple(
            dict.fromkeys(item.competency_floor_id for item in command.candidate_contexts)
        )
        floors = self._load_records(
            floor_ids, self.repository.get_competency_floor, "competency floor"
        )
        return ClosedLoopReplanner().replan(
            previous_strategy=previous_strategy,
            completed_block=block,
            block_review=review,
            training_responses=responses,
            selected_estimates=estimates,
            adaptations=adaptations,
            competency_floors=floors,
            candidate_contexts=command.candidate_contexts,
            priority_policy=priority_policy,
            generated_at=command.generated_at,
            review_after_days=command.review_after_days,
        )

    @staticmethod
    def _load_records(
        record_ids: Iterable[UUID],
        getter: Callable[[UUID], _Record | None],
        label: str,
    ) -> tuple[_Record, ...]:
        records = []
        for record_id in record_ids:
            record = getter(record_id)
            if record is None:
                raise ReplanningNotFoundError(f"{label} {record_id} does not exist")
            records.append(record)
        return tuple(records)
