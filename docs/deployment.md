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
4. API and PWA ports bind to host loopback, not every network interface.
5. Production API startup requires external authentication with HTTPS issuer/JWKS settings.
6. No development bearer selector is passed to a production container.
7. The production PWA image includes an install manifest, maskable icon, and fail-closed offline
   shell without storing athlete records.

The reference database is useful for validating topology. A real deployment may use managed
PostgreSQL instead, but it must retain migration ordering, encrypted transport where appropriate,
backups, and restore validation.

## Configuration boundary

Copy `.env.production.example` to a secret-managed path outside the repository. The example is a
schema, not a usable environment. Replace every hostname and credential.

`NEXT_PUBLIC_API_URL` is intentionally public and is compiled into the PWA image. Changing it
requires rebuilding the image. Never place a provider secret or access token in `NEXT_PUBLIC_*`.

All `AGAS_EXTERNAL_AUTH_*` values are server-only runtime configuration. The API accepts only a
token with the configured issuer, audience, asymmetric signature, required timestamps, and subject.
The current PWA does not yet acquire that token; browser authorization-code-with-PKCE or a reviewed
server-session design remains the next authentication milestone.

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

The API and web ports are loopback-only. Put a maintained HTTPS reverse proxy or equivalent cloud
ingress in front of both public hostnames. The API CORS origin must exactly match the public PWA
origin. Apply provider-specific proxy trust, forwarded-header, request-size, timeout, and rate-limit
settings only after reviewing that provider's deployment contract.

## Not production-ready yet

Container packaging is necessary for independent phone access but is not authorization to handle
production athlete data. Before production use, the project still needs:

- a selected identity provider and complete browser login/logout/session flow;
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
