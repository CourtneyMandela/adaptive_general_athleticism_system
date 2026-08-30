from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from agas_domain import (
    Adaptation,
    AdaptationResourceDemand,
    AssessmentReviewDecision,
    BlockPlan,
    Environment,
    EvidenceClaim,
    Exercise,
    ExerciseResolution,
    Observation,
    ResourceAllocation,
    StimulusRequirement,
    WeeklyPlan,
    WeeklySchedulingPolicy,
    WeeklySchedulingPolicyReview,
)
from agas_domain.persistence.repository import DomainRepository
from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy.orm import Session


class FirstWeekPreparationNotFoundError(LookupError):
    pass


class FirstWeekPreparationProjectionError(RuntimeError):
    pass


class FirstWeekAllocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    allocation: ResourceAllocation
    resource_demand: AdaptationResourceDemand
    adaptation: Adaptation
    stimulus_requirement: StimulusRequirement | None = None
    exercise_resolution: ExerciseResolution | None = None
    selected_exercise: Exercise | None = None

    @model_validator(mode="after")
    def preserve_allocation_chain(self) -> FirstWeekAllocationInput:
        active = self.allocation.allocated_weekly_minutes > 0
        linked = (
            self.stimulus_requirement,
            self.exercise_resolution,
            self.selected_exercise,
        )
        if active and any(item is None for item in linked):
            raise ValueError("active first-week allocation requires its complete exercise chain")
        if not active and any(item is not None for item in linked):
            raise ValueError("zero-resource allocation cannot expose an active exercise chain")
        return self


class WeeklySchedulingPolicyOption(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy: WeeklySchedulingPolicy
    current_review: WeeklySchedulingPolicyReview | None = None

    @property
    def is_currently_approved(self) -> bool:
        return (
            self.current_review is not None
            and self.current_review.decision is AssessmentReviewDecision.APPROVED
        )


class FirstWeekPreparationProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    block: BlockPlan
    projected_at: datetime
    allocation_inputs: tuple[FirstWeekAllocationInput, ...]
    environments: tuple[Environment, ...]
    scheduling_policy_options: tuple[WeeklySchedulingPolicyOption, ...]
    existing_first_week_plans: tuple[WeeklyPlan, ...]
    source_observations: tuple[Observation, ...]
    evidence_claims: tuple[EvidenceClaim, ...]
    projection_version: str = "first-week-preparation@1.0.0"


class FirstWeekPreparationProjector:
    """Expose exact weekly-plan inputs without choosing a prescription or calendar."""

    def __init__(self, session: Session) -> None:
        self.repository = DomainRepository(session)

    def project(
        self, block_id: UUID, projected_at: datetime | None = None
    ) -> FirstWeekPreparationProjection:
        block = self.repository.get_block_plan(block_id)
        if block is None:
            raise FirstWeekPreparationNotFoundError("block plan does not exist")
        instant = projected_at or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("first-week preparation time must include a timezone")
        if instant < block.generated_at:
            raise ValueError("first-week preparation cannot predate its block")

        inputs = tuple(self._allocation_input(item) for item in block.allocations)
        policy_options = tuple(
            WeeklySchedulingPolicyOption(
                policy=policy,
                current_review=self.repository.get_current_weekly_scheduling_policy_review(
                    policy.id
                ),
            )
            for policy in self.repository.list_weekly_scheduling_policies()
        )
        demand_ids = tuple(item.resource_demand.id for item in inputs)
        demands = tuple(item.resource_demand for item in inputs)
        requirements = tuple(
            item.stimulus_requirement for item in inputs if item.stimulus_requirement is not None
        )
        observation_ids = self._ordered_union(
            block.source_observation_ids,
            *(item.source_observation_ids for item in demands),
            *(item.source_observation_ids for item in requirements),
        )
        review_claim_ids = tuple(
            claim_id
            for option in policy_options
            if option.current_review is not None
            for claim_id in option.current_review.evidence_claim_ids
        )
        evidence_ids = self._ordered_union(
            block.evidence_claim_ids,
            *(item.evidence_claim_ids for item in demands),
            *(item.evidence_claim_ids for item in requirements),
            review_claim_ids,
        )
        first_week_plans = tuple(
            plan
            for plan in self.repository.list_weekly_plans_for_block(block.id)
            if plan.block_week == 1
        )
        if len(set(demand_ids)) != len(demand_ids):
            raise FirstWeekPreparationProjectionError(
                "block allocations do not preserve unique resource-demand lineage"
            )
        return FirstWeekPreparationProjection(
            block=block,
            projected_at=instant,
            allocation_inputs=inputs,
            environments=self.repository.list_environments(block.athlete_id),
            scheduling_policy_options=policy_options,
            existing_first_week_plans=first_week_plans,
            source_observations=tuple(
                self._require_observation(block, item) for item in observation_ids
            ),
            evidence_claims=tuple(self._require_evidence_claim(item) for item in evidence_ids),
        )

    def _allocation_input(self, allocation: ResourceAllocation) -> FirstWeekAllocationInput:
        demand = self.repository.get_adaptation_resource_demand(allocation.resource_demand_id)
        if demand is None:
            raise FirstWeekPreparationProjectionError(
                f"resource demand {allocation.resource_demand_id} does not exist"
            )
        adaptation = self.repository.get_adaptation(allocation.adaptation_id)
        if adaptation is None:
            raise FirstWeekPreparationProjectionError(
                f"adaptation {allocation.adaptation_id} does not exist"
            )
        if allocation.allocated_weekly_minutes == 0:
            return FirstWeekAllocationInput(
                allocation=allocation,
                resource_demand=demand,
                adaptation=adaptation,
            )
        if allocation.stimulus_requirement_id is None or allocation.exercise_resolution_id is None:
            raise FirstWeekPreparationProjectionError(
                "active block allocation has incomplete stimulus or resolution lineage"
            )
        requirement = self.repository.get_stimulus_requirement(allocation.stimulus_requirement_id)
        resolution = self.repository.get_exercise_resolution(allocation.exercise_resolution_id)
        if requirement is None or resolution is None:
            raise FirstWeekPreparationProjectionError(
                "active block allocation references missing stimulus or resolution state"
            )
        exercise = (
            self.repository.get_exercise(resolution.selected_exercise_id)
            if resolution.selected_exercise_id is not None
            else None
        )
        if exercise is None:
            raise FirstWeekPreparationProjectionError(
                "active block allocation has no selected exercise available for prescription"
            )
        return FirstWeekAllocationInput(
            allocation=allocation,
            resource_demand=demand,
            adaptation=adaptation,
            stimulus_requirement=requirement,
            exercise_resolution=resolution,
            selected_exercise=exercise,
        )

    def _require_observation(self, block: BlockPlan, observation_id: UUID) -> Observation:
        observation = self.repository.get_observation(observation_id)
        if observation is None:
            raise FirstWeekPreparationProjectionError(
                f"first-week observation {observation_id} does not exist"
            )
        if observation.athlete_id != block.athlete_id:
            raise FirstWeekPreparationProjectionError(
                "first-week observation belongs to a different athlete"
            )
        return observation

    def _require_evidence_claim(self, claim_id: UUID) -> EvidenceClaim:
        claim = self.repository.get_evidence_claim(claim_id)
        if claim is None:
            raise FirstWeekPreparationProjectionError(
                f"first-week evidence claim {claim_id} does not exist"
            )
        return claim

    @staticmethod
    def _ordered_union(*groups: tuple[UUID, ...]) -> tuple[UUID, ...]:
        return tuple(dict.fromkeys(item for group in groups for item in group))
