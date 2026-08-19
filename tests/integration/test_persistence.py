from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from agas_domain import (
    Adaptation,
    AdaptationRelationship,
    AdaptationRelationshipType,
    Applicability,
    Athlete,
    CapabilityDomain,
    CapabilityEstimate,
    Confidence,
    CostLevel,
    Environment,
    Equipment,
    EquipmentAvailability,
    EvidenceClaim,
    EvidenceSourceIdentifier,
    EvidenceStrength,
    Exercise,
    ImpactLevel,
    Loadability,
    Observation,
    ObservationSource,
    Provenance,
)
from agas_domain.persistence.models import (
    AthleteRecord,
    CapabilityEstimateRecord,
    ImmutableHistoricalRecordError,
    ObservationRecord,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from sqlalchemy import func, select
from sqlalchemy.orm import Session

NOW = datetime(2026, 8, 19, 14, 0, tzinfo=UTC)


def make_observation(athlete_id: UUID, *, offset_days: int = 0) -> Observation:
    return Observation(
        athlete_id=athlete_id,
        observed_at=NOW + timedelta(days=offset_days),
        observation_type="six_minute_walk",
        measurement={"distance": 612, "surface": "track"},
        unit="m",
        source=ObservationSource.TEST_RESULT,
        reliability=Confidence.MODERATE,
        context={"temperature_c": 19, "protocol": "field-test-v1"},
        provenance=Provenance(
            recorded_by="athlete",
            source_system="agas-web",
            ingestion_method="guided-test",
            external_reference=f"test-{offset_days}",
            raw_record_hash="sha256:example",
        ),
    )


def make_evidence_claim() -> EvidenceClaim:
    return EvidenceClaim(
        claim="Verified placeholder claim used only to test persistence semantics.",
        domain="software_test",
        population="not applicable",
        intervention="not applicable",
        outcome="provenance survives persistence",
        study_design="test fixture",
        uncertainty="This is not a scientific training claim.",
        limitations=("Fixture only",),
        evidence_strength=EvidenceStrength.INSUFFICIENT,
        athlete_applicability=Applicability.UNKNOWN,
        applicability_notes="Not applicable to an athlete.",
        source_identifiers=(EvidenceSourceIdentifier(scheme="other", value="fixture:1"),),
        reviewer="automated-test",
        claim_version="fixture@1.0.0",
    )


def test_round_trip_preserves_observation_and_estimate_provenance(session: Session) -> None:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Round trip athlete", goals=("hiking",))
    repository.add_athlete(athlete)
    observation = make_observation(athlete.id)
    second_observation = make_observation(athlete.id, offset_days=1)
    repository.add_observation(observation)
    repository.add_observation(second_observation)
    estimate = CapabilityEstimate(
        athlete_id=athlete.id,
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        estimate={"band": "moderate", "basis": "distance"},
        unit_or_scale="field_test_band_v1",
        confidence=Confidence.MODERATE,
        calculation_method="six-minute-walk-band",
        source_observation_ids=(second_observation.id, observation.id),
        estimated_at=NOW,
        valid_until=NOW + timedelta(days=42),
        rule_version="six-minute-walk-band@1.0.0",
    )
    repository.add_capability_estimate(estimate)
    session.commit()
    session.expire_all()

    restored_observation = repository.get_observation(observation.id)
    restored_estimate = repository.get_capability_estimate(estimate.id)

    assert restored_observation == observation
    assert restored_estimate == estimate
    assert restored_estimate is not None
    assert restored_estimate.source_observation_ids == (
        second_observation.id,
        observation.id,
    )


def test_estimate_rejects_foreign_athlete_observation(session: Session) -> None:
    repository = DomainRepository(session)
    first = Athlete(display_name="First")
    second = Athlete(display_name="Second")
    repository.add_athlete(first)
    repository.add_athlete(second)
    observation = make_observation(first.id)
    repository.add_observation(observation)
    session.flush()

    estimate = CapabilityEstimate(
        athlete_id=second.id,
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        estimate="unknown",
        unit_or_scale="ordinal",
        confidence=Confidence.LOW,
        calculation_method="provisional",
        source_observation_ids=(observation.id,),
        estimated_at=NOW,
        rule_version="provisional@1.0.0",
    )
    with pytest.raises(DomainIntegrityError, match="same athlete"):
        repository.add_capability_estimate(estimate)


def test_multiple_environments_and_availability_history_preserve_athlete_identity(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Traveler")
    repository.add_athlete(athlete)
    gym = Environment(athlete_id=athlete.id, name="Full gym", outdoor_access=False)
    hotel = Environment(
        athlete_id=athlete.id,
        name="Hotel",
        space_constraints={"floor_area_m2": 8},
        noise_constraints="no jumping",
        outdoor_access=True,
    )
    repository.add_environment(gym)
    repository.add_environment(hotel)
    dumbbells = Equipment(
        name="Adjustable dumbbells",
        category="external_load",
        capabilities={"independently_loaded": True},
    )
    repository.add_equipment(dumbbells)
    session.flush()

    available = EquipmentAvailability(
        environment_id=hotel.id,
        equipment_id=dumbbells.id,
        is_available=True,
        effective_from=NOW,
        load_limits={"per_hand": {"value": 22.5, "unit": "kg"}},
    )
    unavailable = EquipmentAvailability(
        environment_id=hotel.id,
        equipment_id=dumbbells.id,
        is_available=False,
        effective_from=NOW + timedelta(days=3),
        reason="maintenance",
    )
    repository.add_equipment_availability(available)
    repository.add_equipment_availability(unavailable)
    session.commit()

    history = repository.equipment_history(hotel.id)
    persisted_athlete = session.get(AthleteRecord, athlete.id)

    assert gym.athlete_id == hotel.athlete_id == athlete.id
    assert [entry.is_available for entry in history] == [True, False]
    assert persisted_athlete is not None
    assert persisted_athlete.id == athlete.id


def test_evidence_claim_round_trip_preserves_sources_and_versions(session: Session) -> None:
    repository = DomainRepository(session)
    claim = make_evidence_claim()
    repository.add_evidence_claim(claim)
    session.commit()
    session.expire_all()

    assert repository.get_evidence_claim(claim.id) == claim


def test_ontology_relationships_are_referential_and_round_trip(session: Session) -> None:
    repository = DomainRepository(session)
    claim = make_evidence_claim()
    repository.add_evidence_claim(claim)
    strength = Adaptation(
        name="Maximal strength",
        domain=CapabilityDomain.MAXIMUM_STRENGTH,
        preferred_stimuli=("high force",),
        valid_modalities=("external resistance",),
        dose_dimensions=("load", "sets", "repetitions"),
        evidence_claim_ids=(claim.id,),
    )
    repository.add_adaptation(strength)
    power = Adaptation(
        name="Explosive power",
        domain=CapabilityDomain.EXPLOSIVE_POWER,
        preferred_stimuli=("high intent velocity",),
        relationships=(
            AdaptationRelationship(
                target_adaptation_id=strength.id,
                relationship=AdaptationRelationshipType.POTENTIATING,
                strength=Confidence.MODERATE,
                confidence=Confidence.LOW,
                population="unspecified test population",
                evidence_claim_ids=(claim.id,),
                notes="Fixture relationship; not a scientific seed claim.",
            ),
        ),
    )
    repository.add_adaptation(power)
    barbell = Equipment(
        name="Barbell",
        category="external_load",
        capabilities={"plate_loaded": True},
    )
    repository.add_equipment(barbell)
    exercise = Exercise(
        name="Example loaded movement",
        movement_patterns=("hinge", "bilateral"),
        primary_adaptation_ids=(strength.id,),
        secondary_adaptation_ids=(power.id,),
        joint_demands=("hip",),
        equipment_requirement_ids=(barbell.id,),
        loading_type="external",
        loadability=Loadability.HIGH,
        skill_complexity=CostLevel.MODERATE,
        impact_level=ImpactLevel.LOW,
        velocity_characteristics=("intent-dependent",),
        stability_demand=CostLevel.MODERATE,
        fatigue_cost=CostLevel.MODERATE,
        soreness_cost=CostLevel.MODERATE,
        measurement_methods=("external load",),
    )
    repository.add_exercise(exercise)
    session.commit()
    session.expire_all()

    assert repository.get_adaptation(strength.id) == strength
    assert repository.get_adaptation(power.id) == power
    assert repository.get_exercise(exercise.id) == exercise


def test_ontology_rejects_dangling_references(session: Session) -> None:
    repository = DomainRepository(session)
    exercise = Exercise(
        name="Dangling exercise",
        movement_patterns=("squat",),
        primary_adaptation_ids=(UUID("00000000-0000-0000-0000-000000000001"),),
        loading_type="bodyweight",
        loadability=Loadability.LIMITED,
        skill_complexity=CostLevel.LOW,
        impact_level=ImpactLevel.LOW,
        stability_demand=CostLevel.LOW,
        fatigue_cost=CostLevel.LOW,
        soreness_cost=CostLevel.LOW,
    )

    with pytest.raises(DomainIntegrityError, match="unknown adaptations"):
        repository.add_exercise(exercise)


def test_historical_records_are_append_only_and_new_estimates_do_not_destroy_history(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="History athlete")
    repository.add_athlete(athlete)
    first_observation = make_observation(athlete.id)
    second_observation = make_observation(athlete.id, offset_days=42)
    repository.add_observation(first_observation)
    repository.add_observation(second_observation)
    session.flush()

    for index, observation in enumerate((first_observation, second_observation), start=1):
        repository.add_capability_estimate(
            CapabilityEstimate(
                athlete_id=athlete.id,
                domain=CapabilityDomain.AEROBIC_CAPACITY,
                estimate={"band": index},
                unit_or_scale="fixture",
                confidence=Confidence.LOW,
                calculation_method="fixture",
                source_observation_ids=(observation.id,),
                estimated_at=observation.observed_at,
                rule_version=f"fixture@{index}.0.0",
            )
        )
    session.commit()

    observation_count = session.scalar(select(func.count()).select_from(ObservationRecord))
    estimate_count = session.scalar(select(func.count()).select_from(CapabilityEstimateRecord))
    assert observation_count == 2
    assert estimate_count == 2

    stored = session.get(ObservationRecord, first_observation.id)
    assert stored is not None
    stored.context = {"rewritten": True}
    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.flush()
    session.rollback()

    assert session.get(ObservationRecord, first_observation.id) is not None
