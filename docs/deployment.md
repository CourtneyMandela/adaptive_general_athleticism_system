# Deployment boundary

## What exists

AGAS can be packaged into two provider-neutral Linux container images:

- `services/api/Dockerfile` builds the FastAPI resource server and Alembic migration runtime.
- `apps/web/Dockerfile` builds the responsive Next.js application using standalone output.

Both final images run as non-root users, declare health checks, and exclude development/test
tooling from their final runtime stages. GitHub CI validates the Compose model and builds both
images on Linux for every pull request and push to `main`.

`compose.production.yml` is a reviewable single-host reference. It demonstrates these invariants:

1. PostgreSQL is authoritative and is not published on a host port.
2. The migration job waits for a healthy database and must finish successfully before the API.
3. The PWA waits for API readiness.
4. Only the PWA port binds to host loopback; FastAPI remains on the private Compose network.
5. Production API startup requires external authentication with HTTPS issuer/JWKS settings.
6. No development bearer selector is passed to a production container.
7. The production PWA image includes an install manifest, maskable icon, and fail-closed offline
   shell without storing athlete records.
8. Production browser API calls use a relative same-origin gateway, an encrypted server session,
   and no JavaScript-readable access token.

The reference database is useful for validating topology. A real deployment may use managed
PostgreSQL instead, but it must retain migration ordering, encrypted transport where appropriate,
backups, and restore validation.

## Configuration boundary

Copy `.env.production.example` to a secret-managed path outside the repository. The example is a
schema, not a usable environment. Replace every hostname and credential.

`NEXT_PUBLIC_API_URL=/api/agas` and `NEXT_PUBLIC_AGAS_AUTH_MODE=session` are intentionally public
build values. Changing them requires rebuilding the image. Never place a provider secret or access
token in `NEXT_PUBLIC_*`.

All `AGAS_EXTERNAL_AUTH_*` values are server-only runtime configuration. The API accepts only a
token with the configured issuer, audience, asymmetric signature, required timestamps, and subject.
The web runtime's `AGAS_INTERNAL_API_URL`, `AGAS_PUBLIC_WEB_ORIGIN`, and
`AGAS_SESSION_ENCRYPTION_KEY` are server-only. Generate the session key from exactly 32 random bytes
encoded as unpadded base64url. Every `AGAS_OIDC_*` value is also server-only. The configured provider
must support a confidential client using authorization code, S256 PKCE, OIDC nonce,
`client_secret_basic`, and asymmetric signed ID tokens. Register the exact callback
`https://YOUR-WEB-ORIGIN/auth/callback`. The optional resource URI and configured scopes must cause
the provider to issue a JWT access token whose issuer and API audience satisfy FastAPI's separate
`AGAS_EXTERNAL_AUTH_*` contract. The reference Compose model deliberately maps the API's external
issuer and JWKS URL into the web verifier so those two trust boundaries cannot drift independently.

Passwords embedded in `AGAS_DATABASE_URL` must be URL-encoded. Prefer a deployment secret store over
a long-lived plaintext environment file. Do not commit the populated file.

## Reference validation and startup

From the repository root:

```bash
docker compose --env-file /secure/path/agas.production.env \
  -f compose.production.yml config
```

Review the rendered output for expected hosts, origins, and port bindings. Then build and start:

```bash
docker compose --env-file /secure/path/agas.production.env \
  -f compose.production.yml up -d --build
```

Inspect the one-shot migration and health state before routing traffic:

```bash
docker compose --env-file /secure/path/agas.production.env \
  -f compose.production.yml ps
docker compose --env-file /secure/path/agas.production.env \
  -f compose.production.yml logs migrate api web
```

The web port is loopback-only and FastAPI is private. Put a maintained HTTPS reverse proxy or
equivalent cloud ingress in front of the one public web hostname. The exact public origin must match
`AGAS_PUBLIC_WEB_ORIGIN`; FastAPI's CORS setting may remain restrictive because ordinary browser
traffic is same-origin through the gateway. Apply provider-specific proxy trust, forwarded-header,
request-size, timeout, and rate-limit settings only after reviewing that provider's deployment
contract.

## Not production-ready yet

Container packaging is necessary for independent phone access but is not authorization to handle
production athlete data. Before production use, the project still needs:

- a selected/provisioned identity provider and a tested hosted login/logout flow;
- a reviewed refresh/revocation and provider-wide logout policy, or acceptance of hourly re-login;
- HTTPS domains and reviewed ingress configuration;
- account recovery, consent, export, and deletion workflows;
- secret rotation and least-privilege production administration;
- database backup, restore, migration rollback, and retention procedures;
- structured logs, metrics, alerting, and availability/error objectives;
- a staging deployment and real phone-sized end-to-end acceptance test;
- a reviewed offline-write/outbox design if workouts must be recordable without connectivity;
- governed scientific content sufficient to create a safe training path.

The reference Compose file does not install a reverse proxy or select commercial infrastructure.
Those choices affect cost, privacy, operations, and account behavior and should be made explicitly.
