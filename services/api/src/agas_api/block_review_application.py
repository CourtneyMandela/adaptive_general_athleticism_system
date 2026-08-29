from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Annotated
from uuid import UUID

from agas_domain import (
    BlockPlan,
    BlockReview,
    ComparisonDirection,
    DecisionRecord,
    ResponseEvaluationTarget,
    SessionAdherence,
    SessionExecution,
    SessionPrescription,
    SessionSafetyDecision,
    TrainingResponse,
    WeeklyPlanStatus,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import BlockReviewEngine, BlockReviewError, TrainingResponseCalculator
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

NonEmptyText = Annotated[str, Field(min_length=1)]


class TrainingResponseDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    adaptation_id: UUID
    prescription_ids: tuple[UUID, ...] = Field(min_length=1)
    baseline_capability_estimate_id: UUID
    followup_capability_estimate_id: UUID
    intervention_summary: str = Field(min_length=1)
    measurement_uncertainty: str = Field(min_length=1)
    contextual_factors: tuple[str, ...] = ()
    comparison_direction: ComparisonDirection
    minimum_meaningful_change: float = Field(ge=0)

    @model_validator(mode="after")
    def require_unique_nonempty_values(self) -> TrainingResponseDraft:
        if len(set(self.prescription_ids)) != len(self.prescription_ids):
            raise ValueError("response prescription_ids must not contain duplicates")
        if any(not item.strip() for item in self.contextual_factors):
            raise ValueError("contextual_factors must not contain blank values")
        if len(set(self.contextual_factors)) != len(self.contextual_factors):
            raise ValueError("contextual_factors must not contain duplicates")
        return self


class CreateBlockReviewCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    block_review_policy_id: UUID
    response_drafts: tuple[TrainingResponseDraft, ...] = Field(min_length=1)
    responses_calculated_at: datetime
    reviewed_at: datetime
    reviewed_by: NonEmptyText
    applicability_rationale: NonEmptyText
    uncertainty: NonEmptyText

    @field_validator("responses_calculated_at", "reviewed_at")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("block review timestamps must include a timezone")
        return value

    @field_validator("reviewed_by", "applicability_rationale", "uncertainty")
    @classmethod
    def require_meaningful_review_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("operator review metadata must not be blank")
        return normalized

    @model_validator(mode="after")
    def require_ordered_times_and_unique_prescriptions(self) -> CreateBlockReviewCommand:
        if self.reviewed_at < self.responses_calculated_at:
            raise ValueError("block review cannot predate its training responses")
        prescription_ids = [
            prescription_id
            for draft in self.response_drafts
            for prescription_id in draft.prescription_ids
        ]
        if len(set(prescription_ids)) != len(prescription_ids):
            raise ValueError("one prescription cannot be assigned to multiple responses")
        return self


class BlockReviewCreationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    training_responses: tuple[TrainingResponse, ...]
    block_review: BlockReview
    decision_record: DecisionRecord


class BlockReviewUseCaseError(RuntimeError):
    """Base error for the persisted completed-block review use case."""


class BlockReviewNotFoundError(BlockReviewUseCaseError):
    pass


class BlockReviewConflictError(BlockReviewUseCaseError):
    pass


class BlockReviewValidationError(BlockReviewUseCaseError):
    pass


class PersistedBlockReviewService:
    """Derive and append all response evidence for one completed block atomically."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(
        self, block_plan_id: UUID, command: CreateBlockReviewCommand
    ) -> BlockReviewCreationResult:
        try:
            result = self._build(block_plan_id, command)
            for response in result.training_responses:
                self.repository.add_training_response(response)
            self.session.flush()
            self.repository.add_block_review(result.block_review)
            self.repository.add_decision_record(result.decision_record)
            self.session.commit()
            return result
        except BlockReviewUseCaseError:
            self.session.rollback()
            raise
        except (BlockReviewError, DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise BlockReviewValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise BlockReviewConflictError("the block already has a completed review") from error

    def _build(
        self, block_plan_id: UUID, command: CreateBlockReviewCommand
    ) -> BlockReviewCreationResult:
        if self.repository.get_block_review_by_block(block_plan_id) is not None:
            raise BlockReviewConflictError("the block already has a completed review")
        block = self.repository.get_block_plan(block_plan_id)
        if block is None:
            raise BlockReviewNotFoundError("block plan does not exist")
        policy = self.repository.get_block_review_policy(command.block_review_policy_id)
        if policy is None:
            raise BlockReviewNotFoundError("block review policy does not exist")

        block_end = block.starts_on + timedelta(weeks=block.duration_weeks)
        if command.reviewed_at.date() < block_end:
            raise BlockReviewValidationError("a block cannot be reviewed before its planned end")

        weekly_plans = self.repository.list_weekly_plans_for_block(block.id)
        expected_weeks = {
            (week, block.starts_on + timedelta(weeks=week - 1))
            for week in range(1, block.duration_weeks + 1)
        }
        actual_weeks = {(plan.block_week, plan.week_start) for plan in weekly_plans}
        if len(weekly_plans) != block.duration_weeks or actual_weeks != expected_weeks:
            raise BlockReviewValidationError(
                "review requires exactly one persisted weekly plan for every block week"
            )
        if any(plan.status is not WeeklyPlanStatus.FEASIBLE for plan in weekly_plans):
            raise BlockReviewValidationError("review requires feasible weekly plans")

        executions: list[SessionExecution] = []
        adherences_by_pair: dict[tuple[UUID, UUID], SessionAdherence] = {}
        all_safety_decisions: list[SessionSafetyDecision] = []
        for plan in weekly_plans:
            for planned_session in plan.sessions:
                execution = self.repository.get_session_execution_by_planned_session(
                    planned_session.id
                )
                if execution is None:
                    raise BlockReviewValidationError(
                        "every planned session requires a persisted execution outcome"
                    )
                executions.append(execution)
                post_session_decisions = self.repository.list_post_session_safety_decisions(
                    execution.id
                )
                if not post_session_decisions:
                    raise BlockReviewValidationError(
                        "every execution requires a persisted post-session safety decision"
                    )
                all_safety_decisions.extend(post_session_decisions)
                for item in execution.items:
                    adherence = self.repository.get_session_adherence_by_execution_and_prescription(
                        execution.id, item.prescription_id
                    )
                    if adherence is None:
                        raise BlockReviewValidationError(
                            "every executed prescription requires persisted adherence"
                        )
                    adherences_by_pair[(execution.id, item.prescription_id)] = adherence

        executed_prescription_ids = {
            item.prescription_id for execution in executions for item in execution.items
        }
        drafted_prescription_ids = {
            prescription_id
            for draft in command.response_drafts
            for prescription_id in draft.prescription_ids
        }
        if drafted_prescription_ids != executed_prescription_ids:
            raise BlockReviewValidationError(
                "response drafts must exactly partition all executed prescriptions"
            )

        responses = tuple(
            self._build_response(
                block=block,
                draft=draft,
                executions=tuple(executions),
                adherences_by_pair=adherences_by_pair,
                block_end=block_end,
                calculated_at=command.responses_calculated_at,
            )
            for draft in command.response_drafts
        )
        targets = tuple(
            ResponseEvaluationTarget(
                training_response_id=response.id,
                comparison_direction=draft.comparison_direction,
                minimum_meaningful_change=draft.minimum_meaningful_change,
            )
            for response, draft in zip(responses, command.response_drafts, strict=True)
        )
        review = BlockReviewEngine().review(
            block=block,
            responses=responses,
            targets=targets,
            safety_decisions=all_safety_decisions,
            policy=policy,
            reviewed_at=command.reviewed_at,
        )
        return BlockReviewCreationResult(
            training_responses=responses,
            block_review=review,
            decision_record=self._decision_record(
                block=block,
                command=command,
                responses=responses,
                review=review,
            ),
        )

    @staticmethod
    def _decision_record(
        *,
        block: BlockPlan,
        command: CreateBlockReviewCommand,
        responses: tuple[TrainingResponse, ...],
        review: BlockReview,
    ) -> DecisionRecord:
        values = [
            f"block_plan:{block.id}",
            f"block_review_policy:{command.block_review_policy_id}",
            *(
                f"response_evaluation_target:{response.id}:"
                f"direction={draft.comparison_direction.value}:"
                f"minimum_meaningful_change={draft.minimum_meaningful_change}"
                for response, draft in zip(responses, command.response_drafts, strict=True)
            ),
            *(f"adaptation:{response.adaptation_id}" for response in responses),
            *(f"training_response:{response.id}" for response in responses),
            *(
                f"session_prescription:{item}"
                for response in responses
                for item in response.prescription_ids
            ),
            *(
                f"session_execution:{item}"
                for response in responses
                for item in response.session_execution_ids
            ),
            *(
                f"session_adherence:{item}"
                for response in responses
                for item in response.session_adherence_ids
            ),
            *(
                f"capability_estimate:{item}"
                for response in responses
                for item in (
                    response.baseline_capability_estimate_id,
                    response.followup_capability_estimate_id,
                )
            ),
            *(
                f"session_safety_decision:{item}"
                for item in review.post_session_safety_decision_ids
            ),
            *(f"observation:{item}" for item in review.source_observation_ids),
            *(f"evidence_claim:{item}" for item in review.evidence_claim_ids),
            f"block_review:{review.id}",
        ]
        return DecisionRecord(
            decision=f"Complete block review {review.id} for block {block.id}.",
            reason=f"Reviewed by {command.reviewed_by}. {command.applicability_rationale}",
            alternatives_considered=(
                "Defer block review until different reviewed response groupings, estimates, "
                "measurement interpretation, or policy authority are available.",
            ),
            evidence=tuple(dict.fromkeys(values)),
            uncertainty=command.uncertainty,
            decision_version=f"block-review-operator-review@1.0.0;engine={review.rule_version}",
            decided_on=command.reviewed_at.date(),
        )

    def _build_response(
        self,
        *,
        block: BlockPlan,
        draft: TrainingResponseDraft,
        executions: tuple[SessionExecution, ...],
        adherences_by_pair: dict[tuple[UUID, UUID], SessionAdherence],
        block_end: date,
        calculated_at: datetime,
    ) -> TrainingResponse:
        prescriptions: list[SessionPrescription] = []
        for prescription_id in draft.prescription_ids:
            prescription = self.repository.get_session_prescription(prescription_id)
            if prescription is None:
                raise BlockReviewNotFoundError("session prescription does not exist")
            prescriptions.append(prescription)
        baseline = self.repository.get_capability_estimate(draft.baseline_capability_estimate_id)
        followup = self.repository.get_capability_estimate(draft.followup_capability_estimate_id)
        if baseline is None or followup is None:
            raise BlockReviewNotFoundError("capability estimate does not exist")
        if baseline.estimated_at.date() > block.starts_on:
            raise BlockReviewValidationError("baseline estimate must not postdate block start")
        if followup.estimated_at.date() < block_end:
            raise BlockReviewValidationError("follow-up estimate must not predate block end")

        prescription_ids = set(draft.prescription_ids)
        response_executions = tuple(
            execution
            for execution in executions
            if any(item.prescription_id in prescription_ids for item in execution.items)
        )
        response_adherences = tuple(
            adherences_by_pair[(execution.id, item.prescription_id)]
            for execution in response_executions
            for item in execution.items
            if item.prescription_id in prescription_ids
        )
        return TrainingResponseCalculator().calculate(
            block=block,
            adaptation_id=draft.adaptation_id,
            prescriptions=prescriptions,
            executions=response_executions,
            adherences=response_adherences,
            baseline=baseline,
            followup=followup,
            intervention_summary=draft.intervention_summary,
            measurement_uncertainty=draft.measurement_uncertainty,
            contextual_factors=draft.contextual_factors,
            calculated_at=calculated_at,
        )
