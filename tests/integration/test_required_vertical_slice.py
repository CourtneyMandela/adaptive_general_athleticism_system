from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

from agas_domain import (
    AdaptationPlanningCandidate,
    AdaptationPriority,
    AdaptationResourceDemand,
    AvailabilityWindow,
    AvailableEquipmentSnapshot,
    BlockPlan,
    BlockReviewOutcome,
    BlockReviewPolicy,
    CapabilityEstimate,
    ComparisonDirection,
    CompetencyFloor,
    Confidence,
    CostLevel,
    EffortRpeTarget,
    EnvironmentSnapshot,
    ExerciseResolution,
    ExerciseResolverPolicy,
    LongRangeStrategy,
    Observation,
    ObservationSource,
    PlannedSession,
    PrescriptionAdjustment,
    PrescriptionModification,
    PriorityPolicy,
    ProgressionDimension,
    ProgressionOutcome,
    ProgressionPolicy,
    Provenance,
    ReadinessLevel,
    ReplanningCandidateContext,
    ResolutionIssueCode,
    ResolutionStatus,
    ResourceAllocationPolicy,
    ResponseEvaluationTarget,
    SafetyGateOutcome,
    SafetyGateTiming,
    SessionAdherence,
    SessionExecution,
    SessionExecutionInput,
    SessionExecutionStatus,
    SessionItemExecutionInput,
    SessionPrescription,
    SessionSafetyCheckInput,
    SessionSafetyDecision,
    SessionSafetyPolicy,
    SessionSection,
    SessionTemplate,
    SessionTemplateItem,
    SetPerformance,
    StimulusRequirement,
    TrainingPriorityState,
    TrainingResponse,
    WeeklyAvailability,
    WeeklyPlan,
    WeeklyPlanStatus,
    WeeklySchedulingPolicy,
)
from agas_planner import (
    BlockPlanner,
    BlockReviewEngine,
    ClosedLoopReplanner,
    CompetencyFloorDetector,
    ExerciseResolver,
    LongRangeStrategyPlanner,
    PrescriptionProgressionApplicator,
    ProgressionEngine,
    SessionAdherenceCalculator,
    SessionExecutionRecorder,
    TrainingResponseCalculator,
    WeeklyScheduler,
)
from agas_safety import SessionSafetyGate
from agas_seed_data import ScenarioEnvironment, SeedCatalog, load_seed_catalog

NOW = datetime(2026, 8, 19, 14, 0, tzinfo=UTC)
BLOCK_START = date(2026, 8, 24)
FIXTURE_VERSION = "required-vertical-slice@1.0.0"
STRENGTH_ADAPTATION_ID = UUID("a0000000-0000-4000-8000-000000000001")
PROVENANCE = Provenance(
    recorded_by="automated-test",
    source_system="pytest",
    ingestion_method="synthetic-vertical-slice-fixture",
)


def test_required_travel_vertical_slice_closes_the_feedback_loop() -> None:
    """Prove the blueprint loop with explicit synthetic inputs, not generated workout logic."""
    catalog = load_seed_catalog()
    scenario = catalog.travel_scenario
    adaptations = tuple(
        adaptation
        for adaptation in catalog.adaptations
        if adaptation.id in scenario.target_adaptation_ids
    )
    strength_id, aerobic_id = scenario.target_adaptation_ids
    evidence_ids = tuple(item.id for item in catalog.evidence_claims[:2])

    intake = _observation(
        scenario.athlete.id,
        "synthetic_intake",
        {
            "activity_history": "previously_sedentary",
            "available_training_days": 4,
            "running_exposure": "limited",
            "jumping_exposure": "limited",
        },
        None,
        source=ObservationSource.USER_REPORT,
    )
    baseline_observations = (
        _observation(scenario.athlete.id, "synthetic_strength_assessment", 60, "fixture_points"),
        _observation(scenario.athlete.id, "synthetic_aerobic_assessment", 20, "fixture_points"),
    )
    baselines = tuple(
        CapabilityEstimate(
            athlete_id=scenario.athlete.id,
            domain=adaptation.domain,
            estimate=value,
            unit_or_scale="fixture_points",
            estimate_scope=f"assessment_specific:{observation.observation_type}",
            confidence=Confidence.MODERATE,
            calculation_method="synthetic test-fixture interpretation",
            source_observation_ids=(observation.id,),
            estimated_at=NOW + timedelta(minutes=5),
            valid_until=NOW + timedelta(days=35),
            rule_version=FIXTURE_VERSION,
        )
        for adaptation, observation, value in zip(
            adaptations, baseline_observations, (60, 20), strict=True
        )
    )
    floors = tuple(
        CompetencyFloor(
            domain=adaptation.domain,
            estimate_scope=estimate.estimate_scope,
            unit_or_scale=estimate.unit_or_scale,
            threshold=threshold,
            comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
            population="synthetic software-test athlete",
            applicability_notes="Structural fixture only; not an operational athlete threshold.",
            uncertainty="The threshold is invented solely to exercise deterministic branches.",
            evidence_claim_ids=(evidence_id,),
            floor_version=FIXTURE_VERSION,
        )
        for adaptation, estimate, threshold, evidence_id in zip(
            adaptations, baselines, (100, 50), evidence_ids, strict=True
        )
    )
    needs = tuple(
        CompetencyFloorDetector().identify(
            scenario.athlete.id, floor, estimate, NOW + timedelta(minutes=10)
        )
        for floor, estimate in zip(floors, baselines, strict=True)
    )
    policy = _priority_policy()
    candidates = tuple(
        AdaptationPlanningCandidate(
            adaptation_id=adaptation.id,
            capability_need_id=need.id,
            general_relevance=0.9,
            goal_relevance=0.9,
            prerequisite_value=0.7,
            expected_trainability=0.7,
            transfer_value=0.8,
            fatigue_cost=0.3,
            time_cost=0.3,
            interference_cost=0.2,
            source_observation_ids=(intake.id, *estimate.source_observation_ids),
            evidence_claim_ids=(evidence_id,),
        )
        for adaptation, need, estimate, evidence_id in zip(
            adaptations, needs, baselines, evidence_ids, strict=True
        )
    )
    strategy = LongRangeStrategyPlanner().build(
        athlete_id=scenario.athlete.id,
        adaptations=adaptations,
        needs=needs,
        candidates=candidates,
        policy=policy,
        generated_at=NOW + timedelta(minutes=15),
        horizon_months=12,
        review_after_days=42,
    )
    assert all(item.state is TrainingPriorityState.DEVELOP for item in strategy.priorities)
    assert intake.id in strategy.source_observation_ids

    requirements = tuple(
        _requirement(strategy, priority, evidence_id)
        for priority, evidence_id in zip(strategy.priorities, evidence_ids, strict=True)
    )
    resolver_policy = _resolver_policy()
    home_environment_id = uuid4()
    travel_environment_id = uuid4()
    home_resolutions = _resolve(
        catalog,
        scenario.home,
        home_environment_id,
        requirements,
        resolver_policy,
        NOW + timedelta(minutes=20),
    )
    travel_resolutions = _resolve(
        catalog,
        scenario.travel,
        travel_environment_id,
        requirements,
        resolver_policy,
        NOW + timedelta(days=14),
    )
    return_resolutions = _resolve(
        catalog,
        scenario.home,
        home_environment_id,
        requirements,
        resolver_policy,
        NOW + timedelta(days=21),
    )
    home_strength = _resolution_for_adaptation(home_resolutions, requirements, strength_id)
    travel_strength = _resolution_for_adaptation(travel_resolutions, requirements, strength_id)
    return_strength = _resolution_for_adaptation(return_resolutions, requirements, strength_id)
    travel_aerobic = _resolution_for_adaptation(travel_resolutions, requirements, aerobic_id)
    assert home_strength.status is ResolutionStatus.FULL
    assert travel_strength.status is ResolutionStatus.PARTIAL
    assert any(
        issue.code is ResolutionIssueCode.INSUFFICIENT_LOADABILITY
        for issue in travel_strength.unresolved_issues
    )
    assert travel_strength.selected_exercise_id != home_strength.selected_exercise_id
    assert return_strength.selected_exercise_id == home_strength.selected_exercise_id
    assert travel_aerobic.status is ResolutionStatus.FULL

    demands = _demands(strategy, home_resolutions, evidence_ids, (60, 60), (2, 2))
    allocation_policy = ResourceAllocationPolicy(
        develop_weight=1,
        maintain_weight=1,
        expose_weight=1,
        allow_partial_exercise_resolution=False,
        policy_version=FIXTURE_VERSION,
    )
    block = BlockPlanner().build(
        strategy=strategy,
        demands=demands,
        resolutions=home_resolutions,
        policy=allocation_policy,
        weekly_budget_minutes=120,
        starts_on=BLOCK_START,
        duration_weeks=4,
        constraints=("Synthetic four-day travel demonstration only",),
        generated_at=NOW + timedelta(minutes=25),
    )

    scheduling_policy = WeeklySchedulingPolicy(
        minimum_high_fatigue_recovery_hours=24,
        maximum_sessions_per_day=1,
        maximum_high_fatigue_sessions_per_day=1,
        allow_partial_exercise_resolution=True,
        policy_version=FIXTURE_VERSION,
    )
    week_inputs = (
        (home_resolutions, home_environment_id),
        (home_resolutions, home_environment_id),
        (travel_resolutions, travel_environment_id),
        (return_resolutions, home_environment_id),
    )
    weekly_bundles = tuple(
        _schedule_week(
            block=block,
            strategy=strategy,
            resolutions=resolutions,
            environment_id=environment_id,
            week_start=BLOCK_START + timedelta(days=7 * index),
            generated_at=NOW + timedelta(days=7 * index, minutes=30),
            scheduling_policy=scheduling_policy,
            weekdays=scenario.available_weekdays,
        )
        for index, (resolutions, environment_id) in enumerate(week_inputs)
    )
    assert all(bundle[0].status is WeeklyPlanStatus.FEASIBLE for bundle in weekly_bundles)
    assert all(len(bundle[0].sessions) == 4 for bundle in weekly_bundles)
    assert {item.environment_id for item in weekly_bundles[2][0].sessions} == {
        travel_environment_id
    }
    assert {item.environment_id for item in weekly_bundles[3][0].sessions} == {home_environment_id}

    safety_policy = _safety_policy(evidence_ids)
    executions: list[SessionExecution] = []
    adherences: list[SessionAdherence] = []
    post_safety: list[SessionSafetyDecision] = []
    for weekly_plan, prescriptions, templates in weekly_bundles:
        for planned_session in weekly_plan.sessions:
            template = next(
                item for item in templates if item.id == planned_session.session_template_id
            )
            prescription = next(
                item for item in prescriptions if item.id == template.items[0].prescription_id
            )
            execution, adherence, post_decision = _execute_session(
                weekly_plan, planned_session, template, prescription, safety_policy
            )
            executions.append(execution)
            adherences.append(adherence)
            post_safety.append(post_decision)
    assert len(executions) == 16
    assert all(item.outcome is SafetyGateOutcome.PROCEED for item in post_safety)

    first_strength = next(
        prescription
        for prescription in weekly_bundles[0][1]
        if prescription.adaptation_id == strength_id
    )
    strength_execution = next(
        execution
        for execution in executions
        if any(item.prescription_id == first_strength.id for item in execution.items)
    )
    strength_adherence = next(
        item
        for item in adherences
        if item.session_execution_id == strength_execution.id
        and item.prescription_id == first_strength.id
    )
    strength_post_safety = tuple(
        item for item in post_safety if item.related_session_execution_id == strength_execution.id
    )
    progression_policy = ProgressionPolicy(
        reference=first_strength.progression_rule_reference,
        minimum_set_completion_ratio=1,
        minimum_dose_completion_ratio=1,
        maximum_session_rpe=8,
        adjustment=PrescriptionAdjustment(
            dimension=ProgressionDimension.REPETITIONS,
            amount=1,
            unit="repetitions_per_set",
            description="Synthetic fixture: add one repetition per set.",
        ),
        evidence_claim_ids=(evidence_ids[0],),
        rationale="Synthetic progression policy used only to prove the versioned branch.",
        policy_version=FIXTURE_VERSION,
    )
    progression = ProgressionEngine().decide(
        prescription=first_strength,
        execution=strength_execution,
        adherence=strength_adherence,
        policy=progression_policy,
        post_session_decisions=strength_post_safety,
        decided_at=strength_post_safety[0].decided_at + timedelta(minutes=1),
    )
    revised_prescription = PrescriptionProgressionApplicator().apply(
        prescription=first_strength,
        decision=progression,
        policy=progression_policy,
        prescribed_at=progression.decided_at + timedelta(minutes=1),
    )
    assert progression.outcome is ProgressionOutcome.PROGRESS
    assert revised_prescription.supersedes_prescription_id == first_strength.id
    assert first_strength.repetitions_per_set is not None
    assert revised_prescription.repetitions_per_set == first_strength.repetitions_per_set + 1

    review_time = datetime.combine(
        block.ends_on + timedelta(days=1), datetime.min.time(), UTC
    ) + timedelta(hours=12)
    followup_observations = (
        _observation(
            scenario.athlete.id,
            "synthetic_strength_reassessment",
            105,
            "fixture_points",
            observed_at=review_time - timedelta(hours=2),
        ),
        _observation(
            scenario.athlete.id,
            "synthetic_aerobic_reassessment",
            35,
            "fixture_points",
            observed_at=review_time - timedelta(hours=2),
        ),
    )
    followups = tuple(
        CapabilityEstimate(
            athlete_id=scenario.athlete.id,
            domain=baseline.domain,
            estimate=value,
            unit_or_scale=baseline.unit_or_scale,
            estimate_scope=baseline.estimate_scope,
            confidence=Confidence.MODERATE,
            calculation_method="synthetic reassessment interpretation",
            source_observation_ids=(observation.id,),
            estimated_at=review_time - timedelta(hours=1),
            valid_until=review_time + timedelta(days=35),
            rule_version=FIXTURE_VERSION,
        )
        for baseline, observation, value in zip(
            baselines, followup_observations, (105, 35), strict=True
        )
    )
    all_prescriptions = tuple(item for _, items, _ in weekly_bundles for item in items)
    responses = tuple(
        _training_response(
            block,
            adaptation.id,
            baseline,
            followup,
            all_prescriptions,
            tuple(executions),
            tuple(adherences),
            review_time,
        )
        for adaptation, baseline, followup in zip(adaptations, baselines, followups, strict=True)
    )
    review_policy = BlockReviewPolicy(
        minimum_adherence_ratio=0.8,
        minimum_response_confidence=Confidence.LOW,
        evidence_claim_ids=evidence_ids,
        rationale="Synthetic interpretation thresholds; not an operational scientific rule.",
        policy_version=FIXTURE_VERSION,
    )
    review = BlockReviewEngine().review(
        block=block,
        responses=responses,
        targets=tuple(
            ResponseEvaluationTarget(
                training_response_id=response.id,
                comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
                minimum_meaningful_change=threshold,
            )
            for response, threshold in zip(responses, (10, 5), strict=True)
        ),
        safety_decisions=post_safety,
        policy=review_policy,
        reviewed_at=review_time,
    )
    assert review.outcome is BlockReviewOutcome.SUPPORTED

    replanning_contexts = tuple(
        ReplanningCandidateContext(
            adaptation_id=adaptation.id,
            competency_floor_id=floor.id,
            capability_estimate_id=followup.id,
            general_relevance=0.9,
            goal_relevance=0.9,
            prerequisite_value=0.7,
            expected_trainability=0.7,
            transfer_value=0.8,
            fatigue_cost=0.3,
            time_cost=0.3,
            interference_cost=0.2,
            source_observation_ids=followup.source_observation_ids,
            evidence_claim_ids=(evidence_id,),
        )
        for adaptation, floor, followup, evidence_id in zip(
            adaptations, floors, followups, evidence_ids, strict=True
        )
    )
    replanning = ClosedLoopReplanner().replan(
        previous_strategy=strategy,
        completed_block=block,
        block_review=review,
        training_responses=responses,
        selected_estimates=followups,
        adaptations=adaptations,
        competency_floors=floors,
        candidate_contexts=replanning_contexts,
        priority_policy=policy,
        generated_at=review_time + timedelta(minutes=1),
        review_after_days=42,
    )
    revised_strategy = replanning.strategy
    revised_state_by_adaptation = {
        item.adaptation_id: item.state for item in revised_strategy.priorities
    }
    assert revised_strategy.supersedes_strategy_id == strategy.id
    assert revised_strategy.triggering_block_review_id == review.id
    assert revised_state_by_adaptation[strength_id] is TrainingPriorityState.MAINTAIN
    assert revised_state_by_adaptation[aerobic_id] is TrainingPriorityState.DEVELOP

    revised_requirements = tuple(
        _requirement(revised_strategy, priority, evidence_id)
        for priority, evidence_id in zip(revised_strategy.priorities, evidence_ids, strict=True)
    )
    revised_resolutions = _resolve(
        catalog,
        scenario.home,
        home_environment_id,
        revised_requirements,
        resolver_policy,
        review_time + timedelta(minutes=2),
    )
    revised_minutes = tuple(
        30 if item.state is TrainingPriorityState.MAINTAIN else 60
        for item in revised_strategy.priorities
    )
    revised_sessions = tuple(
        1 if item.state is TrainingPriorityState.MAINTAIN else 2
        for item in revised_strategy.priorities
    )
    next_block = BlockPlanner().build(
        strategy=revised_strategy,
        demands=_demands(
            revised_strategy,
            revised_resolutions,
            evidence_ids,
            revised_minutes,
            revised_sessions,
        ),
        resolutions=revised_resolutions,
        policy=allocation_policy,
        weekly_budget_minutes=sum(revised_minutes),
        starts_on=block.ends_on + timedelta(days=1),
        duration_weeks=4,
        constraints=("Synthetic response-dependent successor block",),
        generated_at=review_time + timedelta(minutes=3),
    )
    next_state_by_adaptation = {
        item.adaptation_id: item.priority_state for item in next_block.allocations
    }
    assert next_block.long_range_strategy_id == revised_strategy.id
    assert next_state_by_adaptation[strength_id] is TrainingPriorityState.MAINTAIN
    assert next_state_by_adaptation[aerobic_id] is TrainingPriorityState.DEVELOP
    assert set(followup.id for followup in followups) <= set(
        revised_strategy.source_capability_estimate_ids
    )
    assert set(observation.id for observation in followup_observations) <= set(
        next_block.source_observation_ids
    )
    assert scenario.athlete.goals == ("Develop general strength", "Develop aerobic base")


def _observation(
    athlete_id: UUID,
    observation_type: str,
    measurement: object,
    unit: str | None,
    *,
    observed_at: datetime = NOW,
    source: ObservationSource = ObservationSource.TEST_RESULT,
) -> Observation:
    return Observation(
        athlete_id=athlete_id,
        observed_at=observed_at,
        observation_type=observation_type,
        measurement=measurement,
        unit=unit,
        source=source,
        reliability=Confidence.MODERATE,
        provenance=PROVENANCE,
    )


def _priority_policy() -> PriorityPolicy:
    return PriorityPolicy(
        deficit_weight=4,
        general_relevance_weight=1,
        goal_relevance_weight=1,
        prerequisite_value_weight=1,
        expected_trainability_weight=1,
        transfer_value_weight=1,
        fatigue_cost_weight=1,
        time_cost_weight=1,
        interference_cost_weight=1,
        cost_penalty=0.2,
        confidence_multipliers={
            Confidence.UNKNOWN: 0,
            Confidence.LOW: 0.5,
            Confidence.MODERATE: 0.75,
            Confidence.HIGH: 1,
        },
        develop_score_threshold=0.3,
        comparative_advantage_threshold=0.5,
        severe_deficit_threshold=0.25,
        max_develop_adaptations=2,
        policy_version=FIXTURE_VERSION,
    )


def _resolver_policy() -> ExerciseResolverPolicy:
    return ExerciseResolverPolicy(
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
        policy_version=FIXTURE_VERSION,
    )


def _requirement(
    strategy: LongRangeStrategy,
    priority: AdaptationPriority,
    evidence_id: UUID,
) -> StimulusRequirement:
    strength = priority.adaptation_id == STRENGTH_ADAPTATION_ID
    return StimulusRequirement(
        athlete_id=strategy.athlete_id,
        long_range_strategy_id=strategy.id,
        adaptation_priority_id=priority.id,
        adaptation_id=priority.adaptation_id,
        priority_state=priority.state,
        movement_patterns=("knee_dominant",) if strength else ("cyclic", "locomotion"),
        allowed_loading_types=("external_load",) if strength else ("cyclic",),
        allowed_lateralities=("bilateral", "unilateral") if strength else ("alternating",),
        minimum_loadability="high" if strength else "limited",
        required_velocity_characteristics=("controlled",) if strength else ("continuous",),
        maximum_skill_complexity="moderate",
        maximum_impact_level="low",
        maximum_stability_demand="moderate",
        maximum_fatigue_cost="high",
        maximum_soreness_cost="high",
        minimum_floor_area_m2=3,
        source_observation_ids=strategy.source_observation_ids,
        evidence_claim_ids=(evidence_id,),
        rationale="Synthetic structural stimulus; not an operational prescription.",
        generated_at=strategy.generated_at,
        rule_version=FIXTURE_VERSION,
    )


def _resolve(
    catalog: SeedCatalog,
    scenario_environment: ScenarioEnvironment,
    environment_id: UUID,
    requirements: tuple[StimulusRequirement, ...],
    policy: ExerciseResolverPolicy,
    resolved_at: datetime,
) -> tuple[ExerciseResolution, ...]:
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
    return tuple(
        resolver.resolve(
            requirement=requirement,
            environment=snapshot,
            exercises=catalog.exercises,
            policy=policy,
            resolved_at=resolved_at,
        )
        for requirement in requirements
    )


def _resolution_for_adaptation(
    resolutions: tuple[ExerciseResolution, ...],
    requirements: tuple[StimulusRequirement, ...],
    adaptation_id: UUID,
) -> ExerciseResolution:
    requirement = next(item for item in requirements if item.adaptation_id == adaptation_id)
    return next(item for item in resolutions if item.stimulus_requirement_id == requirement.id)


def _demands(
    strategy: LongRangeStrategy,
    resolutions: tuple[ExerciseResolution, ...],
    evidence_ids: tuple[UUID, ...],
    weekly_minutes: tuple[int, ...],
    sessions_per_week: tuple[int, ...],
) -> tuple[AdaptationResourceDemand, ...]:
    demands: list[AdaptationResourceDemand] = []
    for priority, evidence_id, minutes, sessions in zip(
        strategy.priorities,
        evidence_ids,
        weekly_minutes,
        sessions_per_week,
        strict=True,
    ):
        # Resolution order is pinned to the ordered strategy priorities in this fixture.
        resolution = resolutions[len(demands)]
        demands.append(
            AdaptationResourceDemand(
                long_range_strategy_id=strategy.id,
                adaptation_priority_id=priority.id,
                adaptation_id=priority.adaptation_id,
                priority_state=priority.state,
                stimulus_requirement_id=resolution.stimulus_requirement_id,
                exercise_resolution_id=resolution.id,
                minimum_weekly_minutes=minutes,
                target_weekly_minutes=minutes,
                sessions_per_week=sessions,
                source_observation_ids=strategy.source_observation_ids,
                evidence_claim_ids=(evidence_id,),
                rationale="Explicit synthetic fixture demand; not a product dose rule.",
                demand_version=FIXTURE_VERSION,
            )
        )
    return tuple(demands)


def _schedule_week(
    *,
    block: BlockPlan,
    strategy: LongRangeStrategy,
    resolutions: tuple[ExerciseResolution, ...],
    environment_id: UUID,
    week_start: date,
    generated_at: datetime,
    scheduling_policy: WeeklySchedulingPolicy,
    weekdays: tuple[int, ...],
) -> tuple[WeeklyPlan, tuple[SessionPrescription, ...], tuple[SessionTemplate, ...]]:
    resolution_by_stimulus = {item.stimulus_requirement_id: item for item in resolutions}
    prescriptions = []
    for allocation in block.allocations:
        assert allocation.stimulus_requirement_id is not None
        resolution = resolution_by_stimulus[allocation.stimulus_requirement_id]
        assert resolution.selected_exercise_id is not None
        strength = allocation.adaptation_id == STRENGTH_ADAPTATION_ID
        prescriptions.append(
            SessionPrescription(
                athlete_id=block.athlete_id,
                block_plan_id=block.id,
                resource_allocation_id=allocation.id,
                exercise_resolution_id=resolution.id,
                exercise_id=resolution.selected_exercise_id,
                adaptation_id=allocation.adaptation_id,
                reason_for_inclusion="Explicit synthetic current-environment prescription.",
                sets=3 if strength else 1,
                repetitions_per_set=5 if strength else None,
                duration_seconds=None if strength else 900,
                intensity_targets=(EffortRpeTarget(minimum=5, maximum=7),),
                rest_seconds=120 if strength else 0,
                progression_rule_reference=(
                    "fixture:strength-repetitions@1.0.0"
                    if strength
                    else "fixture:aerobic-review-only@1.0.0"
                ),
                substitution_class="same_stimulus_current_environment",
                planned_duration_minutes=30,
                fatigue_cost=CostLevel.MODERATE,
                source_observation_ids=strategy.source_observation_ids,
                evidence_claim_ids=strategy.evidence_claim_ids,
                prescribed_at=generated_at,
                rule_version=FIXTURE_VERSION,
            )
        )
    prescription_items = tuple(prescriptions)
    templates = tuple(
        SessionTemplate(
            athlete_id=block.athlete_id,
            block_plan_id=block.id,
            name=f"Synthetic {index} session",
            items=(
                SessionTemplateItem(
                    prescription_id=prescription.id,
                    order_index=1,
                    section=SessionSection.PRIMARY,
                ),
            ),
            sessions_per_week=2,
            planned_duration_minutes=30,
            fatigue_cost=CostLevel.MODERATE,
            source_observation_ids=strategy.source_observation_ids,
            evidence_claim_ids=strategy.evidence_claim_ids,
            created_for_block_at=generated_at,
            rule_version=FIXTURE_VERSION,
        )
        for index, prescription in enumerate(prescription_items, start=1)
    )
    availability = WeeklyAvailability(
        athlete_id=block.athlete_id,
        week_start=week_start,
        windows=tuple(
            AvailabilityWindow(
                environment_id=environment_id,
                starts_at=datetime.combine(
                    week_start + timedelta(days=weekday), datetime.min.time(), UTC
                )
                + timedelta(hours=18),
                ends_at=datetime.combine(
                    week_start + timedelta(days=weekday), datetime.min.time(), UTC
                )
                + timedelta(hours=19),
            )
            for weekday in weekdays
        ),
        source_observation_ids=strategy.source_observation_ids,
        recorded_at=generated_at,
        rule_version=FIXTURE_VERSION,
    )
    weekly_plan = WeeklyScheduler().schedule(
        block=block,
        availability=availability,
        prescriptions=prescription_items,
        session_templates=templates,
        resolutions=resolutions,
        policy=scheduling_policy,
        generated_at=generated_at,
    )
    return weekly_plan, prescription_items, templates


def _safety_policy(evidence_ids: tuple[UUID, ...]) -> SessionSafetyPolicy:
    modifications = (PrescriptionModification.REDUCE_VOLUME,)
    return SessionSafetyPolicy(
        allowed_modifications=modifications,
        limited_readiness_modifications=modifications,
        unusual_soreness_modifications=modifications,
        sleep_disruption_modifications=modifications,
        schedule_limitation_modifications=modifications,
        evidence_claim_ids=evidence_ids,
        rationale="Synthetic policy used only to exercise the deterministic safety gate.",
        policy_version=FIXTURE_VERSION,
    )


def _execute_session(
    weekly_plan: WeeklyPlan,
    planned_session: PlannedSession,
    template: SessionTemplate,
    prescription: SessionPrescription,
    safety_policy: SessionSafetyPolicy,
) -> tuple[SessionExecution, SessionAdherence, SessionSafetyDecision]:
    pre_check = SessionSafetyCheckInput(
        athlete_id=weekly_plan.athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned_session.id,
        timing=SafetyGateTiming.PRE_SESSION,
        readiness=ReadinessLevel.READY,
        reported_at=planned_session.starts_at - timedelta(minutes=2),
        reliability=Confidence.HIGH,
        provenance=PROVENANCE,
    )
    _, pre_decision = SessionSafetyGate().evaluate(
        check=pre_check,
        weekly_plan=weekly_plan,
        planned_session=planned_session,
        policy=safety_policy,
        decided_at=planned_session.starts_at - timedelta(minutes=1),
    )
    performances = tuple(
        SetPerformance(
            set_index=index,
            performed=True,
            target_completed=True,
            actual_repetitions=prescription.repetitions_per_set,
            actual_duration_seconds=prescription.duration_seconds,
            effort_rpe=7,
            technique_constraint_met=True,
        )
        for index in range(1, prescription.sets + 1)
    )
    execution_input = SessionExecutionInput(
        athlete_id=weekly_plan.athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned_session.id,
        pre_session_safety_decision_id=pre_decision.id,
        status=SessionExecutionStatus.COMPLETED,
        started_at=planned_session.starts_at,
        ended_at=planned_session.ends_at,
        items=(
            SessionItemExecutionInput(
                prescription_id=prescription.id,
                status=SessionExecutionStatus.COMPLETED,
                performances=performances,
                item_rpe=7,
            ),
        ),
        session_rpe=7,
        logged_at=planned_session.ends_at + timedelta(minutes=1),
        reliability=Confidence.HIGH,
        provenance=PROVENANCE,
    )
    _, execution = SessionExecutionRecorder().record(
        execution_input=execution_input,
        weekly_plan=weekly_plan,
        planned_session=planned_session,
        session_template=template,
        prescriptions=(prescription,),
        pre_session_decision=pre_decision,
    )
    adherence = SessionAdherenceCalculator().calculate(
        execution=execution,
        planned_session=planned_session,
        prescription=prescription,
        calculated_at=execution.logged_at + timedelta(seconds=1),
    )
    post_check = SessionSafetyCheckInput(
        athlete_id=weekly_plan.athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned_session.id,
        related_session_execution_id=execution.id,
        timing=SafetyGateTiming.POST_SESSION,
        reported_at=execution.logged_at + timedelta(minutes=1),
        reliability=Confidence.HIGH,
        provenance=PROVENANCE,
    )
    _, post_decision = SessionSafetyGate().evaluate(
        check=post_check,
        weekly_plan=weekly_plan,
        planned_session=planned_session,
        policy=safety_policy,
        decided_at=execution.logged_at + timedelta(minutes=2),
        related_execution=execution,
    )
    return execution, adherence, post_decision


def _training_response(
    block: BlockPlan,
    adaptation_id: UUID,
    baseline: CapabilityEstimate,
    followup: CapabilityEstimate,
    prescriptions: tuple[SessionPrescription, ...],
    executions: tuple[SessionExecution, ...],
    adherences: tuple[SessionAdherence, ...],
    calculated_at: datetime,
) -> TrainingResponse:
    selected_prescriptions = tuple(
        item for item in prescriptions if item.adaptation_id == adaptation_id
    )
    selected_ids = {item.id for item in selected_prescriptions}
    selected_executions = tuple(
        item
        for item in executions
        if any(execution_item.prescription_id in selected_ids for execution_item in item.items)
    )
    selected_execution_ids = {item.id for item in selected_executions}
    selected_adherences = tuple(
        item
        for item in adherences
        if item.session_execution_id in selected_execution_ids
        and item.prescription_id in selected_ids
    )
    return TrainingResponseCalculator().calculate(
        block=block,
        adaptation_id=adaptation_id,
        prescriptions=selected_prescriptions,
        executions=selected_executions,
        adherences=selected_adherences,
        baseline=baseline,
        followup=followup,
        intervention_summary="Synthetic four-week delivered-dose fixture.",
        measurement_uncertainty="Synthetic values exercise lineage, not scientific inference.",
        contextual_factors=("one hotel-equipment week", "software test fixture"),
        calculated_at=calculated_at,
    )
