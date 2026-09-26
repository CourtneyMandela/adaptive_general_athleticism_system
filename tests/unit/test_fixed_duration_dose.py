from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from agas_domain import (
    Adaptation,
    AdaptationPriority,
    CapabilityDomain,
    CapabilityEstimate,
    CapabilityNeed,
    CompetencyStatus,
    Confidence,
    FixedDurationDosePolicy,
    PlanningReason,
    TrainingPriorityState,
)
from agas_planner import FixedDurationDoseError, FixedDurationDosePlanner
from pydantic import ValidationError

NOW = datetime(2026, 9, 25, 8, 0, tzinfo=UTC)
SCOPE = "assessment_specific:aerobic_field_distance_m"


def inputs(
    *, estimate_value: float = 1500
) -> tuple[
    Adaptation,
    AdaptationPriority,
    CapabilityNeed,
    CapabilityEstimate,
    FixedDurationDosePolicy,
]:
    athlete_id = uuid4()
    observation_id = uuid4()
    claim_id = uuid4()
    adaptation = Adaptation(
        name="Fixture aerobic base",
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        evidence_claim_ids=(claim_id,),
    )
    estimate = CapabilityEstimate(
        athlete_id=athlete_id,
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        estimate=estimate_value,
        unit_or_scale="m",
        estimate_scope=SCOPE,
        confidence=Confidence.LOW,
        calculation_method="fixture direct field-distance observation",
        source_observation_ids=(observation_id,),
        estimated_at=NOW - timedelta(days=1),
        valid_until=NOW + timedelta(days=27),
        rule_version="fixture-aerobic-estimate@1.0.0",
    )
    need = CapabilityNeed(
        athlete_id=athlete_id,
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        competency_floor_id=uuid4(),
        capability_estimate_id=estimate.id,
        status=CompetencyStatus.BELOW_FLOOR,
        observed_value=estimate_value,
        floor_value=1600,
        unit_or_scale="m",
        gap_from_floor=1600 - estimate_value,
        normalized_deficit=(1600 - estimate_value) / 1600,
        confidence=Confidence.LOW,
        rationale="Synthetic below-floor fixture.",
        evidence_claim_ids=(claim_id,),
        identified_at=NOW - timedelta(hours=12),
        rule_version="fixture-need@1.0.0",
    )
    priority = AdaptationPriority(
        adaptation_id=adaptation.id,
        capability_need_id=need.id,
        state=TrainingPriorityState.DEVELOP,
        score=1,
        rank=1,
        development_allocation=1,
        score_components={"deficit": 1},
        reason_codes=(PlanningReason.COMPETENCY_DEFICIT,),
        rationale=("The governed need is below its floor.",),
    )
    policy = FixedDurationDosePolicy(
        adaptation_id=adaptation.id,
        estimate_scope=SCOPE,
        sets=1,
        duration_seconds_per_set=600,
        maximum_initial_total_duration_seconds=600,
        rest_seconds=0,
        effort_rpe_minimum=3,
        effort_rpe_maximum=5,
        technique_constraints=("Maintain continuous controlled cyclic work.",),
        planned_duration_minutes=10,
        progression_policy_id=uuid4(),
        evidence_claim_ids=(),
        numeric_value_origin="engineering_judgment",
        authority_reference="fixture-duration-authority@1.0.0",
        rationale="Synthetic fixed starting duration.",
        uncertainty="The fixture values are not scientific findings.",
        policy_version="fixture-fixed-duration@1.0.0",
    )
    return adaptation, priority, need, estimate, policy


def test_fixed_duration_preserves_lineage_without_converting_distance_to_seconds() -> None:
    adaptation, priority, need, estimate, policy = inputs(estimate_value=1500)

    result = FixedDurationDosePlanner().derive(
        adaptation=adaptation,
        priority=priority,
        need=need,
        estimate=estimate,
        policy=policy,
        derived_at=NOW,
    )

    assert result.sets == 1
    assert result.duration_seconds_per_set == 600
    assert result.capability_estimate_id == estimate.id
    assert result.capability_need_id == need.id
    assert result.source_observation_ids == estimate.source_observation_ids
    assert result.numeric_value_origin == "engineering_judgment"
    assert "estimate value not used as dose arithmetic" in result.calculation_method


def test_fixed_duration_is_invariant_to_numeric_estimate() -> None:
    first = inputs(estimate_value=1500)
    second = inputs(estimate_value=900)

    results = [
        FixedDurationDosePlanner().derive(
            adaptation=item[0],
            priority=item[1],
            need=item[2],
            estimate=item[3],
            policy=item[4],
            derived_at=NOW,
        )
        for item in (first, second)
    ]

    assert [item.duration_seconds_per_set for item in results] == [600, 600]


def test_fixed_duration_supports_distinct_maintenance_authority() -> None:
    adaptation, priority, need, estimate, policy = inputs()
    maintained_need = need.model_copy(
        update={
            "status": CompetencyStatus.MEETS_FLOOR,
            "observed_value": 1700,
            "gap_from_floor": None,
            "normalized_deficit": None,
        }
    )
    result = FixedDurationDosePlanner().derive(
        adaptation=adaptation,
        priority=priority.model_copy(
            update={"state": TrainingPriorityState.MAINTAIN, "development_allocation": 0}
        ),
        need=maintained_need,
        estimate=estimate.model_copy(update={"estimate": 1700}),
        policy=policy.model_copy(
            update={
                "priority_state": TrainingPriorityState.MAINTAIN,
                "duration_seconds_per_set": 480,
                "maximum_initial_total_duration_seconds": 480,
            }
        ),
        derived_at=NOW,
    )

    assert result.duration_seconds_per_set == 480


def test_fixed_duration_rejects_stale_cross_scope_or_wrong_need_lineage() -> None:
    adaptation, priority, need, estimate, policy = inputs()
    planner = FixedDurationDosePlanner()

    with pytest.raises(FixedDurationDoseError, match="below-floor"):
        planner.derive(
            adaptation=adaptation,
            priority=priority,
            need=need.model_copy(
                update={
                    "status": CompetencyStatus.MEETS_FLOOR,
                    "gap_from_floor": None,
                    "normalized_deficit": None,
                }
            ),
            estimate=estimate,
            policy=policy,
            derived_at=NOW,
        )
    with pytest.raises(FixedDurationDoseError, match="stale"):
        planner.derive(
            adaptation=adaptation,
            priority=priority,
            need=need,
            estimate=estimate.model_copy(update={"valid_until": NOW}),
            policy=policy,
            derived_at=NOW,
        )
    with pytest.raises(FixedDurationDoseError, match="scope"):
        planner.derive(
            adaptation=adaptation,
            priority=priority,
            need=need,
            estimate=estimate,
            policy=policy.model_copy(update={"estimate_scope": "assessment_specific:other"}),
            derived_at=NOW,
        )


def test_fixed_duration_policy_labels_numeric_authority_and_enforces_cap() -> None:
    _, _, _, _, policy = inputs()
    invalid_cap = policy.model_dump()
    invalid_cap["maximum_initial_total_duration_seconds"] = 599
    with pytest.raises(ValidationError, match="maximum initial total"):
        FixedDurationDosePolicy.model_validate(invalid_cap)

    invalid_envelope = policy.model_dump()
    invalid_envelope["planned_duration_minutes"] = 9
    with pytest.raises(ValidationError, match="planned session envelope"):
        FixedDurationDosePolicy.model_validate(invalid_envelope)

    unsupported_scientific = policy.model_dump()
    unsupported_scientific["numeric_value_origin"] = "scientific_evidence"
    with pytest.raises(ValidationError, match="scientific numeric origin"):
        FixedDurationDosePolicy.model_validate(unsupported_scientific)
