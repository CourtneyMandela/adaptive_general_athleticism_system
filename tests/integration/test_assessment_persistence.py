from datetime import UTC, datetime, timedelta

import pytest
from agas_domain import (
    Applicability,
    AssessmentContext,
    AssessmentDefinition,
    AssessmentDefinitionReview,
    AssessmentEligibilityOutcome,
    AssessmentEligibilityReview,
    AssessmentIntensity,
    AssessmentResultInput,
    AssessmentReviewDecision,
    Athlete,
    CapabilityDomain,
    CapabilityEstimationPolicy,
    Confidence,
    EvidenceClaim,
    EvidenceSourceIdentifier,
    EvidenceStrength,
    Observation,
    ObservationSource,
    Provenance,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import (
    AdaptiveAssessmentSelector,
    AssessmentResultRecorder,
    ConservativeCapabilityEstimator,
)
from sqlalchemy.orm import Session

NOW = datetime(2026, 8, 19, 14, 0, tzinfo=UTC)


def intake(athlete: Athlete) -> Observation:
    return Observation(
        athlete_id=athlete.id,
        observed_at=NOW,
        observation_type="assessment_intake",
        measurement={"training_age_months": 18},
        source=ObservationSource.USER_REPORT,
        reliability=Confidence.LOW,
        provenance=Provenance(
            recorded_by="athlete",
            source_system="agas-web",
            ingestion_method="intake-form",
        ),
    )


def assessment() -> AssessmentDefinition:
    return AssessmentDefinition(
        slug="submax_cycle",
        name="Submaximal cycle",
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        observation_type="submax_cycle_result",
        intensity=AssessmentIntensity.MODERATE,
        unit_or_scale="w",
        protocol_version="submax-cycle@1.0.0",
        required_equipment_categories=("cycle_ergometer",),
    )


def approve(
    repository: DomainRepository, definition: AssessmentDefinition
) -> AssessmentDefinitionReview:
    evidence = EvidenceClaim(
        claim="Synthetic software fixture for assessment persistence tests.",
        domain="software_test_fixture",
        population="No athlete population; software fixture only.",
        intervention="No intervention.",
        outcome="Assessment persistence behavior.",
        study_design="software_test_fixture",
        uncertainty="Not scientific evidence and not operationally applicable.",
        evidence_strength=EvidenceStrength.INSUFFICIENT,
        athlete_applicability=Applicability.UNKNOWN,
        applicability_notes="Not applicable to athletes.",
        source_identifiers=(
            EvidenceSourceIdentifier(scheme="other", value="urn:agas:test:assessment-persistence"),
        ),
        reviewer="automated-test-fixture",
        claim_version="software-fixture@1.0.0",
    )
    review = AssessmentDefinitionReview(
        assessment_definition_id=definition.id,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=1,
        protocol_instructions=("Follow the isolated software-test fixture protocol.",),
        result_entry_instructions="Enter the synthetic fixture value.",
        recommended_reassessment_days=28,
        self_administered=True,
        evidence_claim_ids=(evidence.id,),
        reviewed_at=NOW,
        reviewer="automated-test-reviewer",
        applicability_notes="Software validation only; not applicable to an athlete.",
        uncertainty="This record does not approve a real assessment protocol.",
        review_version="assessment-review-fixture@1.0.0",
    )
    repository.add_evidence_claim(evidence)
    repository.add_assessment_definition_review(review)
    return review


def allow_selection(
    repository: DomainRepository, athlete: Athlete, source: Observation
) -> AssessmentEligibilityReview:
    review = AssessmentEligibilityReview(
        athlete_id=athlete.id,
        outcome=AssessmentEligibilityOutcome.SELECTION_ALLOWED,
        sequence_number=1,
        source_observation_ids=(source.id,),
        reviewed_at=NOW,
        valid_until=NOW + timedelta(days=7),
        reviewed_by="automated-test-reviewer",
        screening_process_reference="software-test-fixture@1.0.0",
        rationale="Software validation only; not an athlete screening decision.",
        uncertainty="This fixture has no operational applicability.",
        rule_version="assessment-eligibility-fixture@1.0.0",
    )
    repository.add_assessment_eligibility_review(review)
    return review


def test_assessment_definition_and_selection_round_trip_with_provenance(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Assessment athlete")
    source = intake(athlete)
    definition = assessment()
    repository.add_athlete(athlete)
    repository.add_observation(source)
    repository.add_assessment_definition(definition)
    approved_review = approve(repository, definition)
    eligibility = allow_selection(repository, athlete, source)
    session.flush()
    context = AssessmentContext(
        athlete_id=athlete.id,
        source_observation_ids=(source.id,),
        health_screening_completed=True,
        available_equipment_categories=("cycle_ergometer",),
        evaluated_at=NOW,
    )
    selection = AdaptiveAssessmentSelector().select_reviewed(
        context, ((definition, approved_review),), eligibility.id
    )[0]
    repository.add_assessment_selection(selection)
    result = AssessmentResultRecorder().record(
        definition,
        AssessmentResultInput(
            athlete_id=athlete.id,
            assessment_definition_id=definition.id,
            performed_at=NOW,
            measurement=180,
            unit="w",
            reliability=Confidence.MODERATE,
            context={"cadence_rpm": 75},
            provenance=Provenance(
                recorded_by="athlete",
                source_system="agas-web",
                ingestion_method="guided-assessment",
            ),
        ),
    )
    repository.add_observation(result)
    estimate = ConservativeCapabilityEstimator().estimate(
        CapabilityEstimationPolicy(
            domain=CapabilityDomain.AEROBIC_CAPACITY,
            observation_type=definition.observation_type,
            unit_or_scale="w",
            calculation_method="latest-matching-observation",
            valid_for_days=28,
            rule_version="latest-matching-observation@1.0.0",
        ),
        (result,),
        NOW,
    )
    repository.add_capability_estimate(estimate)
    session.commit()
    session.expire_all()

    assert repository.get_assessment_definition(definition.id) == definition
    assert repository.get_assessment_selection(selection.id) == selection
    assert repository.get_observation(result.id) == result
    assert repository.get_capability_estimate(estimate.id) == estimate


def test_selection_rejects_a_foreign_athlete_source_observation(session: Session) -> None:
    repository = DomainRepository(session)
    first = Athlete(display_name="First")
    second = Athlete(display_name="Second")
    source = intake(first)
    eligibility_source = intake(second)
    definition = assessment()
    repository.add_athlete(first)
    repository.add_athlete(second)
    repository.add_observation(source)
    repository.add_observation(eligibility_source)
    repository.add_assessment_definition(definition)
    approved_review = approve(repository, definition)
    eligibility = allow_selection(repository, second, eligibility_source)
    session.flush()
    context = AssessmentContext(
        athlete_id=second.id,
        source_observation_ids=(source.id,),
        health_screening_completed=True,
        available_equipment_categories=("cycle_ergometer",),
        evaluated_at=NOW,
    )
    selection = AdaptiveAssessmentSelector().select_reviewed(
        context, ((definition, approved_review),), eligibility.id
    )[0]

    with pytest.raises(DomainIntegrityError, match="same athlete"):
        repository.add_assessment_selection(selection)


def test_selection_rejects_an_unreviewed_assessment_definition(session: Session) -> None:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Unreviewed assessment athlete")
    source = intake(athlete)
    definition = assessment()
    repository.add_athlete(athlete)
    repository.add_observation(source)
    repository.add_assessment_definition(definition)
    session.flush()
    selection = AdaptiveAssessmentSelector().select(
        AssessmentContext(
            athlete_id=athlete.id,
            source_observation_ids=(source.id,),
            health_screening_completed=True,
            available_equipment_categories=("cycle_ergometer",),
            evaluated_at=NOW,
        ),
        (definition,),
    )[0]

    with pytest.raises(DomainIntegrityError, match="current approved"):
        repository.add_assessment_selection(selection)
