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
    FixedRepetitionDosePolicy,
    PlanningReason,
    TrainingPriorityState,
)
from agas_planner import FixedRepetitionDoseError, FixedRepetitionDosePlanner
from pydantic import ValidationError

NOW = datetime(2026, 9, 23, 16, 0, tzinfo=UTC)
SCOPE = "assessment_specific:countermovement_vertical_jump_height_cm"


def inputs(
    *, estimate_value: float = 32.5
) -> tuple[
    Adaptation,
    AdaptationPriority,
    CapabilityNeed,
    CapabilityEstimate,
    FixedRepetitionDosePolicy,
]:
    athlete_id = uuid4()
    observation_id = uuid4()
    claim_id = uuid4()
    adaptation = Adaptation(
        name="Fixture explosive power",
        domain=CapabilityDomain.EXPLOSIVE_POWER,
        evidence_claim_ids=(claim_id,),
    )
    estimate = CapabilityEstimate(
        athlete_id=athlete_id,
        domain=CapabilityDomain.EXPLOSIVE_POWER,
        estimate=estimate_value,
        unit_or_scale="cm",
        estimate_scope=SCOPE,
        confidence=Confidence.LOW,
        calculation_method="fixture direct jump-height observation",
        source_observation_ids=(observation_id,),
        estimated_at=NOW - timedelta(days=1),
        valid_until=NOW + timedelta(days=27),
        rule_version="fixture-jump-estimate@1.0.0",
    )
    need = CapabilityNeed(
        athlete_id=athlete_id,
        domain=CapabilityDomain.EXPLOSIVE_POWER,
        competency_floor_id=uuid4(),
        capability_estimate_id=estimate.id,
        status=CompetencyStatus.BELOW_FLOOR,
        observed_value=estimate_value,
        floor_value=35,
        unit_or_scale="cm",
        gap_from_floor=35 - estimate_value,
        normalized_deficit=(35 - estimate_value) / 35,
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
    policy = FixedRepetitionDosePolicy(
        adaptation_id=adaptation.id,
        estimate_scope=SCOPE,
        sets=3,
        repetitions_per_set=3,
        maximum_initial_total_repetitions=9,
        rest_seconds=120,
        effort_rpe_minimum=4,
        effort_rpe_maximum=6,
        technique_constraints=("Reset fully before each repetition.",),
        planned_duration_minutes=12,
        progression_policy_id=uuid4(),
        evidence_claim_ids=(),
        numeric_value_origin="engineering_judgment",
        authority_reference="fixture-fixed-dose-authority@1.0.0",
        rationale="Synthetic fixed starting dose.",
        uncertainty="The fixture values are not scientific findings.",
        policy_version="fixture-fixed-jump-dose@1.0.0",
    )
    return adaptation, priority, need, estimate, policy


def test_fixed_dose_preserves_develop_lineage_without_using_jump_height_as_repetitions() -> None:
    adaptation, priority, need, estimate, policy = inputs(estimate_value=32.5)

    result = FixedRepetitionDosePlanner().derive(
        adaptation=adaptation,
        priority=priority,
        need=need,
        estimate=estimate,
        policy=policy,
        derived_at=NOW,
    )

    assert result.sets == 3
    assert result.repetitions_per_set == 3
    assert result.capability_estimate_id == estimate.id
    assert result.capability_need_id == need.id
    assert result.adaptation_priority_id == priority.id
    assert result.source_observation_ids == estimate.source_observation_ids
    assert result.numeric_value_origin == "engineering_judgment"
    assert "estimate value not used as dose arithmetic" in result.calculation_method


def test_fixed_dose_is_invariant_to_the_numeric_estimate_when_lineage_is_otherwise_valid() -> None:
    first = inputs(estimate_value=32.5)
    second = inputs(estimate_value=20)

    first_result = FixedRepetitionDosePlanner().derive(
        adaptation=first[0],
        priority=first[1],
        need=first[2],
        estimate=first[3],
        policy=first[4],
        derived_at=NOW,
    )
    second_result = FixedRepetitionDosePlanner().derive(
        adaptation=second[0],
        priority=second[1],
        need=second[2],
        estimate=second[3],
        policy=second[4],
        derived_at=NOW,
    )

    assert (first_result.sets, first_result.repetitions_per_set) == (3, 3)
    assert (second_result.sets, second_result.repetitions_per_set) == (3, 3)


def test_fixed_dose_supports_a_distinct_maintain_authority_at_or_above_floor() -> None:
    adaptation, priority, need, estimate, policy = inputs()
    estimate = estimate.model_copy(update={"estimate": 37})
    maintain_priority = priority.model_copy(
        update={"state": TrainingPriorityState.MAINTAIN, "development_allocation": 0}
    )
    maintained_need = need.model_copy(
        update={
            "status": CompetencyStatus.MEETS_FLOOR,
            "observed_value": 37,
            "gap_from_floor": None,
            "normalized_deficit": None,
        }
    )
    maintenance_policy = policy.model_copy(
        update={
            "priority_state": TrainingPriorityState.MAINTAIN,
            "sets": 2,
            "repetitions_per_set": 3,
            "maximum_initial_total_repetitions": 6,
            "planned_duration_minutes": 6,
            "policy_version": "fixture-fixed-jump-maintenance-dose@1.0.0",
        }
    )

    result = FixedRepetitionDosePlanner().derive(
        adaptation=adaptation,
        priority=maintain_priority,
        need=maintained_need,
        estimate=estimate,
        policy=maintenance_policy,
        derived_at=NOW,
    )

    assert result.sets == 2
    assert result.repetitions_per_set == 3
    assert result.capability_need_id == maintained_need.id
    assert result.adaptation_priority_id == maintain_priority.id


def test_fixed_dose_rejects_state_or_need_status_outside_policy_scope() -> None:
    adaptation, priority, need, estimate, policy = inputs()
    maintenance_policy = policy.model_copy(
        update={"priority_state": TrainingPriorityState.MAINTAIN}
    )
    maintain_priority = priority.model_copy(
        update={"state": TrainingPriorityState.MAINTAIN, "development_allocation": 0}
    )

    with pytest.raises(FixedRepetitionDoseError, match="MAINTAIN"):
        FixedRepetitionDosePlanner().derive(
            adaptation=adaptation,
            priority=priority,
            need=need,
            estimate=estimate,
            policy=maintenance_policy,
            derived_at=NOW,
        )
    with pytest.raises(FixedRepetitionDoseError, match="at-or-above-floor"):
        FixedRepetitionDosePlanner().derive(
            adaptation=adaptation,
            priority=maintain_priority,
            need=need,
            estimate=estimate,
            policy=maintenance_policy,
            derived_at=NOW,
        )


def test_fixed_dose_rejects_non_develop_non_deficit_stale_or_cross_scope_lineage() -> None:
    adaptation, priority, need, estimate, policy = inputs()
    planner = FixedRepetitionDosePlanner()

    with pytest.raises(FixedRepetitionDoseError, match="DEVELOP"):
        planner.derive(
            adaptation=adaptation,
            priority=priority.model_copy(
                update={
                    "state": TrainingPriorityState.MAINTAIN,
                    "development_allocation": 0,
                }
            ),
            need=need,
            estimate=estimate,
            policy=policy,
            derived_at=NOW,
        )
    with pytest.raises(FixedRepetitionDoseError, match="below-floor"):
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
    with pytest.raises(FixedRepetitionDoseError, match="stale"):
        planner.derive(
            adaptation=adaptation,
            priority=priority,
            need=need,
            estimate=estimate.model_copy(update={"valid_until": NOW}),
            policy=policy,
            derived_at=NOW,
        )
    with pytest.raises(FixedRepetitionDoseError, match="scope"):
        planner.derive(
            adaptation=adaptation,
            priority=priority,
            need=need,
            estimate=estimate,
            policy=policy.model_copy(update={"estimate_scope": "assessment_specific:other"}),
            derived_at=NOW,
        )


def test_fixed_policy_labels_numeric_authority_and_enforces_initial_cap() -> None:
    _, _, _, _, policy = inputs()
    assert policy.priority_state is TrainingPriorityState.DEVELOP
    invalid_cap = policy.model_dump()
    invalid_cap["maximum_initial_total_repetitions"] = 8
    with pytest.raises(ValidationError, match="maximum initial total"):
        FixedRepetitionDosePolicy.model_validate(invalid_cap)

    unsupported_scientific = policy.model_dump()
    unsupported_scientific["numeric_value_origin"] = "scientific_evidence"
    with pytest.raises(ValidationError, match="scientific numeric origin"):
        FixedRepetitionDosePolicy.model_validate(unsupported_scientific)
