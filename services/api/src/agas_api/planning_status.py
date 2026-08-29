from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Literal
from uuid import UUID

from agas_domain import (
    AssessmentReviewDecision,
    BlockPlan,
    BlockPlanStatus,
    CapabilityEstimate,
    CompetencyFloor,
    ResolutionStatus,
    TrainingPriorityState,
    WeeklyPlan,
    WeeklyPlanStatus,
)
from agas_domain.persistence.repository import DomainRepository
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

PlanningStatus = Literal[
    "capability_estimate_required",
    "capability_estimate_stale",
    "planning_authorities_required",
    "planning_context_review_required",
    "resource_demand_preparation_required",
    "resource_allocation_policy_required",
    "exercise_resolution_review_required",
    "block_context_review_required",
    "block_infeasible",
    "block_selection_review_required",
    "weekly_scheduling_policy_required",
    "weekly_plan_context_review_required",
    "first_week_created",
    "first_week_infeasible",
    "first_week_selection_review_required",
]
PlanningRequirementCode = Literal[
    "approved_priority_policy_required",
    "approved_compatible_competency_floor_required",
    "reviewed_candidate_context_required",
    "resource_demand_coverage_required",
    "block_eligible_resolution_required",
    "resource_allocation_policy_required",
    "reviewed_block_context_required",
    "unambiguous_block_selection_required",
    "weekly_scheduling_policy_required",
    "explicit_prescription_context_required",
    "explicit_session_composition_required",
    "confirmed_weekly_availability_required",
    "unambiguous_first_week_selection_required",
]


class PlanningStatusNotFoundError(LookupError):
    pass


class InitialStrategySummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy_id: UUID
    generated_at: datetime
    next_review_at: datetime
    horizon_months: int
    rule_version: str
    priority_count: int


class PlanningRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: PlanningRequirementCode
    label: str
    satisfied: bool
    matching_record_count: int


class BlockPlanSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    block_plan_id: UUID
    starts_on: date
    ends_on: date
    duration_weeks: int
    weekly_budget_minutes: int
    status: BlockPlanStatus
    allocation_count: int
    rule_version: str


class FirstBlockReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy_priority_count: int
    priorities_with_resource_demand_count: int
    block_eligible_priority_count: int
    historical_resource_demand_count: int
    full_resolution_count: int
    partial_resolution_count: int
    infeasible_resolution_count: int
    resource_allocation_policy_count: int
    block_plan_count: int
    block_plan: BlockPlanSummary | None


class FirstWeekPlanSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    weekly_plan_id: UUID
    week_start: date
    week_end: date
    status: WeeklyPlanStatus
    prescription_count: int
    session_template_count: int
    availability_window_count: int
    scheduled_session_count: int
    scheduling_issue_count: int
    scheduling_policy_id: UUID
    scheduling_policy_review_id: UUID | None
    rule_version: str


class FirstWeekReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    active_resource_allocation_count: int
    weekly_scheduling_policy_count: int
    first_week_plan_count: int
    first_week_plan: FirstWeekPlanSummary | None


class PlanningStatusProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    athlete_id: UUID
    athlete_display_name: str
    as_of: datetime
    status: PlanningStatus
    message: str
    capability_estimate_count: int
    current_capability_estimate_count: int
    stale_capability_estimate_count: int
    approved_priority_policy_count: int
    approved_compatible_competency_floor_count: int
    covered_current_capability_estimate_count: int
    uncovered_current_capability_estimate_count: int
    requirements: tuple[PlanningRequirement, ...]
    initial_strategy: InitialStrategySummary | None
    first_block_readiness: FirstBlockReadiness | None
    first_week_readiness: FirstWeekReadiness | None
    projection_version: str = "athlete-planning-status-projection@1.3.0"


def get_planning_status_projection(
    session: Session, athlete_id: UUID, as_of: datetime | None = None
) -> PlanningStatusProjection:
    repository = DomainRepository(session)
    athlete = repository.get_athlete(athlete_id)
    if athlete is None:
        raise PlanningStatusNotFoundError("athlete does not exist")
    instant = as_of or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("planning status time must include a timezone")

    estimates = tuple(
        estimate
        for estimate in repository.list_capability_estimates(athlete_id)
        if estimate.estimated_at <= instant
    )
    current_estimates = tuple(
        estimate
        for estimate in estimates
        if estimate.valid_until is None or estimate.valid_until > instant
    )
    stale_estimates = tuple(
        estimate
        for estimate in estimates
        if estimate.valid_until is not None and estimate.valid_until <= instant
    )
    strategy = repository.get_initial_long_range_strategy(athlete_id)
    approved_policies = tuple(
        policy
        for policy in repository.list_priority_policies()
        if (
            (policy_review := repository.get_current_priority_policy_review(policy.id)) is not None
            and policy_review.decision is AssessmentReviewDecision.APPROVED
            and policy_review.reviewed_at <= instant
        )
    )
    approved_floors = tuple(
        floor
        for floor in repository.list_competency_floors()
        if (
            (floor_review := repository.get_current_competency_floor_review(floor.id)) is not None
            and floor_review.decision is AssessmentReviewDecision.APPROVED
            and floor_review.reviewed_at <= instant
            and any(_floor_matches_estimate(floor, estimate) for estimate in current_estimates)
        )
    )
    covered_estimate_ids = {
        estimate.id
        for estimate in current_estimates
        if any(_floor_matches_estimate(floor, estimate) for floor in approved_floors)
    }
    authorities_ready = bool(approved_policies and approved_floors)

    if strategy is not None:
        strategy_summary = InitialStrategySummary(
            strategy_id=strategy.id,
            generated_at=strategy.generated_at,
            next_review_at=strategy.next_review_at,
            horizon_months=strategy.horizon_months,
            rule_version=strategy.rule_version,
            priority_count=len(strategy.priorities),
        )
        status, message, requirements, block_readiness, week_readiness = _block_readiness(
            repository, strategy.id, instant
        )
    elif current_estimates:
        if authorities_ready:
            status = "planning_context_review_required"
            message = (
                "Approved planning authorities are available for the measured state. An operator "
                "must still review adaptation choice, athlete-specific relevance, costs, "
                "applicability, and uncertainty before creating the initial strategy."
            )
        else:
            status = "planning_authorities_required"
            message = (
                "Current capability estimates are available, but approved planning authorities "
                "are incomplete. No strategy can be created until a current approved priority "
                "policy and at least one compatible reviewed competency floor exist."
            )
        strategy_summary = None
        requirements = _planning_requirements(
            approved_priority_policy_count=len(approved_policies),
            approved_floor_count=len(approved_floors),
            context_reviewed=False,
        )
        block_readiness = None
        week_readiness = None
    elif stale_estimates:
        status = "capability_estimate_stale"
        message = (
            "Only stale capability estimates are available. Reassessment or reviewed "
            "interpretation is required before initial planning."
        )
        strategy_summary = None
        requirements = ()
        block_readiness = None
        week_readiness = None
    else:
        status = "capability_estimate_required"
        message = (
            "No capability estimate is available yet. Complete governed assessment and "
            "interpretation before initial planning."
        )
        strategy_summary = None
        requirements = ()
        block_readiness = None
        week_readiness = None

    return PlanningStatusProjection(
        athlete_id=athlete.id,
        athlete_display_name=athlete.display_name,
        as_of=instant,
        status=status,
        message=message,
        capability_estimate_count=len(estimates),
        current_capability_estimate_count=len(current_estimates),
        stale_capability_estimate_count=len(stale_estimates),
        approved_priority_policy_count=len(approved_policies),
        approved_compatible_competency_floor_count=len(approved_floors),
        covered_current_capability_estimate_count=len(covered_estimate_ids),
        uncovered_current_capability_estimate_count=(
            len(current_estimates) - len(covered_estimate_ids)
        ),
        requirements=requirements,
        initial_strategy=strategy_summary,
        first_block_readiness=block_readiness,
        first_week_readiness=week_readiness,
    )


def _floor_matches_estimate(floor: CompetencyFloor, estimate: CapabilityEstimate) -> bool:
    return (
        floor.domain is estimate.domain
        and floor.estimate_scope == estimate.estimate_scope
        and floor.unit_or_scale == estimate.unit_or_scale
    )


def _planning_requirements(
    *,
    approved_priority_policy_count: int,
    approved_floor_count: int,
    context_reviewed: bool,
) -> tuple[PlanningRequirement, ...]:
    return (
        PlanningRequirement(
            code="approved_priority_policy_required",
            label="Current approved priority policy",
            satisfied=approved_priority_policy_count > 0,
            matching_record_count=approved_priority_policy_count,
        ),
        PlanningRequirement(
            code="approved_compatible_competency_floor_required",
            label="Compatible approved competency floor",
            satisfied=approved_floor_count > 0,
            matching_record_count=approved_floor_count,
        ),
        PlanningRequirement(
            code="reviewed_candidate_context_required",
            label="Reviewed athlete-specific planning context",
            satisfied=context_reviewed,
            matching_record_count=1 if context_reviewed else 0,
        ),
    )


def _block_readiness(
    repository: DomainRepository, strategy_id: UUID, instant: datetime
) -> tuple[
    PlanningStatus,
    str,
    tuple[PlanningRequirement, ...],
    FirstBlockReadiness,
    FirstWeekReadiness | None,
]:
    strategy = repository.get_long_range_strategy(strategy_id)
    if strategy is None:
        raise ValueError("block readiness strategy does not exist")
    demands = repository.list_adaptation_resource_demands_for_strategy(strategy.id)
    policies = repository.list_resource_allocation_policies()
    blocks = repository.list_block_plans_for_strategy(strategy.id)
    demands_by_priority = {
        priority.id: tuple(
            demand for demand in demands if demand.adaptation_priority_id == priority.id
        )
        for priority in strategy.priorities
    }
    priorities_with_demands = sum(bool(items) for items in demands_by_priority.values())
    resolution_statuses = []
    eligible_priority_count = 0
    partial_allowed = any(policy.allow_partial_exercise_resolution for policy in policies)
    for priority in strategy.priorities:
        priority_eligible = False
        for demand in demands_by_priority[priority.id]:
            if priority.state is TrainingPriorityState.DEFER:
                priority_eligible = True
                continue
            if demand.exercise_resolution_id is None:
                continue
            resolution = repository.get_exercise_resolution(demand.exercise_resolution_id)
            if resolution is None:
                continue
            resolution_statuses.append(resolution.status)
            if resolution.status is ResolutionStatus.FULL or (
                resolution.status is ResolutionStatus.PARTIAL and partial_allowed
            ):
                priority_eligible = True
        eligible_priority_count += int(priority_eligible)

    priority_count = len(strategy.priorities)
    block_summary = _single_block_summary(blocks)
    readiness = FirstBlockReadiness(
        strategy_priority_count=priority_count,
        priorities_with_resource_demand_count=priorities_with_demands,
        block_eligible_priority_count=eligible_priority_count,
        historical_resource_demand_count=len(demands),
        full_resolution_count=resolution_statuses.count(ResolutionStatus.FULL),
        partial_resolution_count=resolution_statuses.count(ResolutionStatus.PARTIAL),
        infeasible_resolution_count=resolution_statuses.count(ResolutionStatus.INFEASIBLE),
        resource_allocation_policy_count=len(policies),
        block_plan_count=len(blocks),
        block_plan=block_summary,
    )

    if len(blocks) > 1:
        return (
            "block_selection_review_required",
            "Multiple blocks reference this strategy. No block is silently selected as current; "
            "an operator must resolve the intended block context.",
            (
                PlanningRequirement(
                    code="unambiguous_block_selection_required",
                    label="Unambiguous current block selection",
                    satisfied=False,
                    matching_record_count=len(blocks),
                ),
            ),
            readiness,
            None,
        )
    if block_summary is not None:
        block = blocks[0]
        week_readiness = _first_week_readiness(repository, block, instant)
        if block_summary.status is BlockPlanStatus.INFEASIBLE:
            return (
                "block_infeasible",
                "The persisted block is infeasible and cannot enter weekly scheduling. Its "
                "resource or exercise limitations require governed review.",
                (),
                readiness,
                week_readiness,
            )
        return _first_week_status(
            week_readiness,
            readiness,
        )

    requirements = _block_requirements(
        priority_count=priority_count,
        priorities_with_demands=priorities_with_demands,
        eligible_priority_count=eligible_priority_count,
        policy_count=len(policies),
    )
    if priorities_with_demands < priority_count:
        return (
            "resource_demand_preparation_required",
            "The strategy is persisted, but every priority still needs an explicit governed "
            "resource demand before block planning.",
            requirements,
            readiness,
            None,
        )
    if not policies:
        return (
            "resource_allocation_policy_required",
            "Every priority has demand history, but no resource-allocation policy is available "
            "to govern block tradeoffs and partial exercise resolution.",
            requirements,
            readiness,
            None,
        )
    if eligible_priority_count < priority_count:
        return (
            "exercise_resolution_review_required",
            "Demand history exists, but one or more priorities lack a block-eligible exercise "
            "resolution under the available allocation policies.",
            requirements,
            readiness,
            None,
        )
    return (
        "block_context_review_required",
        "Resource demands and allocation policy are available. An operator must still choose the "
        "exact demand history, weekly budget, dates, duration, and constraints for the block.",
        requirements,
        readiness,
        None,
    )


def _block_requirements(
    *,
    priority_count: int,
    priorities_with_demands: int,
    eligible_priority_count: int,
    policy_count: int,
) -> tuple[PlanningRequirement, ...]:
    return (
        PlanningRequirement(
            code="resource_demand_coverage_required",
            label="Resource demand history for every strategy priority",
            satisfied=priorities_with_demands == priority_count,
            matching_record_count=priorities_with_demands,
        ),
        PlanningRequirement(
            code="resource_allocation_policy_required",
            label="Versioned resource-allocation policy",
            satisfied=policy_count > 0,
            matching_record_count=policy_count,
        ),
        PlanningRequirement(
            code="block_eligible_resolution_required",
            label="Block-eligible exercise resolution for every priority",
            satisfied=eligible_priority_count == priority_count,
            matching_record_count=eligible_priority_count,
        ),
        PlanningRequirement(
            code="reviewed_block_context_required",
            label="Reviewed budget, dates, duration, constraints, and exact demand selection",
            satisfied=False,
            matching_record_count=0,
        ),
    )


def _single_block_summary(blocks: tuple[BlockPlan, ...]) -> BlockPlanSummary | None:
    if len(blocks) != 1:
        return None
    block = blocks[0]
    return BlockPlanSummary(
        block_plan_id=block.id,
        starts_on=block.starts_on,
        ends_on=block.ends_on,
        duration_weeks=block.duration_weeks,
        weekly_budget_minutes=block.weekly_budget_minutes,
        status=block.status,
        allocation_count=len(block.allocations),
        rule_version=block.rule_version,
    )


def _first_week_readiness(
    repository: DomainRepository, block: BlockPlan, instant: datetime
) -> FirstWeekReadiness:
    policies = tuple(
        policy
        for policy in repository.list_weekly_scheduling_policies()
        if (
            (review := repository.get_current_weekly_scheduling_policy_review(policy.id))
            is not None
            and review.decision is AssessmentReviewDecision.APPROVED
            and review.reviewed_at <= instant
        )
    )
    first_week_plans = tuple(
        plan for plan in repository.list_weekly_plans_for_block(block.id) if plan.block_week == 1
    )
    plan_summary = (
        _first_week_plan_summary(repository, first_week_plans[0])
        if len(first_week_plans) == 1
        else None
    )
    return FirstWeekReadiness(
        active_resource_allocation_count=sum(
            allocation.allocated_weekly_minutes > 0 for allocation in block.allocations
        ),
        weekly_scheduling_policy_count=len(policies),
        first_week_plan_count=len(first_week_plans),
        first_week_plan=plan_summary,
    )


def _first_week_status(
    week_readiness: FirstWeekReadiness,
    block_readiness: FirstBlockReadiness,
) -> tuple[
    PlanningStatus,
    str,
    tuple[PlanningRequirement, ...],
    FirstBlockReadiness,
    FirstWeekReadiness,
]:
    if week_readiness.first_week_plan_count > 1:
        return (
            "first_week_selection_review_required",
            "Multiple first-week plans reference this block. No plan is silently selected as "
            "current; an operator must resolve the intended first-week context.",
            (
                PlanningRequirement(
                    code="unambiguous_first_week_selection_required",
                    label="Unambiguous first-week plan selection",
                    satisfied=False,
                    matching_record_count=week_readiness.first_week_plan_count,
                ),
            ),
            block_readiness,
            week_readiness,
        )
    if week_readiness.first_week_plan is not None:
        if week_readiness.first_week_plan.status is WeeklyPlanStatus.INFEASIBLE:
            return (
                "first_week_infeasible",
                "The first weekly plan is persisted but infeasible. Its scheduled diagnostic "
                "output and structured issues remain visible for governed review.",
                (),
                block_readiness,
                week_readiness,
            )
        return (
            "first_week_created",
            "A feasible first week is persisted with explicit dose, session composition, dated "
            "availability, scheduling policy, and block lineage.",
            (),
            block_readiness,
            week_readiness,
        )

    requirements = _first_week_requirements(
        policy_count=week_readiness.weekly_scheduling_policy_count
    )
    if week_readiness.weekly_scheduling_policy_count == 0:
        return (
            "weekly_scheduling_policy_required",
            "The block is persisted, but no current approved weekly-scheduling policy is "
            "available to govern calendar feasibility and partial exercise resolution.",
            requirements,
            block_readiness,
            week_readiness,
        )
    return (
        "weekly_plan_context_review_required",
        "The block and a current approved scheduling policy are available. An operator must still "
        "provide exact "
        "prescriptions, session composition, dated availability, and policy selection for week "
        "one.",
        requirements,
        block_readiness,
        week_readiness,
    )


def _first_week_requirements(*, policy_count: int) -> tuple[PlanningRequirement, ...]:
    return (
        PlanningRequirement(
            code="weekly_scheduling_policy_required",
            label="Versioned weekly-scheduling policy",
            satisfied=policy_count > 0,
            matching_record_count=policy_count,
        ),
        PlanningRequirement(
            code="explicit_prescription_context_required",
            label="Explicit prescriptions for every active block allocation",
            satisfied=False,
            matching_record_count=0,
        ),
        PlanningRequirement(
            code="explicit_session_composition_required",
            label="Explicit session composition, order, duration, and frequency",
            satisfied=False,
            matching_record_count=0,
        ),
        PlanningRequirement(
            code="confirmed_weekly_availability_required",
            label="Dated availability with observation provenance",
            satisfied=False,
            matching_record_count=0,
        ),
    )


def _first_week_plan_summary(
    repository: DomainRepository, plan: WeeklyPlan
) -> FirstWeekPlanSummary:
    availability = repository.get_weekly_availability(plan.weekly_availability_id)
    if availability is None:
        raise ValueError("first-week plan availability does not exist")
    template_ids = {
        *(session.session_template_id for session in plan.sessions),
        *(issue.session_template_id for issue in plan.issues),
    }
    templates = tuple(
        template
        for template_id in sorted(template_ids, key=str)
        if (template := repository.get_session_template(template_id)) is not None
    )
    if len(templates) != len(template_ids):
        raise ValueError("first-week plan session-template lineage is incomplete")
    prescription_ids = {item.prescription_id for template in templates for item in template.items}
    if any(repository.get_session_prescription(item_id) is None for item_id in prescription_ids):
        raise ValueError("first-week plan prescription lineage is incomplete")
    return FirstWeekPlanSummary(
        weekly_plan_id=plan.id,
        week_start=plan.week_start,
        week_end=plan.week_start + timedelta(days=6),
        status=plan.status,
        prescription_count=len(prescription_ids),
        session_template_count=len(template_ids),
        availability_window_count=len(availability.windows),
        scheduled_session_count=len(plan.sessions),
        scheduling_issue_count=len(plan.issues),
        scheduling_policy_id=plan.scheduling_policy_id,
        scheduling_policy_review_id=plan.scheduling_policy_review_id,
        rule_version=plan.rule_version,
    )
