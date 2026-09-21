from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from agas_domain import (
    Adaptation,
    Applicability,
    Athlete,
    CapabilityDomain,
    Confidence,
    EvidenceClaim,
    EvidenceSourceIdentifier,
    EvidenceStrength,
    ExposureNeed,
    ExposureNeedStatus,
    ExposureType,
    IntroductoryExposureDose,
    IntroductoryExposureDosePolicy,
    Observation,
    ObservationSource,
    PrescriptionAdjustment,
    ProgressionDimension,
    ProgressionPolicy,
    Provenance,
)
from agas_domain.persistence.models import (
    ExposureNeedRecord,
    ImmutableHistoricalRecordError,
    IntroductoryExposureDoseRecord,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import IntroductoryExposureDosePlanner
from sqlalchemy.orm import Session

NOW = datetime(2026, 9, 20, 21, 0, tzinfo=UTC)
TARGET_SCOPE = "assessment:countermovement_vertical_jump:maximal"


def claim() -> EvidenceClaim:
    return EvidenceClaim(
        claim="Software fixture: jumping is a separately tracked exposure type.",
        domain="software_test",
        population="synthetic persistence fixture",
        intervention="not applicable",
        outcome="referential integrity",
        study_design="software test fixture",
        uncertainty="This is not scientific training evidence.",
        limitations=("Not operational evidence",),
        evidence_strength=EvidenceStrength.INSUFFICIENT,
        athlete_applicability=Applicability.UNKNOWN,
        applicability_notes="Used only to verify provenance.",
        source_identifiers=(
            EvidenceSourceIdentifier(scheme="other", value="fixture:intro-exposure-dose"),
        ),
        reviewer="automated-test",
        claim_version="fixture@1.0.0",
    )


def progression(claim_id: UUID) -> ProgressionPolicy:
    return ProgressionPolicy(
        reference="fixture-jump-exposure-progression@1.0.0",
        minimum_set_completion_ratio=1,
        minimum_dose_completion_ratio=1,
        maximum_session_rpe=4,
        adjustment=PrescriptionAdjustment(
            dimension=ProgressionDimension.REPETITIONS,
            amount=1,
            unit="repetitions_per_set",
            description="Add one contact per set after a compliant exposure.",
        ),
        exposure_type=ExposureType.JUMPING,
        evidence_claim_ids=(claim_id,),
        rationale="Synthetic progression authority.",
        policy_version="fixture-jump-exposure-progression@1.0.0",
    )


def dose_policy(
    adaptation_id: UUID, progression_id: UUID, claim_id: UUID
) -> IntroductoryExposureDosePolicy:
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
        technique_constraints=("Use low effort and land under control.",),
        planned_duration_minutes=6,
        progression_policy_id=progression_id,
        evidence_claim_ids=(claim_id,),
        numeric_value_origin="engineering_judgment",
        authority_reference="candidate:fixture-intro-jump@1.0.0",
        rationale="Synthetic conservative starting dose.",
        uncertainty="Values are engineering fixtures, not scientific thresholds.",
        policy_version="fixture-intro-jump@1.0.0",
    )


def test_introductory_exposure_policy_and_derived_dose_round_trip(session: Session) -> None:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Exposure persistence fixture")
    observation = Observation(
        athlete_id=athlete.id,
        observed_at=NOW,
        observation_type="assessment_readiness_self_report",
        measurement={"recent_jump_exposure": "no"},
        source=ObservationSource.USER_REPORT,
        reliability=Confidence.MODERATE,
        provenance=Provenance(
            recorded_by="fixture",
            source_system="pytest",
            ingestion_method="fixture",
        ),
    )
    need = ExposureNeed(
        athlete_id=athlete.id,
        exposure_type=ExposureType.JUMPING,
        target_scope=TARGET_SCOPE,
        status=ExposureNeedStatus.INTRODUCTORY_EXPOSURE_NEEDED,
        lookback_days=28,
        minimum_exposure_days=2,
        source_observation_ids=(observation.id,),
        confidence=Confidence.MODERATE,
        rationale="Recent exposure was not confirmed.",
        uncertainty="Self-report only.",
        authority_reference="engineering-decision:0124@1.0.0",
        identified_at=NOW,
        valid_until=NOW + timedelta(hours=24),
        rule_version="fixture-exposure-need@1.0.0",
    )
    adaptation = Adaptation(
        name="Fixture landing exposure",
        domain=CapabilityDomain.DECELERATION,
    )
    evidence = claim()
    progression_policy = progression(evidence.id)
    policy = dose_policy(adaptation.id, progression_policy.id, evidence.id)

    repository.add_athlete(athlete)
    repository.add_observation(observation)
    repository.add_adaptation(adaptation)
    repository.add_evidence_claim(evidence)
    session.flush()
    repository.add_exposure_need(need)
    repository.add_progression_policy(progression_policy)
    session.flush()
    repository.add_introductory_exposure_dose_policy(policy)
    session.flush()
    dose = IntroductoryExposureDosePlanner().derive(
        dose_id=uuid4(),
        need=need,
        adaptation=adaptation,
        policy=policy,
        derived_at=NOW + timedelta(minutes=1),
    )
    repository.add_introductory_exposure_dose(dose)
    session.commit()

    assert repository.get_introductory_exposure_dose_policy(policy.id) == policy
    assert repository.get_introductory_exposure_dose(dose.id) == dose

    record = session.get(IntroductoryExposureDoseRecord, dose.id)
    assert record is not None
    record.total_dose = 8
    with pytest.raises(ImmutableHistoricalRecordError):
        session.commit()
    session.rollback()

    need_record = session.get(ExposureNeedRecord, need.id)
    assert need_record is not None
    need_record.status = "recent_exposure_confirmed"
    with pytest.raises(ImmutableHistoricalRecordError):
        session.commit()
    session.rollback()


def test_derived_dose_cannot_drop_its_need_observation(session: Session) -> None:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Exposure mismatch fixture")
    other_observation = Observation(
        athlete_id=athlete.id,
        observed_at=NOW,
        observation_type="other",
        measurement="other",
        source=ObservationSource.USER_REPORT,
        reliability=Confidence.LOW,
        provenance=Provenance(
            recorded_by="fixture", source_system="pytest", ingestion_method="fixture"
        ),
    )
    repository.add_athlete(athlete)
    repository.add_observation(other_observation)
    session.flush()

    fake_dose = IntroductoryExposureDose(
        athlete_id=athlete.id,
        exposure_need_id=uuid4(),
        policy_id=uuid4(),
        adaptation_id=uuid4(),
        exposure_type=ExposureType.JUMPING,
        target_scope=TARGET_SCOPE,
        dose_unit="repetitions",
        sets=1,
        dose_per_set=1,
        total_dose=1,
        rest_seconds=0,
        effort_rpe_minimum=1,
        effort_rpe_maximum=2,
        technique_constraints=("fixture",),
        planned_duration_minutes=1,
        source_observation_ids=(other_observation.id,),
        numeric_value_origin="engineering_judgment",
        authority_reference="fixture",
        rationale="fixture",
        uncertainty="fixture",
        derived_at=NOW,
        rule_version="fixture@1.0.0",
    )
    with pytest.raises(DomainIntegrityError, match="need is missing"):
        repository.add_introductory_exposure_dose(fake_dose)
