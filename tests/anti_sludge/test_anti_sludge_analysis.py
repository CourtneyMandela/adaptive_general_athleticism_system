from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from agas_domain import (
    Adaptation,
    AdaptationPlanningCandidate,
    AvailableEquipmentSnapshot,
    CapabilityDomain,
    CapabilityEstimate,
    ComparisonDirection,
    CompetencyFloor,
    Confidence,
    CostLevel,
    EnvironmentSnapshot,
    Exercise,
    ExerciseResolverPolicy,
    ImpactLevel,
    Loadability,
    LongRangeStrategy,
    PriorityPolicy,
    StimulusRequirement,
    TrainingPriorityState,
)
from agas_evaluation import (
    AntiSludgeAnalyzer,
    AntiSludgeDimension,
    AntiSludgeInputError,
    CounterfactualExpectation,
    ProgramSignature,
)
from agas_planner import CompetencyFloorDetector, ExerciseResolver, LongRangeStrategyPlanner

NOW = datetime(2026, 9, 11, 12, 0, tzinfo=UTC)


def test_opposite_capability_profiles_change_priority_structure() -> None:
    athlete_id = uuid4()
    aerobic = Adaptation(name="Aerobic base", domain=CapabilityDomain.AEROBIC_CAPACITY)
    strength = Adaptation(name="Maximum strength", domain=CapabilityDomain.MAXIMUM_STRENGTH)
    adaptations = (aerobic, strength)
    endurance_limited = _strategy(athlete_id, adaptations, (55, 130))
    strength_limited = _strategy(athlete_id, adaptations, (130, 55))
    names = {item.id: item.name for item in adaptations}

    report = AntiSludgeAnalyzer().compare(
        ProgramSignature.from_artifacts(
            label="endurance limited",
            strategy=endurance_limited,
            adaptation_names=names,
        ),
        ProgramSignature.from_artifacts(
            label="strength limited",
            strategy=strength_limited,
            adaptation_names=names,
        ),
        CounterfactualExpectation(
            changed_input="Swap only aerobic and maximum-strength capability estimates.",
            must_change=(AntiSludgeDimension.PRIORITY_STRUCTURE,),
            must_remain_stable=(
                AntiSludgeDimension.RESOURCE_ALLOCATION,
                AntiSludgeDimension.EXERCISE_SELECTION,
                AntiSludgeDimension.PRESCRIPTION_DOSE,
                AntiSludgeDimension.WEEKLY_STRUCTURE,
            ),
            rationale="The measured deficit should control the one available development slot.",
            expectation_version="opposite-capability-profile@1.0.0",
        ),
    )

    assert report.verdict == "responsive"
    assert report.alert is False
    assert report.dimension_similarity[AntiSludgeDimension.PRIORITY_STRUCTURE] == 0
    assert set(report.changed_dimensions) == {AntiSludgeDimension.PRIORITY_STRUCTURE}


def test_identical_output_raises_generic_program_alert_when_change_is_required() -> None:
    athlete_id = uuid4()
    adaptation = Adaptation(name="Aerobic base", domain=CapabilityDomain.AEROBIC_CAPACITY)
    strategy = _strategy(athlete_id, (adaptation,), (55,))
    signature = ProgramSignature.from_artifacts(
        label="baseline",
        strategy=strategy,
        adaptation_names={adaptation.id: adaptation.name},
    )

    report = AntiSludgeAnalyzer().compare(
        signature,
        signature.model_copy(update={"label": "counterfactual"}),
        CounterfactualExpectation(
            changed_input="Synthetic meaningful capability change.",
            must_change=(AntiSludgeDimension.PRIORITY_STRUCTURE,),
            rationale="A test fixture requiring a planning response must not converge identically.",
            expectation_version="identical-output-detection@1.0.0",
        ),
    )

    assert report.verdict == "generic_program_alert"
    assert report.alert is True
    assert report.missing_required_changes == (AntiSludgeDimension.PRIORITY_STRUCTURE,)
    assert report.overall_similarity == 1


def test_signature_rejects_missing_semantic_names_instead_of_uuid_noise() -> None:
    athlete_id = uuid4()
    adaptation = Adaptation(name="Aerobic base", domain=CapabilityDomain.AEROBIC_CAPACITY)
    strategy = _strategy(athlete_id, (adaptation,), (55,))

    with pytest.raises(AntiSludgeInputError, match="missing semantic name"):
        ProgramSignature.from_artifacts(
            label="opaque identity",
            strategy=strategy,
            adaptation_names={},
        )


def test_equipment_counterfactual_changes_exercise_but_preserves_adaptation_priority() -> None:
    athlete_id = uuid4()
    adaptation = Adaptation(name="Maximum strength", domain=CapabilityDomain.MAXIMUM_STRENGTH)
    strategy = _strategy(athlete_id, (adaptation,), (55,))
    barbell_id = uuid4()
    dumbbell_id = uuid4()
    requirement = _strength_requirement(athlete_id, strategy, adaptation.id)
    barbell_squat = _exercise("Barbell squat", adaptation.id, barbell_id, Loadability.HIGH)
    dumbbell_split_squat = _exercise(
        "Dumbbell split squat", adaptation.id, dumbbell_id, Loadability.MODERATE
    )
    policy = _resolver_policy()
    resolver = ExerciseResolver()
    gym = _environment(athlete_id, barbell_id, floor_area_m2=20)
    hotel = _environment(athlete_id, dumbbell_id, floor_area_m2=8)
    exercises = (barbell_squat, dumbbell_split_squat)
    gym_resolution = resolver.resolve(
        requirement=requirement,
        environment=gym,
        exercises=exercises,
        policy=policy,
        resolved_at=NOW,
    )
    hotel_resolution = resolver.resolve(
        requirement=requirement,
        environment=hotel,
        exercises=exercises,
        policy=policy,
        resolved_at=NOW,
    )
    adaptation_names = {adaptation.id: adaptation.name}
    exercise_names = {item.id: item.name for item in exercises}

    baseline = ProgramSignature.from_artifacts(
        label="full gym",
        strategy=strategy,
        adaptation_names=adaptation_names,
        stimulus_requirements=(requirement,),
        resolutions=(gym_resolution,),
        exercise_names=exercise_names,
    )
    variant = ProgramSignature.from_artifacts(
        label="hotel gym",
        strategy=strategy,
        adaptation_names=adaptation_names,
        stimulus_requirements=(requirement,),
        resolutions=(hotel_resolution,),
        exercise_names=exercise_names,
    )
    expectation = CounterfactualExpectation(
        changed_input="Replace full-gym barbell availability with hotel dumbbells.",
        must_change=(AntiSludgeDimension.EXERCISE_SELECTION,),
        must_remain_stable=(AntiSludgeDimension.PRIORITY_STRUCTURE,),
        rationale="Equipment changes the feasible means without silently changing the goal.",
        expectation_version="equipment-means-not-goal@1.0.0",
    )

    report = AntiSludgeAnalyzer().compare(
        baseline,
        variant,
        expectation,
    )

    assert report.verdict == "responsive"
    assert report.alert is False
    assert report.dimension_similarity[AntiSludgeDimension.PRIORITY_STRUCTURE] == 1
    assert report.dimension_similarity[AntiSludgeDimension.EXERCISE_SELECTION] == 0

    invalid_payload = variant.model_dump(mode="json")
    invalid_payload["priority_structure"][0]["rank"] = 2
    spillover = AntiSludgeAnalyzer().compare(
        baseline,
        ProgramSignature.model_validate(invalid_payload),
        expectation,
    )
    assert spillover.verdict == "invariant_violation_alert"
    assert spillover.violated_stability == (AntiSludgeDimension.PRIORITY_STRUCTURE,)


def _strategy(
    athlete_id: UUID,
    adaptations: tuple[Adaptation, ...],
    values: tuple[float, ...],
) -> LongRangeStrategy:
    evidence_id = uuid4()
    detector = CompetencyFloorDetector()
    needs = []
    candidates = []
    for adaptation, value in zip(adaptations, values, strict=True):
        observation_id = uuid4()
        floor = CompetencyFloor(
            domain=adaptation.domain,
            estimate_scope="assessment_specific:anti_sludge_fixture",
            unit_or_scale="fixture_unit",
            threshold=100,
            comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
            population="Synthetic anti-sludge fixture only.",
            applicability_notes="Not an operational scientific floor.",
            uncertainty="Threshold exists only to exercise responsiveness checks.",
            evidence_claim_ids=(evidence_id,),
            floor_version="anti-sludge-fixture@1.0.0",
        )
        estimate = CapabilityEstimate(
            athlete_id=athlete_id,
            domain=adaptation.domain,
            estimate=value,
            unit_or_scale="fixture_unit",
            estimate_scope="assessment_specific:anti_sludge_fixture",
            confidence=Confidence.HIGH,
            calculation_method="synthetic-fixture",
            source_observation_ids=(observation_id,),
            estimated_at=NOW,
            valid_until=NOW + timedelta(days=30),
            rule_version="anti-sludge-fixture@1.0.0",
        )
        need = detector.identify(athlete_id, floor, estimate, NOW)
        needs.append(need)
        candidates.append(
            AdaptationPlanningCandidate(
                adaptation_id=adaptation.id,
                capability_need_id=need.id,
                general_relevance=0,
                goal_relevance=0,
                prerequisite_value=0,
                expected_trainability=0,
                transfer_value=0,
                fatigue_cost=0,
                time_cost=0,
                interference_cost=0,
                source_observation_ids=(observation_id,),
                evidence_claim_ids=(evidence_id,),
            )
        )
    policy = PriorityPolicy(
        deficit_weight=1,
        general_relevance_weight=0,
        goal_relevance_weight=0,
        prerequisite_value_weight=0,
        expected_trainability_weight=0,
        transfer_value_weight=0,
        fatigue_cost_weight=0,
        time_cost_weight=0,
        interference_cost_weight=0,
        cost_penalty=0,
        confidence_multipliers={
            Confidence.UNKNOWN: 0,
            Confidence.LOW: 0.5,
            Confidence.MODERATE: 0.75,
            Confidence.HIGH: 1,
        },
        develop_score_threshold=0.01,
        comparative_advantage_threshold=1,
        severe_deficit_threshold=0.25,
        max_develop_adaptations=1,
        policy_version="anti-sludge-deficit-only@1.0.0",
    )
    return LongRangeStrategyPlanner().build(
        athlete_id=athlete_id,
        adaptations=adaptations,
        needs=needs,
        candidates=candidates,
        policy=policy,
        generated_at=NOW,
        horizon_months=12,
        review_after_days=42,
    )


def _strength_requirement(
    athlete_id: UUID, strategy: LongRangeStrategy, adaptation_id: UUID
) -> StimulusRequirement:
    priority = strategy.priorities[0]
    return StimulusRequirement(
        athlete_id=athlete_id,
        long_range_strategy_id=strategy.id,
        adaptation_priority_id=priority.id,
        adaptation_id=adaptation_id,
        priority_state=TrainingPriorityState.DEVELOP,
        movement_patterns=("knee_dominant",),
        allowed_loading_types=("external_load",),
        allowed_lateralities=("bilateral",),
        minimum_loadability=Loadability.HIGH,
        required_velocity_characteristics=("controlled",),
        maximum_skill_complexity=CostLevel.MODERATE,
        maximum_impact_level=ImpactLevel.LOW,
        maximum_stability_demand=CostLevel.MODERATE,
        maximum_fatigue_cost=CostLevel.MODERATE,
        maximum_soreness_cost=CostLevel.MODERATE,
        source_observation_ids=strategy.source_observation_ids,
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic anti-sludge strength stimulus.",
        generated_at=NOW,
        rule_version="anti-sludge-fixture@1.0.0",
    )


def _exercise(
    name: str,
    adaptation_id: UUID,
    equipment_id: UUID,
    loadability: Loadability,
) -> Exercise:
    return Exercise(
        name=name,
        movement_patterns=("knee_dominant",),
        primary_adaptation_ids=(adaptation_id,),
        equipment_requirement_ids=(equipment_id,),
        loading_type="external_load",
        laterality="bilateral",
        loadability=loadability,
        skill_complexity=CostLevel.MODERATE,
        impact_level=ImpactLevel.LOW,
        velocity_characteristics=("controlled",),
        stability_demand=CostLevel.MODERATE,
        fatigue_cost=CostLevel.MODERATE,
        soreness_cost=CostLevel.MODERATE,
    )


def _environment(
    athlete_id: UUID, equipment_id: UUID, *, floor_area_m2: float
) -> EnvironmentSnapshot:
    return EnvironmentSnapshot(
        athlete_id=athlete_id,
        environment_id=uuid4(),
        captured_at=NOW,
        available_equipment=(
            AvailableEquipmentSnapshot(equipment_id=equipment_id, category="external_load"),
        ),
        source_availability_ids=(uuid4(),),
        floor_area_m2=floor_area_m2,
        max_noise_level=CostLevel.HIGH,
        outdoor_access=False,
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
        policy_version="anti-sludge-resolver@1.0.0",
    )
