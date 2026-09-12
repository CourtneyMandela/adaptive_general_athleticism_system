from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from agas_api.athlete_data_export import (
    AthleteDataExport,
    AthleteDataExporter,
    calculate_export_content_digest,
)
from agas_api.athlete_data_restore import (
    AthleteDataRestoreBlockedError,
    AthleteDataRestorer,
)
from agas_api.identity_admin import grant_athlete_ownership
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
from agas_domain.persistence.models import Base
from agas_domain.persistence.repository import DomainRepository
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

NOW = datetime(2026, 9, 12, 12, 0, tzinfo=UTC)
OWNER_ISSUER = "urn:agas:recovery-test"
OWNER_SUBJECT = "archive-owner"


@contextmanager
def _empty_database() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        with Session(engine, expire_on_commit=False) as target:
            yield target
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def _source_archive(session: Session) -> tuple[AthleteDataExport, Equipment]:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Recovery athlete", goals=("Build broad capability",))
    equipment = Equipment(
        name="Stable chair",
        category="support",
        capabilities={"stable_seat": True},
    )
    repository.add_athlete(athlete)
    repository.add_equipment(equipment)
    session.flush()
    grant_athlete_ownership(
        session,
        athlete_id=athlete.id,
        issuer=OWNER_ISSUER,
        subject=OWNER_SUBJECT,
        granted_at=NOW,
    )
    environment = Environment(athlete_id=athlete.id, name="Home")
    observation = Observation(
        athlete_id=athlete.id,
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
    repository.add_environment(environment)
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
    return AthleteDataExporter(session).export(athlete.id, generated_at=NOW), equipment


def test_preflight_blocks_missing_shared_dependencies_then_restores_round_trip(
    session: Session,
) -> None:
    archive, equipment = _source_archive(session)

    with _empty_database() as target:
        restorer = AthleteDataRestorer(target)
        missing = restorer.preflight(
            archive, owner_issuer=OWNER_ISSUER, owner_subject=OWNER_SUBJECT
        )

        assert missing.can_restore is False
        assert any(
            blocker.code == "missing_external_reference" and blocker.table_name == "equipment"
            for blocker in missing.blockers
        )

        DomainRepository(target).add_equipment(equipment)
        target.commit()
        ready = restorer.preflight(archive, owner_issuer=OWNER_ISSUER, owner_subject=OWNER_SUBJECT)
        assert ready.can_restore is True
        assert ready.target_has_no_athletes is True

        result = restorer.restore(
            archive,
            owner_issuer=OWNER_ISSUER,
            owner_subject=OWNER_SUBJECT,
            restored_at=NOW,
        )
        target.commit()

        assert result.round_trip_digest_verified is True
        assert result.content_digest == archive.manifest.content_digest
        assert result.inserted_table_counts["athletes"] == 1
        assert result.inserted_table_counts["equipment_availability"] == 1
        restored = AthleteDataExporter(target).export(archive.athlete_id, generated_at=NOW)
        assert restored.manifest.content_digest == archive.manifest.content_digest
        assert DomainRepository(target).get_athlete(archive.athlete_id) is not None

        blocked_again = restorer.preflight(
            archive, owner_issuer=OWNER_ISSUER, owner_subject=OWNER_SUBJECT
        )
        assert blocked_again.can_restore is False
        assert any(blocker.code == "target_contains_athletes" for blocker in blocked_again.blockers)


def test_preflight_detects_content_tampering_before_database_writes(session: Session) -> None:
    archive, equipment = _source_archive(session)
    payload = archive.model_dump(mode="json")
    athlete_table = next(table for table in payload["tables"] if table["table_name"] == "athletes")
    athlete_table["rows"][0]["display_name"] = "Tampered athlete"
    tampered = AthleteDataExport.model_validate(payload)

    with _empty_database() as target:
        DomainRepository(target).add_equipment(equipment)
        target.commit()
        preflight = AthleteDataRestorer(target).preflight(
            tampered, owner_issuer=OWNER_ISSUER, owner_subject=OWNER_SUBJECT
        )

        assert preflight.can_restore is False
        assert any(blocker.code == "digest_mismatch" for blocker in preflight.blockers)
        assert DomainRepository(target).get_athlete(archive.athlete_id) is None


def test_preflight_retains_compatibility_with_initial_export_version(session: Session) -> None:
    archive, equipment = _source_archive(session)
    legacy = archive.model_copy(
        update={
            "export_version": "athlete-data-export@1.0.0",
            "manifest": archive.manifest.model_copy(
                update={"restore_status": "restore requires a separately validated procedure"}
            ),
        }
    )
    legacy = legacy.model_copy(
        update={
            "manifest": legacy.manifest.model_copy(
                update={
                    "content_digest": calculate_export_content_digest(
                        legacy.athlete_id,
                        legacy.tables,
                        legacy.external_references,
                        export_version=legacy.export_version,
                    )
                }
            )
        }
    )

    with _empty_database() as target:
        DomainRepository(target).add_equipment(equipment)
        target.commit()
        preflight = AthleteDataRestorer(target).preflight(
            legacy, owner_issuer=OWNER_ISSUER, owner_subject=OWNER_SUBJECT
        )

        assert preflight.can_restore is True


def test_preflight_rejects_externalized_athlete_owned_dependencies(session: Session) -> None:
    archive, equipment = _source_archive(session)
    observation_table = next(
        table for table in archive.tables if table.table_name == "observations"
    )
    reduced_tables = tuple(table for table in archive.tables if table.table_name != "observations")
    availability = next(
        table for table in archive.tables if table.table_name == "equipment_availability"
    )
    source_observation_id = availability.rows[0]["source_observation_id"]
    references = [item.model_dump(mode="json") for item in archive.external_references]
    references.append(
        {
            "source_table": "equipment_availability",
            "source_column": "source_observation_id",
            "target_table": "observations",
            "target_column": "id",
            "target_value": source_observation_id,
        }
    )
    payload = archive.model_dump(mode="json")
    payload["tables"] = [table.model_dump(mode="json") for table in reduced_tables]
    payload["external_references"] = references
    payload["manifest"]["record_count"] -= len(observation_table.rows)
    payload["manifest"]["table_counts"].pop("observations")
    candidate = AthleteDataExport.model_validate(payload)
    candidate = candidate.model_copy(
        update={
            "manifest": candidate.manifest.model_copy(
                update={
                    "content_digest": calculate_export_content_digest(
                        candidate.athlete_id,
                        candidate.tables,
                        candidate.external_references,
                    )
                }
            )
        }
    )

    with _empty_database() as target:
        DomainRepository(target).add_equipment(equipment)
        target.commit()
        preflight = AthleteDataRestorer(target).preflight(
            candidate, owner_issuer=OWNER_ISSUER, owner_subject=OWNER_SUBJECT
        )

        assert preflight.can_restore is False
        assert any(blocker.code == "external_athlete_reference" for blocker in preflight.blockers)


def test_restore_refuses_invalid_archive_without_partial_inserts(session: Session) -> None:
    archive, _equipment = _source_archive(session)

    with _empty_database() as target:
        restorer = AthleteDataRestorer(target)
        try:
            restorer.restore(
                archive,
                owner_issuer=OWNER_ISSUER,
                owner_subject=OWNER_SUBJECT,
                restored_at=NOW,
            )
        except AthleteDataRestoreBlockedError as error:
            assert any(
                blocker.code == "missing_external_reference" for blocker in error.preflight.blockers
            )
        else:
            raise AssertionError("restore should have been blocked")

        assert DomainRepository(target).get_athlete(archive.athlete_id) is None
