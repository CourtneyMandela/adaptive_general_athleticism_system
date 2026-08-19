from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, timedelta
from uuid import UUID

from agas_domain import (
    AdaptationPriority,
    AdaptationResourceDemand,
    BlockIssue,
    BlockIssueCode,
    BlockPlan,
    BlockPlanStatus,
    CostLevel,
    ExerciseResolution,
    LongRangeStrategy,
    PlannedSession,
    ResolutionStatus,
    ResourceAllocation,
    ResourceAllocationPolicy,
    SchedulingIssue,
    SchedulingIssueCode,
    SessionPrescription,
    TrainingPriorityState,
    WeeklyAvailability,
    WeeklyPlan,
    WeeklyPlanStatus,
    WeeklySchedulingPolicy,
)


class BlockPlanningError(ValueError):
    """Raised when block or weekly planning inputs violate a domain invariant."""


class BlockPlanner:
    """Allocate explicit weekly demands without inventing scientific dose targets."""

    def __init__(self, rule_version: str = "block-planner@1.0.0") -> None:
        self.rule_version = rule_version

    def build(
        self,
        *,
        strategy: LongRangeStrategy,
        demands: Iterable[AdaptationResourceDemand],
        resolutions: Iterable[ExerciseResolution],
        policy: ResourceAllocationPolicy,
        weekly_budget_minutes: int,
        starts_on: date,
        duration_weeks: int,
        constraints: tuple[str, ...],
        generated_at: datetime,
    ) -> BlockPlan:
        self._require_aware(generated_at)
        if weekly_budget_minutes <= 0:
            raise BlockPlanningError("weekly budget must be positive")
        if duration_weeks not in range(4, 7):
            raise BlockPlanningError("block duration must be four to six weeks")
        if generated_at < strategy.generated_at:
            raise BlockPlanningError("block cannot predate its long-range strategy")
        if starts_on < generated_at.date():
            raise BlockPlanningError("block cannot start before it is generated")

        priority_by_id = {item.id: item for item in strategy.priorities}
        demand_list = tuple(demands)
        if len({item.id for item in demand_list}) != len(demand_list):
            raise BlockPlanningError("resource demands contain duplicate ids")
        if {item.adaptation_priority_id for item in demand_list} != set(priority_by_id):
            raise BlockPlanningError("resource demands must cover every strategy priority exactly")

        resolution_list = tuple(resolutions)
        resolution_by_id = {item.id: item for item in resolution_list}
        if len(resolution_by_id) != len(resolution_list):
            raise BlockPlanningError("exercise resolutions contain duplicate ids")

        ordered_demands = sorted(
            demand_list,
            key=lambda item: (
                priority_by_id[item.adaptation_priority_id].rank,
                str(item.adaptation_priority_id),
            ),
        )
        for demand in ordered_demands:
            priority = priority_by_id[demand.adaptation_priority_id]
            if demand.long_range_strategy_id != strategy.id:
                raise BlockPlanningError("resource demand belongs to a different strategy")
            if demand.adaptation_id != priority.adaptation_id:
                raise BlockPlanningError("resource demand adaptation differs from its priority")
            if demand.priority_state is not priority.state:
                raise BlockPlanningError("resource demand state differs from its priority")
            if demand.priority_state is TrainingPriorityState.DEFER:
                continue
            resolution_id = demand.exercise_resolution_id
            if resolution_id is None:
                raise BlockPlanningError("active resource demand has no resolution id")
            resolution = resolution_by_id.get(resolution_id)
            if resolution is None:
                raise BlockPlanningError("active resource demand has no supplied resolution")
            if resolution.stimulus_requirement_id != demand.stimulus_requirement_id:
                raise BlockPlanningError("resource demand stimulus differs from its resolution")

        minimum_total = sum(item.minimum_weekly_minutes for item in ordered_demands)
        hard_resolution_failure = any(
            self._resolution_is_hard_failure(item, resolution_by_id, policy)
            for item in ordered_demands
        )
        if minimum_total > weekly_budget_minutes:
            allocations = tuple(
                self._minimum_failure_allocation(item, weekly_budget_minutes, minimum_total)
                for item in ordered_demands
            )
        elif hard_resolution_failure:
            allocations = tuple(
                self._resolution_failure_allocation(item, resolution_by_id, policy)
                for item in ordered_demands
            )
        else:
            allocations = self._allocate(
                ordered_demands,
                priority_by_id,
                resolution_by_id,
                policy,
                weekly_budget_minutes,
            )

        statuses = {item.status for item in allocations}
        if BlockPlanStatus.INFEASIBLE in statuses:
            status = BlockPlanStatus.INFEASIBLE
        elif BlockPlanStatus.PARTIAL in statuses:
            status = BlockPlanStatus.PARTIAL
        else:
            status = BlockPlanStatus.FULL

        return BlockPlan(
            athlete_id=strategy.athlete_id,
            long_range_strategy_id=strategy.id,
            resource_allocation_policy_id=policy.id,
            starts_on=starts_on,
            ends_on=starts_on + timedelta(days=duration_weeks * 7 - 1),
            duration_weeks=duration_weeks,
            weekly_budget_minutes=weekly_budget_minutes,
            status=status,
            hypothesis=strategy.block_hypothesis,
            allocations=allocations,
            constraints=constraints,
            source_observation_ids=self._ordered_union(
                strategy.source_observation_ids,
                *(item.source_observation_ids for item in ordered_demands),
            ),
            evidence_claim_ids=self._ordered_union(
                strategy.evidence_claim_ids,
                *(item.evidence_claim_ids for item in ordered_demands),
            ),
            generated_at=generated_at,
            rule_version=f"{self.rule_version};policy={policy.policy_version}",
        )

    @staticmethod
    def _resolution_is_hard_failure(
        demand: AdaptationResourceDemand,
        resolutions: dict[UUID, ExerciseResolution],
        policy: ResourceAllocationPolicy,
    ) -> bool:
        if demand.priority_state is TrainingPriorityState.DEFER:
            return False
        resolution_id = demand.exercise_resolution_id
        if resolution_id is None:
            raise BlockPlanningError("active resource demand has no resolution id")
        resolution = resolutions[resolution_id]
        return resolution.status is ResolutionStatus.INFEASIBLE or (
            resolution.status is ResolutionStatus.PARTIAL
            and not policy.allow_partial_exercise_resolution
        )

    @staticmethod
    def _minimum_failure_allocation(
        demand: AdaptationResourceDemand,
        budget: int,
        minimum_total: int,
    ) -> ResourceAllocation:
        if demand.priority_state is TrainingPriorityState.DEFER:
            return BlockPlanner._full_deferred_allocation(demand)
        issue = BlockIssue(
            code=BlockIssueCode.MINIMUM_RESOURCE_UNMET,
            detail=(
                f"weekly budget {budget} minutes cannot satisfy "
                f"{minimum_total} required minimum minutes"
            ),
        )
        return BlockPlanner._allocation(demand, 0, BlockPlanStatus.INFEASIBLE, (issue,))

    @staticmethod
    def _resolution_failure_allocation(
        demand: AdaptationResourceDemand,
        resolutions: dict[UUID, ExerciseResolution],
        policy: ResourceAllocationPolicy,
    ) -> ResourceAllocation:
        if demand.priority_state is TrainingPriorityState.DEFER:
            return BlockPlanner._full_deferred_allocation(demand)
        resolution_id = demand.exercise_resolution_id
        if resolution_id is None:
            raise BlockPlanningError("active resource demand has no resolution id")
        resolution = resolutions[resolution_id]
        if resolution.status is ResolutionStatus.INFEASIBLE or (
            resolution.status is ResolutionStatus.PARTIAL
            and not policy.allow_partial_exercise_resolution
        ):
            issue = BlockIssue(
                code=BlockIssueCode.INFEASIBLE_EXERCISE_RESOLUTION,
                detail=(
                    "exercise resolution is infeasible"
                    if resolution.status is ResolutionStatus.INFEASIBLE
                    else "allocation policy does not permit a partial exercise resolution"
                ),
            )
            return BlockPlanner._allocation(demand, 0, BlockPlanStatus.INFEASIBLE, (issue,))
        issues = BlockPlanner._allocation_issues(
            demand,
            demand.minimum_weekly_minutes,
            resolution,
        )
        status = BlockPlanStatus.PARTIAL if issues else BlockPlanStatus.FULL
        return BlockPlanner._allocation(demand, demand.minimum_weekly_minutes, status, issues)

    @staticmethod
    def _allocate(
        demands: list[AdaptationResourceDemand],
        priorities: dict[UUID, AdaptationPriority],
        resolutions: dict[UUID, ExerciseResolution],
        policy: ResourceAllocationPolicy,
        budget: int,
    ) -> tuple[ResourceAllocation, ...]:
        allocated = {item.id: item.minimum_weekly_minutes for item in demands}
        remaining = budget - sum(allocated.values())

        while True:
            candidates = []
            for demand in demands:
                if demand.sessions_per_week == 0:
                    continue
                current = allocated[demand.id]
                gap = demand.target_weekly_minutes - current
                if gap < demand.sessions_per_week or remaining < demand.sessions_per_week:
                    continue
                priority = priorities[demand.adaptation_priority_id]
                weight = BlockPlanner._weight(demand, priority, policy)
                if weight <= 0:
                    continue
                total_gap = demand.target_weekly_minutes - demand.minimum_weekly_minutes
                relative_gap = gap / total_gap if total_gap else 0.0
                candidates.append((-(weight * relative_gap), priority.rank, str(demand.id), demand))
            if not candidates:
                break
            _, _, _, selected = min(candidates)
            allocated[selected.id] += selected.sessions_per_week
            remaining -= selected.sessions_per_week

        result = []
        for demand in demands:
            if demand.priority_state is TrainingPriorityState.DEFER:
                result.append(BlockPlanner._full_deferred_allocation(demand))
                continue
            resolution_id = demand.exercise_resolution_id
            if resolution_id is None:
                raise BlockPlanningError("active resource demand has no resolution id")
            resolution = resolutions[resolution_id]
            issues = BlockPlanner._allocation_issues(demand, allocated[demand.id], resolution)
            status = BlockPlanStatus.PARTIAL if issues else BlockPlanStatus.FULL
            result.append(BlockPlanner._allocation(demand, allocated[demand.id], status, issues))
        return tuple(result)

    @staticmethod
    def _weight(
        demand: AdaptationResourceDemand,
        priority: AdaptationPriority,
        policy: ResourceAllocationPolicy,
    ) -> float:
        if demand.priority_state is TrainingPriorityState.DEVELOP:
            return policy.develop_weight * priority.development_allocation
        if demand.priority_state is TrainingPriorityState.MAINTAIN:
            return policy.maintain_weight
        if demand.priority_state is TrainingPriorityState.EXPOSE:
            return policy.expose_weight
        return 0.0

    @staticmethod
    def _allocation_issues(
        demand: AdaptationResourceDemand,
        allocated: int,
        resolution: ExerciseResolution,
    ) -> tuple[BlockIssue, ...]:
        issues = []
        if allocated < demand.target_weekly_minutes:
            issues.append(
                BlockIssue(
                    code=BlockIssueCode.TARGET_RESOURCE_SHORTFALL,
                    detail=(
                        f"allocated {allocated} of {demand.target_weekly_minutes} target "
                        "weekly minutes"
                    ),
                )
            )
        if resolution.status is ResolutionStatus.PARTIAL:
            issues.append(
                BlockIssue(
                    code=BlockIssueCode.PARTIAL_EXERCISE_RESOLUTION,
                    detail="selected exercise retains the resolver's explicit fidelity limitations",
                )
            )
        return tuple(issues)

    @staticmethod
    def _allocation(
        demand: AdaptationResourceDemand,
        allocated: int,
        status: BlockPlanStatus,
        issues: tuple[BlockIssue, ...],
    ) -> ResourceAllocation:
        return ResourceAllocation(
            resource_demand_id=demand.id,
            adaptation_priority_id=demand.adaptation_priority_id,
            adaptation_id=demand.adaptation_id,
            priority_state=demand.priority_state,
            stimulus_requirement_id=demand.stimulus_requirement_id,
            exercise_resolution_id=demand.exercise_resolution_id,
            minimum_weekly_minutes=demand.minimum_weekly_minutes,
            target_weekly_minutes=demand.target_weekly_minutes,
            allocated_weekly_minutes=allocated,
            sessions_per_week=demand.sessions_per_week,
            status=status,
            issues=issues,
        )

    @staticmethod
    def _full_deferred_allocation(demand: AdaptationResourceDemand) -> ResourceAllocation:
        return BlockPlanner._allocation(demand, 0, BlockPlanStatus.FULL, ())

    @staticmethod
    def _ordered_union(*groups: Iterable[UUID]) -> tuple[UUID, ...]:
        result = []
        seen = set()
        for group in groups:
            for item in group:
                if item not in seen:
                    seen.add(item)
                    result.append(item)
        return tuple(result)

    @staticmethod
    def _require_aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise BlockPlanningError("planning timestamps must include a timezone")


class WeeklyScheduler:
    """Place explicit prescriptions into dated windows or explain why the week is infeasible."""

    def __init__(self, rule_version: str = "weekly-scheduler@1.0.0") -> None:
        self.rule_version = rule_version

    def schedule(
        self,
        *,
        block: BlockPlan,
        availability: WeeklyAvailability,
        prescriptions: Iterable[SessionPrescription],
        resolutions: Iterable[ExerciseResolution],
        policy: WeeklySchedulingPolicy,
        generated_at: datetime,
    ) -> WeeklyPlan:
        BlockPlanner._require_aware(generated_at)
        if block.status is BlockPlanStatus.INFEASIBLE:
            raise BlockPlanningError("an infeasible block cannot be scheduled")
        if availability.athlete_id != block.athlete_id:
            raise BlockPlanningError("weekly availability belongs to a different athlete")
        days_from_start = (availability.week_start - block.starts_on).days
        if days_from_start < 0 or days_from_start % 7 != 0:
            raise BlockPlanningError("availability week does not align with the block")
        block_week = days_from_start // 7 + 1
        if block_week > block.duration_weeks:
            raise BlockPlanningError("availability week falls outside the block")
        if generated_at < block.generated_at or generated_at < availability.recorded_at:
            raise BlockPlanningError("weekly plan cannot predate its block or availability")

        active_allocations = {
            item.id: item for item in block.allocations if item.allocated_weekly_minutes > 0
        }
        prescription_list = tuple(prescriptions)
        prescription_by_allocation = {
            item.resource_allocation_id: item for item in prescription_list
        }
        if len(prescription_by_allocation) != len(prescription_list):
            raise BlockPlanningError("each allocation may have only one prescription template")
        if set(prescription_by_allocation) != set(active_allocations):
            raise BlockPlanningError("prescriptions must cover every active allocation exactly")
        resolution_list = tuple(resolutions)
        resolution_by_id = {item.id: item for item in resolution_list}
        if len(resolution_by_id) != len(resolution_list):
            raise BlockPlanningError("exercise resolutions contain duplicate ids")

        occurrences = []
        for allocation_id, allocation in active_allocations.items():
            prescription = prescription_by_allocation[allocation_id]
            if (
                prescription.athlete_id != block.athlete_id
                or prescription.block_plan_id != block.id
            ):
                raise BlockPlanningError("prescription belongs to a different athlete or block")
            if prescription.adaptation_id != allocation.adaptation_id:
                raise BlockPlanningError("prescription adaptation differs from its allocation")
            if prescription.exercise_resolution_id != allocation.exercise_resolution_id:
                raise BlockPlanningError("prescription resolution differs from its allocation")
            resolution = resolution_by_id.get(prescription.exercise_resolution_id)
            if resolution is None or resolution.selected_exercise_id != prescription.exercise_id:
                raise BlockPlanningError("prescription must use the resolution's selected exercise")
            if (
                prescription.planned_duration_minutes * allocation.sessions_per_week
                != allocation.allocated_weekly_minutes
            ):
                raise BlockPlanningError(
                    "prescription duration and frequency must equal allocated weekly minutes"
                )
            if generated_at < prescription.prescribed_at:
                raise BlockPlanningError("weekly plan cannot predate its prescription")
            for occurrence_index in range(1, allocation.sessions_per_week + 1):
                occurrences.append((prescription, allocation, resolution, occurrence_index))

        fatigue_rank = {CostLevel.HIGH: 0, CostLevel.MODERATE: 1, CostLevel.LOW: 2}
        occurrences.sort(
            key=lambda item: (
                fatigue_rank[item[0].fatigue_cost],
                str(item[0].id),
                item[3],
            )
        )
        sessions: list[PlannedSession] = []
        issues = []
        used_windows: set[UUID] = set()
        sessions_by_day: dict[date, int] = {}
        high_fatigue_by_day: dict[date, int] = {}

        for prescription, allocation, resolution, occurrence_index in occurrences:
            matching_environment = [
                window
                for window in availability.windows
                if window.environment_id == resolution.environment_id
            ]
            long_enough = [
                window
                for window in matching_environment
                if window.ends_at - window.starts_at
                >= timedelta(minutes=prescription.planned_duration_minutes)
            ]
            selected = None
            rejected_codes = set()
            for window in sorted(long_enough, key=lambda item: (item.starts_at, str(item.id))):
                if window.id in used_windows:
                    continue
                day = window.starts_at.date()
                if sessions_by_day.get(day, 0) >= policy.maximum_sessions_per_day:
                    rejected_codes.add(SchedulingIssueCode.DAILY_SESSION_LIMIT)
                    continue
                if (
                    prescription.fatigue_cost is CostLevel.HIGH
                    and high_fatigue_by_day.get(day, 0)
                    >= policy.maximum_high_fatigue_sessions_per_day
                ):
                    rejected_codes.add(SchedulingIssueCode.HIGH_FATIGUE_DAILY_LIMIT)
                    continue
                candidate_end = window.starts_at + timedelta(
                    minutes=prescription.planned_duration_minutes
                )
                if prescription.fatigue_cost is CostLevel.HIGH and not self._has_recovery(
                    window.starts_at,
                    candidate_end,
                    sessions,
                    policy.minimum_high_fatigue_recovery_hours,
                ):
                    rejected_codes.add(SchedulingIssueCode.RECOVERY_CONSTRAINT)
                    continue
                selected = (window, candidate_end)
                break

            if selected is None:
                if not matching_environment:
                    code = SchedulingIssueCode.NO_MATCHING_ENVIRONMENT
                    detail = "no availability window uses the resolved exercise environment"
                elif not long_enough:
                    code = SchedulingIssueCode.WINDOW_TOO_SHORT
                    detail = "matching availability windows are shorter than the prescription"
                elif rejected_codes:
                    code = sorted(rejected_codes, key=lambda item: item.value)[0]
                    detail = "all matching windows violate the configured scheduling policy"
                else:
                    code = SchedulingIssueCode.NO_AVAILABLE_WINDOW
                    detail = "all matching availability windows are already occupied"
                issues.append(
                    SchedulingIssue(
                        code=code,
                        detail=detail,
                        prescription_id=prescription.id,
                        occurrence_index=occurrence_index,
                    )
                )
                continue

            window, ends_at = selected
            session = PlannedSession(
                prescription_id=prescription.id,
                resource_allocation_id=allocation.id,
                occurrence_index=occurrence_index,
                availability_window_id=window.id,
                environment_id=window.environment_id,
                starts_at=window.starts_at,
                ends_at=ends_at,
                planned_duration_minutes=prescription.planned_duration_minutes,
                fatigue_cost=prescription.fatigue_cost,
            )
            sessions.append(session)
            used_windows.add(window.id)
            day = window.starts_at.date()
            sessions_by_day[day] = sessions_by_day.get(day, 0) + 1
            if prescription.fatigue_cost is CostLevel.HIGH:
                high_fatigue_by_day[day] = high_fatigue_by_day.get(day, 0) + 1

        sessions.sort(key=lambda item: (item.starts_at, str(item.id)))
        status = WeeklyPlanStatus.INFEASIBLE if issues else WeeklyPlanStatus.FEASIBLE
        return WeeklyPlan(
            athlete_id=block.athlete_id,
            block_plan_id=block.id,
            weekly_availability_id=availability.id,
            scheduling_policy_id=policy.id,
            week_start=availability.week_start,
            block_week=block_week,
            status=status,
            sessions=tuple(sessions),
            issues=tuple(issues),
            generated_at=generated_at,
            rule_version=f"{self.rule_version};policy={policy.policy_version}",
        )

    @staticmethod
    def _has_recovery(
        starts_at: datetime,
        ends_at: datetime,
        sessions: Iterable[PlannedSession],
        minimum_hours: int,
    ) -> bool:
        required = timedelta(hours=minimum_hours)
        for session in sessions:
            if session.fatigue_cost is not CostLevel.HIGH:
                continue
            if ends_at <= session.starts_at:
                gap = session.starts_at - ends_at
            elif session.ends_at <= starts_at:
                gap = starts_at - session.ends_at
            else:
                return False
            if gap < required:
                return False
        return True
