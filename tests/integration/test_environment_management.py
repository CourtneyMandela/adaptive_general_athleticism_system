from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from agas_api.database import database_session_dependency
from agas_api.environment_management import (
    EnvironmentManagementValidationError,
    PersistedEquipmentStateService,
    RecordEquipmentStateCommand,
    get_athlete_environment_projection,
)
from agas_api.main import app
from agas_domain import (
    Athlete,
    Confidence,
    Environment,
    Equipment,
    EquipmentAvailability,
    Observation,
    ObservationSource,
    Provenance,
)
from agas_domain.persistence.models import EquipmentAvailabilityRecord, ObservationRecord
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

BASE = datetime(2026, 8, 28, 14, 0, tzinfo=UTC)
PROVENANCE = {
    "recorded_by": "unverified-athlete-user",
    "source_system": "agas-web",
    "ingestion_method": "equipment-state-form",
}


def test_equipment_report_preserves_observation_lineage_and_temporary_state(
    session: Session,
) -> None:
    repository, athlete, environment, floor, dumbbells, bike, baseline = _fixture(session)
    command_body = {
        "changes": [
            {
                "equipment_id": str(dumbbells.id),
                "is_available": False,
                "effective_from": (BASE + timedelta(days=1)).isoformat(),
                "effective_until": (BASE + timedelta(days=3)).isoformat(),
                "reason": "Temporary hotel maintenance",
            },
            {
                "equipment_id": str(floor.id),
                "is_available": True,
                "effective_from": (BASE + timedelta(days=1)).isoformat(),
            },
        ],
        "reported_at": (BASE + timedelta(hours=2)).isoformat(),
        "reliability": "moderate",
        "provenance": PROVENANCE,
        "report_reason": "Travel equipment check",
    }

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    try:
        response = TestClient(app).post(
            f"/v1/athletes/{athlete.id}/environments/{environment.id}/equipment-reports",
            json=command_body,
        )
        during_response = TestClient(app).get(
            f"/v1/athletes/{athlete.id}/environments",
            params={"at": (BASE + timedelta(days=2)).isoformat()},
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code == 201
    assert during_response.status_code == 200
    result = response.json()
    observation_id = result["observation"]["id"]
    assert result["observation"]["observation_type"] == "equipment_environment_state_report"
    measurement = cast(dict[str, Any], result["observation"]["measurement"])
    assert measurement["environment_id"] == str(environment.id)
    assert measurement["report_reason"] == "Travel equipment check"
    assert len(measurement["changes"]) == 2
    assert all(
        item["source_observation_id"] == observation_id for item in result["availability_events"]
    )

    during = during_response.json()["environments"][0]
    states = {item["equipment_id"]: item for item in during["equipment"]}
    assert states[str(dumbbells.id)]["state"] == "unavailable"
    assert states[str(dumbbells.id)]["source_observation_id"] == observation_id
    assert states[str(floor.id)]["state"] == "available"
    assert states[str(bike.id)]["state"] == "unknown"

    after = get_athlete_environment_projection(session, athlete.id, BASE + timedelta(days=4))
    after_states = {item.equipment_id: item for item in after.environments[0].equipment}
    assert after_states[dumbbells.id].state == "available"
    assert after_states[dumbbells.id].availability_event_id == baseline.id
    assert repository.get_athlete(athlete.id) == athlete


def test_equipment_report_is_partial_and_rolls_back_a_late_event_failure(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, athlete, environment, _floor, dumbbells, bike, baseline = _fixture(session)
    command = RecordEquipmentStateCommand.model_validate(
        {
            "changes": [
                {
                    "equipment_id": str(bike.id),
                    "is_available": True,
                    "effective_from": (BASE + timedelta(days=1)).isoformat(),
                }
            ],
            "reported_at": (BASE + timedelta(hours=3)).isoformat(),
            "reliability": "low",
            "provenance": PROVENANCE,
            "report_reason": "Bike added",
        }
    )
    counts_before = (
        session.scalar(select(func.count()).select_from(ObservationRecord)),
        session.scalar(select(func.count()).select_from(EquipmentAvailabilityRecord)),
    )

    def reject_event(_repository: DomainRepository, _event: EquipmentAvailability) -> None:
        raise DomainIntegrityError("synthetic equipment event failure")

    with monkeypatch.context() as patch_context:
        patch_context.setattr(DomainRepository, "add_equipment_availability", reject_event)
        with pytest.raises(
            EnvironmentManagementValidationError,
            match="synthetic equipment event failure",
        ):
            PersistedEquipmentStateService(session).execute(athlete.id, environment.id, command)

    counts_after = (
        session.scalar(select(func.count()).select_from(ObservationRecord)),
        session.scalar(select(func.count()).select_from(EquipmentAvailabilityRecord)),
    )
    assert counts_after == counts_before
    current = get_athlete_environment_projection(session, athlete.id, BASE + timedelta(days=2))
    states = {item.equipment_id: item.state for item in current.environments[0].equipment}
    assert states[dumbbells.id] == "available"
    assert states[bike.id] == "unknown"
    assert repository.list_equipment_availability(environment.id) == (baseline,)


def test_equipment_report_rejects_duplicates_naive_times_and_cross_athlete_sources(
    session: Session,
) -> None:
    repository, athlete, environment, _floor, dumbbells, _bike, _baseline = _fixture(session)
    duplicate_change = {
        "equipment_id": str(dumbbells.id),
        "is_available": False,
        "effective_from": (BASE + timedelta(days=1)).isoformat(),
    }
    base_body = {
        "changes": [duplicate_change],
        "reported_at": (BASE + timedelta(hours=2)).isoformat(),
        "reliability": "moderate",
        "provenance": PROVENANCE,
        "report_reason": "Fixture",
    }

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    try:
        duplicate_response = TestClient(app).post(
            f"/v1/athletes/{athlete.id}/environments/{environment.id}/equipment-reports",
            json={**base_body, "changes": [duplicate_change, duplicate_change]},
        )
        naive_response = TestClient(app).post(
            f"/v1/athletes/{athlete.id}/environments/{environment.id}/equipment-reports",
            json={
                **base_body,
                "changes": [{**duplicate_change, "effective_from": "2026-08-29T14:00:00"}],
            },
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert duplicate_response.status_code == 422
    assert naive_response.status_code == 422

    other = Athlete(created_at=BASE, display_name="Other athlete")
    repository.add_athlete(other)
    session.flush()
    other_observation = Observation(
        created_at=BASE,
        athlete_id=other.id,
        observed_at=BASE,
        observation_type="other_fixture",
        measurement=True,
        source=ObservationSource.USER_REPORT,
        reliability=Confidence.LOW,
        provenance=Provenance.model_validate(PROVENANCE),
    )
    repository.add_observation(other_observation)
    session.flush()
    with pytest.raises(DomainIntegrityError, match="another athlete"):
        repository.add_equipment_availability(
            EquipmentAvailability(
                environment_id=environment.id,
                equipment_id=dumbbells.id,
                source_observation_id=other_observation.id,
                is_available=False,
                effective_from=BASE + timedelta(days=1),
            )
        )


def _fixture(
    session: Session,
) -> tuple[
    DomainRepository,
    Athlete,
    Environment,
    Equipment,
    Equipment,
    Equipment,
    EquipmentAvailability,
]:
    repository = DomainRepository(session)
    athlete = Athlete(created_at=BASE, display_name="Travel fixture", goals=("Stay active",))
    repository.add_athlete(athlete)
    environment = Environment(
        created_at=BASE,
        athlete_id=athlete.id,
        name="Hotel",
        space_constraints={"floor_area_m2": 10},
        noise_constraints="No impact after 9 PM",
        outdoor_access=True,
    )
    repository.add_environment(environment)
    floor = Equipment(name="Open floor", category="space")
    dumbbells = Equipment(name="Light dumbbells", category="external_load")
    bike = Equipment(name="Stationary bike", category="cardio")
    for item in (floor, dumbbells, bike):
        repository.add_equipment(item)
    session.flush()
    baseline_observation = Observation(
        created_at=BASE,
        athlete_id=athlete.id,
        observed_at=BASE,
        observation_type="baseline_equipment_fixture",
        measurement={"equipment_id": str(dumbbells.id), "available": True},
        source=ObservationSource.USER_REPORT,
        reliability=Confidence.MODERATE,
        provenance=Provenance.model_validate(PROVENANCE),
    )
    repository.add_observation(baseline_observation)
    session.flush()
    baseline = EquipmentAvailability(
        created_at=BASE,
        environment_id=environment.id,
        equipment_id=dumbbells.id,
        source_observation_id=baseline_observation.id,
        is_available=True,
        effective_from=BASE,
        load_limits={"maximum_total_kg": 20},
        reason="Baseline report",
    )
    repository.add_equipment_availability(baseline)
    session.commit()
    return repository, athlete, environment, floor, dumbbells, bike, baseline
