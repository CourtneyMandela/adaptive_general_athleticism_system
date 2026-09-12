from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

from agas_api.athlete_data_export import AthleteDataExporter
from agas_api.database import database_session_dependency
from agas_api.identity import authenticated_principal_dependency
from agas_api.identity_admin import grant_athlete_ownership
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
from agas_domain.persistence.repository import DomainRepository
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

NOW = datetime(2026, 9, 11, 18, 0, tzinfo=UTC)


def _seed_two_athletes(session: Session) -> tuple[Athlete, Athlete, Equipment]:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Export owner", goals=("Build broad capability",))
    other = Athlete(display_name="Different owner")
    repository.add_athlete(athlete)
    repository.add_athlete(other)
    equipment = Equipment(
        name="Stable chair",
        category="support",
        capabilities={"stable_seat": True},
    )
    repository.add_equipment(equipment)
    session.flush()

    for index, owner in enumerate((athlete, other)):
        environment = Environment(athlete_id=owner.id, name=f"Home {index + 1}")
        repository.add_environment(environment)
        observation = Observation(
            athlete_id=owner.id,
            observed_at=NOW,
            observation_type="equipment_report",
            measurement={"stable_chair": True},
            source=ObservationSource.USER_REPORT,
            reliability=Confidence.MODERATE,
            provenance=Provenance(
                recorded_by="fixture",
                source_system="test-suite",
                ingestion_method="test",
            ),
        )
        repository.add_observation(observation)
        session.flush()
        repository.add_equipment_availability(
            EquipmentAvailability(
                environment_id=environment.id,
                equipment_id=equipment.id,
                source_observation_id=observation.id,
                is_available=True,
                effective_from=NOW,
            )
        )
    session.commit()
    return athlete, other, equipment


def test_owner_export_includes_dependent_history_and_excludes_other_athletes(
    session: Session,
) -> None:
    athlete, other, equipment = _seed_two_athletes(session)

    export = AthleteDataExporter(session).export(athlete.id, generated_at=NOW)
    repeated = AthleteDataExporter(session).export(
        athlete.id, generated_at=NOW + timedelta(minutes=1)
    )
    tables = {item.table_name: item for item in export.tables}

    assert export.manifest.content_digest == repeated.manifest.content_digest
    assert export.manifest.record_count == sum(export.manifest.table_counts.values())
    assert len(tables["athletes"].rows) == 1
    assert len(tables["environments"].rows) == 1
    assert len(tables["observations"].rows) == 1
    assert len(tables["equipment_availability"].rows) == 1
    assert "equipment" not in tables
    assert all(str(other.id) not in str(table.rows) for table in export.tables)
    assert any(
        reference.target_table == "equipment" and reference.target_value == str(equipment.id)
        for reference in export.external_references
    )
    assert export.manifest.restore_status == "restore requires a separately validated procedure"


def test_export_digest_changes_when_athlete_history_changes(session: Session) -> None:
    athlete, _other, _equipment = _seed_two_athletes(session)
    before = AthleteDataExporter(session).export(athlete.id, generated_at=NOW)
    DomainRepository(session).add_observation(
        Observation(
            athlete_id=athlete.id,
            observed_at=NOW + timedelta(minutes=2),
            observation_type="new_report",
            measurement={"value": 1},
            source=ObservationSource.USER_REPORT,
            reliability=Confidence.UNKNOWN,
            provenance=Provenance(
                recorded_by="fixture",
                source_system="test-suite",
                ingestion_method="test",
            ),
        )
    )
    session.commit()

    after = AthleteDataExporter(session).export(athlete.id, generated_at=NOW)

    assert before.manifest.content_digest != after.manifest.content_digest
    assert after.manifest.table_counts["observations"] == 2


def test_data_export_endpoint_requires_authentication_and_serializes_manifest(
    session: Session,
) -> None:
    athlete, _other, _equipment = _seed_two_athletes(session)

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    authenticated_override = app.dependency_overrides[authenticated_principal_dependency]
    try:
        authorized = TestClient(app).get(f"/v1/athletes/{athlete.id}/data-export")
        app.dependency_overrides.pop(authenticated_principal_dependency)
        unauthenticated = TestClient(app).get(f"/v1/athletes/{athlete.id}/data-export")
    finally:
        app.dependency_overrides[authenticated_principal_dependency] = authenticated_override
        app.dependency_overrides.pop(database_session_dependency, None)

    assert authorized.status_code == 200, authorized.text
    assert authorized.json()["athlete_id"] == str(athlete.id)
    assert authorized.json()["manifest"]["content_digest"].startswith("sha256:")
    assert unauthenticated.status_code == 401


def test_data_export_endpoint_enforces_athlete_ownership(session: Session) -> None:
    athlete, other, _equipment = _seed_two_athletes(session)
    grant_athlete_ownership(
        session,
        athlete_id=athlete.id,
        issuer="urn:agas:development",
        subject="export-owner",
        granted_at=NOW,
    )

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    authenticated_override = app.dependency_overrides.pop(authenticated_principal_dependency)
    try:
        client = TestClient(app)
        headers = {"Authorization": "Bearer dev.export-owner"}
        owned = client.get(f"/v1/athletes/{athlete.id}/data-export", headers=headers)
        not_owned = client.get(f"/v1/athletes/{other.id}/data-export", headers=headers)
    finally:
        app.dependency_overrides[authenticated_principal_dependency] = authenticated_override
        app.dependency_overrides.pop(database_session_dependency, None)

    assert owned.status_code == 200, owned.text
    assert not_owned.status_code == 404
    assert not_owned.json() == {"detail": "athlete does not exist"}
