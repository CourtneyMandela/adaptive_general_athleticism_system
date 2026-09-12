from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from agas_api.database import database_session_dependency
from agas_api.identity import AuthenticatedPrincipal, authenticated_principal_dependency
from agas_api.identity_admin import grant_athlete_ownership, set_account_role
from agas_api.main import app
from agas_api.owner_alpha_access import OwnerAlphaAccessError, OwnerAlphaAccessService
from agas_api.settings import Settings, get_settings
from agas_domain import AccountRole, AccountRoleStatus, Athlete
from agas_domain.persistence.repository import DomainRepository
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

ISSUER = "urn:agas:development"
SUBJECT = "courtney-owner"
NOW = datetime(2026, 9, 12, 12, 0, tzinfo=UTC)


def configured_settings(subject: str | None = SUBJECT) -> Settings:
    return Settings(
        environment="development",
        auth_mode="development",
        development_auth_issuer=ISSUER,
        owner_alpha_operator_subject=subject,
    )


def principal(subject: str = SUBJECT) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        issuer=ISSUER,
        subject=subject,
        authentication_method="development-bearer",
    )


def seed_owned_athlete(session: Session, subject: str = SUBJECT) -> None:
    athlete = Athlete(created_at=NOW, display_name="Owner alpha")
    DomainRepository(session).add_athlete(athlete)
    session.commit()
    grant_athlete_ownership(
        session,
        athlete_id=athlete.id,
        issuer=ISSUER,
        subject=subject,
        granted_at=NOW,
    )


def test_exact_owner_may_activate_both_required_roles_idempotently(session: Session) -> None:
    seed_owned_athlete(session)
    service = OwnerAlphaAccessService(session, configured_settings())

    before = service.project(principal())
    first = service.activate(principal(), activated_at=NOW)
    second = service.activate(principal(), activated_at=NOW + timedelta(minutes=1))

    assert before.status == "eligible"
    assert before.can_activate is True
    assert first.activated is True
    assert first.access.status == "active"
    assert second.activated is False
    assert second.access.status == "active"
    repository = DomainRepository(session)
    account = repository.get_account_by_identity(ISSUER, SUBJECT)
    assert account is not None
    for role in (AccountRole.ASSESSMENT_REVIEWER, AccountRole.PLANNING_REVIEWER):
        history = repository.list_account_role_assignments(account.id, role)
        assert len(history) == 1
        assert history[0].status is AccountRoleStatus.ACTIVE
        assert history[0].assigned_by == f"owner-alpha-activation:{ISSUER}:{SUBJECT}"


def test_activation_requires_configured_exact_identity_and_owned_athlete(session: Session) -> None:
    unconfigured = OwnerAlphaAccessService(session, configured_settings(None))
    assert unconfigured.project(principal()).status == "not_configured"
    with pytest.raises(OwnerAlphaAccessError, match="not allowlisted"):
        unconfigured.activate(principal())

    mismatched = OwnerAlphaAccessService(session, configured_settings())
    assert mismatched.project(principal("someone-else")).status == "identity_not_allowlisted"
    with pytest.raises(OwnerAlphaAccessError, match="not the deployment-allowlisted"):
        mismatched.activate(principal("someone-else"))

    wrong_issuer = AuthenticatedPrincipal(
        issuer="https://different-issuer.example/",
        subject=SUBJECT,
        authentication_method="external-jwt",
    )
    assert mismatched.project(wrong_issuer).status == "identity_not_allowlisted"
    with pytest.raises(OwnerAlphaAccessError, match="not the deployment-allowlisted"):
        mismatched.activate(wrong_issuer)

    assert mismatched.project(principal()).status == "account_required"
    with pytest.raises(OwnerAlphaAccessError, match="athlete profile"):
        mismatched.activate(principal())


def test_revoked_role_cannot_be_self_reactivated(session: Session) -> None:
    seed_owned_athlete(session)
    service = OwnerAlphaAccessService(session, configured_settings())
    service.activate(principal(), activated_at=NOW)
    set_account_role(
        session,
        issuer=ISSUER,
        subject=SUBJECT,
        role=AccountRole.PLANNING_REVIEWER,
        status=AccountRoleStatus.REVOKED,
        assigned_at=NOW + timedelta(minutes=1),
        rationale="Exercise irreversible owner-alpha revocation boundary.",
    )

    projection = service.project(principal())
    assert projection.status == "revoked"
    assert projection.can_activate is False
    with pytest.raises(OwnerAlphaAccessError, match="revoked"):
        service.activate(principal(), activated_at=NOW + timedelta(minutes=2))


def test_wildcard_owner_subject_is_rejected() -> None:
    with pytest.raises(ValidationError, match="cannot be a wildcard"):
        configured_settings("*")


def test_authenticated_endpoint_reports_and_activates_exact_owner(session: Session) -> None:
    seed_owned_athlete(session)
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    app.dependency_overrides[database_session_dependency] = lambda: session
    app.dependency_overrides[get_settings] = configured_settings
    client = TestClient(app)
    try:
        before = client.get(
            "/v1/owner-alpha/operator-access",
            headers={"Authorization": f"Bearer dev.{SUBJECT}"},
        )
        activated = client.post(
            "/v1/owner-alpha/operator-access/activation",
            headers={"Authorization": f"Bearer dev.{SUBJECT}"},
            json={"attestation": True},
        )
        repeated = client.post(
            "/v1/owner-alpha/operator-access/activation",
            headers={"Authorization": f"Bearer dev.{SUBJECT}"},
            json={"attestation": True},
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)
        app.dependency_overrides.pop(get_settings, None)

    assert before.status_code == 200
    assert before.json()["status"] == "eligible"
    assert before.json()["authenticated_subject"] == SUBJECT
    assert activated.status_code == 200
    assert activated.json()["activated"] is True
    assert activated.json()["access"]["status"] == "active"
    assert repeated.status_code == 200
    assert repeated.json()["activated"] is False


def test_activation_endpoint_rejects_mismatch_and_false_attestation(session: Session) -> None:
    seed_owned_athlete(session)
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    app.dependency_overrides[database_session_dependency] = lambda: session
    app.dependency_overrides[get_settings] = configured_settings
    client = TestClient(app)
    try:
        mismatch = client.post(
            "/v1/owner-alpha/operator-access/activation",
            headers={"Authorization": "Bearer dev.someone-else"},
            json={"attestation": True},
        )
        unattested = client.post(
            "/v1/owner-alpha/operator-access/activation",
            headers={"Authorization": f"Bearer dev.{SUBJECT}"},
            json={"attestation": False},
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)
        app.dependency_overrides.pop(get_settings, None)

    assert mismatch.status_code == 403
    assert unattested.status_code == 422
