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


def test_replanning_endpoint_reports_missing_review_without_creating_state(
    session: Session,
) -> None:
    def override_session() -> Iterator[Session]:
        yield session

    request_body = {
        "candidate_contexts": [
            {
                "adaptation_id": str(uuid4()),
                "competency_floor_id": str(uuid4()),
                "capability_estimate_id": str(uuid4()),
                "general_relevance": 0.5,
                "goal_relevance": 0.5,
                "prerequisite_value": 0.5,
                "expected_trainability": 0.5,
                "transfer_value": 0.5,
                "fatigue_cost": 0.5,
                "time_cost": 0.5,
                "interference_cost": 0.5,
            }
        ],
        "generated_at": datetime(2026, 8, 22, tzinfo=UTC).isoformat(),
        "review_after_days": 42,
    }
    app.dependency_overrides[database_session_dependency] = override_session
    try:
        response = TestClient(app).post(
            f"/v1/block-reviews/{uuid4()}/replan",
            json=request_body,
        )
        naive_time_response = TestClient(app).post(
            f"/v1/block-reviews/{uuid4()}/replan",
            json={**request_body, "generated_at": "2026-08-22T00:00:00"},
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "block review does not exist"}
    assert naive_time_response.status_code == 422
