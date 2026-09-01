from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[2]


def _service(blueprint: dict[str, Any], name: str) -> dict[str, Any]:
    services = cast(list[dict[str, Any]], blueprint["services"])
    return next(service for service in services if service["name"] == name)


def _environment(service: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = cast(list[dict[str, Any]], service["envVars"])
    return {cast(str, entry["key"]): entry for entry in entries}


def test_staging_blueprint_preserves_private_data_and_secret_boundaries() -> None:
    blueprint = cast(
        dict[str, Any],
        yaml.safe_load((ROOT / "render.yaml").read_text(encoding="utf-8")),
    )
    api = _service(blueprint, "agas-api-staging")
    web = _service(blueprint, "agas-courtneymandela-staging")
    api_environment = _environment(api)
    web_environment = _environment(web)

    assert api["type"] == "pserv"
    assert api["preDeployCommand"] == "alembic upgrade head"
    assert api["autoDeployTrigger"] == "checksPass"
    assert api_environment["AGAS_DATABASE_URL"]["fromDatabase"] == {
        "name": "agas-postgres-staging",
        "property": "connectionString",
    }
    assert api_environment["AGAS_AUTH_MODE"]["value"] == "external"
    assert api_environment["AGAS_ENVIRONMENT"]["value"] == "production"

    assert web["type"] == "web"
    assert web["autoDeployTrigger"] == "checksPass"
    assert web_environment["AGAS_INTERNAL_API_HOSTPORT"]["fromService"] == {
        "name": "agas-api-staging",
        "type": "pserv",
        "property": "hostport",
    }
    assert web_environment["NEXT_PUBLIC_API_URL"]["value"] == "/api/agas"
    assert web_environment["NEXT_PUBLIC_AGAS_AUTH_MODE"]["value"] == "session"
    assert (
        api_environment["AGAS_EXTERNAL_AUTH_AUDIENCE"]["value"]
        == web_environment["AGAS_OIDC_AUDIENCE"]["value"]
    )

    for key in (
        "AGAS_SESSION_ENCRYPTION_KEY",
        "AGAS_OIDC_ISSUER",
        "AGAS_OIDC_AUTHORIZATION_URL",
        "AGAS_OIDC_TOKEN_URL",
        "AGAS_OIDC_JWKS_URL",
        "AGAS_OIDC_CLIENT_ID",
        "AGAS_OIDC_CLIENT_SECRET",
    ):
        assert web_environment[key] == {"key": key, "sync": False}
    for key in ("AGAS_EXTERNAL_AUTH_ISSUER", "AGAS_EXTERNAL_AUTH_JWKS_URL"):
        assert api_environment[key] == {"key": key, "sync": False}

    databases = cast(list[dict[str, Any]], blueprint["databases"])
    assert databases == [
        {
            "name": "agas-postgres-staging",
            "plan": "0.1c-256mb",
            "region": "virginia",
            "databaseName": "agas",
            "user": "agas",
            "postgresMajorVersion": "16",
            "ipAllowList": [],
        }
    ]
