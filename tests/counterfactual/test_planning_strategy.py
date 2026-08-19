from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from agas_domain import (
    Adaptation,
    AdaptationPlanningCandidate,
    CapabilityDomain,
    CapabilityEstimate,
    ComparisonDirection,
    CompetencyFloor,
    Confidence,
    LongRangeStrategy,
    PriorityPolicy,
    TrainingPriorityState,
)
from agas_planner import CompetencyFloorDetector, LongRangeStrategyPlanner

NOW = datetime(2026, 8, 19, 14, 0, tzinfo=UTC)


def planning_policy() -> PriorityPolicy:
    return PriorityPolicy(
        deficit_weight=5,
        general_relevance_weight=1,
        goal_relevance_weight=1,
        prerequisite_value_weight=1,
        expected_trainability_weight=1,
        transfer_value_weight=1,
        fatigue_cost_weight=1,
        time_cost_weight=1,
        interference_cost_weight=1,
        cost_penalty=0.1,
        confidence_multipliers={
            Confidence.UNKNOWN: 0.0,
            Confidence.LOW: 0.5,
            Confidence.MODERATE: 0.75,
            Confidence.HIGH: 1.0,
        },
        develop_score_threshold=0.35,
        comparative_advantage_threshold=0.3,
        severe_deficit_threshold=0.25,
        max_develop_adaptations=1,
        policy_version="counterfactual-priority@1.0.0",
    )


def opposite_profile_strategy(
    athlete_id: UUID,
    aerobic_value: float,
    strength_value: float,
    *,
    cultivate_strength: bool = False,
) -> tuple[LongRangeStrategy, Adaptation, Adaptation]:
    evidence_id = uuid4()
    aerobic = Adaptation(name="Aerobic base", domain=CapabilityDomain.AEROBIC_CAPACITY)
    strength = Adaptation(name="Maximum strength", domain=CapabilityDomain.MAXIMUM_STRENGTH)
    adaptations = (aerobic, strength)
    values = (aerobic_value, strength_value)
    observations = (uuid4(), uuid4())
    floors = tuple(
        CompetencyFloor(
            domain=adaptation.domain,
            estimate_scope="assessment_specific:fixture",
            unit_or_scale="fixture_unit",
            threshold=100,
            comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
            population="synthetic test population",
            applicability_notes="Counterfactual software fixture only.",
            uncertainty="Not an operational scientific floor.",
            evidence_claim_ids=(evidence_id,),
            floor_version="fixture@1.0.0",
        )
        for adaptation in adaptations
    )
    estimates = tuple(
        CapabilityEstimate(
            athlete_id=athlete_id,
            domain=adaptation.domain,
            estimate=value,
            unit_or_scale="fixture_unit",
            estimate_scope="assessment_specific:fixture",
            confidence=Confidence.HIGH,
            calculation_method="fixture",
            source_observation_ids=(observation_id,),
            estimated_at=NOW,
            valid_until=NOW + timedelta(days=30),
            rule_version="fixture@1.0.0",
        )
        for adaptation, value, observation_id in zip(adaptations, values, observations, strict=True)
    )
    detector = CompetencyFloorDetector()
    needs = tuple(
        detector.identify(athlete_id, floor, estimate, NOW)
        for floor, estimate in zip(floors, estimates, strict=True)
    )
    candidates = tuple(
        AdaptationPlanningCandidate(
            adaptation_id=adaptation.id,
            capability_need_id=need.id,
            general_relevance=0.9,
            goal_relevance=0.6,
            prerequisite_value=0.6,
            expected_trainability=0.7,
            transfer_value=0.8,
            fatigue_cost=0.3,
            time_cost=0.3,
            interference_cost=0.2,
            cultivate_comparative_advantage=cultivate_strength and index == 1,
            source_observation_ids=(observation_id,),
            evidence_claim_ids=(evidence_id,),
        )
        for index, (adaptation, need, observation_id) in enumerate(
            zip(adaptations, needs, observations, strict=True)
        )
    )
    strategy = LongRangeStrategyPlanner().build(
        athlete_id=athlete_id,
        adaptations=adaptations,
        needs=needs,
        candidates=candidates,
        policy=planning_policy(),
        generated_at=NOW,
        horizon_months=12,
        review_after_days=42,
    )
    return strategy, aerobic, strength


def test_opposite_profiles_receive_opposite_development_allocations() -> None:
    athlete_id = uuid4()
    endurance_limited, aerobic_a, strength_a = opposite_profile_strategy(athlete_id, 55, 130)
    strength_limited, aerobic_b, strength_b = opposite_profile_strategy(athlete_id, 130, 55)

    states_a = {item.adaptation_id: item.state for item in endurance_limited.priorities}
    states_b = {item.adaptation_id: item.state for item in strength_limited.priorities}

    assert states_a[aerobic_a.id] is TrainingPriorityState.DEVELOP
    assert states_a[strength_a.id] is TrainingPriorityState.MAINTAIN
    assert states_b[aerobic_b.id] is TrainingPriorityState.MAINTAIN
    assert states_b[strength_b.id] is TrainingPriorityState.DEVELOP
    assert endurance_limited.block_hypothesis != strength_limited.block_hypothesis


def test_athlete_valued_strength_can_continue_after_competency_floors_are_met() -> None:
    athlete_id = uuid4()
    balanced, _, ordinary_strength = opposite_profile_strategy(athlete_id, 120, 130)
    cultivated, _, valued_strength = opposite_profile_strategy(
        athlete_id, 120, 130, cultivate_strength=True
    )
    balanced_states = {item.adaptation_id: item.state for item in balanced.priorities}
    cultivated_states = {item.adaptation_id: item.state for item in cultivated.priorities}

    assert balanced_states[ordinary_strength.id] is TrainingPriorityState.MAINTAIN
    assert cultivated_states[valued_strength.id] is TrainingPriorityState.DEVELOP
