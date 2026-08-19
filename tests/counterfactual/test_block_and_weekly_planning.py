from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from agas_domain import (
    AdaptationPriority,
    AdaptationResourceDemand,
    AvailabilityWindow,
    BlockIssueCode,
    BlockPlan,
    BlockPlanStatus,
    Confidence,
    CostLevel,
    ExerciseMatch,
    ExerciseResolution,
    LongRangeStrategy,
    PrescriptionModification,
    Provenance,
    ReadinessLevel,
    ResolutionIssue,
    ResolutionIssueCode,
    ResolutionStatus,
    ResourceAllocationPolicy,
    RoadmapItem,
    SafetyGateOutcome,
    SafetyGateTiming,
    SafetySignal,
    SafetySignalClass,
    SchedulingIssueCode,
    SessionExecutionInput,
    SessionExecutionStatus,
    SessionPrescription,
    SessionSafetyCheckInput,
    SessionSafetyPolicy,
    SetPerformance,
    TrainingPriorityState,
    WeeklyAvailability,
    WeeklyPlan,
    WeeklyPlanStatus,
    WeeklySchedulingPolicy,
)
from agas_planner import (
    BlockPlanner,
    ExecutionRecordingError,
    SessionAdherenceCalculator,
    SessionExecutionRecorder,
    WeeklyScheduler,
)
from agas_safety import SessionSafetyGate

NOW = datetime(2026, 8, 19, 14, 0, tzinfo=UTC)
BLOCK_START = date(2026, 8, 24)


def strategy_fixture() -> tuple[LongRangeStrategy, AdaptationPriority, AdaptationPriority]:
    observation_id = uuid4()
    evidence_id = uuid4()
    develop = AdaptationPriority(
        adaptation_id=uuid4(),
        capability_need_id=uuid4(),
        state=TrainingPriorityState.DEVELOP,
        score=0.9,
        rank=1,
        development_allocation=1,
        score_components={"final_score": 0.9},
        reason_codes=("competency_deficit",),
        rationale=("Synthetic software fixture deficit",),
    )
    maintain = AdaptationPriority(
        adaptation_id=uuid4(),
        capability_need_id=uuid4(),
        state=TrainingPriorityState.MAINTAIN,
        score=0.7,
        rank=2,
        score_components={"final_score": 0.7},
        reason_codes=("competency_met",),
        rationale=("Synthetic software fixture maintenance",),
    )
    strategy = LongRangeStrategy(
        athlete_id=uuid4(),
        priority_policy_id=uuid4(),
        horizon_months=12,
        priorities=(develop, maintain),
        roadmap=tuple(
            RoadmapItem(
                adaptation_id=priority.adaptation_id,
                current_state=priority.state,
                sequence_group=1,
                rationale="Synthetic roadmap fixture",
                review_trigger="scheduled fixture review",
            )
            for priority in (develop, maintain)
        ),
        block_hypothesis="Develop the synthetic deficit while maintaining the other capability.",
        source_observation_ids=(observation_id,),
        source_capability_estimate_ids=(uuid4(),),
        competency_floor_ids=(uuid4(),),
        evidence_claim_ids=(evidence_id,),
        generated_at=NOW,
        next_review_at=NOW + timedelta(days=42),
        rule_version="fixture@1.0.0",
    )
    return strategy, develop, maintain


def resolution_fixture(
    *,
    status: ResolutionStatus = ResolutionStatus.FULL,
    environment_id: UUID | None = None,
) -> ExerciseResolution:
    exercise_id = uuid4()
    issue = ResolutionIssue(
        code=ResolutionIssueCode.INSUFFICIENT_LOADABILITY,
        detail="Synthetic partial-fidelity fixture",
    )
    issues = (issue,) if status is ResolutionStatus.PARTIAL else ()
    match = ExerciseMatch(
        exercise_id=exercise_id,
        quality=status,
        score=0.8 if issues else 1,
        score_components={
            "adaptation_role": 1,
            "movement_pattern": 1,
            "loading_type": 1,
            "loadability": 0.67 if issues else 1,
            "velocity": 1,
        },
        issues=issues,
    )
    return ExerciseResolution(
        stimulus_requirement_id=uuid4(),
        environment_id=environment_id or uuid4(),
        resolver_policy_id=uuid4(),
        status=status,
        selected_exercise_id=exercise_id,
        ranked_matches=(match,),
        unresolved_issues=issues,
        rationale="Synthetic resolution fixture",
        resolved_at=NOW,
        rule_version="fixture@1.0.0",
    )


def demand_fixture(
    strategy: LongRangeStrategy,
    priority: AdaptationPriority,
    resolution: ExerciseResolution,
    *,
    minimum: int,
    target: int,
    sessions: int,
) -> AdaptationResourceDemand:
    return AdaptationResourceDemand(
        long_range_strategy_id=strategy.id,
        adaptation_priority_id=priority.id,
        adaptation_id=priority.adaptation_id,
        priority_state=priority.state,
        stimulus_requirement_id=resolution.stimulus_requirement_id,
        exercise_resolution_id=resolution.id,
        minimum_weekly_minutes=minimum,
        target_weekly_minutes=target,
        sessions_per_week=sessions,
        source_observation_ids=strategy.source_observation_ids,
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic resource-demand fixture",
        demand_version="fixture@1.0.0",
    )


def allocation_policy(*, allow_partial: bool = True) -> ResourceAllocationPolicy:
    return ResourceAllocationPolicy(
        develop_weight=2,
        maintain_weight=1,
        expose_weight=0.5,
        allow_partial_exercise_resolution=allow_partial,
        policy_version="fixture@1.0.0",
    )


def build_block(
    *, budget: int = 180
) -> tuple[
    BlockPlan,
    LongRangeStrategy,
    tuple[ExerciseResolution, ExerciseResolution],
]:
    strategy, develop, maintain = strategy_fixture()
    environment_id = uuid4()
    resolutions = (
        resolution_fixture(environment_id=environment_id),
        resolution_fixture(environment_id=environment_id),
    )
    demands = (
        demand_fixture(strategy, develop, resolutions[0], minimum=60, target=120, sessions=2),
        demand_fixture(strategy, maintain, resolutions[1], minimum=30, target=60, sessions=1),
    )
    block = BlockPlanner().build(
        strategy=strategy,
        demands=demands,
        resolutions=resolutions,
        policy=allocation_policy(),
        weekly_budget_minutes=budget,
        starts_on=BLOCK_START,
        duration_weeks=4,
        constraints=("Synthetic software fixture only",),
        generated_at=NOW,
    )
    return block, strategy, resolutions


def build_from_inputs(
    strategy: LongRangeStrategy,
    demands: tuple[AdaptationResourceDemand, ...],
    resolutions: tuple[ExerciseResolution, ...],
    policy: ResourceAllocationPolicy,
    budget: int,
) -> BlockPlan:
    return BlockPlanner().build(
        strategy=strategy,
        demands=demands,
        resolutions=resolutions,
        policy=policy,
        weekly_budget_minutes=budget,
        starts_on=BLOCK_START,
        duration_weeks=4,
        constraints=("Synthetic software fixture only",),
        generated_at=NOW,
    )


def prescriptions_for(
    block: BlockPlan,
    strategy: LongRangeStrategy,
    resolutions: tuple[ExerciseResolution, ExerciseResolution],
) -> tuple[SessionPrescription, ...]:
    resolution_by_id = {item.id: item for item in resolutions}
    result = []
    for allocation in block.allocations:
        if allocation.allocated_weekly_minutes == 0:
            continue
        resolution_id = allocation.exercise_resolution_id
        assert resolution_id is not None
        resolution = resolution_by_id[resolution_id]
        assert resolution.selected_exercise_id is not None
        result.append(
            SessionPrescription(
                athlete_id=block.athlete_id,
                block_plan_id=block.id,
                resource_allocation_id=allocation.id,
                exercise_resolution_id=resolution.id,
                exercise_id=resolution.selected_exercise_id,
                adaptation_id=allocation.adaptation_id,
                reason_for_inclusion="Synthetic prescription fixture",
                sets=3,
                repetitions_per_set=5,
                intensity_target="fixture effort target",
                rest_seconds=120,
                progression_rule_reference="fixture:no-automatic-progression@1.0.0",
                substitution_class="fixture_resolution_candidates",
                planned_duration_minutes=(
                    allocation.allocated_weekly_minutes // allocation.sessions_per_week
                ),
                fatigue_cost=(
                    CostLevel.HIGH
                    if allocation.priority_state is TrainingPriorityState.DEVELOP
                    else CostLevel.MODERATE
                ),
                source_observation_ids=strategy.source_observation_ids,
                evidence_claim_ids=strategy.evidence_claim_ids,
                prescribed_at=NOW,
                rule_version="fixture@1.0.0",
            )
        )
    return tuple(result)


def availability_fixture(
    athlete_id: UUID,
    environment_id: UUID,
    days: tuple[int, ...],
) -> WeeklyAvailability:
    return WeeklyAvailability(
        athlete_id=athlete_id,
        week_start=BLOCK_START,
        windows=tuple(
            AvailabilityWindow(
                environment_id=environment_id,
                starts_at=datetime(2026, 8, 24 + day, 18, 0, tzinfo=UTC),
                ends_at=datetime(2026, 8, 24 + day, 19, 0, tzinfo=UTC),
            )
            for day in days
        ),
        source_observation_ids=(uuid4(),),
        recorded_at=NOW,
        rule_version="fixture@1.0.0",
    )


def scheduling_policy() -> WeeklySchedulingPolicy:
    return WeeklySchedulingPolicy(
        minimum_high_fatigue_recovery_hours=24,
        maximum_sessions_per_day=1,
        maximum_high_fatigue_sessions_per_day=1,
        policy_version="fixture@1.0.0",
    )


def safety_policy() -> SessionSafetyPolicy:
    return SessionSafetyPolicy(
        allowed_modifications=(
            PrescriptionModification.REDUCE_VOLUME,
            PrescriptionModification.REDUCE_INTENSITY,
            PrescriptionModification.REMOVE_HIGH_IMPACT,
            PrescriptionModification.SHORTEN_SESSION,
        ),
        limited_readiness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        unusual_soreness_modifications=(PrescriptionModification.REMOVE_HIGH_IMPACT,),
        sleep_disruption_modifications=(PrescriptionModification.REDUCE_INTENSITY,),
        schedule_limitation_modifications=(PrescriptionModification.SHORTEN_SESSION,),
        evidence_claim_ids=(uuid4(),),
        rationale="Synthetic safety-policy fixture; not clinical guidance.",
        policy_version="fixture@1.0.0",
    )


def execution_fixture() -> tuple[
    BlockPlan,
    SessionPrescription,
    WeeklyPlan,
]:
    block, strategy, resolutions = build_block()
    prescriptions = prescriptions_for(block, strategy, resolutions)
    availability = availability_fixture(
        block.athlete_id,
        resolutions[0].environment_id,
        (0, 2, 4),
    )
    weekly_plan = WeeklyScheduler().schedule(
        block=block,
        availability=availability,
        prescriptions=prescriptions,
        resolutions=resolutions,
        policy=scheduling_policy(),
        generated_at=NOW,
    )
    planned_session = weekly_plan.sessions[0]
    prescription = next(
        item for item in prescriptions if item.id == planned_session.prescription_id
    )
    return block, prescription, weekly_plan


def test_less_time_reduces_targets_without_silently_breaching_minimums() -> None:
    strategy, develop, maintain = strategy_fixture()
    resolutions = (resolution_fixture(), resolution_fixture())
    demands = (
        demand_fixture(strategy, develop, resolutions[0], minimum=60, target=120, sessions=2),
        demand_fixture(strategy, maintain, resolutions[1], minimum=30, target=60, sessions=1),
    )
    policy = allocation_policy()
    full = build_from_inputs(strategy, demands, resolutions, policy, 180)
    constrained = build_from_inputs(strategy, demands, resolutions, policy, 150)
    infeasible = build_from_inputs(strategy, demands, resolutions, policy, 80)

    assert full.status is BlockPlanStatus.FULL
    assert sum(item.allocated_weekly_minutes for item in full.allocations) == 180
    assert constrained.status is BlockPlanStatus.PARTIAL
    assert sum(item.allocated_weekly_minutes for item in constrained.allocations) == 150
    assert all(
        item.allocated_weekly_minutes >= item.minimum_weekly_minutes
        for item in constrained.allocations
    )
    assert any(
        issue.code is BlockIssueCode.TARGET_RESOURCE_SHORTFALL
        for allocation in constrained.allocations
        for issue in allocation.issues
    )
    assert infeasible.status is BlockPlanStatus.INFEASIBLE
    assert all(item.allocated_weekly_minutes == 0 for item in infeasible.allocations)
    assert any(
        issue.code is BlockIssueCode.MINIMUM_RESOURCE_UNMET
        for allocation in infeasible.allocations
        for issue in allocation.issues
    )


def test_partial_exercise_policy_is_explicit() -> None:
    strategy, develop, maintain = strategy_fixture()
    partial = resolution_fixture(status=ResolutionStatus.PARTIAL)
    full = resolution_fixture()
    demands = (
        demand_fixture(strategy, develop, partial, minimum=60, target=60, sessions=2),
        demand_fixture(strategy, maintain, full, minimum=30, target=30, sessions=1),
    )
    resolutions = (partial, full)
    allowed = build_from_inputs(
        strategy,
        demands,
        resolutions,
        allocation_policy(allow_partial=True),
        90,
    )
    rejected = build_from_inputs(
        strategy,
        demands,
        resolutions,
        allocation_policy(allow_partial=False),
        90,
    )

    assert allowed.status is BlockPlanStatus.PARTIAL
    assert rejected.status is BlockPlanStatus.INFEASIBLE
    assert partial.stimulus_requirement_id == demands[0].stimulus_requirement_id


def test_availability_change_changes_schedule_not_block_or_prescriptions() -> None:
    block, strategy, resolutions = build_block()
    prescriptions = prescriptions_for(block, strategy, resolutions)
    environment_id = resolutions[0].environment_id
    spacious_week = availability_fixture(block.athlete_id, environment_id, (0, 2, 4))
    constrained_week = availability_fixture(block.athlete_id, environment_id, (0, 2))
    scheduler = WeeklyScheduler()

    feasible = scheduler.schedule(
        block=block,
        availability=spacious_week,
        prescriptions=prescriptions,
        resolutions=resolutions,
        policy=scheduling_policy(),
        generated_at=NOW,
    )
    infeasible = scheduler.schedule(
        block=block,
        availability=constrained_week,
        prescriptions=prescriptions,
        resolutions=resolutions,
        policy=scheduling_policy(),
        generated_at=NOW,
    )

    assert feasible.status is WeeklyPlanStatus.FEASIBLE
    assert len(feasible.sessions) == 3
    assert infeasible.status is WeeklyPlanStatus.INFEASIBLE
    assert len(infeasible.sessions) == 2
    assert any(issue.code is SchedulingIssueCode.NO_AVAILABLE_WINDOW for issue in infeasible.issues)
    assert feasible.block_plan_id == infeasible.block_plan_id == block.id
    assert {item.prescription_id for item in feasible.sessions} == {
        item.id for item in prescriptions
    }


def test_configured_high_fatigue_recovery_can_make_week_infeasible() -> None:
    block, strategy, resolutions = build_block()
    prescriptions = prescriptions_for(block, strategy, resolutions)
    environment_id = resolutions[0].environment_id
    availability = availability_fixture(block.athlete_id, environment_id, (0, 1, 2))
    strict_recovery = WeeklySchedulingPolicy(
        minimum_high_fatigue_recovery_hours=48,
        maximum_sessions_per_day=1,
        maximum_high_fatigue_sessions_per_day=1,
        policy_version="strict-recovery-fixture@1.0.0",
    )

    result = WeeklyScheduler().schedule(
        block=block,
        availability=availability,
        prescriptions=prescriptions,
        resolutions=resolutions,
        policy=strict_recovery,
        generated_at=NOW,
    )

    assert result.status is WeeklyPlanStatus.INFEASIBLE
    assert any(issue.code is SchedulingIssueCode.RECOVERY_CONSTRAINT for issue in result.issues)


def test_completed_session_creates_direct_performance_and_derived_adherence() -> None:
    _, prescription, weekly_plan = execution_fixture()
    planned_session = weekly_plan.sessions[0]
    report_time = planned_session.starts_at - timedelta(minutes=5)
    provenance = Provenance(
        recorded_by="synthetic-athlete",
        source_system="pytest",
        ingestion_method="fixture",
    )
    check = SessionSafetyCheckInput(
        athlete_id=weekly_plan.athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned_session.id,
        timing=SafetyGateTiming.PRE_SESSION,
        readiness=ReadinessLevel.READY,
        reported_at=report_time,
        reliability=Confidence.HIGH,
        provenance=provenance,
    )
    readiness_observation, decision = SessionSafetyGate().evaluate(
        check=check,
        weekly_plan=weekly_plan,
        planned_session=planned_session,
        policy=safety_policy(),
        decided_at=report_time,
    )
    assert decision.outcome is SafetyGateOutcome.PROCEED
    execution_input = SessionExecutionInput(
        athlete_id=weekly_plan.athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned_session.id,
        pre_session_safety_decision_id=decision.id,
        status=SessionExecutionStatus.COMPLETED,
        started_at=planned_session.starts_at,
        ended_at=planned_session.ends_at,
        performances=tuple(
            SetPerformance(
                set_index=index,
                performed=True,
                target_completed=True,
                actual_repetitions=5,
                load_value=20,
                load_unit="kg",
                effort_rpe=7,
                technique_constraint_met=True,
            )
            for index in range(1, 4)
        ),
        session_rpe=7,
        logged_at=planned_session.ends_at,
        reliability=Confidence.HIGH,
        provenance=provenance,
    )
    performance_observation, execution = SessionExecutionRecorder().record(
        execution_input=execution_input,
        weekly_plan=weekly_plan,
        planned_session=planned_session,
        prescription=prescription,
        pre_session_decision=decision,
    )
    adherence = SessionAdherenceCalculator().calculate(
        execution=execution,
        planned_session=planned_session,
        prescription=prescription,
        calculated_at=execution.logged_at,
    )

    assert readiness_observation.id in decision.source_observation_ids
    assert performance_observation.id == execution.performance_observation_id
    assert adherence.kind == "derived"
    assert adherence.source_observation_ids == (performance_observation.id,)
    assert adherence.set_completion_ratio == 1
    assert adherence.dose_completion_ratio == 1

    post_check = SessionSafetyCheckInput(
        athlete_id=weekly_plan.athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned_session.id,
        related_session_execution_id=execution.id,
        timing=SafetyGateTiming.POST_SESSION,
        signals=(
            SafetySignal(
                tag="fixture:governed_escalation",
                classification=SafetySignalClass.ESCALATE,
            ),
        ),
        reported_at=execution.logged_at,
        reliability=Confidence.HIGH,
        provenance=provenance,
    )
    _, post_decision = SessionSafetyGate().evaluate(
        check=post_check,
        weekly_plan=weekly_plan,
        planned_session=planned_session,
        policy=safety_policy(),
        decided_at=execution.logged_at,
        related_execution=execution,
    )
    assert post_decision.outcome is SafetyGateOutcome.STOP_AND_ESCALATE
    assert post_decision.related_session_execution_id == execution.id


def test_same_session_is_modified_or_blocked_by_preclassified_safety_input() -> None:
    _, prescription, weekly_plan = execution_fixture()
    planned_session = weekly_plan.sessions[0]
    report_time = planned_session.starts_at - timedelta(minutes=5)
    provenance = Provenance(
        recorded_by="synthetic-athlete",
        source_system="pytest",
        ingestion_method="fixture",
    )
    policy = safety_policy()
    modification_check = SessionSafetyCheckInput(
        athlete_id=weekly_plan.athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned_session.id,
        timing=SafetyGateTiming.PRE_SESSION,
        readiness=ReadinessLevel.LIMITED,
        unusual_soreness=True,
        reported_at=report_time,
        reliability=Confidence.MODERATE,
        provenance=provenance,
    )
    _, modification_decision = SessionSafetyGate().evaluate(
        check=modification_check,
        weekly_plan=weekly_plan,
        planned_session=planned_session,
        policy=policy,
        decided_at=report_time,
    )
    assert modification_decision.outcome is SafetyGateOutcome.MODIFY
    assert set(modification_decision.required_modifications) == {
        PrescriptionModification.REDUCE_VOLUME,
        PrescriptionModification.REMOVE_HIGH_IMPACT,
    }
    unmodified_execution = SessionExecutionInput(
        athlete_id=weekly_plan.athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned_session.id,
        pre_session_safety_decision_id=modification_decision.id,
        status=SessionExecutionStatus.PARTIAL,
        started_at=planned_session.starts_at,
        ended_at=planned_session.ends_at,
        performances=(
            SetPerformance(
                set_index=1,
                performed=True,
                target_completed=False,
                actual_repetitions=3,
                effort_rpe=7,
                technique_constraint_met=True,
            ),
        ),
        logged_at=planned_session.ends_at,
        reliability=Confidence.MODERATE,
        provenance=provenance,
    )
    with pytest.raises(ExecutionRecordingError, match="must exactly match"):
        SessionExecutionRecorder().record(
            execution_input=unmodified_execution,
            weekly_plan=weekly_plan,
            planned_session=planned_session,
            prescription=prescription,
            pre_session_decision=modification_decision,
        )

    escalation_check = modification_check.model_copy(
        update={
            "readiness": ReadinessLevel.READY,
            "unusual_soreness": False,
            "signals": (
                SafetySignal(
                    tag="fixture:governed_escalation",
                    classification=SafetySignalClass.ESCALATE,
                ),
            ),
        }
    )
    _, escalation_decision = SessionSafetyGate().evaluate(
        check=escalation_check,
        weekly_plan=weekly_plan,
        planned_session=planned_session,
        policy=policy,
        decided_at=report_time,
    )
    assert escalation_decision.outcome is SafetyGateOutcome.STOP_AND_ESCALATE
    with pytest.raises(ExecutionRecordingError, match="does not authorize"):
        SessionExecutionRecorder().record(
            execution_input=unmodified_execution.model_copy(
                update={
                    "pre_session_safety_decision_id": escalation_decision.id,
                    "status": SessionExecutionStatus.NOT_STARTED,
                    "started_at": None,
                    "ended_at": None,
                    "performances": (),
                }
            ),
            weekly_plan=weekly_plan,
            planned_session=planned_session,
            prescription=prescription,
            pre_session_decision=escalation_decision,
        )
