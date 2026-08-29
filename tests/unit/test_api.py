from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

from agas_api.database import database_session_dependency
from agas_api.main import app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_health_reports_service_version() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "agas-api", "version": "0.1.0"}


def test_current_week_endpoint_reports_missing_athlete_and_requires_date(
    session: Session,
) -> None:
    def override_session() -> Iterator[Session]:
        yield session

    path = f"/v1/athletes/{uuid4()}/current-week"
    app.dependency_overrides[database_session_dependency] = override_session
    try:
        missing_athlete_response = TestClient(app).get(path, params={"on": "2026-08-24"})
        missing_date_response = TestClient(app).get(path)
        invalid_date_response = TestClient(app).get(path, params={"on": "not-a-date"})
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert missing_athlete_response.status_code == 404
    assert missing_athlete_response.json() == {"detail": "athlete does not exist"}
    assert missing_date_response.status_code == 422
    assert invalid_date_response.status_code == 422


def test_post_block_authoring_is_not_exposed_to_athlete_http_clients() -> None:
    block_id = uuid4()
    review_id = uuid4()

    review_response = TestClient(app).post(f"/v1/blocks/{block_id}/reviews", json={})
    replanning_response = TestClient(app).post(f"/v1/block-reviews/{review_id}/replan", json={})

    assert review_response.status_code == 404
    assert replanning_response.status_code == 404


def test_resource_and_block_authoring_are_not_exposed_to_athlete_http_clients() -> None:
    strategy_id = uuid4()
    priority_id = uuid4()
    demand_response = TestClient(app).post(
        f"/v1/strategies/{strategy_id}/priorities/{priority_id}/resource-demands",
        json={},
    )
    block_response = TestClient(app).post(f"/v1/strategies/{strategy_id}/blocks", json={})

    assert demand_response.status_code == 404
    assert block_response.status_code == 404


def test_weekly_plan_authoring_is_not_exposed_to_athlete_http_clients() -> None:
    response = TestClient(app).post(f"/v1/blocks/{uuid4()}/weekly-plans", json={})

    assert response.status_code == 404


def test_progression_endpoint_reports_missing_execution_and_rejects_naive_time(
    session: Session,
) -> None:
    def override_session() -> Iterator[Session]:
        yield session

    execution_id = uuid4()
    prescription_id = uuid4()
    path = f"/v1/session-executions/{execution_id}/prescriptions/{prescription_id}/progression"
    request_body = {
        "decided_at": datetime(2026, 8, 22, tzinfo=UTC).isoformat(),
    }
    app.dependency_overrides[database_session_dependency] = override_session
    try:
        missing_execution_response = TestClient(app).post(path, json=request_body)
        naive_time_response = TestClient(app).post(
            path, json={**request_body, "decided_at": "2026-08-22T00:00:00"}
        )
        client_policy_response = TestClient(app).post(
            path,
            json={**request_body, "progression_policy_id": str(uuid4())},
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert missing_execution_response.status_code == 404
    assert missing_execution_response.json() == {"detail": "session execution does not exist"}
    assert naive_time_response.status_code == 422
    assert client_policy_response.status_code == 422
