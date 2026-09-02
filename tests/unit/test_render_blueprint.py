import json
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[2]


def _load(relative_path: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8")),
    )


def _service(blueprint: dict[str, Any], name: str) -> dict[str, Any]:
    services = cast(list[dict[str, Any]], blueprint["services"])
    return next(service for service in services if service["name"] == name)


def _environment(service: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = cast(list[dict[str, Any]], service["envVars"])
    return {cast(str, entry["key"]): entry for entry in entries}


def test_default_blueprint_is_a_no_card_single_service_alpha() -> None:
    blueprint = _load("render.yaml")
    services = cast(list[dict[str, Any]], blueprint["services"])

    assert [service["name"] for service in services] == ["agas-api-staging"]
    assert "databases" not in blueprint

    api = services[0]
    api_environment = _environment(api)
    assert api["type"] == "web"
    assert api["plan"] == "free"
    assert api["healthCheckPath"] == "/ready"
    assert api["autoDeployTrigger"] == "commit"
    assert "maxShutdownDelaySeconds" not in api
    assert "preDeployCommand" not in api

    assert api_environment["AGAS_MIGRATE_ON_STARTUP"]["value"] == "true"
    assert api_environment["AGAS_AUTH_MODE"]["value"] == "external"
    assert api_environment["AGAS_ENVIRONMENT"]["value"] == "production"
    assert api_environment["AGAS_CORS_ORIGINS"]["value"] == "[]"

    for key in (
        "AGAS_DATABASE_URL",
        "AGAS_EXTERNAL_AUTH_ISSUER",
        "AGAS_EXTERNAL_AUTH_JWKS_URL",
    ):
        assert api_environment[key] == {"key": key, "sync": False}


def test_paid_private_topology_remains_an_explicit_future_option() -> None:
    blueprint = _load("deploy/render-paid.yaml")
    api = _service(blueprint, "agas-api-staging")
    web = _service(blueprint, "agas-courtneymandela-staging")
    api_environment = _environment(api)
    web_environment = _environment(web)

    assert api["type"] == "pserv"
    assert api["plan"] != "free"
    assert api["preDeployCommand"] == "alembic upgrade head"
    assert api_environment["AGAS_DATABASE_URL"]["fromDatabase"] == {
        "name": "agas-postgres-staging",
        "property": "connectionString",
    }

    assert web["type"] == "web"
    assert web["plan"] != "free"
    assert web_environment["AGAS_INTERNAL_API_HOSTPORT"]["fromService"] == {
        "name": "agas-api-staging",
        "type": "pserv",
        "property": "hostport",
    }
    assert (
        api_environment["AGAS_EXTERNAL_AUTH_AUDIENCE"]["value"]
        == web_environment["AGAS_OIDC_AUDIENCE"]["value"]
    )

    databases = cast(list[dict[str, Any]], blueprint["databases"])
    assert databases[0]["ipAllowList"] == []


def test_api_container_migrations_are_explicitly_opt_in() -> None:
    entrypoint = (ROOT / "services/api/docker-entrypoint.sh").read_text(encoding="utf-8")
    dockerfile = (ROOT / "services/api/Dockerfile").read_text(encoding="utf-8")

    assert "${AGAS_MIGRATE_ON_STARTUP:-false}" in entrypoint
    assert "alembic upgrade head" in entrypoint
    assert 'exec "$@"' in entrypoint
    assert 'ENTRYPOINT ["agas-api-entrypoint"]' in dockerfile


def test_vercel_manifest_preserves_nextjs_server_runtime() -> None:
    manifest = json.loads((ROOT / "apps/web/vercel.json").read_text(encoding="utf-8"))
    gateway_route = (ROOT / "apps/web/app/api/agas/[...path]/route.ts").read_text(encoding="utf-8")

    assert manifest == {
        "$schema": "https://openapi.vercel.sh/vercel.json",
        "framework": "nextjs",
    }
    assert 'export const runtime = "nodejs";' in gateway_route
    assert "export const maxDuration = 60;" in gateway_route
