from datetime import UTC, datetime

import agas_api.identity as identity_module
import pytest
from agas_api.identity import DevelopmentBearerVerifier, IdentityAuthenticationError
from agas_api.settings import Settings
from agas_domain import Account, AthleteOwnership
from fastapi import HTTPException
from pydantic import ValidationError


def test_account_identity_is_opaque_case_sensitive_and_normalized() -> None:
    account = Account(issuer=" urn:issuer ", subject=" Subject-A ")

    assert account.issuer == "urn:issuer"
    assert account.subject == "Subject-A"
    assert Account(issuer="urn:issuer", subject="subject-a").subject != account.subject
    with pytest.raises(ValidationError, match="at least 1 character"):
        Account(issuer="", subject="subject")


def test_ownership_requires_an_explicit_aware_grant_time() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        AthleteOwnership(
            account_id=Account(issuer="issuer", subject="subject").id,
            athlete_id=Account(issuer="issuer", subject="another").id,
            granted_at=datetime(2026, 8, 22),
            grant_method="fixture",
            rule_version="fixture@1.0.0",
        )


def test_development_verifier_accepts_only_bounded_dev_subjects() -> None:
    verifier = DevelopmentBearerVerifier("urn:agas:development")

    principal = verifier.verify("dev.local-browser")
    assert principal.issuer == "urn:agas:development"
    assert principal.subject == "local-browser"
    assert principal.authentication_method == "development-bearer"
    assert principal.test_bypass is False

    for invalid in ("local-browser", "dev.a", "dev.contains spaces", "prod.local-browser"):
        with pytest.raises(IdentityAuthenticationError):
            verifier.verify(invalid)


def test_production_configuration_rejects_development_authentication() -> None:
    with pytest.raises(ValidationError, match="production environments"):
        Settings(environment="production", auth_mode="development")

    settings = Settings(environment="production", auth_mode="external")
    assert settings.auth_mode == "external"


def test_external_mode_fails_closed_until_a_verifier_is_connected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        identity_module,
        "get_settings",
        lambda: Settings(environment="development", auth_mode="external"),
    )

    with pytest.raises(HTTPException) as raised:
        identity_module.authenticated_principal_dependency("Bearer external-token")

    assert raised.value.status_code == 503
    assert raised.value.detail == "external token verification is not configured"


def test_identity_record_timestamps_remain_utc_aware() -> None:
    recorded_at = datetime(2026, 8, 22, 20, 0, tzinfo=UTC)
    account = Account(created_at=recorded_at, issuer="issuer", subject="subject")
    assert account.created_at == recorded_at
