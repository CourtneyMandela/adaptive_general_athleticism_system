from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from agas_domain import (
    Adaptation,
    AdaptationPlanningCandidate,
    CapabilityDomain,
    CapabilityEstimate,
    ComparisonDirection,
    CompetencyFloor,
    CompetencyStatus,
    Confidence,
    PriorityPolicy,
    TrainingPriorityState,
)
from agas_planner import CompetencyFloorDetector, LongRangeStrategyPlanner

NOW = datetime(2026, 8, 19, 14, 0, tzinfo=UTC)


def policy(*, max_develop: int = 2) -> PriorityPolicy:
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
        develop_score_threshold=0.35,
        comparative_advantage_threshold=0.5,
        severe_deficit_threshold=0.25,
        max_develop_adaptations=max_develop,
        policy_version="test-priority@1.0.0",
    )


def floor(
    domain: CapabilityDomain = CapabilityDomain.AEROBIC_CAPACITY,
    *,
    direction: ComparisonDirection = ComparisonDirection.HIGHER_IS_BETTER,
) -> CompetencyFloor:
    return CompetencyFloor(
        domain=domain,
        estimate_scope="assessment_specific:fixture",
        unit_or_scale="fixture_unit",
        threshold=100,
        comparison_direction=direction,
        population="synthetic test population",
        applicability_notes="Test fixture only; not an operational scientific floor.",
        uncertainty="Threshold exists only to exercise deterministic software behavior.",
        evidence_claim_ids=(uuid4(),),
        floor_version="fixture-floor@1.0.0",
    )


def estimate(
    athlete_id: UUID,
    domain: CapabilityDomain,
    value: float,
    observation_id: UUID,
) -> CapabilityEstimate:
    return CapabilityEstimate(
        athlete_id=athlete_id,
        domain=domain,
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


def test_competency_floor_detection_preserves_gap_direction_and_staleness() -> None:
    athlete_id = uuid4()
    observation_id = uuid4()
    detector = CompetencyFloorDetector()
    higher_floor = floor()
    lower_floor = floor(direction=ComparisonDirection.LOWER_IS_BETTER)
    below = detector.identify(
        athlete_id,
        higher_floor,
        estimate(athlete_id, higher_floor.domain, 70, observation_id),
        NOW,
    )
    above_limit = detector.identify(
        athlete_id,
        lower_floor,
        estimate(athlete_id, lower_floor.domain, 125, observation_id),
        NOW,
    )
    stale_estimate = estimate(athlete_id, higher_floor.domain, 70, observation_id).model_copy(
        update={"valid_until": NOW - timedelta(seconds=1), "estimated_at": NOW - timedelta(days=31)}
    )
    stale = detector.identify(athlete_id, higher_floor, stale_estimate, NOW)

    assert below.status is CompetencyStatus.BELOW_FLOOR
    assert below.gap_from_floor == 30
    assert below.normalized_deficit == 0.3
    assert above_limit.status is CompetencyStatus.BELOW_FLOOR
    assert above_limit.gap_from_floor == 25
    assert stale.status is CompetencyStatus.STALE
    assert stale.normalized_deficit is None


def test_planner_assigns_all_four_states_without_generating_prescriptions() -> None:
    athlete_id = uuid4()
    evidence_id = uuid4()
    adaptations = tuple(
        Adaptation(name=name, domain=domain)
        for name, domain in (
            ("Aerobic base", CapabilityDomain.AEROBIC_CAPACITY),
            ("Maximum strength", CapabilityDomain.MAXIMUM_STRENGTH),
            ("Jump exposure", CapabilityDomain.TISSUE_EXPOSURE),
            ("High-speed running", CapabilityDomain.HIGH_SPEED_RUNNING),
        )
    )
    floors = [floor(item.domain) for item in adaptations]
    values = (60, 120, 90, 90)
    observations = tuple(uuid4() for _ in adaptations)
    estimates = tuple(
        estimate(athlete_id, item.domain, value, observation_id)
        for item, value, observation_id in zip(adaptations, values, observations, strict=True)
    )
    detector = CompetencyFloorDetector()
    needs = tuple(
        detector.identify(athlete_id, floor_item, estimate_item, NOW)
        for floor_item, estimate_item in zip(floors, estimates, strict=True)
    )
    candidates = tuple(
        AdaptationPlanningCandidate(
            adaptation_id=adaptation.id,
            capability_need_id=need.id,
            general_relevance=0.8,
            goal_relevance=0.7,
            prerequisite_value=0.5,
            expected_trainability=0.7,
            transfer_value=0.8,
            fatigue_cost=0.3,
            time_cost=0.3,
            interference_cost=0.2,
            introductory_exposure_needed=index == 2,
            safe_to_train=index != 3,
            source_observation_ids=(observations[index],),
            evidence_claim_ids=(evidence_id,),
        )
        for index, (adaptation, need) in enumerate(zip(adaptations, needs, strict=True))
    )

    strategy = LongRangeStrategyPlanner().build(
        athlete_id=athlete_id,
        adaptations=adaptations,
        needs=needs,
        candidates=candidates,
        policy=policy(max_develop=1),
        generated_at=NOW,
        horizon_months=12,
        review_after_days=42,
    )
    states = {item.adaptation_id: item.state for item in strategy.priorities}

    assert states[adaptations[0].id] is TrainingPriorityState.DEVELOP
    assert states[adaptations[1].id] is TrainingPriorityState.MAINTAIN
    assert states[adaptations[2].id] is TrainingPriorityState.EXPOSE
    assert states[adaptations[3].id] is TrainingPriorityState.DEFER
    assert sum(item.development_allocation for item in strategy.priorities) == 1
    assert "exercise" not in strategy.model_dump()
    assert strategy.source_capability_estimate_ids == tuple(item.id for item in estimates)
