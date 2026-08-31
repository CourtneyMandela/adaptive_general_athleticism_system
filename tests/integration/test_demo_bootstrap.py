from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from agas_api.database import database_session_dependency
from agas_api.demo import (
    DEMO_ASSESSMENT_REVIEWER_SUBJECT,
    DEMO_ATHLETE_SUBJECT,
    DEMO_FIXTURE_VERSION,
    DEMO_REVIEWER_SUBJECT,
    LocalDemoBootstrapError,
    bootstrap_local_demo,
)
from agas_api.identity import authenticated_principal_dependency
from agas_api.main import app
from agas_api.settings import Settings
from agas_domain import (
    AccountRole,
    AccountRoleStatus,
    Confidence,
    Observation,
    ObservationSource,
    Provenance,
)
from agas_domain.persistence.models import (
    AccountRecord,
    AthleteRecord,
    CatalogImportRecord,
    EnvironmentRecord,
    EquipmentAvailabilityRecord,
    EvidenceClaimRecord,
    ObservationRecord,
)
from agas_domain.persistence.repository import DomainRepository
from agas_seed_data import load_seed_catalog
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

BOOTSTRAPPED_AT = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)


def development_settings() -> Settings:
    return Settings(
        environment="development",
        auth_mode="development",
        development_auth_issuer="urn:agas:development",
        database_url="sqlite+pysqlite:///:memory:",
    )


def test_demo_bootstrap_is_idempotent_and_exposes_an_honest_browser_boundary(
    session: Session,
) -> None:
    catalog = load_seed_catalog()
    first = bootstrap_local_demo(
        session,
        settings=development_settings(),
        bootstrapped_at=BOOTSTRAPPED_AT,
    )
    repository = DomainRepository(session)
    account = repository.get_account_by_identity("urn:agas:development", DEMO_ATHLETE_SUBJECT)
    reviewer = repository.get_account_by_identity("urn:agas:development", DEMO_REVIEWER_SUBJECT)
    assessment_reviewer = repository.get_account_by_identity(
        "urn:agas:development", DEMO_ASSESSMENT_REVIEWER_SUBJECT
    )
    assert account is not None
    assert reviewer is not None
    assert assessment_reviewer is not None
    assert first.fixture_version == DEMO_FIXTURE_VERSION
    assert first.catalog_version == catalog.manifest.catalog_version
    assert first.catalog_created is True
    assert first.athlete_id == catalog.travel_scenario.athlete.id
    assert first.athlete_access_token == "dev.local-browser"
    assert first.reviewer_access_token == "dev.local-reviewer"
    assert first.assessment_reviewer_access_token == "dev.local-assessment-reviewer"
    assert first.planning_status == "capability_estimate_required"
    assert first.created_records == {
        "accounts": 3,
        "athletes": 1,
        "ownerships": 1,
        "role_assignments": 2,
        "observations": 1,
        "environments": 2,
        "equipment_availability": 11,
    }
    ownership = repository.get_athlete_ownership(first.athlete_id)
    assert ownership is not None
    assert ownership.account_id == account.id
    assignment = repository.get_current_account_role_assignment(
        reviewer.id, AccountRole.PLANNING_REVIEWER
    )
    assert assignment is not None
    assert assignment.id == first.reviewer_role_assignment_id
    assert assignment.status is AccountRoleStatus.ACTIVE
    assessment_assignment = repository.get_current_account_role_assignment(
        assessment_reviewer.id, AccountRole.ASSESSMENT_REVIEWER
    )
    assert assessment_assignment is not None
    assert assessment_assignment.id == first.assessment_reviewer_role_assignment_id
    assert assessment_assignment.status is AccountRoleStatus.ACTIVE

    demo_observation = session.scalar(
        select(ObservationRecord).where(
            ObservationRecord.observation_type == "synthetic_local_demo_profile_environment_report"
        )
    )
    assert demo_observation is not None
    assert demo_observation.context["synthetic"] is True
    assert demo_observation.context["operational_training_authority"] is False
    availability_source_ids = set(
        session.scalars(select(EquipmentAvailabilityRecord.source_observation_id)).all()
    )
    assert availability_source_ids == {demo_observation.id}
    assert session.scalar(select(func.count()).select_from(EvidenceClaimRecord)) == len(
        catalog.evidence_claims
    )

    historical_observation = Observation(
        athlete_id=first.athlete_id,
        observed_at=BOOTSTRAPPED_AT + timedelta(minutes=5),
        observation_type="synthetic_demo_follow_up",
        measurement={"note": "must survive a repeated bootstrap"},
        source=ObservationSource.MANUAL_ENTRY,
        reliability=Confidence.LOW,
        provenance=Provenance(
            recorded_by="test",
            source_system="test-suite",
            ingestion_method="regression-fixture",
        ),
    )
    repository.add_observation(historical_observation)
    session.commit()
    counts_before = _bootstrap_record_counts(session)

    second = bootstrap_local_demo(
        session,
        settings=development_settings(),
        bootstrapped_at=BOOTSTRAPPED_AT + timedelta(hours=1),
    )

    assert second.catalog_created is False
    assert second.created_records == {key: 0 for key in first.created_records}
    assert second.athlete_id == first.athlete_id
    assert second.reviewer_role_assignment_id == first.reviewer_role_assignment_id
    assert (
        second.assessment_reviewer_role_assignment_id
        == first.assessment_reviewer_role_assignment_id
    )
    assert repository.get_observation(historical_observation.id) == historical_observation
    assert _bootstrap_record_counts(session) == counts_before

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    try:
        queue_response = TestClient(app).get(
            "/v1/operator/planning-review-queue",
            params={"at": BOOTSTRAPPED_AT.isoformat()},
            headers={"Authorization": "Bearer dev.local-reviewer"},
        )
        assessment_governance_response = TestClient(app).get(
            "/v1/operator/assessment-governance",
            params={"at": BOOTSTRAPPED_AT.isoformat()},
            headers={"Authorization": "Bearer dev.local-assessment-reviewer"},
        )
        athlete_response = TestClient(app).get(
            f"/v1/athletes/{first.athlete_id}/current-week",
            params={"on": "2026-08-30"},
            headers={"Authorization": "Bearer dev.local-browser"},
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert queue_response.status_code == 200
    demo_queue_item = next(
        item
        for item in queue_response.json()["items"]
        if item["athlete_id"] == str(first.athlete_id)
    )
    assert demo_queue_item["status"] == "capability_estimate_required"
    assert demo_queue_item["readiness"] == "blocked"
    assert assessment_governance_response.status_code == 200
    assert assessment_governance_response.json()["items"] == []
    assert athlete_response.status_code == 200
    assert athlete_response.json()["athlete_display_name"] == "Synthetic four-day traveler"
    assert athlete_response.json()["week"] is None


def test_demo_bootstrap_fails_closed_outside_local_development(session: Session) -> None:
    with pytest.raises(
        LocalDemoBootstrapError, match="local demo bootstrap is disabled in production"
    ):
        bootstrap_local_demo(
            session,
            settings=Settings(
                environment="production",
                auth_mode="external",
                external_auth_issuer="https://issuer.example/",
                external_auth_audience="https://api.agas.example",
                external_auth_jwks_url="https://issuer.example/.well-known/jwks.json",
                database_url="sqlite+pysqlite:///:memory:",
            ),
            bootstrapped_at=BOOTSTRAPPED_AT,
        )

    assert session.scalar(select(func.count()).select_from(AccountRecord)) == 0
    assert session.scalar(select(func.count()).select_from(AthleteRecord)) == 0
    assert session.scalar(select(func.count()).select_from(CatalogImportRecord)) == 0


def _bootstrap_record_counts(session: Session) -> tuple[int, ...]:
    return tuple(
        session.scalar(select(func.count()).select_from(record_type)) or 0
        for record_type in (
            AccountRecord,
            AthleteRecord,
            ObservationRecord,
            EnvironmentRecord,
            EquipmentAvailabilityRecord,
            CatalogImportRecord,
        )
    )
