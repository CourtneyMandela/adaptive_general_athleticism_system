from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from agas_domain import (
    Adaptation,
    AdaptationPlanningCandidate,
    AdaptationResourceDemand,
    Applicability,
    Athlete,
    AvailabilityWindow,
    BlockPlan,
    BlockPlanStatus,
    BlockReviewOutcome,
    BlockReviewPolicy,
    CapabilityDomain,
    CapabilityEstimate,
    ComparisonDirection,
    CompetencyFloor,
    Confidence,
    CostLevel,
    EffortRpeTarget,
    Environment,
    Equipment,
    EquipmentAvailability,
    EvidenceClaim,
    EvidenceSourceIdentifier,
    EvidenceStrength,
    Exercise,
    ExerciseResolution,
    ExerciseResolverPolicy,
    ExposureDefinition,
    ExposureProgressionPolicy,
    ExposureTarget,
    ExposureType,
    ImpactLevel,
    Loadability,
    LongRangeStrategy,
    Observation,
    ObservationSource,
    PrescriptionAdjustment,
    PrescriptionModification,
    PriorityPolicy,
    ProgressionDimension,
    ProgressionPolicy,
    Provenance,
    ReadinessLevel,
    ResolutionIssueCode,
    ResolutionStatus,
    ResourceAllocationPolicy,
    ResponseEvaluationTarget,
    SafetyGateOutcome,
    SafetyGateTiming,
    SafetySignal,
    SafetySignalClass,
    SessionExecutionInput,
    SessionExecutionStatus,
    SessionItemExecutionInput,
    SessionPrescription,
    SessionSafetyCheckInput,
    SessionSafetyPolicy,
    SessionSection,
    SessionTemplate,
    SessionTemplateItem,
    SetPerformance,
    StimulusRequirement,
    StimulusSpecification,
    WeeklyAvailability,
    WeeklyPlan,
    WeeklyPlanStatus,
    WeeklySchedulingPolicy,
)
from agas_domain.persistence.models import (
    BlockReviewRecord,
    ExerciseResolutionRecord,
    ImmutableHistoricalRecordError,
    LongRangeStrategyRecord,
    SessionAdherenceRecord,
    SessionExecutionRecord,
    TrainingResponseRecord,
    WeeklyPlanRecord,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import (
    BlockPlanner,
    BlockReviewEngine,
    CompetencyFloorDetector,
    EnvironmentSnapshotBuilder,
    ExerciseResolver,
    ExposureEntryCalculator,
    ExposureProgressionValidator,
    LongRangeStrategyPlanner,
    PrescriptionProgressionApplicator,
    ProgressionEngine,
    SessionAdherenceCalculator,
    SessionExecutionRecorder,
    StimulusRequirementBuilder,
    TrainingResponseCalculator,
    WeeklyScheduler,
)
from agas_safety import SessionSafetyGate
from sqlalchemy.orm import Session

NOW = datetime(2026, 8, 19, 14, 0, tzinfo=UTC)


def evidence_claim() -> EvidenceClaim:
    return EvidenceClaim(
        claim="Software fixture: a configured threshold remains linked to its provenance.",
        domain="software_test",
        population="synthetic persistence fixture",
        intervention="not applicable",
        outcome="referential integrity",
        study_design="software test fixture",
        uncertainty="This is not a scientific training claim.",
        limitations=("Not operational evidence",),
        evidence_strength=EvidenceStrength.INSUFFICIENT,
        athlete_applicability=Applicability.UNKNOWN,
        applicability_notes="Used only to verify software provenance.",
        source_identifiers=(
            EvidenceSourceIdentifier(scheme="other", value="fixture:planning-persistence"),
        ),
        reviewer="automated-test",
        claim_version="fixture@1.0.0",
    )


def priority_policy() -> PriorityPolicy:
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
            Confidence.UNKNOWN: 0.0,
            Confidence.LOW: 0.5,
            Confidence.MODERATE: 0.75,
            Confidence.HIGH: 1.0,
        },
        develop_score_threshold=0.3,
        comparative_advantage_threshold=0.5,
        severe_deficit_threshold=0.25,
        max_develop_adaptations=2,
        policy_version="persistence-fixture@1.0.0",
    )


def build_and_persist_strategy(
    session: Session,
) -> tuple[DomainRepository, LongRangeStrategy]:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Planning persistence athlete")
    claim = evidence_claim()
    repository.add_athlete(athlete)
    repository.add_evidence_claim(claim)
    observation = Observation(
        athlete_id=athlete.id,
        observed_at=NOW,
        observation_type="fixture_strength_test",
        measurement=60,
        unit="fixture_unit",
        source=ObservationSource.TEST_RESULT,
        reliability=Confidence.MODERATE,
        provenance=Provenance(
            recorded_by="automated-test",
            source_system="pytest",
            ingestion_method="fixture",
        ),
    )
    repository.add_observation(observation)
    session.flush()
    estimate = CapabilityEstimate(
        athlete_id=athlete.id,
        domain=CapabilityDomain.MAXIMUM_STRENGTH,
        estimate=60,
        unit_or_scale="fixture_unit",
        estimate_scope="assessment_specific:fixture_strength_test",
        confidence=Confidence.MODERATE,
        calculation_method="fixture",
        source_observation_ids=(observation.id,),
        estimated_at=NOW,
        valid_until=NOW + timedelta(days=30),
        rule_version="fixture@1.0.0",
    )
    repository.add_capability_estimate(estimate)
    adaptation = Adaptation(
        name="Maximum strength",
        domain=CapabilityDomain.MAXIMUM_STRENGTH,
    )
    repository.add_adaptation(adaptation)
    floor = CompetencyFloor(
        domain=CapabilityDomain.MAXIMUM_STRENGTH,
        estimate_scope=estimate.estimate_scope,
        unit_or_scale="fixture_unit",
        threshold=100,
        comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
        population="synthetic test population",
        applicability_notes="Software fixture only.",
        uncertainty="Not an operational scientific threshold.",
        evidence_claim_ids=(claim.id,),
        floor_version="fixture@1.0.0",
    )
    repository.add_competency_floor(floor)
    session.flush()
    need = CompetencyFloorDetector().identify(athlete.id, floor, estimate, NOW)
    repository.add_capability_need(need)
    policy = priority_policy()
    repository.add_priority_policy(policy)
    session.flush()
    candidate = AdaptationPlanningCandidate(
        adaptation_id=adaptation.id,
        capability_need_id=need.id,
        general_relevance=0.9,
        goal_relevance=0.8,
        prerequisite_value=0.7,
        expected_trainability=0.7,
        transfer_value=0.8,
        fatigue_cost=0.3,
        time_cost=0.3,
        interference_cost=0.2,
        source_observation_ids=(observation.id,),
        evidence_claim_ids=(claim.id,),
    )
    strategy = LongRangeStrategyPlanner().build(
        athlete_id=athlete.id,
        adaptations=(adaptation,),
        needs=(need,),
        candidates=(candidate,),
        policy=policy,
        generated_at=NOW,
        horizon_months=12,
        review_after_days=42,
    )
    repository.add_long_range_strategy(strategy)
    session.commit()
    return repository, strategy


def test_planning_chain_round_trip_preserves_rules_scores_and_provenance(
    session: Session,
) -> None:
    repository, strategy = build_and_persist_strategy(session)
    session.expire_all()

    restored = repository.get_long_range_strategy(strategy.id)

    assert restored == strategy
    assert repository.get_priority_policy(strategy.priority_policy_id) is not None
    assert repository.get_capability_need(strategy.priorities[0].capability_need_id) is not None
    assert repository.get_competency_floor(strategy.competency_floor_ids[0]) is not None
    assert restored is not None
    assert restored.source_observation_ids == strategy.source_observation_ids
    assert restored.source_capability_estimate_ids == strategy.source_capability_estimate_ids
    assert restored.evidence_claim_ids == strategy.evidence_claim_ids
    assert restored.priorities[0].score_components == strategy.priorities[0].score_components


def test_long_range_strategy_history_is_append_only(session: Session) -> None:
    _, strategy = build_and_persist_strategy(session)
    record = session.get(LongRangeStrategyRecord, strategy.id)
    assert record is not None
    record.block_hypothesis = "silently rewritten"

    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.flush()


def test_competency_floor_rejects_unknown_evidence(session: Session) -> None:
    floor = CompetencyFloor(
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        estimate_scope="assessment_specific:fixture",
        unit_or_scale="fixture_unit",
        threshold=100,
        comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
        population="synthetic test population",
        applicability_notes="Software fixture only.",
        uncertainty="Not an operational scientific threshold.",
        evidence_claim_ids=(uuid4(),),
        floor_version="fixture@1.0.0",
    )

    with pytest.raises(DomainIntegrityError, match="evidence claims"):
        DomainRepository(session).add_competency_floor(floor)


def build_and_persist_resolution_chain(
    session: Session,
) -> tuple[
    DomainRepository,
    LongRangeStrategy,
    StimulusRequirement,
    ExerciseResolution,
    ExerciseResolverPolicy,
    Environment,
    EquipmentAvailability,
    Exercise,
]:
    repository, strategy = build_and_persist_strategy(session)
    priority = strategy.priorities[0]
    adaptation = repository.get_adaptation(priority.adaptation_id)
    assert adaptation is not None
    environment = Environment(
        athlete_id=strategy.athlete_id,
        name="Hotel fixture",
        space_constraints={"floor_area_m2": 8},
        max_noise_level=CostLevel.MODERATE,
    )
    dumbbell = Equipment(name="Fixture dumbbell", category="external_load")
    availability = EquipmentAvailability(
        environment_id=environment.id,
        equipment_id=dumbbell.id,
        is_available=True,
        effective_from=NOW,
        load_limits={"maximum_total_kg": 40},
    )
    exercise = Exercise(
        name="Fixture dumbbell split squat",
        movement_patterns=("knee_dominant",),
        primary_adaptation_ids=(adaptation.id,),
        equipment_requirement_ids=(dumbbell.id,),
        loading_type="external",
        loadability=Loadability.MODERATE,
        skill_complexity=CostLevel.MODERATE,
        impact_level=ImpactLevel.LOW,
        velocity_characteristics=("controlled",),
        stability_demand=CostLevel.MODERATE,
        fatigue_cost=CostLevel.MODERATE,
        soreness_cost=CostLevel.MODERATE,
    )
    repository.add_environment(environment)
    repository.add_equipment(dumbbell)
    session.flush()
    repository.add_equipment_availability(availability)
    repository.add_exercise(exercise)
    specification = StimulusSpecification(
        movement_patterns=("knee_dominant",),
        allowed_loading_types=("external",),
        minimum_loadability=Loadability.HIGH,
        required_velocity_characteristics=("controlled",),
        maximum_skill_complexity=CostLevel.MODERATE,
        maximum_impact_level=ImpactLevel.LOW,
        maximum_stability_demand=CostLevel.MODERATE,
        maximum_fatigue_cost=CostLevel.MODERATE,
        maximum_soreness_cost=CostLevel.MODERATE,
        source_observation_ids=strategy.source_observation_ids,
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic high-force stimulus persistence fixture.",
    )
    requirement = StimulusRequirementBuilder().build(
        strategy=strategy,
        priority=priority,
        adaptation=adaptation,
        specification=specification,
        generated_at=NOW,
    )
    policy = ExerciseResolverPolicy(
        adaptation_role_weight=2,
        movement_pattern_weight=2,
        loading_type_weight=1,
        loadability_weight=3,
        velocity_weight=1,
        secondary_adaptation_credit=0.5,
        partial_match_threshold=0.7,
        full_match_threshold=0.95,
        max_ranked_candidates=5,
        policy_version="persistence-resolver@1.0.0",
    )
    snapshot = EnvironmentSnapshotBuilder().build(
        environment,
        (dumbbell,),
        (availability,),
        NOW,
    )
    resolution = ExerciseResolver().resolve(
        requirement=requirement,
        environment=snapshot,
        exercises=(exercise,),
        policy=policy,
        resolved_at=NOW,
    )
    repository.add_stimulus_requirement(requirement)
    repository.add_exercise_resolver_policy(policy)
    session.flush()
    repository.add_exercise_resolution(resolution)
    session.commit()
    session.expire_all()

    return (
        repository,
        strategy,
        requirement,
        resolution,
        policy,
        environment,
        availability,
        exercise,
    )


def test_stimulus_and_partial_exercise_resolution_round_trip_preserves_provenance(
    session: Session,
) -> None:
    (
        repository,
        strategy,
        requirement,
        resolution,
        policy,
        _,
        availability,
        _,
    ) = build_and_persist_resolution_chain(session)
    priority = strategy.priorities[0]

    assert repository.get_stimulus_requirement(requirement.id) == requirement
    assert repository.get_exercise_resolver_policy(policy.id) == policy
    assert repository.get_exercise_resolution(resolution.id) == resolution
    assert resolution.status is ResolutionStatus.PARTIAL
    assert resolution.source_availability_ids == (availability.id,)
    assert any(
        issue.code is ResolutionIssueCode.INSUFFICIENT_LOADABILITY
        for issue in resolution.unresolved_issues
    )
    assert requirement.adaptation_id == priority.adaptation_id

    record = session.get(ExerciseResolutionRecord, resolution.id)
    assert record is not None
    record.rationale = "silently rewritten"
    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.flush()


def build_and_persist_weekly_chain(
    session: Session,
) -> tuple[
    DomainRepository,
    LongRangeStrategy,
    StimulusRequirement,
    ExerciseResolution,
    AdaptationResourceDemand,
    ResourceAllocationPolicy,
    BlockPlan,
    SessionPrescription,
    SessionTemplate,
    WeeklyAvailability,
    WeeklySchedulingPolicy,
    WeeklyPlan,
]:
    (
        repository,
        strategy,
        requirement,
        resolution,
        _,
        environment,
        _,
        exercise,
    ) = build_and_persist_resolution_chain(session)
    priority = strategy.priorities[0]
    demand = AdaptationResourceDemand(
        long_range_strategy_id=strategy.id,
        adaptation_priority_id=priority.id,
        adaptation_id=priority.adaptation_id,
        priority_state=priority.state,
        stimulus_requirement_id=requirement.id,
        exercise_resolution_id=resolution.id,
        minimum_weekly_minutes=60,
        target_weekly_minutes=60,
        sessions_per_week=2,
        source_observation_ids=strategy.source_observation_ids,
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic resource persistence fixture.",
        demand_version="fixture@1.0.0",
    )
    allocation_policy = ResourceAllocationPolicy(
        develop_weight=1,
        maintain_weight=1,
        expose_weight=1,
        allow_partial_exercise_resolution=True,
        policy_version="fixture@1.0.0",
    )
    block = BlockPlanner().build(
        strategy=strategy,
        demands=(demand,),
        resolutions=(resolution,),
        policy=allocation_policy,
        weekly_budget_minutes=60,
        starts_on=date(2026, 8, 24),
        duration_weeks=4,
        constraints=("Synthetic fixture constraint",),
        generated_at=NOW,
    )
    assert block.status is BlockPlanStatus.PARTIAL
    allocation = block.allocations[0]
    assert resolution.selected_exercise_id == exercise.id
    prescription = SessionPrescription(
        athlete_id=strategy.athlete_id,
        block_plan_id=block.id,
        resource_allocation_id=allocation.id,
        exercise_resolution_id=resolution.id,
        exercise_id=exercise.id,
        adaptation_id=priority.adaptation_id,
        reason_for_inclusion="Synthetic persistence prescription.",
        sets=3,
        repetitions_per_set=5,
        intensity_targets=(EffortRpeTarget(minimum=6, maximum=8),),
        rest_seconds=120,
        progression_rule_reference="fixture:no-automatic-progression@1.0.0",
        substitution_class="fixture_resolution_candidates",
        planned_duration_minutes=30,
        fatigue_cost=CostLevel.MODERATE,
        source_observation_ids=strategy.source_observation_ids,
        evidence_claim_ids=strategy.evidence_claim_ids,
        prescribed_at=NOW,
        rule_version="fixture@1.0.0",
    )
    session_template = SessionTemplate(
        athlete_id=strategy.athlete_id,
        block_plan_id=block.id,
        name="Synthetic persisted training session",
        items=(
            SessionTemplateItem(
                prescription_id=prescription.id,
                order_index=1,
                section=SessionSection.PRIMARY,
            ),
        ),
        sessions_per_week=allocation.sessions_per_week,
        planned_duration_minutes=prescription.planned_duration_minutes,
        fatigue_cost=prescription.fatigue_cost,
        source_observation_ids=strategy.source_observation_ids,
        evidence_claim_ids=strategy.evidence_claim_ids,
        created_for_block_at=NOW,
        rule_version="fixture@1.0.0",
    )
    weekly_availability = WeeklyAvailability(
        athlete_id=strategy.athlete_id,
        week_start=block.starts_on,
        windows=(
            AvailabilityWindow(
                environment_id=environment.id,
                starts_at=datetime(2026, 8, 24, 18, 0, tzinfo=UTC),
                ends_at=datetime(2026, 8, 24, 18, 30, tzinfo=UTC),
            ),
            AvailabilityWindow(
                environment_id=environment.id,
                starts_at=datetime(2026, 8, 27, 18, 0, tzinfo=UTC),
                ends_at=datetime(2026, 8, 27, 18, 30, tzinfo=UTC),
            ),
        ),
        source_observation_ids=strategy.source_observation_ids,
        recorded_at=NOW,
        rule_version="fixture@1.0.0",
    )
    scheduling_policy = WeeklySchedulingPolicy(
        minimum_high_fatigue_recovery_hours=24,
        maximum_sessions_per_day=1,
        maximum_high_fatigue_sessions_per_day=1,
        policy_version="fixture@1.0.0",
    )
    weekly_plan = WeeklyScheduler().schedule(
        block=block,
        availability=weekly_availability,
        prescriptions=(prescription,),
        session_templates=(session_template,),
        resolutions=(resolution,),
        policy=scheduling_policy,
        generated_at=NOW,
    )
    assert weekly_plan.status is WeeklyPlanStatus.FEASIBLE

    repository.add_adaptation_resource_demand(demand)
    repository.add_resource_allocation_policy(allocation_policy)
    session.flush()
    repository.add_block_plan(block)
    session.flush()
    repository.add_session_prescription(prescription)
    repository.add_session_template(session_template)
    repository.add_weekly_availability(weekly_availability)
    repository.add_weekly_scheduling_policy(scheduling_policy)
    session.flush()
    repository.add_weekly_plan(weekly_plan)
    session.commit()
    session.expire_all()

    return (
        repository,
        strategy,
        requirement,
        resolution,
        demand,
        allocation_policy,
        block,
        prescription,
        session_template,
        weekly_availability,
        scheduling_policy,
        weekly_plan,
    )


def test_block_prescription_and_weekly_plan_round_trip_preserves_full_chain(
    session: Session,
) -> None:
    (
        repository,
        strategy,
        requirement,
        _,
        demand,
        allocation_policy,
        block,
        prescription,
        session_template,
        weekly_availability,
        scheduling_policy,
        weekly_plan,
    ) = build_and_persist_weekly_chain(session)

    assert repository.get_adaptation_resource_demand(demand.id) == demand
    assert repository.get_resource_allocation_policy(allocation_policy.id) == allocation_policy
    assert repository.get_block_plan(block.id) == block
    assert repository.get_session_prescription(prescription.id) == prescription
    assert repository.get_session_template(session_template.id) == session_template
    assert repository.get_weekly_availability(weekly_availability.id) == weekly_availability
    assert repository.get_weekly_scheduling_policy(scheduling_policy.id) == scheduling_policy
    assert repository.get_weekly_plan(weekly_plan.id) == weekly_plan
    assert weekly_plan.sessions[0].session_template_id == session_template.id
    assert block.long_range_strategy_id == strategy.id
    assert demand.stimulus_requirement_id == requirement.id

    record = session.get(WeeklyPlanRecord, weekly_plan.id)
    assert record is not None
    record.rule_version = "silently rewritten"
    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.flush()


def test_safety_execution_and_adherence_round_trip_preserves_provenance(
    session: Session,
) -> None:
    (
        repository,
        strategy,
        _,
        _,
        _,
        _,
        _,
        prescription,
        session_template,
        _,
        _,
        weekly_plan,
    ) = build_and_persist_weekly_chain(session)
    planned_session = weekly_plan.sessions[0]
    policy = SessionSafetyPolicy(
        allowed_modifications=(
            PrescriptionModification.REDUCE_VOLUME,
            PrescriptionModification.REDUCE_INTENSITY,
            PrescriptionModification.SHORTEN_SESSION,
        ),
        limited_readiness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        unusual_soreness_modifications=(PrescriptionModification.REDUCE_INTENSITY,),
        sleep_disruption_modifications=(PrescriptionModification.REDUCE_INTENSITY,),
        schedule_limitation_modifications=(PrescriptionModification.SHORTEN_SESSION,),
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic deterministic safety-gate persistence fixture.",
        policy_version="fixture-safety@1.0.0",
    )
    provenance = Provenance(
        recorded_by="automated-test",
        source_system="pytest",
        ingestion_method="fixture",
    )
    pre_check = SessionSafetyCheckInput(
        athlete_id=strategy.athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned_session.id,
        timing=SafetyGateTiming.PRE_SESSION,
        readiness=ReadinessLevel.READY,
        reported_at=planned_session.starts_at - timedelta(minutes=15),
        reliability=Confidence.HIGH,
        provenance=provenance,
    )
    pre_observation, pre_decision = SessionSafetyGate().evaluate(
        check=pre_check,
        weekly_plan=weekly_plan,
        planned_session=planned_session,
        policy=policy,
        decided_at=planned_session.starts_at - timedelta(minutes=10),
    )
    assert pre_decision.outcome is SafetyGateOutcome.PROCEED

    repository.add_session_safety_policy(policy)
    repository.add_observation(pre_observation)
    session.flush()
    repository.add_session_safety_decision(pre_decision)
    session.flush()

    performances = tuple(
        SetPerformance(
            set_index=set_index,
            performed=True,
            target_completed=True,
            actual_repetitions=5,
            load_value=20,
            load_unit="kg",
            effort_rpe=7,
            technique_constraint_met=True,
        )
        for set_index in range(1, 4)
    )
    execution_input = SessionExecutionInput(
        athlete_id=strategy.athlete_id,
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
        logged_at=planned_session.ends_at + timedelta(minutes=2),
        reliability=Confidence.HIGH,
        provenance=provenance,
    )
    performance_observation, execution = SessionExecutionRecorder().record(
        execution_input=execution_input,
        weekly_plan=weekly_plan,
        planned_session=planned_session,
        session_template=session_template,
        prescriptions=(prescription,),
        pre_session_decision=pre_decision,
    )
    repository.add_observation(performance_observation)
    session.flush()
    repository.add_session_execution(execution)
    session.flush()

    adherence = SessionAdherenceCalculator().calculate(
        execution=execution,
        planned_session=planned_session,
        prescription=prescription,
        calculated_at=execution.logged_at + timedelta(minutes=1),
    )
    repository.add_session_adherence(adherence)
    session.flush()

    post_check = SessionSafetyCheckInput(
        athlete_id=strategy.athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned_session.id,
        related_session_execution_id=execution.id,
        timing=SafetyGateTiming.POST_SESSION,
        signals=(
            SafetySignal(
                tag="fixture_preclassified_escalation",
                classification=SafetySignalClass.ESCALATE,
            ),
        ),
        reported_at=adherence.calculated_at + timedelta(minutes=1),
        reliability=Confidence.HIGH,
        provenance=provenance,
    )
    post_observation, post_decision = SessionSafetyGate().evaluate(
        check=post_check,
        weekly_plan=weekly_plan,
        planned_session=planned_session,
        policy=policy,
        decided_at=post_check.reported_at + timedelta(minutes=1),
        related_execution=execution,
    )
    assert post_decision.outcome is SafetyGateOutcome.STOP_AND_ESCALATE
    repository.add_observation(post_observation)
    session.flush()
    repository.add_session_safety_decision(post_decision)
    session.commit()
    session.expire_all()

    assert repository.get_session_safety_policy(policy.id) == policy
    assert repository.get_session_safety_decision(pre_decision.id) == pre_decision
    assert repository.get_session_execution(execution.id) == execution
    assert repository.get_session_adherence(adherence.id) == adherence
    assert repository.get_session_safety_decision(post_decision.id) == post_decision
    assert performance_observation.source is ObservationSource.WORKOUT_RESULT
    assert adherence.kind == "derived"
    assert adherence.source_observation_ids == (performance_observation.id,)
    assert post_decision.related_session_execution_id == execution.id

    execution_record = session.get(SessionExecutionRecord, execution.id)
    assert execution_record is not None
    execution_record.status = SessionExecutionStatus.PARTIAL.value
    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.flush()
    session.rollback()

    adherence_record = session.get(SessionAdherenceRecord, adherence.id)
    assert adherence_record is not None
    adherence_record.actual_dose_total = 0
    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.flush()


def test_progression_exposure_and_revised_prescription_round_trip(session: Session) -> None:
    (repository, strategy, _, _, _, _, block, prescription, session_template, _, _, weekly_plan) = (
        build_and_persist_weekly_chain(session)
    )
    planned = weekly_plan.sessions[0]
    claim_ids = strategy.evidence_claim_ids
    provenance = Provenance(
        recorded_by="automated-test", source_system="pytest", ingestion_method="fixture"
    )
    safety_policy = SessionSafetyPolicy(
        allowed_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        limited_readiness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        unusual_soreness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        sleep_disruption_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        schedule_limitation_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        evidence_claim_ids=claim_ids,
        rationale="fixture",
        policy_version="fixture@1.0.0",
    )
    check = SessionSafetyCheckInput(
        athlete_id=strategy.athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned.id,
        timing=SafetyGateTiming.PRE_SESSION,
        readiness=ReadinessLevel.READY,
        reported_at=planned.starts_at - timedelta(minutes=2),
        reliability=Confidence.HIGH,
        provenance=provenance,
    )
    safety_observation, safety_decision = SessionSafetyGate().evaluate(
        check=check,
        weekly_plan=weekly_plan,
        planned_session=planned,
        policy=safety_policy,
        decided_at=planned.starts_at - timedelta(minutes=1),
    )
    repository.add_session_safety_policy(safety_policy)
    repository.add_observation(safety_observation)
    session.flush()
    repository.add_session_safety_decision(safety_decision)
    session.flush()
    execution_input = SessionExecutionInput(
        athlete_id=strategy.athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned.id,
        pre_session_safety_decision_id=safety_decision.id,
        status=SessionExecutionStatus.COMPLETED,
        started_at=planned.starts_at,
        ended_at=planned.ends_at,
        items=(
            SessionItemExecutionInput(
                prescription_id=prescription.id,
                status=SessionExecutionStatus.COMPLETED,
                performances=tuple(
                    SetPerformance(
                        set_index=index,
                        performed=True,
                        target_completed=True,
                        actual_repetitions=5,
                        effort_rpe=7,
                        technique_constraint_met=True,
                    )
                    for index in range(1, 4)
                ),
                item_rpe=7,
            ),
        ),
        session_rpe=7,
        logged_at=planned.ends_at + timedelta(minutes=1),
        reliability=Confidence.HIGH,
        provenance=provenance,
    )
    performance_observation, execution = SessionExecutionRecorder().record(
        execution_input=execution_input,
        weekly_plan=weekly_plan,
        planned_session=planned,
        session_template=session_template,
        prescriptions=(prescription,),
        pre_session_decision=safety_decision,
    )
    repository.add_observation(performance_observation)
    session.flush()
    repository.add_session_execution(execution)
    session.flush()
    adherence = SessionAdherenceCalculator().calculate(
        execution=execution,
        planned_session=planned,
        prescription=prescription,
        calculated_at=execution.logged_at + timedelta(minutes=1),
    )
    repository.add_session_adherence(adherence)
    definition = ExposureDefinition(
        exercise_id=prescription.exercise_id,
        exposure_type=ExposureType.JUMPING,
        dose_unit="repetitions",
        evidence_claim_ids=claim_ids,
        rationale="fixture",
        definition_version="fixture@1.0.0",
    )
    repository.add_exposure_definition(definition)
    session.flush()
    entry = ExposureEntryCalculator().calculate(
        execution=execution, prescription=prescription, definition=definition
    )
    repository.add_exposure_entry(entry)
    exposure_policy = ExposureProgressionPolicy(
        exposure_type=ExposureType.JUMPING,
        dose_unit="repetitions",
        lookback_days=14,
        minimum_recent_entries=1,
        maximum_initial_dose=10,
        maximum_relative_increase=0.2,
        maximum_absolute_increase=5,
        evidence_claim_ids=claim_ids,
        rationale="fixture",
        policy_version="fixture@1.0.0",
    )
    repository.add_exposure_progression_policy(exposure_policy)
    session.flush()
    target = ExposureTarget(
        athlete_id=strategy.athlete_id,
        prescription_id=prescription.id,
        exposure_type=ExposureType.JUMPING,
        proposed_dose=16,
        dose_unit="repetitions",
        proposed_for=planned.starts_at + timedelta(days=7),
    )
    exposure_decision = ExposureProgressionValidator().validate(
        target=target, policy=exposure_policy, entries=(entry,), decided_at=target.proposed_for
    )
    repository.add_exposure_validation_decision(exposure_decision)
    progression_policy = ProgressionPolicy(
        reference=prescription.progression_rule_reference,
        minimum_set_completion_ratio=1,
        minimum_dose_completion_ratio=1,
        maximum_session_rpe=8,
        adjustment=PrescriptionAdjustment(
            dimension=ProgressionDimension.REPETITIONS,
            amount=1,
            unit="repetitions_per_set",
            description="add one repetition per set",
        ),
        exposure_type=ExposureType.JUMPING,
        evidence_claim_ids=claim_ids,
        rationale="fixture",
        policy_version="fixture@1.0.0",
    )
    repository.add_progression_policy(progression_policy)
    session.flush()
    progression = ProgressionEngine().decide(
        prescription=prescription,
        execution=execution,
        adherence=adherence,
        policy=progression_policy,
        exposure_validation=exposure_decision,
        decided_at=target.proposed_for,
    )
    repository.add_progression_decision(progression)
    session.flush()
    revised = PrescriptionProgressionApplicator().apply(
        prescription=prescription,
        decision=progression,
        policy=progression_policy,
        prescribed_at=target.proposed_for + timedelta(minutes=1),
    )
    repository.add_session_prescription(revised)
    session.commit()
    session.expire_all()

    assert repository.get_exposure_definition(definition.id) == definition
    assert repository.get_exposure_entry(entry.id) == entry
    assert repository.get_exposure_progression_policy(exposure_policy.id) == exposure_policy
    assert repository.get_exposure_validation_decision(exposure_decision.id) == exposure_decision
    assert repository.get_progression_policy(progression_policy.id) == progression_policy
    assert repository.get_progression_decision(progression.id) == progression
    assert repository.get_session_prescription(revised.id) == revised

    baseline = repository.get_capability_estimate(strategy.source_capability_estimate_ids[0])
    assert baseline is not None
    review_time = datetime(2026, 9, 21, 14, 0, tzinfo=UTC)
    followup_observation = Observation(
        athlete_id=strategy.athlete_id,
        observed_at=review_time - timedelta(hours=1),
        observation_type="fixture_strength_test",
        measurement=70,
        unit="fixture_unit",
        source=ObservationSource.TEST_RESULT,
        reliability=Confidence.MODERATE,
        provenance=provenance,
    )
    repository.add_observation(followup_observation)
    session.flush()
    followup = CapabilityEstimate(
        athlete_id=strategy.athlete_id,
        domain=baseline.domain,
        estimate=70,
        unit_or_scale=baseline.unit_or_scale,
        estimate_scope=baseline.estimate_scope,
        confidence=Confidence.MODERATE,
        calculation_method="fixture follow-up",
        source_observation_ids=(followup_observation.id,),
        estimated_at=review_time,
        valid_until=review_time + timedelta(days=30),
        rule_version="fixture@1.0.0",
    )
    repository.add_capability_estimate(followup)
    session.flush()
    response = TrainingResponseCalculator().calculate(
        block=block,
        adaptation_id=prescription.adaptation_id,
        prescriptions=(prescription,),
        executions=(execution,),
        adherences=(adherence,),
        baseline=baseline,
        followup=followup,
        intervention_summary="Synthetic completed strength prescription.",
        measurement_uncertainty="Software fixture; no operational measurement claim.",
        contextual_factors=("synthetic fixture",),
        calculated_at=review_time + timedelta(minutes=1),
    )
    review_policy = BlockReviewPolicy(
        minimum_adherence_ratio=0.8,
        minimum_response_confidence=Confidence.LOW,
        evidence_claim_ids=claim_ids,
        rationale="Software fixture only.",
        policy_version="fixture@1.0.0",
    )
    review = BlockReviewEngine().review(
        block=block,
        responses=(response,),
        targets=(
            ResponseEvaluationTarget(
                training_response_id=response.id,
                comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
                minimum_meaningful_change=5,
            ),
        ),
        safety_decisions=(),
        policy=review_policy,
        reviewed_at=review_time + timedelta(minutes=2),
    )
    assert review.outcome is BlockReviewOutcome.SUPPORTED
    low_delivery_response = response.model_copy(update={"adherence_ratio": 0.5})
    low_delivery_review = BlockReviewEngine().review(
        block=block,
        responses=(low_delivery_response,),
        targets=(
            ResponseEvaluationTarget(
                training_response_id=low_delivery_response.id,
                comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
                minimum_meaningful_change=5,
            ),
        ),
        safety_decisions=(),
        policy=review_policy,
        reviewed_at=review_time + timedelta(minutes=2),
    )
    assert low_delivery_review.outcome is BlockReviewOutcome.INCONCLUSIVE
    assert low_delivery_review.response_evaluations[0].threshold_met is None
    repository.add_training_response(response)
    repository.add_block_review_policy(review_policy)
    session.flush()
    repository.add_block_review(review)
    session.commit()
    session.expire_all()
    assert repository.get_training_response(response.id) == response
    assert repository.get_block_review_policy(review_policy.id) == review_policy
    assert repository.get_block_review(review.id) == review

    response_record = session.get(TrainingResponseRecord, response.id)
    assert response_record is not None
    response_record.actual_dose_total = 0
    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.flush()
    session.rollback()

    review_record = session.get(BlockReviewRecord, review.id)
    assert review_record is not None
    review_record.outcome = BlockReviewOutcome.INCONCLUSIVE.value
    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.flush()
