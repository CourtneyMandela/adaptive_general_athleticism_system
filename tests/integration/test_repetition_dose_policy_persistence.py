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
    PrescriptionAdjustment,
    ProgressionDimension,
    ProgressionPolicy,
    RepetitionDosePolicy,
)
from agas_domain.persistence.models import (
    ImmutableHistoricalRecordError,
    RepetitionDosePolicyRecord,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import ValidationError
from sqlalchemy.orm import Session

NOW = datetime(2026, 9, 11, 11, 0, tzinfo=UTC)


def fixture_claim() -> EvidenceClaim:
    return EvidenceClaim(
        claim="Software fixture: dose policy provenance remains attached to the rule.",
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
            EvidenceSourceIdentifier(scheme="other", value="fixture:repetition-dose"),
        ),
        reviewer="automated-test",
        claim_version="fixture@1.0.0",
    )


def fixture_progression_policy(claim_id: UUID) -> ProgressionPolicy:
    return ProgressionPolicy(
        reference="fixture-repetition-progression@1.0.0",
        minimum_set_completion_ratio=1,
        minimum_dose_completion_ratio=1,
        maximum_session_rpe=7,
        adjustment=PrescriptionAdjustment(
            dimension=ProgressionDimension.REPETITIONS,
            amount=1,
            unit="repetitions_per_set",
            description="Add one repetition to each set.",
        ),
        evidence_claim_ids=(claim_id,),
        rationale="Synthetic policy used only for persistence testing.",
        policy_version="fixture-repetition-progression@1.0.0",
    )


def fixture_dose_policy(
    adaptation_id: UUID,
    progression_policy_id: UUID,
    claim_id: UUID,
) -> RepetitionDosePolicy:
    return RepetitionDosePolicy(
        adaptation_id=adaptation_id,
        estimate_scope="assessment_specific:thirty_second_chair_stand_repetitions",
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
        progression_policy_id=progression_policy_id,
        evidence_claim_ids=(claim_id,),
        rationale="Synthetic deterministic dose-policy fixture.",
        uncertainty="The numeric constants are test values, not evidence claims.",
        policy_version="fixture-chair-stand-dose@1.0.0",
    )


def test_repetition_dose_policy_round_trip_preserves_provenance_and_filters(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    claim = fixture_claim()
    adaptation = Adaptation(
        name="Fixture lower-body repetition capacity",
        domain=CapabilityDomain.MUSCULAR_ENDURANCE,
    )
    progression = fixture_progression_policy(claim.id)
    policy = fixture_dose_policy(adaptation.id, progression.id, claim.id)

    repository.add_evidence_claim(claim)
    repository.add_adaptation(adaptation)
    session.flush()
    repository.add_progression_policy(progression)
    session.flush()
    repository.add_repetition_dose_policy(policy)
    session.commit()

    assert repository.get_repetition_dose_policy(policy.id) == policy
    assert repository.list_repetition_dose_policies(adaptation_id=adaptation.id) == (policy,)
    assert repository.list_repetition_dose_policies(
        estimate_scope="assessment_specific:thirty_second_chair_stand_repetitions"
    ) == (policy,)
    assert repository.list_repetition_dose_policies(adaptation_id=uuid4()) == ()


def test_repetition_dose_policy_requires_persisted_progression_policy(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    claim = fixture_claim()
    adaptation = Adaptation(
        name="Fixture lower-body repetition capacity",
        domain=CapabilityDomain.MUSCULAR_ENDURANCE,
    )
    repository.add_evidence_claim(claim)
    repository.add_adaptation(adaptation)
    session.flush()

    policy = fixture_dose_policy(adaptation.id, uuid4(), claim.id)
    with pytest.raises(
        DomainIntegrityError,
        match="repetition dose policy progression policy does not exist",
    ):
        repository.add_repetition_dose_policy(policy)


def test_repetition_dose_policy_validates_bounds_and_is_immutable(session: Session) -> None:
    repository = DomainRepository(session)
    claim = fixture_claim()
    adaptation = Adaptation(
        name="Fixture lower-body repetition capacity",
        domain=CapabilityDomain.MUSCULAR_ENDURANCE,
    )
    progression = fixture_progression_policy(claim.id)
    policy = fixture_dose_policy(adaptation.id, progression.id, claim.id)
    repository.add_evidence_claim(claim)
    repository.add_adaptation(adaptation)
    session.flush()
    repository.add_progression_policy(progression)
    session.flush()
    repository.add_repetition_dose_policy(policy)
    session.commit()

    record = session.get(RepetitionDosePolicyRecord, policy.id)
    assert record is not None
    record.target_fraction_of_estimate = 0.75
    with pytest.raises(ImmutableHistoricalRecordError):
        session.commit()
    session.rollback()

    invalid = fixture_dose_policy(adaptation.id, progression.id, claim.id).model_dump()
    invalid.update(minimum_repetitions_per_set=9, maximum_repetitions_per_set=8)
    with pytest.raises(ValidationError, match="maximum repetitions cannot be below minimum"):
        RepetitionDosePolicy.model_validate(invalid)
