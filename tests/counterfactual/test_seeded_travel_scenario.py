from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from agas_domain import (
    AdaptationPriority,
    AdaptationResourceDemand,
    AvailabilityWindow,
    AvailableEquipmentSnapshot,
    BlockPlan,
    CostLevel,
    EffortRpeTarget,
    EnvironmentSnapshot,
    ExerciseResolution,
    ExerciseResolverPolicy,
    LongRangeStrategy,
    ResolutionIssueCode,
    ResolutionStatus,
    ResourceAllocationPolicy,
    RoadmapItem,
    SessionPrescription,
    SessionSection,
    SessionTemplate,
    SessionTemplateItem,
    StimulusRequirement,
    TrainingPriorityState,
    WeeklyAvailability,
    WeeklyPlan,
    WeeklyPlanStatus,
    WeeklySchedulingPolicy,
)
from agas_planner import BlockPlanner, BlockPlanningError, ExerciseResolver, WeeklyScheduler
from agas_seed_data import ScenarioEnvironment, SeedCatalog, load_seed_catalog

NOW = datetime(2026, 8, 19, 14, 0, tzinfo=UTC)
BLOCK_START = date(2026, 8, 24)


def test_home_travel_return_preserves_strategy_and_marks_partial_strength_fidelity() -> None:
    catalog = load_seed_catalog()
    scenario = catalog.travel_scenario
    strength_id, aerobic_id = scenario.target_adaptation_ids
    observation_id = uuid4()
    evidence_id = catalog.evidence_claims[0].id
    priorities = tuple(
        AdaptationPriority(
            adaptation_id=adaptation_id,
            capability_need_id=uuid4(),
            state=TrainingPriorityState.DEVELOP,
            score=0.9 - index * 0.1,
            rank=index + 1,
            development_allocation=0.5,
            score_components={"final_score": 0.9 - index * 0.1},
            reason_codes=("competency_deficit",),
            rationale=("Synthetic counterfactual fixture; not a scientific priority rule",),
        )
        for index, adaptation_id in enumerate(scenario.target_adaptation_ids)
    )
    strategy = LongRangeStrategy(
        athlete_id=scenario.athlete.id,
        priority_policy_id=uuid4(),
        horizon_months=12,
        priorities=priorities,
        roadmap=tuple(
            RoadmapItem(
                adaptation_id=priority.adaptation_id,
                current_state=priority.state,
                sequence_group=1,
                rationale="Synthetic travel scenario roadmap",
                review_trigger="scheduled fixture review",
            )
            for priority in priorities
        ),
        block_hypothesis="Develop strength and aerobic base across a temporary travel constraint.",
        source_observation_ids=(observation_id,),
        source_capability_estimate_ids=(uuid4(),),
        competency_floor_ids=(uuid4(),),
        evidence_claim_ids=(evidence_id,),
        generated_at=NOW,
        next_review_at=NOW + timedelta(days=42),
        rule_version="seeded-travel-fixture@1.0.0",
    )
    strength_requirement = _requirement(
        strategy,
        priorities[0],
        movement_patterns=("knee_dominant",),
        loading_types=("external_load",),
        lateralities=("bilateral", "unilateral"),
        minimum_loadability="high",
        velocity=("controlled",),
        evidence_id=evidence_id,
    )
    aerobic_requirement = _requirement(
        strategy,
        priorities[1],
        movement_patterns=("cyclic", "locomotion"),
        loading_types=("cyclic",),
        lateralities=("alternating",),
        minimum_loadability="limited",
        velocity=("continuous",),
        evidence_id=evidence_id,
    )
    policy = ExerciseResolverPolicy(
        adaptation_role_weight=2,
        movement_pattern_weight=2,
        loading_type_weight=1,
        loadability_weight=3,
        velocity_weight=1,
        laterality_weight=1,
        secondary_adaptation_credit=0.5,
        partial_match_threshold=0.7,
        full_match_threshold=0.95,
        max_ranked_candidates=5,
        policy_version="seeded-travel-fixture@1.0.0",
    )
    home_environment_id = uuid4()
    travel_environment_id = uuid4()
    home_resolutions = _resolve_pair(
        catalog,
        scenario.home,
        home_environment_id,
        (strength_requirement, aerobic_requirement),
        policy,
        NOW,
    )
    travel_time = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
    travel_resolutions = _resolve_pair(
        catalog,
        scenario.travel,
        travel_environment_id,
        (strength_requirement, aerobic_requirement),
        policy,
        travel_time,
    )
    return_time = datetime(2026, 9, 6, 14, 0, tzinfo=UTC)
    return_resolutions = _resolve_pair(
        catalog,
        scenario.home,
        home_environment_id,
        (strength_requirement, aerobic_requirement),
        policy,
        return_time,
    )

    assert home_resolutions[0].status is ResolutionStatus.FULL
    assert travel_resolutions[0].status is ResolutionStatus.PARTIAL
    assert any(
        issue.code is ResolutionIssueCode.INSUFFICIENT_LOADABILITY
        for issue in travel_resolutions[0].unresolved_issues
    )
    assert home_resolutions[0].selected_exercise_id != travel_resolutions[0].selected_exercise_id
    assert return_resolutions[0].selected_exercise_id == home_resolutions[0].selected_exercise_id
    assert all(
        item.status is ResolutionStatus.FULL
        for item in (home_resolutions[1], travel_resolutions[1], return_resolutions[1])
    )

    demands = tuple(
        AdaptationResourceDemand(
            long_range_strategy_id=strategy.id,
            adaptation_priority_id=priority.id,
            adaptation_id=priority.adaptation_id,
            priority_state=priority.state,
            stimulus_requirement_id=resolution.stimulus_requirement_id,
            exercise_resolution_id=resolution.id,
            minimum_weekly_minutes=60,
            target_weekly_minutes=60,
            sessions_per_week=2,
            source_observation_ids=(observation_id,),
            evidence_claim_ids=(evidence_id,),
            rationale="Synthetic travel scheduling fixture; dose is not a product rule.",
            demand_version="seeded-travel-fixture@1.0.0",
        )
        for priority, resolution in zip(priorities, home_resolutions, strict=True)
    )
    block = BlockPlanner().build(
        strategy=strategy,
        demands=demands,
        resolutions=home_resolutions,
        policy=ResourceAllocationPolicy(
            develop_weight=1,
            maintain_weight=1,
            expose_weight=1,
            allow_partial_exercise_resolution=False,
            policy_version="seeded-travel-fixture@1.0.0",
        ),
        weekly_budget_minutes=120,
        starts_on=BLOCK_START,
        duration_weeks=4,
        constraints=("Synthetic counterfactual only",),
        generated_at=NOW,
    )
    scheduling_policy = WeeklySchedulingPolicy(
        minimum_high_fatigue_recovery_hours=24,
        maximum_sessions_per_day=1,
        maximum_high_fatigue_sessions_per_day=1,
        allow_partial_exercise_resolution=True,
        policy_version="seeded-travel-fixture@1.0.0",
    )
    plans = tuple(
        _schedule_week(
            block,
            strategy,
            resolutions,
            environment_id,
            BLOCK_START + timedelta(days=7 * week),
            generated_at,
            scheduling_policy,
            scenario.available_weekdays,
        )
        for week, resolutions, environment_id, generated_at in (
            (0, home_resolutions, home_environment_id, NOW),
            (1, travel_resolutions, travel_environment_id, travel_time),
            (2, return_resolutions, home_environment_id, return_time),
        )
    )

    assert all(plan.status is WeeklyPlanStatus.FEASIBLE for plan in plans)
    assert all(len(plan.sessions) == 4 for plan in plans)
    assert all(plan.block_plan_id == block.id for plan in plans)
    assert tuple(item.adaptation_id for item in strategy.priorities) == (strength_id, aerobic_id)

    with pytest.raises(BlockPlanningError, match="partial exercise re-resolution is disabled"):
        _schedule_week(
            block,
            strategy,
            travel_resolutions,
            travel_environment_id,
            BLOCK_START + timedelta(days=7),
            travel_time,
            scheduling_policy.model_copy(update={"allow_partial_exercise_resolution": False}),
            scenario.available_weekdays,
        )


def _requirement(
    strategy: LongRangeStrategy,
    priority: AdaptationPriority,
    *,
    movement_patterns: tuple[str, ...],
    loading_types: tuple[str, ...],
    lateralities: tuple[str, ...],
    minimum_loadability: str,
    velocity: tuple[str, ...],
    evidence_id: UUID,
) -> StimulusRequirement:
    return StimulusRequirement(
        athlete_id=strategy.athlete_id,
        long_range_strategy_id=strategy.id,
        adaptation_priority_id=priority.id,
        adaptation_id=priority.adaptation_id,
        priority_state=priority.state,
        movement_patterns=movement_patterns,
        allowed_loading_types=loading_types,
        allowed_lateralities=lateralities,
        minimum_loadability=minimum_loadability,
        required_velocity_characteristics=velocity,
        maximum_skill_complexity="moderate",
        maximum_impact_level="low",
        maximum_stability_demand="moderate",
        maximum_fatigue_cost="high",
        maximum_soreness_cost="high",
        minimum_floor_area_m2=3,
        source_observation_ids=strategy.source_observation_ids,
        evidence_claim_ids=(evidence_id,),
        rationale="Synthetic structural stimulus used only for travel counterfactual testing.",
        generated_at=NOW,
        rule_version="seeded-travel-fixture@1.0.0",
    )


def _resolve_pair(
    catalog: SeedCatalog,
    scenario_environment: ScenarioEnvironment,
    environment_id: UUID,
    requirements: tuple[StimulusRequirement, StimulusRequirement],
    policy: ExerciseResolverPolicy,
    resolved_at: datetime,
) -> tuple[ExerciseResolution, ExerciseResolution]:
    equipment_by_id = {item.id: item for item in catalog.equipment}
    snapshot = EnvironmentSnapshot(
        athlete_id=catalog.travel_scenario.athlete.id,
        environment_id=environment_id,
        captured_at=resolved_at,
        available_equipment=tuple(
            AvailableEquipmentSnapshot(
                equipment_id=equipment_id,
                category=equipment_by_id[equipment_id].category,
                capabilities=equipment_by_id[equipment_id].capabilities,
            )
            for equipment_id in scenario_environment.equipment_ids
        ),
        source_availability_ids=tuple(uuid4() for _ in scenario_environment.equipment_ids),
        floor_area_m2=scenario_environment.floor_area_m2,
        max_noise_level=scenario_environment.max_noise_level,
        outdoor_access=scenario_environment.outdoor_access,
    )
    resolver = ExerciseResolver()
    first, second = requirements
    return (
        resolver.resolve(
            requirement=first,
            environment=snapshot,
            exercises=catalog.exercises,
            policy=policy,
            resolved_at=resolved_at,
        ),
        resolver.resolve(
            requirement=second,
            environment=snapshot,
            exercises=catalog.exercises,
            policy=policy,
            resolved_at=resolved_at,
        ),
    )


def _schedule_week(
    block: BlockPlan,
    strategy: LongRangeStrategy,
    resolutions: tuple[ExerciseResolution, ExerciseResolution],
    environment_id: UUID,
    week_start: date,
    generated_at: datetime,
    policy: WeeklySchedulingPolicy,
    weekdays: tuple[int, ...],
) -> WeeklyPlan:
    resolution_by_stimulus = {item.stimulus_requirement_id: item for item in resolutions}
    prescriptions_list = []
    for allocation in block.allocations:
        stimulus_requirement_id = allocation.stimulus_requirement_id
        assert stimulus_requirement_id is not None
        resolution = resolution_by_stimulus[stimulus_requirement_id]
        assert resolution.selected_exercise_id is not None
        prescriptions_list.append(
            SessionPrescription(
                athlete_id=block.athlete_id,
                block_plan_id=block.id,
                resource_allocation_id=allocation.id,
                exercise_resolution_id=resolution.id,
                exercise_id=resolution.selected_exercise_id,
                adaptation_id=allocation.adaptation_id,
                reason_for_inclusion="Synthetic current-environment resolution",
                sets=1,
                duration_seconds=900,
                intensity_targets=(EffortRpeTarget(minimum=5, maximum=7),),
                rest_seconds=0,
                progression_rule_reference="fixture:no-automatic-progression@1.0.0",
                substitution_class="same_stimulus_current_environment",
                planned_duration_minutes=30,
                fatigue_cost=CostLevel.MODERATE,
                source_observation_ids=strategy.source_observation_ids,
                evidence_claim_ids=strategy.evidence_claim_ids,
                prescribed_at=generated_at,
                rule_version="seeded-travel-fixture@1.0.0",
            )
        )
    prescriptions = tuple(prescriptions_list)
    templates = tuple(
        SessionTemplate(
            athlete_id=block.athlete_id,
            block_plan_id=block.id,
            name=f"Synthetic session {index}",
            items=(
                SessionTemplateItem(
                    prescription_id=prescription.id, order_index=1, section=SessionSection.PRIMARY
                ),
            ),
            sessions_per_week=2,
            planned_duration_minutes=30,
            fatigue_cost=CostLevel.MODERATE,
            source_observation_ids=strategy.source_observation_ids,
            evidence_claim_ids=strategy.evidence_claim_ids,
            created_for_block_at=generated_at,
            rule_version="seeded-travel-fixture@1.0.0",
        )
        for index, prescription in enumerate(prescriptions, start=1)
    )
    availability = WeeklyAvailability(
        athlete_id=block.athlete_id,
        week_start=week_start,
        windows=tuple(
            AvailabilityWindow(
                environment_id=environment_id,
                starts_at=datetime.combine(
                    week_start + timedelta(days=day), datetime.min.time(), UTC
                )
                + timedelta(hours=18),
                ends_at=datetime.combine(week_start + timedelta(days=day), datetime.min.time(), UTC)
                + timedelta(hours=19),
            )
            for day in weekdays
        ),
        source_observation_ids=strategy.source_observation_ids,
        recorded_at=generated_at,
        rule_version="seeded-travel-fixture@1.0.0",
    )
    return WeeklyScheduler().schedule(
        block=block,
        availability=availability,
        prescriptions=prescriptions,
        session_templates=templates,
        resolutions=resolutions,
        policy=policy,
        generated_at=generated_at,
    )
