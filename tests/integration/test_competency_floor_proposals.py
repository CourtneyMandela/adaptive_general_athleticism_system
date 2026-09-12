import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from agas_api.competency_floor_proposals import (
    CompetencyFloorProposalValidationError,
    competency_floor_proposal_batch,
)
from agas_api.database import database_session_dependency
from agas_api.identity import authenticated_principal_dependency
from agas_api.identity_admin import set_account_role
from agas_api.main import app
from agas_domain import AccountRole, AccountRoleStatus, CapabilityDomain
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

NOW = datetime(2026, 9, 12, 18, 0, tzinfo=UTC)


def test_proposal_batch_spans_domains_and_discloses_non_evidence_values() -> None:
    batch = competency_floor_proposal_batch()
    source_by_id = {source.source_id: source for source in batch.source_catalog}
    proposal_by_slug = {proposal.slug: proposal for proposal in batch.proposals}

    assert len(batch.proposals) == 15
    assert batch.content_digest.startswith("sha256:")
    assert len({proposal.content_digest for proposal in batch.proposals}) == 15
    assert {
        CapabilityDomain.AEROBIC_CAPACITY,
        CapabilityDomain.MAXIMUM_STRENGTH,
        CapabilityDomain.MUSCULAR_ENDURANCE,
        CapabilityDomain.EXPLOSIVE_POWER,
        CapabilityDomain.BALANCE_COORDINATION,
        CapabilityDomain.REPEATED_EFFORT_CAPACITY,
        CapabilityDomain.RELATIVE_STRENGTH,
        CapabilityDomain.LOADED_LOCOMOTION,
        CapabilityDomain.MOVEMENT_VERSATILITY,
        CapabilityDomain.CHANGE_OF_DIRECTION,
    }.issubset({proposal.domain for proposal in batch.proposals})
    assert source_by_id["acsm-12-table-3-8"].isbn13 == "9781975219246"
    assert source_by_id["nsca-5-table-14-34"].isbn13 == "9781718216273"
    assert proposal_by_slug["treadmill_vo2max_male_30_39_p55"].threshold == 41.6
    carry = proposal_by_slug["loaded_carry_0_5xbw_100m"]
    assert carry.operational_use_origin == "professional_judgment_required"
    assert carry.source_ids == ()
    assert "not found" in carry.evidence_gap
    assert all(proposal.stage == "proposal_only" for proposal in batch.proposals)


def test_proposal_loader_rejects_stale_artifact_digest(tmp_path: Path) -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "governance_proposals"
        / "competency_floors"
        / "owner_alpha_reference_batch.json"
    )
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["proposals"][0]["threshold"] = 99
    destination = tmp_path / "stale.json"
    destination.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CompetencyFloorProposalValidationError, match="stale content digest"):
        competency_floor_proposal_batch(destination)
    competency_floor_proposal_batch.cache_clear()


def test_proposal_endpoint_is_read_only_and_requires_planning_authority(
    session: Session,
) -> None:
    for subject, role in (
        ("assessment-only", AccountRole.ASSESSMENT_REVIEWER),
        ("planning-reviewer", AccountRole.PLANNING_REVIEWER),
    ):
        set_account_role(
            session,
            issuer="urn:agas:development",
            subject=subject,
            role=role,
            status=AccountRoleStatus.ACTIVE,
            assigned_at=NOW - timedelta(days=1),
            rationale="Competency-floor proposal review authorization.",
        )

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    try:
        client = TestClient(app)
        unauthenticated = client.get("/v1/operator/competency-floor-proposals")
        forbidden = client.get(
            "/v1/operator/competency-floor-proposals",
            headers={"Authorization": "Bearer dev.assessment-only"},
        )
        allowed = client.get(
            "/v1/operator/competency-floor-proposals",
            headers={"Authorization": "Bearer dev.planning-reviewer"},
        )
        no_ratification_route = client.post(
            "/v1/operator/competency-floor-proposals/ratifications",
            headers={"Authorization": "Bearer dev.planning-reviewer"},
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert unauthenticated.status_code == 401
    assert forbidden.status_code == 403
    assert allowed.status_code == 200
    assert len(allowed.json()["proposals"]) == 15
    assert no_ratification_route.status_code == 404
