from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from agas_domain import (
    AssessmentDefinition,
    AssessmentDefinitionReview,
    AssessmentIntensity,
    AssessmentResultInput,
    AssessmentReviewDecision,
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


def test_approved_assessment_review_requires_an_explicit_reassessment_interval() -> None:
    with pytest.raises(ValueError, match="reassessment interval"):
        AssessmentDefinitionReview(
            assessment_definition_id=definition().id,
            decision=AssessmentReviewDecision.APPROVED,
            sequence_number=1,
            protocol_instructions=("Follow the test-only fixture protocol.",),
            result_entry_instructions="Enter the observed fixture value.",
            evidence_claim_ids=(uuid4(),),
            reviewed_at=NOW,
            reviewer="test-reviewer",
            applicability_notes="Software validation fixture only.",
            uncertainty="Not an operational assessment protocol.",
            review_version="assessment-review-test@1.0.0",
        )


def test_assessment_review_requires_linear_history_and_unique_provenance() -> None:
    definition_id = definition().id
    evidence_id = uuid4()

    with pytest.raises(ValueError, match="reference their predecessor"):
        AssessmentDefinitionReview(
            assessment_definition_id=definition_id,
            decision=AssessmentReviewDecision.NEEDS_REVISION,
            sequence_number=2,
            protocol_instructions=("Review this test-only fixture protocol.",),
            result_entry_instructions="Enter the fixture value.",
            evidence_claim_ids=(evidence_id,),
            reviewed_at=NOW,
            reviewer="test-reviewer",
            applicability_notes="Software validation fixture only.",
            uncertainty="Not an operational assessment protocol.",
            review_version="assessment-review-test@1.0.0",
        )

    with pytest.raises(ValueError, match="evidence_claim_ids"):
        AssessmentDefinitionReview(
            assessment_definition_id=definition_id,
            decision=AssessmentReviewDecision.NEEDS_REVISION,
            sequence_number=1,
            protocol_instructions=("Review this test-only fixture protocol.",),
            result_entry_instructions="Enter the fixture value.",
            evidence_claim_ids=(evidence_id, evidence_id),
            reviewed_at=NOW,
            reviewer="test-reviewer",
            applicability_notes="Software validation fixture only.",
            uncertainty="Not an operational assessment protocol.",
            review_version="assessment-review-test@1.0.0",
        )
