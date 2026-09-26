from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from agas_api.database import database_session, get_engine, get_session_factory
from agas_api.identity import authenticated_principal_dependency
from agas_api.main import app
from agas_api.settings import get_settings
from agas_domain import Equipment
from agas_domain.persistence.repository import DomainRepository
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_DATABASE_ENVIRONMENT_VARIABLE = "AGAS_TEST_DATABASE_URL"
OWNER_SUBJECT = "postgres-golden-owner"
OTHER_SUBJECT = "postgres-golden-other"
REPORTED_AT = datetime(2026, 9, 23, 14, 0, tzinfo=UTC)


def _clear_database_configuration() -> None:
    get_session_factory.cache_clear()
    get_engine.cache_clear()
    get_settings.cache_clear()


@pytest.fixture
def migrated_postgres_database(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    database_url = os.getenv(TEST_DATABASE_ENVIRONMENT_VARIABLE)
    if not database_url:
        pytest.skip(
            f"set {TEST_DATABASE_ENVIRONMENT_VARIABLE} to run the PostgreSQL API golden path"
        )

    parsed_url = make_url(database_url)
    if parsed_url.get_backend_name() != "postgresql":
        pytest.fail(f"{TEST_DATABASE_ENVIRONMENT_VARIABLE} must use PostgreSQL")
    if parsed_url.database is None or not parsed_url.database.casefold().endswith("_test"):
        pytest.fail(
            f"{TEST_DATABASE_ENVIRONMENT_VARIABLE} must target a dedicated database ending in _test"
        )

    monkeypatch.setenv("AGAS_DATABASE_URL", database_url)
    _clear_database_configuration()
    migration_config = Config(str(PROJECT_ROOT / "alembic.ini"))
    migration_config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))

    try:
        command.upgrade(migration_config, "head")
        yield
    finally:
        get_engine().dispose()
        command.downgrade(migration_config, "base")
        _clear_database_configuration()


def _onboarding_body(
    *, display_name: str, equipment_id: UUID, reported_at: datetime
) -> dict[str, Any]:
    return {
        "display_name": display_name,
        "goals": ["Build broad athletic capacity"],
        "preferred_activities": ["Hiking"],
        "disliked_activities": [],
        "environments": [
            {
                "name": "Home",
                "floor_area_m2": 10,
                "max_noise_level": "low",
                "outdoor_access": True,
                "equipment": [{"equipment_id": str(equipment_id)}],
            }
        ],
        "reported_at": reported_at.isoformat(),
        "reliability": "moderate",
        "provenance": {
            "recorded_by": display_name,
            "source_system": "agas-postgres-golden-path",
            "ingestion_method": "onboarding-form",
        },
    }


def test_migrated_postgres_api_onboarding_preserves_provenance_and_owner_isolation(
    migrated_postgres_database: None,
) -> None:
    floor = Equipment(name="PostgreSQL golden-path floor", category="space")
    with database_session() as session:
        DomainRepository(session).add_equipment(floor)
        session.commit()

    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    owner_headers = {"Authorization": f"Bearer dev.{OWNER_SUBJECT}"}
    other_headers = {"Authorization": f"Bearer dev.{OTHER_SUBJECT}"}

    with TestClient(app) as client:
        assert client.get("/ready").json() == {"status": "ready"}
        equipment_response = client.get("/v1/onboarding/equipment")
        empty_directory_response = client.get("/v1/athletes", headers=owner_headers)
        owner_onboarding_response = client.post(
            "/v1/onboarding/athletes",
            headers=owner_headers,
            json=_onboarding_body(
                display_name="PostgreSQL owner",
                equipment_id=floor.id,
                reported_at=REPORTED_AT,
            ),
        )
        other_onboarding_response = client.post(
            "/v1/onboarding/athletes",
            headers=other_headers,
            json=_onboarding_body(
                display_name="PostgreSQL other owner",
                equipment_id=floor.id,
                reported_at=REPORTED_AT + timedelta(minutes=1),
            ),
        )

        assert equipment_response.status_code == 200
        assert equipment_response.json() == [
            {
                "equipment_id": str(floor.id),
                "name": floor.name,
                "category": floor.category,
                "capabilities": {},
            }
        ]
        assert empty_directory_response.status_code == 200
        assert empty_directory_response.json()["athletes"] == []
        assert owner_onboarding_response.status_code == 201
        assert other_onboarding_response.status_code == 201

        owner_result = owner_onboarding_response.json()
        owner_athlete_id = UUID(owner_result["athlete"]["id"])
        owner_observation_id = UUID(owner_result["intake_observation"]["id"])
        owner_environment_id = UUID(owner_result["environments"][0]["id"])

        owner_directory_response = client.get("/v1/athletes", headers=owner_headers)
        other_directory_response = client.get("/v1/athletes", headers=other_headers)
        owner_environment_response = client.get(
            f"/v1/athletes/{owner_athlete_id}/environments",
            headers=owner_headers,
        )
        forbidden_cross_owner_response = client.get(
            f"/v1/athletes/{owner_athlete_id}/environments",
            headers=other_headers,
        )

    assert owner_directory_response.status_code == 200
    assert [item["athlete_id"] for item in owner_directory_response.json()["athletes"]] == [
        str(owner_athlete_id)
    ]
    assert [item["display_name"] for item in other_directory_response.json()["athletes"]] == [
        "PostgreSQL other owner"
    ]
    assert owner_environment_response.status_code == 200
    assert owner_environment_response.json()["environments"][0]["environment_id"] == str(
        owner_environment_id
    )
    assert forbidden_cross_owner_response.status_code == 404

    with database_session() as session:
        repository = DomainRepository(session)
        observation = repository.get_observation(owner_observation_id)
        ownership = repository.get_athlete_ownership(owner_athlete_id)
        assert observation is not None
        assert observation.athlete_id == owner_athlete_id
        assert observation.provenance.source_system == "agas-postgres-golden-path"
        assert observation.context == {
            "onboarding_rule_version": "profile-environment-onboarding@1.0.0"
        }
        assert ownership is not None
        assert ownership.grant_method == "self-service-onboarding"
        account = repository.get_account(ownership.account_id)
        assert account is not None
        assert account.issuer == "urn:agas:development"
        assert account.subject == OWNER_SUBJECT
