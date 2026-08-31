import json
from datetime import UTC, datetime, timedelta
from typing import Any

import agas_api.identity as identity_module
import pytest
from agas_api.identity import (
    DevelopmentBearerVerifier,
    ExternalJWTVerifier,
    IdentityAuthenticationError,
    IdentityAuthenticationUnavailableError,
)
from agas_api.settings import Settings
from agas_domain import Account, AthleteOwnership
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jwt import PyJWKClient, encode
from jwt.algorithms import RSAAlgorithm
from jwt.exceptions import PyJWKClientConnectionError
from pydantic import ValidationError


class StaticJWKClient(PyJWKClient):
    def __init__(self, jwk_set: dict[str, Any]) -> None:
        super().__init__("https://issuer.example/.well-known/jwks.json")
        self.jwk_set = jwk_set

    def fetch_data(self) -> dict[str, Any]:
        return self.jwk_set


class UnavailableJWKClient(PyJWKClient):
    def __init__(self) -> None:
        super().__init__("https://issuer.example/.well-known/jwks.json")

    def get_signing_key_from_jwt(self, token: str | bytes) -> Any:
        raise PyJWKClientConnectionError("synthetic provider outage")


def external_verifier() -> tuple[ExternalJWTVerifier, rsa.RSAPrivateKey]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": "fixture-key", "alg": "RS256", "use": "sig"})
    return (
        ExternalJWTVerifier(
            issuer="https://issuer.example/",
            audience="https://api.agas.example",
            jwks_url="https://issuer.example/.well-known/jwks.json",
            algorithms=("RS256",),
            leeway_seconds=30,
            jwks_timeout_seconds=5,
            jwks_cache_seconds=300,
            jwks_client=StaticJWKClient({"keys": [public_jwk]}),
        ),
        private_key,
    )


def external_token(
    private_key: rsa.RSAPrivateKey,
    *,
    issuer: str = "https://issuer.example/",
    audience: str = "https://api.agas.example",
    subject: str | None = "opaque-provider-subject",
    expires_at: datetime | None = None,
) -> str:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": expires_at or now + timedelta(minutes=5),
    }
    if subject is not None:
        claims["sub"] = subject
    return encode(claims, private_key, algorithm="RS256", headers={"kid": "fixture-key"})


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

    with pytest.raises(ValidationError, match="requires issuer, audience, and JWKS"):
        Settings(environment="production", auth_mode="external")

    settings = Settings(
        environment="production",
        auth_mode="external",
        external_auth_issuer="https://issuer.example/",
        external_auth_audience="https://api.agas.example",
        external_auth_jwks_url="https://issuer.example/.well-known/jwks.json",
    )
    assert settings.auth_mode == "external"

    with pytest.raises(ValidationError, match="must use HTTPS"):
        Settings(
            environment="production",
            auth_mode="external",
            external_auth_issuer="http://issuer.example/",
            external_auth_audience="https://api.agas.example",
            external_auth_jwks_url="https://issuer.example/.well-known/jwks.json",
        )

    with pytest.raises(ValidationError, match="at least 1 item"):
        Settings(external_auth_algorithms=())
    with pytest.raises(ValidationError, match="Input should be"):
        Settings(external_auth_algorithms=("HS256",))


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


def test_external_verifier_rejects_an_unsafe_direct_algorithm_configuration() -> None:
    for algorithms in ((), ("HS256",)):
        with pytest.raises(ValueError, match="asymmetric allow-list"):
            ExternalJWTVerifier(
                issuer="https://issuer.example/",
                audience="https://api.agas.example",
                jwks_url="https://issuer.example/.well-known/jwks.json",
                algorithms=algorithms,
                leeway_seconds=30,
                jwks_timeout_seconds=5,
                jwks_cache_seconds=300,
            )


def test_external_verifier_accepts_only_the_exact_signed_resource_server_contract() -> None:
    verifier, private_key = external_verifier()

    principal = verifier.verify(external_token(private_key))

    assert principal.issuer == "https://issuer.example/"
    assert principal.subject == "opaque-provider-subject"
    assert principal.authentication_method == "external-jwt"
    assert principal.test_bypass is False

    other_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(UTC)
    invalid_tokens = (
        external_token(private_key, issuer="https://other-issuer.example/"),
        external_token(private_key, audience="https://other-api.example"),
        external_token(private_key, subject=None),
        external_token(private_key, subject="   "),
        external_token(private_key, expires_at=datetime.now(UTC) - timedelta(minutes=5)),
        external_token(other_private_key),
        encode(
            {
                "iss": "https://issuer.example/",
                "aud": "https://api.agas.example",
                "iat": now,
                "exp": now + timedelta(minutes=5),
                "sub": "opaque-provider-subject",
            },
            "attacker-selected-symmetric-secret",
            algorithm="HS256",
            headers={"kid": "fixture-key"},
        ),
    )
    for invalid_token in invalid_tokens:
        with pytest.raises(IdentityAuthenticationError, match="token is invalid"):
            verifier.verify(invalid_token)


def test_external_verifier_distinguishes_signing_key_outage_without_leaking_details() -> None:
    verifier = ExternalJWTVerifier(
        issuer="https://issuer.example/",
        audience="https://api.agas.example",
        jwks_url="https://issuer.example/.well-known/jwks.json",
        algorithms=("RS256",),
        leeway_seconds=30,
        jwks_timeout_seconds=5,
        jwks_cache_seconds=300,
        jwks_client=UnavailableJWKClient(),
    )

    with pytest.raises(
        IdentityAuthenticationUnavailableError,
        match="signing keys are temporarily unavailable",
    ) as raised:
        verifier.verify("token-contents-must-not-appear")

    assert "token-contents" not in str(raised.value)


def test_identity_record_timestamps_remain_utc_aware() -> None:
    recorded_at = datetime(2026, 8, 22, 20, 0, tzinfo=UTC)
    account = Account(created_at=recorded_at, issuer="issuer", subject="subject")
    assert account.created_at == recorded_at
