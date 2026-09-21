from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from agas_api.assessment_governance_candidates import (
    RatifyAssessmentGovernanceCandidateCommand,
    list_assessment_governance_candidates,
    ratify_assessment_governance_candidate,
)
from agas_api.assessment_readiness import (
    PersistedAssessmentReadinessService,
    SubmitAssessmentReadinessReportCommand,
)
from agas_api.identity import AuthenticatedPrincipal, AuthorizedRole
from agas_api.introductory_exposure import (
    IntroductoryExposureConflictError,
    IntroductoryExposureValidationError,
    PersistedIntroductoryExposureService,
    RecordIntroductoryExposureCommand,
)
from agas_api.training_construction_candidates import (
    JUMP_EXPOSURE_CANDIDATE_ID,
    RatifyTrainingConstructionCandidateCommand,
    list_training_construction_candidates,
    ratify_training_construction_candidate,
)
from agas_domain import (
    AccountRole,
    Athlete,
    Confidence,
    Environment,
    EquipmentAvailability,
    ExposureNeedStatus,
    Provenance,
)
from agas_domain.persistence.models import (
    ImmutableHistoricalRecordError,
    IntroductoryExposureExecutionRecord,
)
from agas_domain.persistence.repository import DomainRepository
from agas_seed_data import SeedCatalogImporter, load_seed_catalog
from sqlalchemy.orm import Session

READY_AT = datetime(2026, 9, 21, 22, 0, tzinfo=UTC)
FIRST_START = datetime(2026, 9, 21, 23, 0, tzinfo=UTC)
SECOND_START = datetime(2026, 9, 22, 1, 0, tzinfo=UTC)
OPEN_FLOOR_ID = UUID("e0000000-0000-4000-8000-000000000008")
PRINCIPAL = AuthenticatedPrincipal(
    issuer="urn:agas:test",
    subject="intro-exposure-owner",
    authentication_method="test",
    test_bypass=True,
)
PROVENANCE = Provenance(
    recorded_by="fixture",
    source_system="pytest",
    ingestion_method="introductory-exposure-test",
)


def _ratify_jump_authorities(session: Session) -> None:
    repository = DomainRepository(session)
    SeedCatalogImporter(repository).import_catalog(
        load_seed_catalog(), imported_at=READY_AT - timedelta(days=1)
    )
    session.commit()
    assessment = next(
        item.candidate
        for item in list_assessment_governance_candidates(
            session, projected_at=READY_AT - timedelta(hours=2)
        ).items
        if item.candidate.slug == "countermovement_vertical_jump"
    )
    ratify_assessment_governance_candidate(
        session,
        assessment.candidate_id,
        RatifyAssessmentGovernanceCandidateCommand(
            candidate_version=assessment.candidate_version,
            content_digest=assessment.content_digest,
            approval_attestation=True,
        ),
        AuthorizedRole(
            account_id=uuid4(),
            assignment_id=uuid4(),
            role=AccountRole.ASSESSMENT_REVIEWER,
            assigned_at=READY_AT - timedelta(days=1),
        ),
        ratified_at=READY_AT - timedelta(hours=1),
    )
    candidate = next(
        item.candidate
        for item in list_training_construction_candidates(
            session, projected_at=READY_AT - timedelta(minutes=30)
        ).items
        if item.candidate.candidate_id == JUMP_EXPOSURE_CANDIDATE_ID
    )
    ratify_training_construction_candidate(
        session,
        candidate.candidate_id,
        RatifyTrainingConstructionCandidateCommand(
            candidate_version=candidate.candidate_version,
            content_digest=candidate.content_digest,
            approval_attestation=True,
        ),
        AuthorizedRole(
            account_id=uuid4(),
            assignment_id=uuid4(),
            role=AccountRole.PLANNING_REVIEWER,
            assigned_at=READY_AT - timedelta(days=1),
        ),
        ratified_at=READY_AT - timedelta(minutes=20),
    )


def _readiness_command() -> SubmitAssessmentReadinessReportCommand:
    return SubmitAssessmentReadinessReportCommand(
        report_id=uuid4(),
        reported_at=READY_AT,
        adult_confirmed=True,
        regular_moderate_activity_last_three_months="yes",
        known_cardiovascular_metabolic_or_renal_disease="no",
        concerning_signs_or_symptoms="no",
        clinician_exercise_restriction="no",
        current_lower_body_or_balance_concern="no",
        controlled_chair_stand_without_arms="yes",
        current_upper_body_wrist_or_hand_concern="no",
        controlled_standard_pushup="yes",
        controlled_two_foot_jump_and_landing="yes",
        recent_two_foot_jump_and_landing_exposure_28_days="no",
        answers_confirmed=True,
    )


def _execution_command(
    need_id: UUID, environment_id: UUID, started_at: datetime
) -> RecordIntroductoryExposureCommand:
    return RecordIntroductoryExposureCommand(
        execution_id=uuid4(),
        exposure_need_id=need_id,
        environment_id=environment_id,
        started_at=started_at,
        ended_at=started_at + timedelta(minutes=8),
        actual_sets=2,
        actual_contacts=6,
        session_rpe=3,
        pre_session_ready=True,
        controlled_landings=True,
        stop_condition_occurred=False,
        answers_confirmed=True,
        reliability=Confidence.MODERATE,
        provenance=PROVENANCE,
    )


def _fixture(session: Session) -> tuple[UUID, UUID, UUID]:
    _ratify_jump_authorities(session)
    repository = DomainRepository(session)
    athlete = Athlete(created_at=READY_AT - timedelta(days=1), display_name="Jump exposure")
    repository.add_athlete(athlete)
    session.flush()
    environment = Environment(
        created_at=READY_AT - timedelta(days=1),
        athlete_id=athlete.id,
        name="Clear home area",
        space_constraints={"floor_area_m2": 20.0},
    )
    repository.add_environment(environment)
    session.flush()
    repository.add_equipment_availability(
        EquipmentAvailability(
            created_at=READY_AT - timedelta(days=1),
            environment_id=environment.id,
            equipment_id=OPEN_FLOOR_ID,
            is_available=True,
            effective_from=READY_AT - timedelta(days=1),
            reason="Fixture confirms a clear nonslip area.",
        )
    )
    session.commit()
    readiness = PersistedAssessmentReadinessService(session).execute(
        athlete.id, _readiness_command(), PRINCIPAL, recorded_at=READY_AT
    )
    return athlete.id, environment.id, readiness.jump_exposure_need_id


def test_two_distinct_safe_exposure_days_unlock_recent_exposure_without_rewriting_history(
    session: Session,
) -> None:
    athlete_id, environment_id, first_need_id = _fixture(session)
    service = PersistedIntroductoryExposureService(session)
    first_command = _execution_command(first_need_id, environment_id, FIRST_START)

    first = service.execute(athlete_id, first_command)
    replay = service.execute(athlete_id, first_command)

    assert first.execution.qualifies_as_exposure_day is True
    assert replay.created is False
    assert replay.execution == first.execution
    assert first.qualifying_exposure_days == 1
    assert first.current_exposure_need.status is ExposureNeedStatus.INTRODUCTORY_EXPOSURE_NEEDED
    assert first.current_exposure_need.id != first_need_id

    with pytest.raises(IntroductoryExposureConflictError, match="different content"):
        service.execute(
            athlete_id,
            first_command.model_copy(update={"actual_contacts": 5}),
        )

    with pytest.raises(IntroductoryExposureConflictError, match=r"one.*per day"):
        service.execute(
            athlete_id,
            _execution_command(
                first.current_exposure_need.id, environment_id, FIRST_START + timedelta(minutes=30)
            ),
        )

    second = service.execute(
        athlete_id,
        _execution_command(first.current_exposure_need.id, environment_id, SECOND_START),
    )

    assert second.qualifying_exposure_days == 2
    assert second.current_exposure_need.status is ExposureNeedStatus.RECENT_EXPOSURE_CONFIRMED
    history = DomainRepository(session).list_exposure_needs(
        athlete_id,
        exposure_type="jumping",
        target_scope="assessment:countermovement_vertical_jump:maximal",
    )
    assert tuple(item.status for item in history) == (
        ExposureNeedStatus.RECENT_EXPOSURE_CONFIRMED,
        ExposureNeedStatus.INTRODUCTORY_EXPOSURE_NEEDED,
        ExposureNeedStatus.INTRODUCTORY_EXPOSURE_NEEDED,
    )
    stored = session.get(IntroductoryExposureExecutionRecord, first.execution.id)
    assert stored is not None
    stored.actual_dose = 99
    with pytest.raises(ImmutableHistoricalRecordError):
        session.commit()


def test_partial_or_safety_stopped_execution_is_preserved_but_does_not_count(
    session: Session,
) -> None:
    athlete_id, environment_id, need_id = _fixture(session)
    command = _execution_command(need_id, environment_id, FIRST_START).model_copy(
        update={
            "actual_sets": 1,
            "actual_contacts": 2,
            "session_rpe": 5,
            "controlled_landings": False,
            "stop_condition_occurred": True,
        }
    )

    result = PersistedIntroductoryExposureService(session).execute(athlete_id, command)

    assert result.execution.status == "stopped_safety"
    assert result.execution.qualifies_as_exposure_day is False
    assert result.qualifying_exposure_days == 0
    assert result.current_exposure_need.id == need_id
    assert DomainRepository(session).get_observation(result.observation.id) is not None


def test_unclear_pre_session_readiness_refuses_to_create_an_execution(session: Session) -> None:
    athlete_id, environment_id, need_id = _fixture(session)
    command = _execution_command(need_id, environment_id, FIRST_START).model_copy(
        update={"pre_session_ready": False, "actual_sets": 0, "actual_contacts": 0}
    )

    with pytest.raises(IntroductoryExposureValidationError, match="do not start"):
        PersistedIntroductoryExposureService(session).execute(athlete_id, command)

    assert DomainRepository(session).list_introductory_exposure_executions(athlete_id) == ()
