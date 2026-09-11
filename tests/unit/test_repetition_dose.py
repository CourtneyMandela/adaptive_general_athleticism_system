from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from agas_domain import (
    Adaptation,
    CapabilityDomain,
    CapabilityEstimate,
    Confidence,
    PrescriptionAdjustment,
    ProgressionDimension,
    RepetitionDosePolicy,
)
from agas_planner import RepetitionDoseError, RepetitionDosePlanner

NOW = datetime(2026, 9, 11, 11, 0, tzinfo=UTC)
SCOPE = "assessment_specific:thirty_second_chair_stand_repetitions"


def inputs(*, value: object = 11) -> tuple[Adaptation, CapabilityEstimate, RepetitionDosePolicy]:
    adaptation = Adaptation(
        name="Fixture lower-body repetition capacity",
        domain=CapabilityDomain.MUSCULAR_ENDURANCE,
    )
    estimate = CapabilityEstimate(
        athlete_id=uuid4(),
        domain=CapabilityDomain.MUSCULAR_ENDURANCE,
        estimate=value,
        unit_or_scale="repetitions",
        estimate_scope=SCOPE,
        confidence=Confidence.MODERATE,
        calculation_method="fixture-latest-observation",
        source_observation_ids=(uuid4(),),
        estimated_at=NOW - timedelta(days=1),
        valid_until=NOW + timedelta(days=29),
        rule_version="fixture-estimate@1.0.0",
    )
    policy = RepetitionDosePolicy(
        adaptation_id=adaptation.id,
        estimate_scope=SCOPE,
        unit_or_scale="repetitions",
        minimum_eligible_estimate=1,
        target_fraction_of_estimate=0.5,
        sets=2,
        minimum_repetitions_per_set=1,
        maximum_repetitions_per_set=8,
        rest_seconds=90,
        effort_rpe_minimum=5,
        effort_rpe_maximum=7,
        technique_constraints=("Use the reviewed chair-stand technique.",),
        planned_duration_minutes=5,
        progression_policy_id=uuid4(),
        evidence_claim_ids=(uuid4(),),
        rationale="Fixture deterministic rule.",
        uncertainty="Fixture constants are not evidence claims.",
        policy_version="fixture-chair-stand-dose@1.0.0",
    )
    return adaptation, estimate, policy


def test_dose_is_derived_from_estimate_with_floor_rounding_and_provenance() -> None:
    adaptation, estimate, policy = inputs(value=11)

    result = RepetitionDosePlanner().derive(
        adaptation=adaptation,
        estimate=estimate,
        policy=policy,
        derived_at=NOW,
    )

    assert result.sets == 2
    assert result.repetitions_per_set == 5
    assert result.capability_estimate_id == estimate.id
    assert result.repetition_dose_policy_id == policy.id
    assert result.progression_policy_id == policy.progression_policy_id
    assert result.rule_version == policy.policy_version


@pytest.mark.parametrize(("estimate_value", "expected"), [(1, 1), (16, 8), (40, 8)])
def test_dose_is_bounded_by_reviewed_policy(estimate_value: int, expected: int) -> None:
    adaptation, estimate, policy = inputs(value=estimate_value)

    result = RepetitionDosePlanner().derive(
        adaptation=adaptation,
        estimate=estimate,
        policy=policy,
        derived_at=NOW,
    )

    assert result.repetitions_per_set == expected


def test_dose_rejects_stale_incomparable_or_non_numeric_estimates() -> None:
    adaptation, estimate, policy = inputs()
    planner = RepetitionDosePlanner()

    with pytest.raises(RepetitionDoseError, match="stale"):
        planner.derive(
            adaptation=adaptation,
            estimate=estimate.model_copy(update={"valid_until": NOW}),
            policy=policy,
            derived_at=NOW,
        )
    with pytest.raises(RepetitionDoseError, match="scope"):
        planner.derive(
            adaptation=adaptation,
            estimate=estimate.model_copy(update={"estimate_scope": "assessment_specific:other"}),
            policy=policy,
            derived_at=NOW,
        )
    with pytest.raises(RepetitionDoseError, match="finite numeric"):
        planner.derive(
            adaptation=adaptation,
            estimate=estimate.model_copy(update={"estimate": "eleven"}),
            policy=policy,
            derived_at=NOW,
        )


def test_dose_policy_does_not_embed_an_adjustment_without_a_progression_authority() -> None:
    _, _, policy = inputs()

    assert policy.progression_policy_id is not None
    assert not hasattr(policy, "adjustment")
    assert PrescriptionAdjustment(
        dimension=ProgressionDimension.REPETITIONS,
        amount=1,
        unit="repetitions_per_set",
        description="Owned by the separately versioned progression policy.",
    )
