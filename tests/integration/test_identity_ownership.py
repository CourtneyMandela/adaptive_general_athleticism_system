from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from agas_api.database import database_session_dependency
from agas_api.identity import authenticated_principal_dependency
from agas_api.identity_admin import grant_athlete_ownership
from agas_api.main import app
from agas_domain import Account, Athlete, AthleteOwnership
from agas_domain.persistence.models import (
    AccountRecord,
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
        f"/v1/blocks/{identity}/reviews",
        f"/v1/block-reviews/{identity}/replan",
        f"/v1/strategies/{identity}/blocks",
        f"/v1/strategies/{identity}/priorities/{identity}/resource-demands",
        f"/v1/blocks/{identity}/weekly-plans",
        f"/v1/weekly-plans/{identity}/roll-forward",
        f"/v1/weekly-plans/{identity}/sessions/{identity}/safety-checks",
        f"/v1/weekly-plans/{identity}/sessions/{identity}/executions",
        f"/v1/session-executions/{identity}/prescriptions/{identity}/progression",
    )
    app.dependency_overrides.pop(authenticated_principal_dependency, None)

    current_week = TestClient(app).get(
        f"/v1/athletes/{identity}/current-week", params={"on": "2026-08-22"}
    )
    post_responses = [TestClient(app).post(path, json={}) for path in protected_posts]

    assert current_week.status_code == 401
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
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert unauthenticated.status_code == 401
    assert unauthenticated.json() == {"detail": "bearer authentication required"}
    assert created.status_code == 201
    assert current_week.status_code == 200
    assert current_week.json()["week"] is None

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
        own = TestClient(app).get(
            f"/v1/athletes/{second_athlete_id}/current-week",
            params={"on": "2026-08-22"},
            headers=development_header("owner-two"),
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert first.status_code == 201
    assert second.status_code == 201
    assert forbidden.status_code == 404
    assert forbidden.json() == {"detail": "athlete does not exist"}
    assert own.status_code == 200


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
