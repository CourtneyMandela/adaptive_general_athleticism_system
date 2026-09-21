from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from agas_domain import (
    Adaptation,
    CapabilityDomain,
    Confidence,
    ExposureNeed,
    ExposureNeedStatus,
    ExposureType,
    IntroductoryExposureDosePolicy,
)
from agas_planner import IntroductoryExposureDoseError, IntroductoryExposureDosePlanner
from pydantic import ValidationError

NOW = datetime(2026, 9, 20, 21, 0, tzinfo=UTC)
TARGET_SCOPE = "assessment:countermovement_vertical_jump:maximal"


def need(
    status: ExposureNeedStatus = ExposureNeedStatus.INTRODUCTORY_EXPOSURE_NEEDED,
) -> ExposureNeed:
    return ExposureNeed(
        athlete_id=uuid4(),
        exposure_type=ExposureType.JUMPING,
        target_scope=TARGET_SCOPE,
        status=status,
        lookback_days=28,
        minimum_exposure_days=2,
        source_observation_ids=(uuid4(),),
        confidence=Confidence.MODERATE,
        rationale="Synthetic unmet exposure prerequisite.",
        uncertainty="Software fixture only.",
        authority_reference="engineering-decision:0124@1.0.0",
        identified_at=NOW,
        valid_until=NOW + timedelta(hours=24),
        rule_version="fixture-exposure-need@1.0.0",
    )


def policy(adaptation_id: UUID) -> IntroductoryExposureDosePolicy:
    return IntroductoryExposureDosePolicy(
        adaptation_id=adaptation_id,
        exposure_type=ExposureType.JUMPING,
        target_scope=TARGET_SCOPE,
        dose_unit="repetitions",
        sets=2,
        dose_per_set=3,
        maximum_total_dose=6,
        rest_seconds=90,
        effort_rpe_minimum=2,
        effort_rpe_maximum=4,
        technique_constraints=("Use submaximal effort and land under control.",),
        planned_duration_minutes=6,
        progression_policy_id=uuid4(),
        evidence_claim_ids=(uuid4(),),
        numeric_value_origin="engineering_judgment",
        authority_reference="candidate:fixture-introductory-jump-dose@1.0.0",
        rationale="Synthetic conservative starting dose.",
        uncertainty="Exact values are engineering fixtures, not scientific thresholds.",
        policy_version="fixture-introductory-jump-dose@1.0.0",
    )


def test_introductory_exposure_dose_preserves_need_and_numeric_origin() -> None:
    adaptation = Adaptation(name="Landing exposure", domain=CapabilityDomain.DECELERATION)
    exposure_need = need()
    dose_policy = policy(adaptation.id)

    dose = IntroductoryExposureDosePlanner().derive(
        dose_id=uuid4(),
        need=exposure_need,
        adaptation=adaptation,
        policy=dose_policy,
        derived_at=NOW + timedelta(minutes=1),
    )

    assert dose.kind == "derived"
    assert dose.exposure_need_id == exposure_need.id
    assert dose.source_observation_ids == exposure_need.source_observation_ids
    assert dose.policy_id == dose_policy.id
    assert dose.total_dose == 6
    assert dose.numeric_value_origin == "engineering_judgment"
    assert dose.evidence_claim_ids == dose_policy.evidence_claim_ids
    assert dose.authority_reference == dose_policy.authority_reference


@pytest.mark.parametrize(
    "status",
    (ExposureNeedStatus.UNKNOWN, ExposureNeedStatus.RECENT_EXPOSURE_CONFIRMED),
)
def test_only_an_unmet_exposure_need_authorizes_a_starting_dose(
    status: ExposureNeedStatus,
) -> None:
    adaptation = Adaptation(name="Landing exposure", domain=CapabilityDomain.DECELERATION)
    with pytest.raises(IntroductoryExposureDoseError, match="does not authorize"):
        IntroductoryExposureDosePlanner().derive(
            dose_id=uuid4(),
            need=need(status),
            adaptation=adaptation,
            policy=policy(adaptation.id),
            derived_at=NOW + timedelta(minutes=1),
        )


def test_stale_or_scope_mismatched_exposure_need_fails_closed() -> None:
    adaptation = Adaptation(name="Landing exposure", domain=CapabilityDomain.DECELERATION)
    exposure_need = need()
    planner = IntroductoryExposureDosePlanner()
    with pytest.raises(IntroductoryExposureDoseError, match="stale"):
        planner.derive(
            dose_id=uuid4(),
            need=exposure_need,
            adaptation=adaptation,
            policy=policy(adaptation.id),
            derived_at=NOW + timedelta(days=2),
        )
    with pytest.raises(IntroductoryExposureDoseError, match="scope"):
        planner.derive(
            dose_id=uuid4(),
            need=exposure_need,
            adaptation=adaptation,
            policy=policy(adaptation.id).model_copy(update={"target_scope": "other"}),
            derived_at=NOW + timedelta(minutes=1),
        )


def test_policy_rejects_false_scientific_origin_and_dose_above_cap() -> None:
    adaptation_id = uuid4()
    values = policy(adaptation_id).model_dump()
    values.update(numeric_value_origin="scientific_evidence", evidence_claim_ids=())
    with pytest.raises(ValidationError, match="scientific numeric origin"):
        IntroductoryExposureDosePolicy.model_validate(values)

    values = policy(adaptation_id).model_dump()
    values.update(maximum_total_dose=5)
    with pytest.raises(ValidationError, match="exceeds the maximum"):
        IntroductoryExposureDosePolicy.model_validate(values)
