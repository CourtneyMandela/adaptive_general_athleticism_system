from collections.abc import Iterator

from agas_api.database import database_session_dependency
from agas_api.identity import authenticated_principal_dependency
from agas_api.main import app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def onboarding_body(display_name: str, reported_at: str, goal: str) -> dict[str, object]:
    return {
        "display_name": display_name,
        "goals": [goal],
        "preferred_activities": [],
        "disliked_activities": [],
        "environments": [
            {
                "name": "Home" if display_name != "Other account" else "Gym",
                "max_noise_level": "moderate",
                "outdoor_access": False,
                "equipment": [],
            }
        ],
        "reported_at": reported_at,
        "reliability": "moderate",
        "provenance": {
            "recorded_by": "unverified-athlete-user",
            "source_system": "agas-web",
            "ingestion_method": "onboarding-form",
        },
    }


def header(subject: str) -> dict[str, str]:
    return {"Authorization": f"Bearer dev.{subject}"}


def test_directory_recovers_only_exact_accounts_owned_profiles(session: Session) -> None:
    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    client = TestClient(app)
    try:
        unauthenticated = client.get("/v1/athletes")
        unregistered = client.get("/v1/athletes", headers=header("new-owner"))
        older = client.post(
            "/v1/onboarding/athletes",
            json=onboarding_body(
                "Courtney Szabo",
                "2026-08-22T20:00:00Z",
                "Build broad athletic capacity",
            ),
            headers=header("owner-one"),
        )
        newer = client.post(
            "/v1/onboarding/athletes",
            json=onboarding_body(
                "Courtney Szabo",
                "2026-08-23T20:00:00Z",
                "Train consistently",
            ),
            headers=header("owner-one"),
        )
        other = client.post(
            "/v1/onboarding/athletes",
            json=onboarding_body(
                "Other account",
                "2026-08-24T20:00:00Z",
                "Unrelated goal",
            ),
            headers=header("owner-two"),
        )
        directory = client.get("/v1/athletes", headers=header("owner-one"))
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert unauthenticated.status_code == 401
    assert unregistered.status_code == 200
    assert unregistered.json() == {
        "projection_version": "account-athlete-directory@1.0.0",
        "athletes": [],
    }
    assert older.status_code == newer.status_code == other.status_code == 201
    assert directory.status_code == 200
    payload = directory.json()
    assert payload["projection_version"] == "account-athlete-directory@1.0.0"
    assert [item["athlete_id"] for item in payload["athletes"]] == [
        newer.json()["athlete"]["id"],
        older.json()["athlete"]["id"],
    ]
    assert [item["goals"] for item in payload["athletes"]] == [
        ["Train consistently"],
        ["Build broad athletic capacity"],
    ]
    assert payload["athletes"][0]["environments"][0]["name"] == "Home"
    assert payload["athletes"][0]["ownership_rule_version"] == (
        "profile-environment-onboarding@1.0.0"
    )
    assert all(item["display_name"] == "Courtney Szabo" for item in payload["athletes"])
    assert all(item["athlete_id"] != other.json()["athlete"]["id"] for item in payload["athletes"])
