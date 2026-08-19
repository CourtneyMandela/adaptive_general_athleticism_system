from datetime import UTC, datetime

import pytest
from agas_domain import (
    AssessmentContext,
    AssessmentDefinition,
    AssessmentIntensity,
    AssessmentResultInput,
    Athlete,
    CapabilityDomain,
    CapabilityEstimationPolicy,
    Confidence,
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
    session.flush()
    context = AssessmentContext(
        athlete_id=athlete.id,
        source_observation_ids=(source.id,),
        health_screening_completed=True,
        available_equipment_categories=("cycle_ergometer",),
        evaluated_at=NOW,
    )
    selection = AdaptiveAssessmentSelector().select(context, (definition,))[0]
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
    definition = assessment()
    repository.add_athlete(first)
    repository.add_athlete(second)
    repository.add_observation(source)
    repository.add_assessment_definition(definition)
    session.flush()
    context = AssessmentContext(
        athlete_id=second.id,
        source_observation_ids=(source.id,),
        health_screening_completed=True,
        available_equipment_categories=("cycle_ergometer",),
        evaluated_at=NOW,
    )
    selection = AdaptiveAssessmentSelector().select(context, (definition,))[0]

    with pytest.raises(DomainIntegrityError, match="same athlete"):
        repository.add_assessment_selection(selection)
