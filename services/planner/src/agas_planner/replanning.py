from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Protocol, TypeVar
from uuid import UUID

from agas_domain import (
    Adaptation,
    AdaptationPlanningCandidate,
    BlockPlan,
    BlockReview,
    CapabilityEstimate,
    ClosedLoopReplanningResult,
    CompetencyFloor,
    CompetencyStatus,
    LongRangeStrategy,
    PriorityPolicy,
    ReplanningCandidateContext,
    TrainingResponse,
)

from agas_planner.planning import (
    CompetencyFloorDetector,
    LongRangeStrategyPlanner,
    PlanningError,
)


class ClosedLoopReplanningError(ValueError):
    """Raised when post-block evidence cannot support an auditable strategy revision."""


class _HasId(Protocol):
    @property
    def id(self) -> UUID: ...


class _HasAdaptationId(Protocol):
    @property
    def adaptation_id(self) -> UUID: ...


_Record = TypeVar("_Record", bound=_HasId)
_AdaptationRecord = TypeVar("_AdaptationRecord", bound=_HasAdaptationId)


class ClosedLoopReplanner:
    """Rebuild needs and strategy from reviewed estimates without rewriting history."""

    def __init__(self, rule_version: str = "closed-loop-replanning@1.0.0") -> None:
        self.rule_version = rule_version

    def replan(
        self,
        *,
        previous_strategy: LongRangeStrategy,
        completed_block: BlockPlan,
        block_review: BlockReview,
        training_responses: Iterable[TrainingResponse],
        selected_estimates: Iterable[CapabilityEstimate],
        adaptations: Iterable[Adaptation],
        competency_floors: Iterable[CompetencyFloor],
        candidate_contexts: Iterable[ReplanningCandidateContext],
        priority_policy: PriorityPolicy,
        generated_at: datetime,
        review_after_days: int,
    ) -> ClosedLoopReplanningResult:
        self._validate_chain(
            previous_strategy=previous_strategy,
            completed_block=completed_block,
            block_review=block_review,
            generated_at=generated_at,
        )
        responses = self._unique_by_adaptation(training_responses, "training responses")
        if tuple(item.id for item in responses.values()) != block_review.training_response_ids:
            raise ClosedLoopReplanningError(
                "training responses must match the block review's ordered responses"
            )
        if any(
            item.athlete_id != previous_strategy.athlete_id
            or item.block_plan_id != completed_block.id
            for item in responses.values()
        ):
            raise ClosedLoopReplanningError("training responses belong to another athlete or block")

        adaptation_by_id = self._unique_by_id(adaptations, "adaptations")
        floor_by_id = self._unique_by_id(competency_floors, "competency floors")
        context_by_adaptation = self._unique_by_adaptation(
            candidate_contexts, "replanning candidate contexts"
        )
        previous_adaptation_ids = {item.adaptation_id for item in previous_strategy.priorities}
        if set(context_by_adaptation) != previous_adaptation_ids:
            raise ClosedLoopReplanningError(
                "replanning contexts must preserve every prior strategy adaptation exactly"
            )
        if set(adaptation_by_id) != previous_adaptation_ids:
            raise ClosedLoopReplanningError(
                "replanning adaptations must preserve every prior strategy adaptation exactly"
            )

        estimate_by_id = self._selected_estimates(
            selected_estimates,
            previous_strategy=previous_strategy,
            responses=responses,
            generated_at=generated_at,
        )
        active_adaptation_ids = {
            item.adaptation_id
            for item in completed_block.allocations
            if item.allocated_weekly_minutes > 0
        }
        detector = CompetencyFloorDetector()
        needs = []
        planning_candidates = []
        for adaptation_id, context in context_by_adaptation.items():
            adaptation = adaptation_by_id[adaptation_id]
            floor = floor_by_id.get(context.competency_floor_id)
            if floor is None:
                raise ClosedLoopReplanningError("replanning context references an unknown floor")
            if floor.domain is not adaptation.domain:
                raise ClosedLoopReplanningError(
                    "replanning adaptation and floor domains must match"
                )
            estimate = estimate_by_id.get(context.capability_estimate_id)
            if estimate is None:
                raise ClosedLoopReplanningError(
                    "replanning context references an unselected capability estimate"
                )
            if adaptation_id in active_adaptation_ids:
                response = responses.get(adaptation_id)
                if response is None:
                    raise ClosedLoopReplanningError(
                        "each trained adaptation requires a reviewed training response"
                    )
                if estimate.id != response.followup_capability_estimate_id:
                    raise ClosedLoopReplanningError(
                        "trained adaptations must use their reviewed follow-up estimate"
                    )
            try:
                need = detector.identify(
                    previous_strategy.athlete_id,
                    floor,
                    estimate,
                    generated_at,
                )
            except PlanningError as error:
                raise ClosedLoopReplanningError(str(error)) from error
            if need.status in {
                CompetencyStatus.UNKNOWN,
                CompetencyStatus.STALE,
                CompetencyStatus.INCOMPARABLE,
            }:
                raise ClosedLoopReplanningError(
                    f"selected estimate cannot support replanning: {need.status.value}"
                )
            needs.append(need)
            planning_candidates.append(
                AdaptationPlanningCandidate(
                    adaptation_id=adaptation_id,
                    capability_need_id=need.id,
                    general_relevance=context.general_relevance,
                    goal_relevance=context.goal_relevance,
                    prerequisite_value=context.prerequisite_value,
                    expected_trainability=context.expected_trainability,
                    transfer_value=context.transfer_value,
                    fatigue_cost=context.fatigue_cost,
                    time_cost=context.time_cost,
                    interference_cost=context.interference_cost,
                    safe_to_train=context.safe_to_train,
                    introductory_exposure_needed=context.introductory_exposure_needed,
                    prerequisites_met=context.prerequisites_met,
                    prerequisite_adaptation_ids=context.prerequisite_adaptation_ids,
                    cultivate_comparative_advantage=context.cultivate_comparative_advantage,
                    source_observation_ids=tuple(
                        dict.fromkeys(
                            (
                                *context.source_observation_ids,
                                *estimate.source_observation_ids,
                                *block_review.source_observation_ids,
                            )
                        )
                    ),
                    evidence_claim_ids=tuple(
                        dict.fromkeys(
                            (*context.evidence_claim_ids, *block_review.evidence_claim_ids)
                        )
                    ),
                )
            )

        strategy = LongRangeStrategyPlanner().build(
            athlete_id=previous_strategy.athlete_id,
            adaptations=adaptation_by_id.values(),
            needs=needs,
            candidates=planning_candidates,
            policy=priority_policy,
            generated_at=generated_at,
            horizon_months=previous_strategy.horizon_months,
            review_after_days=review_after_days,
        )
        strategy = LongRangeStrategy.model_validate(
            {
                **strategy.model_dump(),
                "supersedes_strategy_id": previous_strategy.id,
                "triggering_block_review_id": block_review.id,
                "rule_version": f"{strategy.rule_version};replanner={self.rule_version}",
            }
        )
        return ClosedLoopReplanningResult(capability_needs=tuple(needs), strategy=strategy)

    @staticmethod
    def _validate_chain(
        *,
        previous_strategy: LongRangeStrategy,
        completed_block: BlockPlan,
        block_review: BlockReview,
        generated_at: datetime,
    ) -> None:
        CompetencyFloorDetector._require_aware(generated_at)
        if completed_block.athlete_id != previous_strategy.athlete_id:
            raise ClosedLoopReplanningError("completed block belongs to another athlete")
        if completed_block.long_range_strategy_id != previous_strategy.id:
            raise ClosedLoopReplanningError(
                "completed block was not governed by the prior strategy"
            )
        if (
            block_review.athlete_id != previous_strategy.athlete_id
            or block_review.block_plan_id != completed_block.id
            or block_review.block_hypothesis != completed_block.hypothesis
        ):
            raise ClosedLoopReplanningError(
                "block review does not match the completed strategy chain"
            )
        if block_review.reviewed_at.date() < completed_block.ends_on:
            raise ClosedLoopReplanningError("replanning cannot occur before the block is complete")
        if generated_at < block_review.reviewed_at:
            raise ClosedLoopReplanningError("replanned strategy cannot predate its block review")

    @staticmethod
    def _selected_estimates(
        estimates: Iterable[CapabilityEstimate],
        *,
        previous_strategy: LongRangeStrategy,
        responses: dict[UUID, TrainingResponse],
        generated_at: datetime,
    ) -> dict[UUID, CapabilityEstimate]:
        result: dict[UUID, CapabilityEstimate] = {}
        reviewed_followup_by_adaptation = {
            adaptation_id: response.followup_capability_estimate_id
            for adaptation_id, response in responses.items()
        }
        for estimate in estimates:
            if estimate.athlete_id != previous_strategy.athlete_id:
                raise ClosedLoopReplanningError("selected estimate belongs to another athlete")
            if estimate.estimated_at > generated_at:
                raise ClosedLoopReplanningError("selected estimate cannot come from the future")
            if estimate.id in result:
                raise ClosedLoopReplanningError("selected estimates contain duplicate ids")
            result[estimate.id] = estimate
        allowed_ids = set(previous_strategy.source_capability_estimate_ids) | set(
            reviewed_followup_by_adaptation.values()
        )
        if any(item_id not in allowed_ids for item_id in result):
            raise ClosedLoopReplanningError(
                "selected estimates must be prior-state or reviewed follow-up estimates"
            )
        return result

    @staticmethod
    def _unique_by_id(items: Iterable[_Record], label: str) -> dict[UUID, _Record]:
        result: dict[UUID, _Record] = {}
        for item in items:
            item_id = item.id
            if item_id in result:
                raise ClosedLoopReplanningError(f"{label} contain duplicate ids")
            result[item_id] = item
        return result

    @staticmethod
    def _unique_by_adaptation(
        items: Iterable[_AdaptationRecord], label: str
    ) -> dict[UUID, _AdaptationRecord]:
        result: dict[UUID, _AdaptationRecord] = {}
        for item in items:
            adaptation_id = item.adaptation_id
            if adaptation_id in result:
                raise ClosedLoopReplanningError(f"{label} contain duplicate adaptation ids")
            result[adaptation_id] = item
        return result
