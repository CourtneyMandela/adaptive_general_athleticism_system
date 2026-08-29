from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from agas_api.database import database_session_dependency
from agas_api.identity import authenticated_principal_dependency
from agas_api.identity_admin import grant_athlete_ownership, set_account_role
from agas_api.main import app
from agas_domain import (
    Account,
    AccountRole,
    AccountRoleAssignment,
    AccountRoleStatus,
    Athlete,
    AthleteOwnership,
)
from agas_domain.persistence.models import (
    AccountRecord,
    AccountRoleAssignmentRecord,
    AthleteOwnershipRecord,
    ImmutableHistoricalRecordError,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

REPORTED_AT = datetime(2026, 8, 22, 20, 0, tzinfo=UTC)


def onboarding_body(display_name: str) -> dict[str, object]:
    return {
        "display_name": display_name,
        "goals": ["Build broad athletic capacity"],
        "preferred_activities": ["Hiking"],
        "disliked_activities": [],
        "environments": [
            {
                "name": "Home",
                "max_noise_level": "moderate",
                "outdoor_access": True,
                "equipment": [],
            }
        ],
        "reported_at": REPORTED_AT.isoformat(),
        "reliability": "moderate",
        "provenance": {
            "recorded_by": "unverified-athlete-user",
            "source_system": "agas-web",
            "ingestion_method": "onboarding-form",
        },
    }


def development_header(subject: str) -> dict[str, str]:
    return {"Authorization": f"Bearer dev.{subject}"}


def test_every_athlete_scoped_route_requires_authentication() -> None:
    identity = uuid4()
    protected_posts = (
        "/v1/onboarding/athletes",
        f"/v1/athletes/{identity}/assessment-runs",
        f"/v1/athletes/{identity}/assessment-runs/{identity}/selections/{identity}/result",
        f"/v1/athletes/{identity}/environments/{identity}/equipment-reports",
        f"/v1/weekly-plans/{identity}/availability-confirmations",
        f"/v1/weekly-plans/{identity}/roll-forward",
        f"/v1/weekly-plans/{identity}/sessions/{identity}/safety-checks",
        f"/v1/weekly-plans/{identity}/sessions/{identity}/executions",
        f"/v1/session-executions/{identity}/prescriptions/{identity}/progression",
        f"/v1/operator/stimulus-requirements/{identity}/exercise-reresolutions",
        f"/v1/operator/weekly-plans/{identity}/environment-prescription-revisions",
    )
    app.dependency_overrides.pop(authenticated_principal_dependency, None)

    current_week = TestClient(app).get(
        f"/v1/athletes/{identity}/current-week", params={"on": "2026-08-22"}
    )
    dashboard = TestClient(app).get(f"/v1/athletes/{identity}/dashboard")
    environments = TestClient(app).get(f"/v1/athletes/{identity}/environments")
    assessment_workflow = TestClient(app).get(f"/v1/athletes/{identity}/assessment-workflow")
    post_responses = [TestClient(app).post(path, json={}) for path in protected_posts]

    assert current_week.status_code == 401
    assert dashboard.status_code == 401
    assert environments.status_code == 401
    assert assessment_workflow.status_code == 401
    assert all(response.status_code == 401 for response in post_responses)


def test_onboarding_creates_identity_and_owner_atomically_and_authorizes_its_athlete(
    session: Session,
) -> None:
    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    try:
        unauthenticated = TestClient(app).post(
            "/v1/onboarding/athletes", json=onboarding_body("No identity")
        )
        created = TestClient(app).post(
            "/v1/onboarding/athletes",
            json=onboarding_body("Owned athlete"),
            headers=development_header("owner-one"),
        )
        athlete_id = created.json()["athlete"]["id"]
        current_week = TestClient(app).get(
            f"/v1/athletes/{athlete_id}/current-week",
            params={"on": "2026-08-22"},
            headers=development_header("owner-one"),
        )
        dashboard = TestClient(app).get(
            f"/v1/athletes/{athlete_id}/dashboard",
            headers=development_header("owner-one"),
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert unauthenticated.status_code == 401
    assert unauthenticated.json() == {"detail": "bearer authentication required"}
    assert created.status_code == 201
    assert current_week.status_code == 200
    assert current_week.json()["week"] is None
    assert dashboard.status_code == 200
    assert dashboard.json()["estimated_domain_count"] == 0
    assert dashboard.json()["unestimated_domain_count"] == len(dashboard.json()["domains"])

    account_record = session.scalar(select(AccountRecord))
    ownership_record = session.scalar(select(AthleteOwnershipRecord))
    assert account_record is not None
    assert account_record.subject == "owner-one"
    assert ownership_record is not None
    assert str(ownership_record.athlete_id) == athlete_id
    assert ownership_record.account_id == account_record.id
    assert ownership_record.grant_method == "self-service-onboarding"


def test_cross_account_athlete_access_is_hidden_as_not_found(session: Session) -> None:
    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    try:
        first = TestClient(app).post(
            "/v1/onboarding/athletes",
            json=onboarding_body("First athlete"),
            headers=development_header("owner-one"),
        )
        second = TestClient(app).post(
            "/v1/onboarding/athletes",
            json={
                **onboarding_body("Second athlete"),
                "reported_at": "2026-08-22T20:01:00Z",
            },
            headers=development_header("owner-two"),
        )
        second_athlete_id = second.json()["athlete"]["id"]
        forbidden = TestClient(app).get(
            f"/v1/athletes/{second_athlete_id}/current-week",
            params={"on": "2026-08-22"},
            headers=development_header("owner-one"),
        )
        forbidden_workflow = TestClient(app).get(
            f"/v1/athletes/{second_athlete_id}/assessment-workflow",
            headers=development_header("owner-one"),
        )
        forbidden_dashboard = TestClient(app).get(
            f"/v1/athletes/{second_athlete_id}/dashboard",
            headers=development_header("owner-one"),
        )
        forbidden_environments = TestClient(app).get(
            f"/v1/athletes/{second_athlete_id}/environments",
            headers=development_header("owner-one"),
        )
        own = TestClient(app).get(
            f"/v1/athletes/{second_athlete_id}/current-week",
            params={"on": "2026-08-22"},
            headers=development_header("owner-two"),
        )
        forbidden_assessment = TestClient(app).post(
            f"/v1/athletes/{second_athlete_id}/assessment-runs",
            json={
                "environment_id": second.json()["environments"][0]["id"],
                "evaluated_at": "2026-08-22T20:02:00Z",
                "reliability": "low",
                "provenance": {
                    "recorded_by": "owner-one",
                    "source_system": "agas-web",
                    "ingestion_method": "assessment-context-form",
                },
            },
            headers=development_header("owner-one"),
        )
        forbidden_result = TestClient(app).post(
            f"/v1/athletes/{second_athlete_id}/assessment-runs/{uuid4()}"
            f"/selections/{uuid4()}/result",
            json={
                "performed_at": "2026-08-22T20:03:00Z",
                "measurement": 1,
                "unit": "fixture_unit",
                "reliability": "low",
                "provenance": {
                    "recorded_by": "owner-one",
                    "source_system": "agas-web",
                    "ingestion_method": "assessment-result-form",
                },
            },
            headers=development_header("owner-one"),
        )
        athlete_owner_operator_write = TestClient(app).post(
            f"/v1/operator/stimulus-requirements/{uuid4()}/exercise-reresolutions",
            json={},
            headers=development_header("owner-two"),
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert first.status_code == 201
    assert second.status_code == 201
    assert forbidden.status_code == 404
    assert forbidden.json() == {"detail": "athlete does not exist"}
    assert forbidden_workflow.status_code == 404
    assert forbidden_workflow.json() == {"detail": "athlete does not exist"}
    assert forbidden_dashboard.status_code == 404
    assert forbidden_dashboard.json() == {"detail": "athlete does not exist"}
    assert forbidden_environments.status_code == 404
    assert forbidden_environments.json() == {"detail": "athlete does not exist"}
    assert forbidden_assessment.status_code == 404
    assert forbidden_assessment.json() == {"detail": "athlete does not exist"}
    assert forbidden_result.status_code == 404
    assert forbidden_result.json() == {"detail": "athlete does not exist"}
    assert own.status_code == 200
    assert athlete_owner_operator_write.status_code == 403


def test_identity_and_owner_round_trip_and_reject_competing_ownership(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Fixture")
    first_account = Account(issuer="issuer", subject="first")
    second_account = Account(issuer="issuer", subject="second")
    ownership = AthleteOwnership(
        account_id=first_account.id,
        athlete_id=athlete.id,
        granted_at=REPORTED_AT,
        grant_method="fixture",
        rule_version="fixture-ownership@1.0.0",
    )
    repository.add_account(first_account)
    repository.add_account(second_account)
    repository.add_athlete(athlete)
    session.flush()
    repository.add_athlete_ownership(ownership)
    session.commit()

    session.expire_all()
    assert repository.get_account_by_identity("issuer", "first") == first_account
    assert repository.get_athlete_ownership(athlete.id) == ownership

    with pytest.raises(DomainIntegrityError, match="already has an owner"):
        repository.add_athlete_ownership(
            AthleteOwnership(
                account_id=second_account.id,
                athlete_id=athlete.id,
                granted_at=REPORTED_AT,
                grant_method="fixture",
                rule_version="fixture-ownership@1.0.0",
            )
        )

    account_record = session.get(AccountRecord, first_account.id)
    assert account_record is not None
    account_record.subject = "silently-rewritten"
    with pytest.raises(ImmutableHistoricalRecordError):
        session.commit()
    session.rollback()
    assert repository.get_account(first_account.id) == first_account


def test_local_operator_grant_is_idempotent_but_cannot_reassign_an_athlete(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Existing fixture")
    repository.add_athlete(athlete)
    session.commit()

    account, ownership, created = grant_athlete_ownership(
        session,
        athlete_id=athlete.id,
        issuer="urn:agas:development",
        subject="local-browser",
        granted_at=REPORTED_AT,
    )
    same_account, same_ownership, created_again = grant_athlete_ownership(
        session,
        athlete_id=athlete.id,
        issuer="urn:agas:development",
        subject="local-browser",
        granted_at=REPORTED_AT,
    )

    assert created is True
    assert created_again is False
    assert same_account == account
    assert same_ownership == ownership
    with pytest.raises(DomainIntegrityError, match="another account"):
        grant_athlete_ownership(
            session,
            athlete_id=athlete.id,
            issuer="urn:agas:development",
            subject="different-account",
            granted_at=REPORTED_AT,
        )
    session.rollback()


def test_planning_reviewer_role_is_append_only_revocable_and_required_by_queue(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    no_role_account = Account(
        created_at=REPORTED_AT,
        issuer="urn:agas:development",
        subject="registered-no-role",
    )
    repository.add_account(no_role_account)
    session.commit()

    reviewer, grant, created, changed = set_account_role(
        session,
        issuer="urn:agas:development",
        subject="reviewer-one",
        role=AccountRole.PLANNING_REVIEWER,
        status=AccountRoleStatus.ACTIVE,
        assigned_at=REPORTED_AT,
        rationale="Exercise the planning-reviewer authorization boundary.",
    )
    same_reviewer, same_grant, created_again, changed_again = set_account_role(
        session,
        issuer="urn:agas:development",
        subject="reviewer-one",
        role=AccountRole.PLANNING_REVIEWER,
        status=AccountRoleStatus.ACTIVE,
        assigned_at=REPORTED_AT,
        rationale="Idempotent repeated local grant.",
    )
    assert created is True
    assert changed is True
    assert created_again is False
    assert changed_again is False
    assert same_reviewer == reviewer
    assert same_grant == grant

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    try:
        unauthenticated = TestClient(app).get("/v1/operator/environment-review-queue")
        unregistered = TestClient(app).get(
            "/v1/operator/environment-review-queue",
            headers=development_header("unregistered-reviewer"),
        )
        no_role = TestClient(app).get(
            "/v1/operator/environment-review-queue",
            headers=development_header("registered-no-role"),
        )
        authorized = TestClient(app).get(
            "/v1/operator/environment-review-queue",
            headers=development_header("reviewer-one"),
            params={"projected_at": "2026-08-22T20:01:00Z"},
        )
        no_role_write = TestClient(app).post(
            f"/v1/operator/stimulus-requirements/{uuid4()}/exercise-reresolutions",
            json={},
            headers=development_header("registered-no-role"),
        )
        authorized_write_contract = TestClient(app).post(
            f"/v1/operator/stimulus-requirements/{uuid4()}/exercise-reresolutions",
            json={},
            headers=development_header("reviewer-one"),
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert unauthenticated.status_code == 401
    assert unregistered.status_code == 401
    assert no_role.status_code == 403
    assert no_role.json() == {"detail": "active planning_reviewer role required"}
    assert authorized.status_code == 200
    assert authorized.json()["items"] == []
    assert no_role_write.status_code == 403
    assert authorized_write_contract.status_code == 422

    _, revocation, _, revoked = set_account_role(
        session,
        issuer="urn:agas:development",
        subject="reviewer-one",
        role=AccountRole.PLANNING_REVIEWER,
        status=AccountRoleStatus.REVOKED,
        assigned_at=REPORTED_AT.replace(minute=1),
        rationale="Exercise append-only role revocation.",
    )
    assert revoked is True
    assert revocation.sequence_number == 2
    assert revocation.supersedes_assignment_id == grant.id
    assert repository.get_account_role_assignment(grant.id) == grant
    assert (
        repository.get_current_account_role_assignment(reviewer.id, AccountRole.PLANNING_REVIEWER)
        == revocation
    )

    app.dependency_overrides[database_session_dependency] = override_session
    try:
        revoked_response = TestClient(app).get(
            "/v1/operator/environment-review-queue",
            headers=development_header("reviewer-one"),
        )
        revoked_write = TestClient(app).post(
            f"/v1/operator/weekly-plans/{uuid4()}/environment-prescription-revisions",
            json={},
            headers=development_header("reviewer-one"),
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)
    assert revoked_response.status_code == 403
    assert revoked_write.status_code == 403

    history = repository.list_account_role_assignments(reviewer.id, AccountRole.PLANNING_REVIEWER)
    assert history == (grant, revocation)
    role_record = session.get(AccountRoleAssignmentRecord, grant.id)
    assert role_record is not None
    role_record.rationale = "silently rewritten"
    with pytest.raises(ImmutableHistoricalRecordError):
        session.commit()
    session.rollback()

    with pytest.raises(ValueError, match="first account role assignment"):
        AccountRoleAssignment(
            account_id=reviewer.id,
            role=AccountRole.PLANNING_REVIEWER,
            status=AccountRoleStatus.ACTIVE,
            sequence_number=1,
            supersedes_assignment_id=uuid4(),
            assigned_at=REPORTED_AT,
            assigned_by="fixture",
            rationale="Invalid lineage fixture.",
            rule_version="fixture-role@1.0.0",
        )
