from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from agas_api.database import database_session_dependency
from agas_api.main import app
from agas_api.onboarding import AthleteOnboardingResult
from agas_domain import Equipment, EquipmentAvailability
from agas_domain.persistence.models import (
    AccountRecord,
    AthleteOwnershipRecord,
    AthleteRecord,
    EnvironmentRecord,
    EquipmentAvailabilityRecord,
    ObservationRecord,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy import func, select
from sqlalchemy.orm import Session

REPORTED_AT = datetime(2026, 8, 22, 16, 0, tzinfo=UTC)


def request_body(equipment: tuple[Equipment, ...]) -> dict[str, Any]:
    return {
        "display_name": "  Onboarding Athlete  ",
        "goals": ["Build broad athletic capacity", "Enjoy recreational hiking"],
        "preferred_activities": ["Hiking", "Cycling"],
        "disliked_activities": ["Long treadmill sessions"],
        "environments": [
            {
                "name": " Home ",
                "floor_area_m2": 12,
                "noise_constraints": "Keep impact quiet after 8 PM",
                "max_noise_level": "low",
                "outdoor_access": True,
                "equipment": [
                    {"equipment_id": str(equipment[0].id)},
                    {
                        "equipment_id": str(equipment[1].id),
                        "load_limits": {"maximum_total_kg": 40},
                    },
                ],
            },
            {
                "name": "Travel",
                "max_noise_level": "moderate",
                "outdoor_access": False,
                "equipment": [{"equipment_id": str(equipment[0].id)}],
            },
        ],
        "reported_at": REPORTED_AT.isoformat(),
        "reliability": "moderate",
        "provenance": {
            "recorded_by": "unverified-athlete-user",
            "source_system": "agas-web",
            "ingestion_method": "onboarding-form",
        },
    }


def test_onboarding_catalog_and_transaction_preserve_reported_profile_provenance(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    equipment = (
        Equipment(name="Open floor area", category="space"),
        Equipment(name="Adjustable dumbbells", category="external_load"),
    )
    for item in equipment:
        repository.add_equipment(item)
    session.commit()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    try:
        options_response = TestClient(app).get("/v1/onboarding/equipment")
        response = TestClient(app).post("/v1/onboarding/athletes", json=request_body(equipment))
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert options_response.status_code == 200
    assert [item["name"] for item in options_response.json()] == [
        "Adjustable dumbbells",
        "Open floor area",
    ]
    assert response.status_code == 201
    result = AthleteOnboardingResult.model_validate(response.json())
    assert result.athlete.display_name == "Onboarding Athlete"
    assert result.athlete.goals == (
        "Build broad athletic capacity",
        "Enjoy recreational hiking",
    )
    assert result.athlete.preferences == {
        "preferred_activities": ["Hiking", "Cycling"],
        "disliked_activities": ["Long treadmill sessions"],
    }
    assert result.intake_observation.athlete_id == result.athlete.id
    assert result.intake_observation.observation_type == ("onboarding_profile_environment_report")
    measurement = cast(dict[str, Any], result.intake_observation.measurement)
    assert measurement["environments"][0]["name"] == "Home"
    assert result.intake_observation.reliability.value == "moderate"
    assert result.intake_observation.provenance.ingestion_method == "onboarding-form"
    assert tuple(item.name for item in result.environments) == ("Home", "Travel")
    assert result.environments[0].space_constraints == {"floor_area_m2": 12.0}
    assert len(result.equipment_availability) == 3
    assert all(
        item.source_observation_id == result.intake_observation.id
        for item in result.equipment_availability
    )
    assert all(
        str(result.intake_observation.id) in (item.reason or "")
        for item in result.equipment_availability
    )

    session.expire_all()
    assert repository.get_athlete(result.athlete.id) == result.athlete
    assert repository.get_observation(result.intake_observation.id) == result.intake_observation
    for environment in result.environments:
        assert repository.get_environment(environment.id) == environment
    assert (
        sum(
            len(repository.list_equipment_availability(environment.id))
            for environment in result.environments
        )
        == 3
    )


def test_onboarding_rejects_unknown_equipment_without_partial_profile(session: Session) -> None:
    repository = DomainRepository(session)
    known = Equipment(name="Known floor", category="space")
    repository.add_equipment(known)
    session.commit()
    body = request_body((known, Equipment(name="Missing", category="external_load")))
    missing_id = uuid4()
    body["environments"][0]["equipment"][0]["equipment_id"] = str(missing_id)

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    try:
        response = TestClient(app).post("/v1/onboarding/athletes", json=body)
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code == 404
    assert response.json() == {"detail": f"equipment selection {missing_id} does not exist"}
    assert session.scalar(select(func.count()).select_from(AthleteRecord)) == 0
    assert session.scalar(select(func.count()).select_from(ObservationRecord)) == 0


def test_onboarding_rolls_back_a_late_environment_persistence_failure(
    session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    repository = DomainRepository(session)
    equipment = (
        Equipment(name="Floor", category="space"),
        Equipment(name="Dumbbells", category="external_load"),
    )
    for item in equipment:
        repository.add_equipment(item)
    session.commit()
    counts_before = tuple(
        session.scalar(select(func.count()).select_from(record_type))
        for record_type in (
            AccountRecord,
            AthleteRecord,
            AthleteOwnershipRecord,
            ObservationRecord,
            EnvironmentRecord,
            EquipmentAvailabilityRecord,
        )
    )

    def reject_availability(
        _repository: DomainRepository, _availability: EquipmentAvailability
    ) -> None:
        raise DomainIntegrityError("synthetic late onboarding failure")

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    try:
        with monkeypatch.context() as context:
            context.setattr(
                DomainRepository,
                "add_equipment_availability",
                reject_availability,
            )
            response = TestClient(app).post("/v1/onboarding/athletes", json=request_body(equipment))
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    counts_after = tuple(
        session.scalar(select(func.count()).select_from(record_type))
        for record_type in (
            AccountRecord,
            AthleteRecord,
            AthleteOwnershipRecord,
            ObservationRecord,
            EnvironmentRecord,
            EquipmentAvailabilityRecord,
        )
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "synthetic late onboarding failure"}
    assert counts_after == counts_before


def test_onboarding_transport_rejects_ambiguous_or_unversioned_reports(
    session: Session,
) -> None:
    equipment = (
        Equipment(name="Floor", category="space"),
        Equipment(name="Dumbbells", category="external_load"),
    )
    repository = DomainRepository(session)
    for item in equipment:
        repository.add_equipment(item)
    session.commit()
    body = request_body(equipment)

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    try:
        duplicate_environment_response = TestClient(app).post(
            "/v1/onboarding/athletes",
            json={
                **body,
                "environments": [
                    body["environments"][0],
                    {**body["environments"][0], "name": "home"},
                ],
            },
        )
        contradictory_preference_response = TestClient(app).post(
            "/v1/onboarding/athletes",
            json={
                **body,
                "disliked_activities": ["cycling"],
            },
        )
        naive_time_response = TestClient(app).post(
            "/v1/onboarding/athletes",
            json={**body, "reported_at": "2026-08-22T16:00:00"},
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert duplicate_environment_response.status_code == 422
    assert contradictory_preference_response.status_code == 422
    assert naive_time_response.status_code == 422
