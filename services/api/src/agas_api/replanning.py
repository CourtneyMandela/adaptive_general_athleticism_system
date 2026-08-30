from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Annotated, TypeVar
from uuid import UUID

from agas_domain import (
    AccountRole,
    AccountRoleStatus,
    Adaptation,
    CapabilityEstimate,
    ClosedLoopReplanningResult,
    CompetencyFloor,
    DecisionRecord,
    LongRangeStrategy,
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
    reviewed_by: Annotated[str, Field(min_length=1)]
    review_authority_assignment_id: UUID | None = None
    applicability_rationale: Annotated[str, Field(min_length=1)]
    uncertainty: Annotated[str, Field(min_length=1)]

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


class PostBlockReplanningResult(ClosedLoopReplanningResult):
    decision_record: DecisionRecord


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
    ) -> PostBlockReplanningResult:
        try:
            result = self._build_result(block_review_id, command)
            for need in result.capability_needs:
                self.repository.add_capability_need(need)
            self.session.flush()
            self.repository.add_long_range_strategy(result.strategy)
            self.repository.add_decision_record(result.decision_record)
            self.session.commit()
            return result
        except ReplanningUseCaseError:
            self.session.rollback()
            raise
        except (ClosedLoopReplanningError, DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise ReplanningValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise ReplanningConflictError(
                "the block review already has a strategy revision"
            ) from error

    def _build_result(
        self, block_review_id: UUID, command: PostBlockReplanningCommand
    ) -> PostBlockReplanningResult:
        if (
            self.repository.get_long_range_strategy_by_triggering_review(block_review_id)
            is not None
        ):
            raise ReplanningConflictError("the block review already has a strategy revision")
        review = self.repository.get_block_review(block_review_id)
        if review is None:
            raise ReplanningNotFoundError("block review does not exist")
        self._validate_review_authority(command)
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
        replanning = ClosedLoopReplanner().replan(
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
        return PostBlockReplanningResult(
            capability_needs=replanning.capability_needs,
            strategy=replanning.strategy,
            decision_record=self._decision_record(
                command=command,
                previous_strategy=previous_strategy,
                completed_block_id=block.id,
                block_review_id=review.id,
                training_responses=responses,
                priority_policy_id=priority_policy.id,
                replanning=replanning,
            ),
        )

    def _validate_review_authority(self, command: PostBlockReplanningCommand) -> None:
        assignment_id = command.review_authority_assignment_id
        if assignment_id is None:
            return
        assignment = self.repository.get_account_role_assignment(assignment_id)
        if assignment is None:
            raise ReplanningValidationError("review authority assignment does not exist")
        current = self.repository.get_current_account_role_assignment(
            assignment.account_id, AccountRole.PLANNING_REVIEWER
        )
        if (
            assignment.role is not AccountRole.PLANNING_REVIEWER
            or assignment.status is not AccountRoleStatus.ACTIVE
            or current is None
            or current.id != assignment.id
        ):
            raise ReplanningValidationError(
                "review authority assignment is not a current planning-reviewer grant"
            )
        if command.reviewed_by != f"account:{assignment.account_id}":
            raise ReplanningValidationError(
                "reviewed_by does not match the review authority account"
            )
        if command.generated_at < assignment.assigned_at:
            raise ReplanningValidationError(
                "replanning cannot predate the reviewer role assignment"
            )

    @staticmethod
    def _decision_record(
        *,
        command: PostBlockReplanningCommand,
        previous_strategy: LongRangeStrategy,
        completed_block_id: UUID,
        block_review_id: UUID,
        training_responses: tuple[TrainingResponse, ...],
        priority_policy_id: UUID,
        replanning: ClosedLoopReplanningResult,
    ) -> DecisionRecord:
        values = [
            f"long_range_strategy:{previous_strategy.id}",
            f"block_plan:{completed_block_id}",
            f"block_review:{block_review_id}",
            *(f"training_response:{item.id}" for item in training_responses),
            f"priority_policy:{priority_policy_id}",
            *(
                "replanning_candidate:"
                f"adaptation={item.adaptation_id}:floor={item.competency_floor_id}:"
                f"estimate={item.capability_estimate_id}:general={item.general_relevance}:"
                f"goal={item.goal_relevance}:prerequisite={item.prerequisite_value}:"
                f"trainability={item.expected_trainability}:transfer={item.transfer_value}:"
                f"fatigue={item.fatigue_cost}:time={item.time_cost}:"
                f"interference={item.interference_cost}:safe={item.safe_to_train}:"
                f"introductory={item.introductory_exposure_needed}:"
                f"prerequisites_met={item.prerequisites_met}:"
                f"comparative_advantage={item.cultivate_comparative_advantage}"
                for item in command.candidate_contexts
            ),
            *(f"adaptation:{item.adaptation_id}" for item in command.candidate_contexts),
            *(
                f"competency_floor:{item.competency_floor_id}"
                for item in command.candidate_contexts
            ),
            *(
                f"capability_estimate:{item.capability_estimate_id}"
                for item in command.candidate_contexts
            ),
            *(f"capability_need:{item.id}" for item in replanning.capability_needs),
            *(f"observation:{item}" for item in replanning.strategy.source_observation_ids),
            *(f"evidence_claim:{item}" for item in replanning.strategy.evidence_claim_ids),
            f"long_range_strategy:{replanning.strategy.id}",
        ]
        if command.review_authority_assignment_id is not None:
            values.append(f"account_role_assignment:{command.review_authority_assignment_id}")
        return DecisionRecord(
            decision=(
                f"Create successor strategy {replanning.strategy.id} from block review "
                f"{block_review_id}."
            ),
            reason=f"Reviewed by {command.reviewed_by}. {command.applicability_rationale}",
            alternatives_considered=(
                "Retain the prior strategy until different reviewed estimates, competency floors, "
                "candidate contexts, policy authority, or review timing are available.",
            ),
            evidence=tuple(dict.fromkeys(values)),
            uncertainty=command.uncertainty,
            decision_version=(
                "post-block-replanning-operator-review@1.0.0;"
                f"planner={replanning.strategy.rule_version}"
            ),
            decided_on=command.generated_at.date(),
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
