from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from agas_domain import (
    AssessmentDefinition,
    AssessmentIntensity,
    AssessmentResultInput,
    CapabilityDomain,
    CapabilityEstimationPolicy,
    Confidence,
    Observation,
    ObservationSource,
    Provenance,
)
from agas_planner import AssessmentError, AssessmentResultRecorder, ConservativeCapabilityEstimator

NOW = datetime(2026, 8, 19, 14, 0, tzinfo=UTC)


def definition() -> AssessmentDefinition:
    return AssessmentDefinition(
        slug="six_minute_walk",
        name="Six-minute walk",
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        observation_type="six_minute_walk_distance",
        intensity=AssessmentIntensity.MODERATE,
        unit_or_scale="m",
        protocol_version="six-minute-walk@1.0.0",
    )


def provenance() -> Provenance:
    return Provenance(
        recorded_by="athlete",
        source_system="agas-web",
        ingestion_method="guided-assessment",
    )


def test_result_recorder_creates_a_direct_observation_with_protocol_provenance() -> None:
    assessment = definition()
    result = AssessmentResultInput(
        athlete_id=uuid4(),
        assessment_definition_id=assessment.id,
        performed_at=NOW,
        measurement=612,
        unit="m",
        reliability=Confidence.MODERATE,
        context={"surface": "track"},
        provenance=provenance(),
    )

    observation = AssessmentResultRecorder().record(assessment, result)

    assert observation.source is ObservationSource.TEST_RESULT
    assert observation.measurement == 612
    assert observation.context["protocol_version"] == "six-minute-walk@1.0.0"
    assert observation.provenance == result.provenance


def test_estimator_is_assessment_specific_and_preserves_ordered_sources() -> None:
    athlete_id = uuid4()
    observations = tuple(
        Observation(
            athlete_id=athlete_id,
            observed_at=NOW + timedelta(days=offset),
            observation_type="six_minute_walk_distance",
            measurement=value,
            unit="m",
            source=ObservationSource.TEST_RESULT,
            reliability=Confidence.MODERATE,
            provenance=provenance(),
        )
        for offset, value in ((-14, 580), (-1, 612))
    )
    policy = CapabilityEstimationPolicy(
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        observation_type="six_minute_walk_distance",
        unit_or_scale="m",
        calculation_method="latest-matching-observation",
        valid_for_days=42,
        rule_version="latest-matching-observation@1.0.0",
    )

    estimate = ConservativeCapabilityEstimator().estimate(policy, reversed(observations), NOW)

    assert estimate.kind == "derived"
    assert estimate.estimate == 612
    assert estimate.estimate_scope == "assessment_specific:six_minute_walk_distance"
    assert estimate.confidence is Confidence.MODERATE
    assert estimate.source_observation_ids == tuple(item.id for item in observations)


def test_estimator_rejects_absent_matching_observations() -> None:
    policy = CapabilityEstimationPolicy(
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        observation_type="six_minute_walk_distance",
        unit_or_scale="m",
        calculation_method="latest-matching-observation",
        valid_for_days=42,
        rule_version="latest-matching-observation@1.0.0",
    )

    with pytest.raises(AssessmentError, match="no matching observations"):
        ConservativeCapabilityEstimator().estimate(policy, (), NOW)


def test_estimator_rejects_an_observation_that_is_inside_the_window_but_stale() -> None:
    policy = CapabilityEstimationPolicy(
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        observation_type="six_minute_walk_distance",
        unit_or_scale="m",
        calculation_method="latest-matching-observation",
        valid_for_days=7,
        multi_observation_window_days=90,
        rule_version="latest-matching-observation@1.0.0",
    )
    stale = Observation(
        athlete_id=uuid4(),
        observed_at=NOW - timedelta(days=8),
        observation_type="six_minute_walk_distance",
        measurement=580,
        unit="m",
        source=ObservationSource.TEST_RESULT,
        reliability=Confidence.MODERATE,
        provenance=provenance(),
    )

    with pytest.raises(AssessmentError, match="stale"):
        ConservativeCapabilityEstimator().estimate(policy, (stale,), NOW)
