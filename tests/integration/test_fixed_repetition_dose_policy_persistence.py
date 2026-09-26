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
    FixedRepetitionDosePolicy,
    PrescriptionAdjustment,
    ProgressionDimension,
    ProgressionPolicy,
    TrainingPriorityState,
)
from agas_domain.persistence.models import (
    FixedRepetitionDosePolicyRecord,
    ImmutableHistoricalRecordError,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from sqlalchemy.orm import Session

NOW = datetime(2026, 9, 23, 16, 0, tzinfo=UTC)
SCOPE = "assessment_specific:countermovement_vertical_jump_height_cm"


def fixture_claim() -> EvidenceClaim:
    return EvidenceClaim(
        claim="Software fixture: fixed dose policy provenance remains attached to the rule.",
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
            EvidenceSourceIdentifier(scheme="other", value="fixture:fixed-repetition-dose"),
        ),
        reviewer="automated-test",
        claim_version="fixture@1.0.0",
    )


def fixture_progression_policy(claim_id: UUID) -> ProgressionPolicy:
    return ProgressionPolicy(
        reference="fixture-fixed-repetition-progression@1.0.0",
        minimum_set_completion_ratio=1,
        minimum_dose_completion_ratio=1,
        maximum_session_rpe=6,
        adjustment=PrescriptionAdjustment(
            dimension=ProgressionDimension.REPETITIONS,
            amount=1,
            unit="repetition_per_set",
            description="Add one repetition per set after governed validation.",
        ),
        evidence_claim_ids=(claim_id,),
        rationale="Synthetic progression authority.",
        policy_version="fixture-fixed-repetition-progression@1.0.0",
    )


def fixture_policy(
    adaptation_id: UUID,
    progression_policy_id: UUID,
    claim_id: UUID,
) -> FixedRepetitionDosePolicy:
    return FixedRepetitionDosePolicy(
        adaptation_id=adaptation_id,
        estimate_scope=SCOPE,
        sets=3,
        repetitions_per_set=3,
        maximum_initial_total_repetitions=9,
        rest_seconds=120,
        effort_rpe_minimum=4,
        effort_rpe_maximum=6,
        technique_constraints=("Reset fully before each repetition.",),
        planned_duration_minutes=12,
        progression_policy_id=progression_policy_id,
        evidence_claim_ids=(claim_id,),
        numeric_value_origin="engineering_judgment",
        authority_reference="fixture-fixed-dose-authority@1.0.0",
        rationale="Synthetic fixed starting-dose policy.",
        uncertainty="The values are test fixtures, not scientific findings.",
        policy_version="fixture-fixed-jump-dose@1.0.0",
    )


def test_fixed_repetition_dose_policy_round_trip_preserves_authority_and_filters(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    claim = fixture_claim()
    adaptation = Adaptation(
        name="Fixture explosive power",
        domain=CapabilityDomain.EXPLOSIVE_POWER,
        evidence_claim_ids=(claim.id,),
    )
    progression = fixture_progression_policy(claim.id)
    policy = fixture_policy(adaptation.id, progression.id, claim.id)

    repository.add_evidence_claim(claim)
    repository.add_adaptation(adaptation)
    session.flush()
    repository.add_progression_policy(progression)
    session.flush()
    repository.add_fixed_repetition_dose_policy(policy)
    session.commit()

    assert repository.get_fixed_repetition_dose_policy(policy.id) == policy
    assert repository.list_fixed_repetition_dose_policies(adaptation_id=adaptation.id) == (policy,)
    assert repository.list_fixed_repetition_dose_policies(estimate_scope=SCOPE) == (policy,)
    assert repository.list_fixed_repetition_dose_policies(
        priority_state=TrainingPriorityState.DEVELOP
    ) == (policy,)
    assert (
        repository.list_fixed_repetition_dose_policies(
            priority_state=TrainingPriorityState.MAINTAIN
        )
        == ()
    )
    assert repository.list_fixed_repetition_dose_policies(adaptation_id=uuid4()) == ()


def test_fixed_repetition_dose_policy_requires_exact_persisted_authorities(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    adaptation = Adaptation(
        name="Fixture explosive power",
        domain=CapabilityDomain.EXPLOSIVE_POWER,
    )
    repository.add_adaptation(adaptation)
    session.flush()

    missing_claim = uuid4()
    policy = fixture_policy(adaptation.id, uuid4(), missing_claim)
    with pytest.raises(DomainIntegrityError, match="progression policy does not exist"):
        repository.add_fixed_repetition_dose_policy(policy)


def test_fixed_repetition_dose_policy_is_immutable(session: Session) -> None:
    repository = DomainRepository(session)
    claim = fixture_claim()
    adaptation = Adaptation(
        name="Fixture explosive power",
        domain=CapabilityDomain.EXPLOSIVE_POWER,
        evidence_claim_ids=(claim.id,),
    )
    progression = fixture_progression_policy(claim.id)
    policy = fixture_policy(adaptation.id, progression.id, claim.id)
    repository.add_evidence_claim(claim)
    repository.add_adaptation(adaptation)
    session.flush()
    repository.add_progression_policy(progression)
    session.flush()
    repository.add_fixed_repetition_dose_policy(policy)
    session.commit()

    record = session.get(FixedRepetitionDosePolicyRecord, policy.id)
    assert record is not None
    record.repetitions_per_set = 4
    with pytest.raises(ImmutableHistoricalRecordError):
        session.commit()
