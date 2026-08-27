from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from agas_domain import (
    AssessmentContext,
    AssessmentDefinition,
    AssessmentDefinitionReview,
    AssessmentEligibilityOutcome,
    AssessmentEligibilityReview,
    AssessmentIntensity,
    AssessmentMeasurementSchema,
    AssessmentMeasurementType,
    AssessmentPerformance,
    AssessmentResultInput,
    AssessmentReviewDecision,
    AssessmentSelectionRun,
    CapabilityDomain,
    CapabilityEstimationPolicy,
    Confidence,
    Observation,
    ObservationSource,
    Provenance,
)
from agas_planner import (
    AdaptiveAssessmentSelector,
    AssessmentError,
    AssessmentReassessmentScheduler,
    AssessmentResultRecorder,
    ConservativeCapabilityEstimator,
)

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


def approved_review(
    assessment: AssessmentDefinition,
    *,
    reassessment_days: int = 28,
    sequence_number: int = 1,
    supersedes_review_id: UUID | None = None,
) -> AssessmentDefinitionReview:
    return AssessmentDefinitionReview(
        assessment_definition_id=assessment.id,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=sequence_number,
        supersedes_review_id=supersedes_review_id,
        protocol_instructions=("Follow the test-only fixture protocol.",),
        result_entry_instructions="Enter the observed fixture value.",
        recommended_reassessment_days=reassessment_days,
        self_administered=True,
        evidence_claim_ids=(uuid4(),),
        reviewed_at=NOW + timedelta(days=sequence_number - 1),
        reviewer="test-reviewer",
        applicability_notes="Software validation fixture only.",
        uncertainty="Not an operational assessment protocol.",
        review_version=f"assessment-review-test@{sequence_number}.0.0",
    )


def estimation_policy(
    *, valid_for_days: int = 42, multi_observation_window_days: int = 90
) -> CapabilityEstimationPolicy:
    assessment = definition()
    return CapabilityEstimationPolicy(
        assessment_definition_id=assessment.id,
        assessment_definition_review_id=uuid4(),
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=1,
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        observation_type="six_minute_walk_distance",
        unit_or_scale="m",
        calculation_method="latest-matching-observation",
        valid_for_days=valid_for_days,
        multi_observation_window_days=multi_observation_window_days,
        evidence_claim_ids=(uuid4(),),
        reviewed_at=NOW,
        reviewed_by="automated-test-reviewer",
        applicability_notes="Software validation only.",
        uncertainty="Not an operational estimation policy.",
        rule_version="latest-matching-observation@1.0.0",
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


def test_numeric_measurement_schema_enforces_type_range_and_step() -> None:
    schema = AssessmentMeasurementSchema(
        measurement_type=AssessmentMeasurementType.NUMBER,
        label="Synthetic test value",
        minimum=-1,
        maximum=10,
        step=0.5,
        measurement_schema_version="software-fixture@1.0.0",
    )

    schema.validate_measurement(7.5)
    schema.validate_measurement(-0.5)
    for unsupported in (True, "7.5", 7.3, -1.5, 10.5, 10**400):
        with pytest.raises(ValueError):
            schema.validate_measurement(unsupported)


def test_integer_and_category_measurement_schemas_are_explicit() -> None:
    integer_schema = AssessmentMeasurementSchema(
        measurement_type=AssessmentMeasurementType.INTEGER,
        label="Synthetic count",
        minimum=0,
        maximum=10,
        step=1,
        measurement_schema_version="software-integer-fixture@1.0.0",
    )
    category_schema = AssessmentMeasurementSchema(
        measurement_type=AssessmentMeasurementType.CATEGORY,
        label="Synthetic category",
        allowed_values=("first", "second"),
        measurement_schema_version="software-category-fixture@1.0.0",
    )

    integer_schema.validate_measurement(7)
    category_schema.validate_measurement("second")
    with pytest.raises(ValueError, match="integer"):
        integer_schema.validate_measurement(7.0)
    with pytest.raises(ValueError, match="allowed category"):
        category_schema.validate_measurement("third")


def test_measurement_schema_rejects_ambiguous_contracts() -> None:
    with pytest.raises(ValueError, match="allowed values"):
        AssessmentMeasurementSchema(
            measurement_type=AssessmentMeasurementType.CATEGORY,
            label="Synthetic category",
            measurement_schema_version="software-category-fixture@1.0.0",
        )
    with pytest.raises(ValueError, match="categorical values"):
        AssessmentMeasurementSchema(
            measurement_type=AssessmentMeasurementType.NUMBER,
            label="Synthetic numeric value",
            allowed_values=("one",),
            measurement_schema_version="software-number-fixture@1.0.0",
        )
    with pytest.raises(ValueError, match="whole numbers"):
        AssessmentMeasurementSchema(
            measurement_type=AssessmentMeasurementType.INTEGER,
            label="Synthetic count",
            step=0.5,
            measurement_schema_version="software-integer-fixture@1.0.0",
        )


def test_reviewed_selection_fails_closed_without_a_measurement_schema() -> None:
    assessment = definition()
    review = AssessmentDefinitionReview(
        assessment_definition_id=assessment.id,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=1,
        protocol_instructions=("Follow the test-only fixture protocol.",),
        result_entry_instructions="Enter the observed fixture value.",
        recommended_reassessment_days=28,
        self_administered=True,
        evidence_claim_ids=(uuid4(),),
        reviewed_at=NOW,
        reviewer="test-reviewer",
        applicability_notes="Software validation fixture only.",
        uncertainty="Not an operational assessment protocol.",
        review_version="assessment-review-test@1.0.0",
    )
    context = AssessmentContext(
        athlete_id=uuid4(),
        source_observation_ids=(uuid4(),),
        health_screening_completed=True,
        evaluated_at=NOW,
    )

    with pytest.raises(AssessmentError, match="no measurement schema"):
        AdaptiveAssessmentSelector().select_reviewed(context, ((assessment, review),), uuid4())


def test_unmeasured_protocol_is_immediately_due_for_assessment() -> None:
    assessment = definition()
    review = approved_review(assessment)

    schedule = AssessmentReassessmentScheduler().schedule(
        ((assessment, review),),
        (),
        {},
        NOW,
    )

    assert schedule.due_definition_ids == (assessment.id,)
    assert schedule.next_reassessment_at is None
    assert schedule.timings[0].interval_source_review_id == review.id


def test_reassessment_uses_latest_performance_and_its_exact_historical_interval() -> None:
    assessment = definition()
    historical_review = approved_review(assessment, reassessment_days=28)
    current_review = approved_review(
        assessment,
        reassessment_days=7,
        sequence_number=2,
        supersedes_review_id=historical_review.id,
    )
    athlete_id = uuid4()
    older = AssessmentPerformance(
        athlete_id=athlete_id,
        assessment_selection_run_id=uuid4(),
        assessment_selection_id=uuid4(),
        assessment_definition_id=assessment.id,
        assessment_definition_review_id=historical_review.id,
        assessment_eligibility_review_id=uuid4(),
        result_observation_id=uuid4(),
        performed_at=NOW - timedelta(days=10),
        rule_version="assessment-performance-test@1.0.0",
    )
    latest = older.model_copy(
        update={
            "id": uuid4(),
            "created_at": NOW,
            "assessment_selection_run_id": uuid4(),
            "assessment_selection_id": uuid4(),
            "result_observation_id": uuid4(),
            "performed_at": NOW,
        }
    )
    scheduler = AssessmentReassessmentScheduler()

    early = scheduler.schedule(
        ((assessment, current_review),),
        (older, latest),
        {historical_review.id: historical_review},
        NOW + timedelta(days=27),
    )
    due = scheduler.schedule(
        ((assessment, current_review),),
        (latest, older),
        {historical_review.id: historical_review},
        NOW + timedelta(days=28),
    )

    assert early.due_definition_ids == ()
    assert early.next_reassessment_at == NOW + timedelta(days=28)
    assert early.timings[0].latest_performance_id == latest.id
    assert early.timings[0].interval_source_review_id == historical_review.id
    assert due.due_definition_ids == (assessment.id,)


def test_reassessment_rejects_missing_historical_interval_authority() -> None:
    assessment = definition()
    review = approved_review(assessment)
    performance = AssessmentPerformance(
        athlete_id=uuid4(),
        assessment_selection_run_id=uuid4(),
        assessment_selection_id=uuid4(),
        assessment_definition_id=assessment.id,
        assessment_definition_review_id=review.id,
        assessment_eligibility_review_id=uuid4(),
        result_observation_id=uuid4(),
        performed_at=NOW,
        rule_version="assessment-performance-test@1.0.0",
    )

    with pytest.raises(AssessmentError, match="interval-source review"):
        AssessmentReassessmentScheduler().schedule(
            ((assessment, review),),
            (performance,),
            {},
            NOW + timedelta(days=28),
        )


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
    policy = estimation_policy()

    estimate = ConservativeCapabilityEstimator().estimate(policy, reversed(observations), NOW)

    assert estimate.kind == "derived"
    assert estimate.estimate == 612
    assert estimate.estimate_scope == "assessment_specific:six_minute_walk_distance"
    assert estimate.confidence is Confidence.MODERATE
    assert estimate.source_observation_ids == tuple(item.id for item in observations)


def test_estimator_rejects_absent_matching_observations() -> None:
    policy = estimation_policy()

    with pytest.raises(AssessmentError, match="no matching observations"):
        ConservativeCapabilityEstimator().estimate(policy, (), NOW)


def test_estimator_rejects_an_observation_that_is_inside_the_window_but_stale() -> None:
    policy = estimation_policy(valid_for_days=7)
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


def test_assessment_eligibility_is_time_bounded_and_predecessor_linked() -> None:
    with pytest.raises(ValueError, match="later than reviewed_at"):
        AssessmentEligibilityReview(
            athlete_id=uuid4(),
            outcome=AssessmentEligibilityOutcome.SELECTION_ALLOWED,
            sequence_number=1,
            source_observation_ids=(uuid4(),),
            reviewed_at=NOW,
            valid_until=NOW,
            reviewed_by="test-reviewer",
            screening_process_reference="test-process@1.0.0",
            rationale="Software fixture only.",
            uncertainty="Not operational.",
            rule_version="test-eligibility@1.0.0",
        )

    with pytest.raises(ValueError, match="reference their predecessor"):
        AssessmentEligibilityReview(
            athlete_id=uuid4(),
            outcome=AssessmentEligibilityOutcome.REVIEW_REQUIRED,
            sequence_number=2,
            source_observation_ids=(uuid4(),),
            reviewed_at=NOW,
            valid_until=NOW + timedelta(days=1),
            reviewed_by="test-reviewer",
            screening_process_reference="test-process@1.0.0",
            rationale="Software fixture only.",
            uncertainty="Not operational.",
            rule_version="test-eligibility@1.0.0",
        )


def test_assessment_selection_run_requires_unique_decisions() -> None:
    selection_id = uuid4()
    with pytest.raises(ValueError, match="selection_ids"):
        AssessmentSelectionRun(
            athlete_id=uuid4(),
            assessment_eligibility_review_id=uuid4(),
            environment_id=uuid4(),
            context_observation_id=uuid4(),
            selection_ids=(selection_id, selection_id),
            evaluated_at=NOW,
            rule_version="assessment-selection-run-test@1.0.0",
        )
