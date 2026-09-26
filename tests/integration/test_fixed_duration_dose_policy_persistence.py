from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from agas_domain import (
    Adaptation,
    Applicability,
    CapabilityDomain,
    EvidenceClaim,
    EvidenceSourceIdentifier,
    EvidenceStrength,
    FixedDurationDosePolicy,
    PrescriptionAdjustment,
    ProgressionDimension,
    ProgressionPolicy,
    TrainingPriorityState,
)
from agas_domain.persistence.models import (
    FixedDurationDosePolicyRecord,
    ImmutableHistoricalRecordError,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from sqlalchemy.orm import Session

NOW = datetime(2026, 9, 25, 8, 0, tzinfo=UTC)
SCOPE = "assessment_specific:aerobic_field_distance_m"


def fixture_claim() -> EvidenceClaim:
    return EvidenceClaim(
        claim="Software fixture: duration-dose provenance remains attached to the rule.",
        domain="software_test",
        population="synthetic persistence fixture",
        intervention="not applicable",
        outcome="referential integrity",
        study_design="software test fixture",
        uncertainty="This is not scientific training evidence.",
        limitations=("Not operational evidence",),
        evidence_strength=EvidenceStrength.INSUFFICIENT,
        athlete_applicability=Applicability.UNKNOWN,
        applicability_notes="Used only to verify software provenance.",
        source_identifiers=(
            EvidenceSourceIdentifier(scheme="other", value="fixture:fixed-duration-dose"),
        ),
        reviewer="automated-test",
        claim_version="fixture@1.0.0",
    )


def fixture_progression_policy(claim_id: UUID) -> ProgressionPolicy:
    return ProgressionPolicy(
        reference="fixture-duration-progression@1.0.0",
        minimum_set_completion_ratio=1,
        minimum_dose_completion_ratio=1,
        maximum_session_rpe=6,
        adjustment=PrescriptionAdjustment(
            dimension=ProgressionDimension.DURATION,
            amount=60,
            unit="seconds_per_set",
            description="Add one minute after governed validation.",
        ),
        maximum_prescription_value=720,
        maximum_prescription_value_unit="seconds_per_set",
        evidence_claim_ids=(claim_id,),
        rationale="Synthetic progression authority.",
        policy_version="fixture-duration-progression@1.0.0",
    )


def fixture_policy(
    adaptation_id: UUID,
    progression_policy_id: UUID,
    claim_id: UUID,
) -> FixedDurationDosePolicy:
    return FixedDurationDosePolicy(
        adaptation_id=adaptation_id,
        estimate_scope=SCOPE,
        sets=1,
        duration_seconds_per_set=600,
        maximum_initial_total_duration_seconds=600,
        rest_seconds=0,
        effort_rpe_minimum=3,
        effort_rpe_maximum=5,
        technique_constraints=("Maintain continuous controlled cyclic work.",),
        planned_duration_minutes=10,
        progression_policy_id=progression_policy_id,
        evidence_claim_ids=(claim_id,),
        numeric_value_origin="engineering_judgment",
        authority_reference="fixture-duration-authority@1.0.0",
        rationale="Synthetic fixed starting-duration policy.",
        uncertainty="The values are test fixtures, not scientific findings.",
        policy_version="fixture-fixed-duration@1.0.0",
    )


def test_fixed_duration_dose_policy_round_trip_and_filters(session: Session) -> None:
    repository = DomainRepository(session)
    claim = fixture_claim()
    adaptation = Adaptation(
        name="Fixture aerobic base",
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        evidence_claim_ids=(claim.id,),
    )
    progression = fixture_progression_policy(claim.id)
    policy = fixture_policy(adaptation.id, progression.id, claim.id)

    repository.add_evidence_claim(claim)
    repository.add_adaptation(adaptation)
    session.flush()
    repository.add_progression_policy(progression)
    session.flush()
    repository.add_fixed_duration_dose_policy(policy)
    session.commit()

    assert repository.get_fixed_duration_dose_policy(policy.id) == policy
    assert repository.get_progression_policy(progression.id) == progression
    assert repository.list_fixed_duration_dose_policies(adaptation_id=adaptation.id) == (policy,)
    assert repository.list_fixed_duration_dose_policies(estimate_scope=SCOPE) == (policy,)
    assert repository.list_fixed_duration_dose_policies(
        priority_state=TrainingPriorityState.DEVELOP
    ) == (policy,)
    assert repository.list_fixed_duration_dose_policies(adaptation_id=uuid4()) == ()


def test_fixed_duration_dose_policy_requires_persisted_progression(session: Session) -> None:
    repository = DomainRepository(session)
    adaptation = Adaptation(name="Fixture aerobic base", domain=CapabilityDomain.AEROBIC_CAPACITY)
    repository.add_adaptation(adaptation)
    session.flush()

    with pytest.raises(DomainIntegrityError, match="progression policy does not exist"):
        repository.add_fixed_duration_dose_policy(fixture_policy(adaptation.id, uuid4(), uuid4()))


def test_fixed_duration_dose_policy_is_immutable(session: Session) -> None:
    repository = DomainRepository(session)
    claim = fixture_claim()
    adaptation = Adaptation(
        name="Fixture aerobic base",
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        evidence_claim_ids=(claim.id,),
    )
    progression = fixture_progression_policy(claim.id)
    policy = fixture_policy(adaptation.id, progression.id, claim.id)
    repository.add_evidence_claim(claim)
    repository.add_adaptation(adaptation)
    session.flush()
    repository.add_progression_policy(progression)
    session.flush()
    repository.add_fixed_duration_dose_policy(policy)
    session.commit()

    record = session.get(FixedDurationDosePolicyRecord, policy.id)
    assert record is not None
    record.duration_seconds_per_set = 660
    with pytest.raises(ImmutableHistoricalRecordError):
        session.commit()
