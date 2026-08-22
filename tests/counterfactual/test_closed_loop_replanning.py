from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from agas_domain import (
    Adaptation,
    AdaptationPlanningCandidate,
    BlockPlan,
    BlockPlanStatus,
    BlockReview,
    BlockReviewOutcome,
    CapabilityDomain,
    CapabilityEstimate,
    ComparisonDirection,
    CompetencyFloor,
    Confidence,
    LongRangeStrategy,
    PriorityPolicy,
    ReplanningCandidateContext,
    ResourceAllocation,
    ResponseEvaluation,
    TrainingPriorityState,
    TrainingResponse,
)
from agas_planner import (
    ClosedLoopReplanner,
    ClosedLoopReplanningError,
    CompetencyFloorDetector,
    LongRangeStrategyPlanner,
)

INITIAL_TIME = datetime(2026, 7, 1, 14, 0, tzinfo=UTC)
REVIEW_TIME = datetime(2026, 8, 4, 14, 0, tzinfo=UTC)


@dataclass(frozen=True)
class ReplanningFixture:
    adaptations: tuple[Adaptation, ...]
    block: BlockPlan
    contexts: tuple[ReplanningCandidateContext, ...]
    floors: tuple[CompetencyFloor, ...]
    followups: tuple[CapabilityEstimate, ...]
    policy: PriorityPolicy
    responses: tuple[TrainingResponse, ...]
    review: BlockReview
    strategy: LongRangeStrategy


def test_reviewed_followups_reverse_priority_without_rewriting_prior_strategy() -> None:
    fixture = _fixture()
    prior_dump = fixture.strategy.model_dump()

    result = ClosedLoopReplanner().replan(
        previous_strategy=fixture.strategy,
        completed_block=fixture.block,
        block_review=fixture.review,
        training_responses=fixture.responses,
        selected_estimates=fixture.followups,
        adaptations=fixture.adaptations,
        competency_floors=fixture.floors,
        candidate_contexts=fixture.contexts,
        priority_policy=fixture.policy,
        generated_at=REVIEW_TIME,
        review_after_days=42,
    )

    old_states = {item.adaptation_id: item.state for item in fixture.strategy.priorities}
    new_states = {item.adaptation_id: item.state for item in result.strategy.priorities}
    aerobic_id, strength_id = (item.id for item in fixture.adaptations)
    assert old_states[aerobic_id] is TrainingPriorityState.DEVELOP
    assert old_states[strength_id] is TrainingPriorityState.MAINTAIN
    assert new_states[aerobic_id] is TrainingPriorityState.MAINTAIN
    assert new_states[strength_id] is TrainingPriorityState.DEVELOP
    assert result.strategy.supersedes_strategy_id == fixture.strategy.id
    assert result.strategy.triggering_block_review_id == fixture.review.id
    assert result.strategy.source_capability_estimate_ids == tuple(
        item.id for item in fixture.followups
    )
    assert fixture.review.outcome is BlockReviewOutcome.INCONCLUSIVE
    assert fixture.strategy.model_dump() == prior_dump


def test_replanning_rejects_estimate_not_reviewed_in_the_completed_block() -> None:
    fixture = _fixture()
    rogue = fixture.followups[0].model_copy(update={"id": uuid4()})

    with pytest.raises(
        ClosedLoopReplanningError,
        match="selected estimates must be prior-state or reviewed follow-up estimates",
    ):
        ClosedLoopReplanner().replan(
            previous_strategy=fixture.strategy,
            completed_block=fixture.block,
            block_review=fixture.review,
            training_responses=fixture.responses,
            selected_estimates=(rogue, fixture.followups[1]),
            adaptations=fixture.adaptations,
            competency_floors=fixture.floors,
            candidate_contexts=fixture.contexts,
            priority_policy=fixture.policy,
            generated_at=REVIEW_TIME,
            review_after_days=42,
        )


def test_replanning_context_must_use_its_adaptations_reviewed_followup() -> None:
    fixture = _fixture()
    first, second = fixture.contexts
    swapped_contexts = (
        first.model_copy(update={"capability_estimate_id": second.capability_estimate_id}),
        second.model_copy(update={"capability_estimate_id": first.capability_estimate_id}),
    )

    with pytest.raises(
        ClosedLoopReplanningError,
        match="trained adaptations must use their reviewed follow-up estimate",
    ):
        ClosedLoopReplanner().replan(
            previous_strategy=fixture.strategy,
            completed_block=fixture.block,
            block_review=fixture.review,
            training_responses=fixture.responses,
            selected_estimates=fixture.followups,
            adaptations=fixture.adaptations,
            competency_floors=fixture.floors,
            candidate_contexts=swapped_contexts,
            priority_policy=fixture.policy,
            generated_at=REVIEW_TIME,
            review_after_days=42,
        )


def test_strategy_revision_lineage_is_an_all_or_nothing_pair() -> None:
    fixture = _fixture()
    payload = fixture.strategy.model_dump()
    payload["supersedes_strategy_id"] = uuid4()

    with pytest.raises(ValueError, match="require both superseded strategy"):
        LongRangeStrategy.model_validate(payload)


def _fixture() -> ReplanningFixture:
    athlete_id = uuid4()
    evidence_id = uuid4()
    adaptations = (
        Adaptation(name="Aerobic base", domain=CapabilityDomain.AEROBIC_CAPACITY),
        Adaptation(name="Maximum strength", domain=CapabilityDomain.MAXIMUM_STRENGTH),
    )
    floors = tuple(_floor(item.domain, evidence_id) for item in adaptations)
    baseline_observations = (uuid4(), uuid4())
    followup_observations = (uuid4(), uuid4())
    baselines = (
        _estimate(
            athlete_id,
            CapabilityDomain.AEROBIC_CAPACITY,
            60,
            baseline_observations[0],
            INITIAL_TIME,
        ),
        _estimate(
            athlete_id,
            CapabilityDomain.MAXIMUM_STRENGTH,
            110,
            baseline_observations[1],
            INITIAL_TIME,
        ),
    )
    detector = CompetencyFloorDetector()
    needs = tuple(
        detector.identify(athlete_id, floor, estimate, INITIAL_TIME)
        for floor, estimate in zip(floors, baselines, strict=True)
    )
    policy = _policy()
    candidates = tuple(
        AdaptationPlanningCandidate(
            adaptation_id=adaptation.id,
            capability_need_id=need.id,
            general_relevance=0.6,
            goal_relevance=0.6,
            prerequisite_value=0.4,
            expected_trainability=0.6,
            transfer_value=0.6,
            fatigue_cost=0.3,
            time_cost=0.3,
            interference_cost=0.2,
            source_observation_ids=(observation_id,),
            evidence_claim_ids=(evidence_id,),
        )
        for adaptation, need, observation_id in zip(
            adaptations, needs, baseline_observations, strict=True
        )
    )
    strategy = LongRangeStrategyPlanner().build(
        athlete_id=athlete_id,
        adaptations=adaptations,
        needs=needs,
        candidates=candidates,
        policy=policy,
        generated_at=INITIAL_TIME,
        horizon_months=12,
        review_after_days=30,
    )
    allocations = tuple(
        ResourceAllocation(
            resource_demand_id=uuid4(),
            adaptation_priority_id=priority.id,
            adaptation_id=priority.adaptation_id,
            priority_state=priority.state,
            stimulus_requirement_id=uuid4(),
            exercise_resolution_id=uuid4(),
            minimum_weekly_minutes=30,
            target_weekly_minutes=30,
            allocated_weekly_minutes=30,
            sessions_per_week=1,
            status=BlockPlanStatus.FULL,
        )
        for priority in strategy.priorities
    )
    block = BlockPlan(
        athlete_id=athlete_id,
        long_range_strategy_id=strategy.id,
        resource_allocation_policy_id=uuid4(),
        starts_on=date(2026, 7, 7),
        ends_on=date(2026, 8, 3),
        duration_weeks=4,
        weekly_budget_minutes=60,
        status=BlockPlanStatus.FULL,
        hypothesis=strategy.block_hypothesis,
        allocations=allocations,
        source_observation_ids=baseline_observations,
        evidence_claim_ids=(evidence_id,),
        generated_at=INITIAL_TIME,
        rule_version="fixture@1.0.0",
    )
    followups = (
        _estimate(
            athlete_id,
            CapabilityDomain.AEROBIC_CAPACITY,
            110,
            followup_observations[0],
            REVIEW_TIME - timedelta(hours=2),
        ),
        _estimate(
            athlete_id,
            CapabilityDomain.MAXIMUM_STRENGTH,
            70,
            followup_observations[1],
            REVIEW_TIME - timedelta(hours=2),
        ),
    )
    responses = tuple(
        _response(
            athlete_id,
            block.id,
            adaptation.id,
            baseline,
            followup,
        )
        for adaptation, baseline, followup in zip(adaptations, baselines, followups, strict=True)
    )
    review = BlockReview(
        athlete_id=athlete_id,
        block_plan_id=block.id,
        block_hypothesis=block.hypothesis,
        block_review_policy_id=uuid4(),
        training_response_ids=tuple(item.id for item in responses),
        response_evaluations=tuple(
            ResponseEvaluation(
                training_response_id=item.id,
                comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
                minimum_meaningful_change=5,
                threshold_met=None,
                rationale="Synthetic low-confidence interpretation.",
            )
            for item in responses
        ),
        prescribed_sessions=2,
        completed_sessions=2,
        aggregate_adherence_ratio=1,
        outcome=BlockReviewOutcome.INCONCLUSIVE,
        source_observation_ids=followup_observations,
        evidence_claim_ids=(evidence_id,),
        rationale=("Causal interpretation is inconclusive.",),
        reviewed_at=REVIEW_TIME,
        rule_version="fixture@1.0.0",
    )
    contexts = tuple(
        ReplanningCandidateContext(
            adaptation_id=adaptation.id,
            competency_floor_id=floor.id,
            capability_estimate_id=followup.id,
            general_relevance=0.6,
            goal_relevance=0.6,
            prerequisite_value=0.4,
            expected_trainability=0.6,
            transfer_value=0.6,
            fatigue_cost=0.3,
            time_cost=0.3,
            interference_cost=0.2,
            evidence_claim_ids=(evidence_id,),
        )
        for adaptation, floor, followup in zip(adaptations, floors, followups, strict=True)
    )
    return ReplanningFixture(
        adaptations=adaptations,
        block=block,
        contexts=contexts,
        floors=floors,
        followups=followups,
        policy=policy,
        responses=responses,
        review=review,
        strategy=strategy,
    )


def _floor(domain: CapabilityDomain, evidence_id: UUID) -> CompetencyFloor:
    return CompetencyFloor(
        domain=domain,
        estimate_scope="assessment_specific:fixture",
        unit_or_scale="fixture_unit",
        threshold=100,
        comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
        population="synthetic test population",
        applicability_notes="Software fixture only.",
        uncertainty="Not an operational scientific floor.",
        evidence_claim_ids=(evidence_id,),
        floor_version="fixture@1.0.0",
    )


def _estimate(
    athlete_id: UUID,
    domain: CapabilityDomain,
    value: float,
    observation_id: UUID,
    estimated_at: datetime,
) -> CapabilityEstimate:
    return CapabilityEstimate(
        athlete_id=athlete_id,
        domain=domain,
        estimate=value,
        unit_or_scale="fixture_unit",
        estimate_scope="assessment_specific:fixture",
        confidence=Confidence.MODERATE,
        calculation_method="synthetic fixture",
        source_observation_ids=(observation_id,),
        estimated_at=estimated_at,
        valid_until=REVIEW_TIME + timedelta(days=30),
        rule_version="fixture@1.0.0",
    )


def _response(
    athlete_id: UUID,
    block_id: UUID,
    adaptation_id: UUID,
    baseline: CapabilityEstimate,
    followup: CapabilityEstimate,
) -> TrainingResponse:
    return TrainingResponse(
        athlete_id=athlete_id,
        block_plan_id=block_id,
        adaptation_id=adaptation_id,
        intervention_summary="Synthetic completed block allocation.",
        prescription_ids=(uuid4(),),
        session_execution_ids=(uuid4(),),
        session_adherence_ids=(uuid4(),),
        prescribed_sessions=1,
        completed_sessions=1,
        prescribed_dose_total=10,
        actual_dose_total=10,
        dose_unit="fixture_units",
        adherence_ratio=1,
        baseline_capability_estimate_id=baseline.id,
        followup_capability_estimate_id=followup.id,
        baseline_value=_numeric_estimate(baseline),
        followup_value=_numeric_estimate(followup),
        observed_change=_numeric_estimate(followup) - _numeric_estimate(baseline),
        measurement_uncertainty="Synthetic fixture.",
        confidence=Confidence.MODERATE,
        source_observation_ids=(
            *baseline.source_observation_ids,
            *followup.source_observation_ids,
        ),
        calculated_at=REVIEW_TIME - timedelta(hours=1),
        calculation_method="synthetic fixture",
        rule_version="fixture@1.0.0",
    )


def _numeric_estimate(estimate: CapabilityEstimate) -> float:
    value = estimate.estimate
    if not isinstance(value, int | float):
        raise TypeError("synthetic fixture estimates must be numeric")
    return float(value)


def _policy() -> PriorityPolicy:
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
        develop_score_threshold=0.25,
        comparative_advantage_threshold=0.5,
        severe_deficit_threshold=0.25,
        max_develop_adaptations=1,
        policy_version="fixture@1.0.0",
    )
