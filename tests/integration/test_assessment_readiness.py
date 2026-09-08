from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from agas_api.assessment_readiness import (
    READINESS_RULE_VERSION,
    AssessmentReadinessConflictError,
    AssessmentReadinessValidationError,
    PersistedAssessmentReadinessService,
    SubmitAssessmentReadinessReportCommand,
)
from agas_api.database import database_session_dependency
from agas_api.identity import AuthenticatedPrincipal
from agas_api.main import app
from agas_domain import AssessmentEligibilityOutcome, AssessmentIntensity, Athlete
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

NOW = datetime(2026, 9, 8, 16, 0, tzinfo=UTC)
PRINCIPAL = AuthenticatedPrincipal(
    issuer="urn:agas:test",
    subject="readiness-owner",
    authentication_method="test",
    test_bypass=True,
)


def command(**updates: object) -> SubmitAssessmentReadinessReportCommand:
    values: dict[str, object] = {
        "report_id": uuid4(),
        "reported_at": NOW,
        "adult_confirmed": True,
        "regular_moderate_activity_last_three_months": "no",
        "known_cardiovascular_metabolic_or_renal_disease": "no",
        "concerning_signs_or_symptoms": "no",
        "clinician_exercise_restriction": "no",
        "current_lower_body_or_balance_concern": "no",
        "controlled_chair_stand_without_arms": "yes",
        "answers_confirmed": True,
    }
    values.update(updates)
    return SubmitAssessmentReadinessReportCommand.model_validate(values)


def athlete_fixture(session: Session) -> Athlete:
    athlete = Athlete(created_at=NOW - timedelta(days=1), display_name="Readiness athlete")
    DomainRepository(session).add_athlete(athlete)
    session.commit()
    return athlete


def test_clear_report_creates_a_narrow_idempotent_eligibility_chain(session: Session) -> None:
    athlete = athlete_fixture(session)
    service = PersistedAssessmentReadinessService(session)
    report = command()

    created = service.execute(athlete.id, report, PRINCIPAL, recorded_at=NOW)
    replayed = service.execute(
        athlete.id, report, PRINCIPAL, recorded_at=NOW + timedelta(minutes=1)
    )

    assert created.created is True
    assert replayed.created is False
    assert replayed.eligibility_review_id == created.eligibility_review_id
    assert created.outcome is AssessmentEligibilityOutcome.SELECTION_ALLOWED
    assert created.maximum_assessment_intensity is AssessmentIntensity.MODERATE
    assert created.valid_until == NOW + timedelta(hours=24)

    repository = DomainRepository(session)
    observation = repository.get_observation(created.observation_id)
    review = repository.get_current_assessment_eligibility_review(athlete.id)
    assert observation is not None
    assert observation.observation_type == "assessment_readiness_self_report"
    assert observation.context["evidence_source_identifiers"] == [
        "PMID:26473759",
        "PMID:28557860",
    ]
    assert review is not None
    assert review.source_observation_ids == (observation.id,)
    assert review.maximum_assessment_intensity is AssessmentIntensity.MODERATE
    assert review.rule_version == READINESS_RULE_VERSION


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    (
        ("adult_confirmed", False, AssessmentEligibilityOutcome.SELECTION_BLOCKED),
        (
            "known_cardiovascular_metabolic_or_renal_disease",
            "yes",
            AssessmentEligibilityOutcome.REVIEW_REQUIRED,
        ),
        ("concerning_signs_or_symptoms", "unsure", AssessmentEligibilityOutcome.REVIEW_REQUIRED),
        ("clinician_exercise_restriction", "yes", AssessmentEligibilityOutcome.REVIEW_REQUIRED),
        (
            "current_lower_body_or_balance_concern",
            "yes",
            AssessmentEligibilityOutcome.REVIEW_REQUIRED,
        ),
        (
            "controlled_chair_stand_without_arms",
            "no",
            AssessmentEligibilityOutcome.REVIEW_REQUIRED,
        ),
    ),
)
def test_concerns_uncertainty_and_product_scope_fail_closed(
    session: Session,
    field: str,
    value: object,
    expected: AssessmentEligibilityOutcome,
) -> None:
    athlete = athlete_fixture(session)
    result = PersistedAssessmentReadinessService(session).execute(
        athlete.id,
        command(**{field: value}),
        PRINCIPAL,
        recorded_at=NOW,
    )
    assert result.outcome is expected
    assert "Do not" in result.next_action


def test_new_report_supersedes_without_destroying_history_and_rejects_identity_reuse(
    session: Session,
) -> None:
    athlete = athlete_fixture(session)
    service = PersistedAssessmentReadinessService(session)
    first_command = command()
    first = service.execute(athlete.id, first_command, PRINCIPAL, recorded_at=NOW)
    second_command = command(
        reported_at=NOW + timedelta(minutes=2),
        concerning_signs_or_symptoms="yes",
    )
    second = service.execute(
        athlete.id,
        second_command,
        PRINCIPAL,
        recorded_at=NOW + timedelta(minutes=2),
    )

    repository = DomainRepository(session)
    first_review = repository.get_assessment_eligibility_review(first.eligibility_review_id)
    second_review = repository.get_assessment_eligibility_review(second.eligibility_review_id)
    assert first_review is not None
    assert second_review is not None
    assert second_review.sequence_number == 2
    assert second_review.supersedes_review_id == first_review.id
    assert repository.get_observation(first.observation_id) is not None

    with pytest.raises(AssessmentReadinessConflictError, match="different content"):
        service.execute(
            athlete.id,
            first_command.model_copy(update={"adult_confirmed": False}),
            PRINCIPAL,
            recorded_at=NOW + timedelta(minutes=3),
        )


def test_report_rolls_back_observation_when_review_persistence_fails(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    athlete = athlete_fixture(session)
    report = command()

    def reject_review(*_args: object, **_kwargs: object) -> None:
        raise DomainIntegrityError("synthetic review failure")

    monkeypatch.setattr(DomainRepository, "add_assessment_eligibility_review", reject_review)
    with pytest.raises(AssessmentReadinessValidationError, match="synthetic review failure"):
        PersistedAssessmentReadinessService(session).execute(
            athlete.id, report, PRINCIPAL, recorded_at=NOW
        )
    assert DomainRepository(session).get_observation(report.report_id) is None


def test_owned_endpoint_returns_rule_decision_not_a_caller_selected_outcome(
    session: Session,
) -> None:
    athlete = athlete_fixture(session)

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    try:
        response = TestClient(app).post(
            f"/v1/athletes/{athlete.id}/assessment-readiness-reports",
            json=command(reported_at=datetime.now(UTC)).model_dump(mode="json"),
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code == 201
    assert response.json()["outcome"] == "selection_allowed"
    assert response.json()["maximum_assessment_intensity"] == "moderate"
    assert "outcome" not in command().model_dump()
