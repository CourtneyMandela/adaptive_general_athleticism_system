from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from agas_domain import (
    BlockPlan,
    BlockPlanStatus,
    BlockReviewPolicy,
    ComparisonDirection,
    Confidence,
    ResourceAllocation,
    ResponseEvaluationTarget,
    TrainingPriorityState,
    TrainingResponse,
)
from agas_planner import BlockReviewEngine

NOW = datetime(2026, 9, 1, 19, 30, tzinfo=UTC)


def _response(
    *,
    athlete_id: UUID,
    block_id: UUID,
    adaptation_id: UUID,
    item_count: int,
    adherence_ratio: float,
    dose_unit: str,
) -> TrainingResponse:
    return TrainingResponse(
        athlete_id=athlete_id,
        block_plan_id=block_id,
        adaptation_id=adaptation_id,
        intervention_summary="Dimensionally explicit software fixture.",
        prescription_ids=(uuid4(),),
        session_execution_ids=tuple(uuid4() for _ in range(item_count)),
        session_adherence_ids=tuple(uuid4() for _ in range(item_count)),
        prescribed_item_count=item_count,
        completed_item_count=item_count,
        prescribed_dose_total=100,
        actual_dose_total=100 * adherence_ratio,
        dose_unit=dose_unit,
        adherence_ratio=adherence_ratio,
        baseline_capability_estimate_id=uuid4(),
        followup_capability_estimate_id=uuid4(),
        baseline_value=10,
        followup_value=11,
        observed_change=1,
        measurement_uncertainty="Software fixture.",
        confidence=Confidence.MODERATE,
        source_observation_ids=(uuid4(),),
        calculated_at=NOW,
        calculation_method="software fixture",
        rule_version="fixture@1.0.0",
    )


def test_block_review_aggregates_dimensionless_adherence_across_dose_units() -> None:
    athlete_id = uuid4()
    adaptation_ids = (uuid4(), uuid4())
    allocations = tuple(
        ResourceAllocation(
            resource_demand_id=uuid4(),
            adaptation_priority_id=uuid4(),
            adaptation_id=adaptation_id,
            priority_state=TrainingPriorityState.DEVELOP,
            minimum_weekly_minutes=30,
            target_weekly_minutes=30,
            allocated_weekly_minutes=30,
            sessions_per_week=1,
            status=BlockPlanStatus.FULL,
        )
        for adaptation_id in adaptation_ids
    )
    starts_on = date(2026, 9, 7)
    evidence_id = uuid4()
    block = BlockPlan(
        athlete_id=athlete_id,
        long_range_strategy_id=uuid4(),
        resource_allocation_policy_id=uuid4(),
        starts_on=starts_on,
        ends_on=starts_on + timedelta(days=27),
        duration_weeks=4,
        weekly_budget_minutes=60,
        status=BlockPlanStatus.FULL,
        hypothesis="Exercise dimensionless delivery aggregation.",
        allocations=allocations,
        source_observation_ids=(uuid4(),),
        evidence_claim_ids=(evidence_id,),
        generated_at=NOW - timedelta(days=1),
        rule_version="fixture@1.0.0",
    )
    responses = (
        _response(
            athlete_id=athlete_id,
            block_id=block.id,
            adaptation_id=adaptation_ids[0],
            item_count=1,
            adherence_ratio=0.5,
            dose_unit="repetitions",
        ),
        _response(
            athlete_id=athlete_id,
            block_id=block.id,
            adaptation_id=adaptation_ids[1],
            item_count=3,
            adherence_ratio=1,
            dose_unit="seconds",
        ),
    )
    policy = BlockReviewPolicy(
        minimum_adherence_ratio=0,
        minimum_response_confidence=Confidence.LOW,
        evidence_claim_ids=(evidence_id,),
        rationale="Software fixture.",
        policy_version="fixture@1.0.0",
    )

    review = BlockReviewEngine().review(
        block=block,
        responses=responses,
        targets=tuple(
            ResponseEvaluationTarget(
                training_response_id=response.id,
                comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
                minimum_meaningful_change=0,
            )
            for response in responses
        ),
        safety_decisions=(),
        policy=policy,
        reviewed_at=NOW + timedelta(minutes=1),
    )

    assert review.prescribed_item_count == 4
    assert review.completed_item_count == 4
    assert review.aggregate_adherence_ratio == pytest.approx(0.875)
    assert review.rule_version.startswith("block-review@1.1.0")
