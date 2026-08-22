from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest
from agas_api.current_week import CurrentWeekProjector
from agas_api.safety_policy_admin import assign_session_safety_policy
from agas_api.session_recording import CreateSessionSafetyDecisionCommand
from agas_domain import (
    Applicability,
    Athlete,
    AthleteSafetyPolicyAssignment,
    EvidenceClaim,
    EvidenceSourceIdentifier,
    EvidenceStrength,
    PrescriptionModification,
    SessionSafetyPolicy,
)
from agas_domain.persistence.models import (
    AthleteSafetyPolicyAssignmentRecord,
    ImmutableHistoricalRecordError,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import ValidationError
from sqlalchemy.orm import Session

NOW = datetime(2026, 8, 22, 22, 0, tzinfo=UTC)


def fixture_claim() -> EvidenceClaim:
    return EvidenceClaim(
        claim="Software fixture: an assigned policy remains traceable to its evidence record.",
        domain="software_test",
        population="synthetic persistence fixture",
        intervention="not applicable",
        outcome="referential integrity",
        study_design="software test fixture",
        uncertainty="This is not scientific or clinical evidence.",
        limitations=("Not operational evidence",),
        evidence_strength=EvidenceStrength.INSUFFICIENT,
        athlete_applicability=Applicability.UNKNOWN,
        applicability_notes="Used only to verify assignment provenance.",
        source_identifiers=(
            EvidenceSourceIdentifier(scheme="other", value="fixture:safety-assignment"),
        ),
        reviewer="automated-test",
        claim_version="fixture@1.0.0",
    )


def fixture_policy(claim_id: UUID, version: str) -> SessionSafetyPolicy:
    return SessionSafetyPolicy(
        allowed_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        limited_readiness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        unusual_soreness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        sleep_disruption_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        schedule_limitation_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        evidence_claim_ids=(claim_id,),
        rationale="Synthetic policy used only to verify governed assignment behavior.",
        policy_version=version,
    )


def persist_assignment_fixture(
    session: Session,
) -> tuple[DomainRepository, Athlete, SessionSafetyPolicy, SessionSafetyPolicy]:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Assignment fixture")
    claim = fixture_claim()
    first_policy = fixture_policy(claim.id, "fixture-safety@1.0.0")
    second_policy = fixture_policy(claim.id, "fixture-safety@2.0.0")
    repository.add_athlete(athlete)
    repository.add_evidence_claim(claim)
    session.flush()
    repository.add_session_safety_policy(first_policy)
    repository.add_session_safety_policy(second_policy)
    session.flush()
    return repository, athlete, first_policy, second_policy


def test_assignment_replacement_is_linear_and_preserves_immutable_history(
    session: Session,
) -> None:
    repository, athlete, first_policy, second_policy = persist_assignment_fixture(session)
    first = AthleteSafetyPolicyAssignment(
        athlete_id=athlete.id,
        safety_policy_id=first_policy.id,
        sequence_number=1,
        assigned_at=NOW,
        assigned_by="reviewer-one",
        applicability_rationale="First reviewed synthetic assignment.",
        rule_version="fixture-assignment@1.0.0",
    )
    repository.add_athlete_safety_policy_assignment(first)
    session.commit()

    second, created = assign_session_safety_policy(
        session,
        athlete_id=athlete.id,
        safety_policy_id=second_policy.id,
        assigned_at=NOW + timedelta(minutes=1),
        assigned_by="reviewer-two",
        applicability_rationale="Replacement reviewed after a policy version change.",
    )

    assert created is True
    assert second.sequence_number == 2
    assert second.supersedes_assignment_id == first.id
    assert repository.get_current_athlete_safety_policy_assignment(athlete.id) == second
    assert repository.get_athlete_safety_policy_assignment(first.id) == first

    first_record = session.get(AthleteSafetyPolicyAssignmentRecord, first.id)
    assert first_record is not None
    first_record.assigned_by = "silently-rewritten"
    with pytest.raises(ImmutableHistoricalRecordError):
        session.commit()
    session.rollback()
    assert repository.get_athlete_safety_policy_assignment(first.id) == first


def test_operator_assignment_is_idempotent_and_current_policy_is_projected(
    session: Session,
) -> None:
    _, athlete, first_policy, _ = persist_assignment_fixture(session)

    assignment, created = assign_session_safety_policy(
        session,
        athlete_id=athlete.id,
        safety_policy_id=first_policy.id,
        assigned_at=NOW,
        assigned_by="reviewer-one",
        applicability_rationale="Reviewed synthetic assignment.",
    )
    same, created_again = assign_session_safety_policy(
        session,
        athlete_id=athlete.id,
        safety_policy_id=first_policy.id,
        assigned_at=NOW + timedelta(minutes=1),
        assigned_by="reviewer-one",
        applicability_rationale="Repeated operator command.",
    )
    projection = CurrentWeekProjector(session).project(athlete.id, date(2026, 8, 22))

    assert created is True
    assert created_again is False
    assert same == assignment
    assert projection.week is None
    assert projection.safety_policy_assignment is not None
    assert projection.safety_policy_assignment.assignment_id == assignment.id
    assert projection.safety_policy_assignment.policy_version == first_policy.policy_version


def test_repository_rejects_a_skipped_or_unlinked_replacement(session: Session) -> None:
    repository, athlete, first_policy, second_policy = persist_assignment_fixture(session)
    first = AthleteSafetyPolicyAssignment(
        athlete_id=athlete.id,
        safety_policy_id=first_policy.id,
        sequence_number=1,
        assigned_at=NOW,
        assigned_by="reviewer-one",
        applicability_rationale="First reviewed synthetic assignment.",
        rule_version="fixture-assignment@1.0.0",
    )
    repository.add_athlete_safety_policy_assignment(first)
    session.commit()

    with pytest.raises(DomainIntegrityError, match="next sequence"):
        repository.add_athlete_safety_policy_assignment(
            AthleteSafetyPolicyAssignment(
                athlete_id=athlete.id,
                safety_policy_id=second_policy.id,
                sequence_number=3,
                supersedes_assignment_id=first.id,
                assigned_at=NOW + timedelta(minutes=1),
                assigned_by="reviewer-two",
                applicability_rationale="Invalid skipped replacement.",
                rule_version="fixture-assignment@1.0.0",
            )
        )


def test_session_safety_command_rejects_a_client_selected_policy() -> None:
    with pytest.raises(ValidationError, match="safety_policy_id"):
        CreateSessionSafetyDecisionCommand.model_validate(
            {
                "safety_policy_id": "00000000-0000-4000-8000-000000000001",
                "timing": "pre_session",
                "readiness": "ready",
                "reported_at": NOW.isoformat(),
                "decided_at": NOW.isoformat(),
                "reliability": "moderate",
                "provenance": {
                    "recorded_by": "automated-test",
                    "source_system": "pytest",
                    "ingestion_method": "fixture",
                },
            }
        )
