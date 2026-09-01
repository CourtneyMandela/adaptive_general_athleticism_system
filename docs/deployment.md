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
The web runtime's server-side `AGAS_INTERNAL_API_URL` (or one platform-supplied
`AGAS_INTERNAL_API_HOSTPORT`), optional `AGAS_API_UPSTREAM_TIMEOUT_MS`,
`AGAS_PUBLIC_WEB_ORIGIN`, and
`AGAS_SESSION_ENCRYPTION_KEY` are server-only. Generate the session key from exactly 32 random bytes
encoded as unpadded base64url. Every `AGAS_OIDC_*` value is also server-only. The configured provider
must support a confidential client using authorization code, S256 PKCE, OIDC nonce,
`client_secret_basic`, and asymmetric signed ID tokens. Register the exact callback
`https://YOUR-WEB-ORIGIN/auth/callback`. The optional resource URI and configured scopes must cause
the provider to issue a JWT access token whose issuer and API audience satisfy FastAPI's separate
`AGAS_EXTERNAL_AUTH_*` contract. `AGAS_OIDC_AUDIENCE` supports providers that select a custom API
with the OAuth audience parameter; `AGAS_OIDC_RESOURCE` remains available for providers that use
the resource parameter. The reference Compose model deliberately maps the API's external
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

## First owner-only alpha: no-card hosting

Decision 0086 selects Vercel Hobby, one Render Free API, Neon Free PostgreSQL, and Auth0 Free. Do not
add a payment method and do not opt into a trial. Without a payment method, quota exhaustion should
pause service instead of producing an overage. Recheck every dashboard before confirming because
provider plans can change.

The topology is:

```text
phone browser
    |
Vercel Next.js PWA + encrypted session gateway
    |
HTTPS + Auth0 bearer (server-side only)
    |
Render Free FastAPI
    |
TLS
    |
Neon Free PostgreSQL
```

FastAPI is publicly reachable in this topology, but athlete and operator routes remain protected by
the exact Auth0 issuer/audience/signature contract. Keep `AGAS_CORS_ORIGINS=[]`; ordinary browser
traffic must go through the Vercel gateway. Never expose the Neon URL or Auth0 client secret through
`NEXT_PUBLIC_*`.

### 1. Create Neon Free PostgreSQL

Create one free project in a US East region where available. Do not add a card. Copy the **direct**
connection string, not the pooled hostname, and retain `sslmode=require`. The direct URL is the
single low-concurrency alpha secret used by both Alembic and SQLAlchemy. Store it only as Render's
`AGAS_DATABASE_URL` secret.

Neon's free storage and restore window are limited. Before irreplaceable training history
accumulates, implement and test an owner export plus restore procedure.

### 2. Create Auth0 Free identity

Create a free tenant without a custom domain, then configure:

1. A custom API named `AGAS staging`, identifier `https://api.agas.staging`, and RS256 signing.
2. A Regular Web Application named `AGAS staging web` with token endpoint authentication method
   `client_secret_basic`.
3. Temporarily leave its callback, logout, and web-origin lists ready for the exact Vercel production
   URL created in step 4. Do not enter a preview-deployment wildcard.

### 3. Create the Render Free API

Create a Blueprint from the repository's root `render.yaml`. It must show exactly one Web Service,
`agas-api-staging`, on plan `free`, and no Render database. If the dashboard displays a charge or
requests a paid plan, cancel instead of continuing.

Supply these prompted secrets:

| Render key | Value |
| --- | --- |
| `AGAS_DATABASE_URL` | Neon direct TLS connection string |
| `AGAS_EXTERNAL_AUTH_ISSUER` | `https://YOUR_AUTH0_DOMAIN/` including trailing slash |
| `AGAS_EXTERNAL_AUTH_JWKS_URL` | `https://YOUR_AUTH0_DOMAIN/.well-known/jwks.json` |

The free tier cannot run a pre-deploy command. `AGAS_MIGRATE_ON_STARTUP=true` therefore runs Alembic
before Uvicorn in this single-instance alpha. Do not reuse that setting in a scaled deployment;
`deploy/render-paid.yaml` retains the separate pre-deploy migration pattern.

After the first deploy, record the exact HTTPS hostname, expected to resemble
`https://agas-api-staging.onrender.com`. Confirm `/health` responds and `/ready` reports readiness.

### 4. Create the Vercel Hobby PWA

Import the GitHub repository as a personal Hobby project and select `apps/web` as its Root
Directory. Do not start a Pro trial. Vercel should detect the root pnpm workspace and Next.js.

Set these public build variables for Production only:

| Vercel key | Value |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | `/api/agas` |
| `NEXT_PUBLIC_AGAS_AUTH_MODE` | `session` |

Set these server-only Production variables:

| Vercel key | Value |
| --- | --- |
| `AGAS_INTERNAL_API_URL` | Exact Render API HTTPS origin, with no trailing path |
| `AGAS_API_UPSTREAM_TIMEOUT_MS` | `55000` |
| `AGAS_PUBLIC_WEB_ORIGIN` | Exact Vercel production origin |
| `AGAS_SESSION_ENCRYPTION_KEY` | 32 random bytes encoded as unpadded base64url |
| `AGAS_OIDC_ISSUER` | Auth0 issuer including trailing slash |
| `AGAS_OIDC_AUTHORIZATION_URL` | `https://YOUR_AUTH0_DOMAIN/authorize` |
| `AGAS_OIDC_TOKEN_URL` | `https://YOUR_AUTH0_DOMAIN/oauth/token` |
| `AGAS_OIDC_JWKS_URL` | Auth0 JWKS URL |
| `AGAS_OIDC_CLIENT_ID` | Regular Web Application client ID |
| `AGAS_OIDC_CLIENT_SECRET` | Regular Web Application client secret |
| `AGAS_OIDC_SCOPES` | `openid` |
| `AGAS_OIDC_AUDIENCE` | `https://api.agas.staging` |
| `AGAS_OIDC_ID_TOKEN_ALGORITHMS` | `RS256` |

Generate the browser-session key locally without saving it to a file:

```bash
node -e "console.log(require('node:crypto').randomBytes(32).toString('base64url'))"
```

Deploy once to obtain the stable production origin. Put that exact origin into
`AGAS_PUBLIC_WEB_ORIGIN`, then configure Auth0 with:

- allowed callback URL: `https://YOUR-VERCEL-ORIGIN/auth/callback`;
- allowed logout URL: `https://YOUR-VERCEL-ORIGIN`;
- allowed web origin: `https://YOUR-VERCEL-ORIGIN`.

Redeploy after all variables and Auth0 URLs are exact. Preview URLs are intentionally not login
origins in the first alpha.

### 5. Acceptance and cost checks

Create one Auth0 user and verify login, onboarding, API reads/writes, logout, and a second login.
Then install and exercise the PWA on a real phone using cellular data, not the workstation's Wi-Fi.
Expect the first authenticated data request after 15 idle minutes to take longer or require one
retry while Render and Neon wake.

Confirm all four dashboards show their free/personal plan and no payment method. Use synthetic or
low-sensitivity data until owner export/restore, deletion, retention, monitoring, and governed
scientific authorities are reviewed. The paid private topology in `deploy/render-paid.yaml` is a
future upgrade option, not authorization to create paid resources.

## Not production-ready yet

Container packaging is necessary for independent phone access but is not authorization to handle
production athlete data. Before production use, the project still needs:

- a provisioned identity provider and a tested hosted login/logout flow;
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

The Playwright suite exercises the provider-neutral login contract against an ephemeral local OIDC
authority and private API. It verifies authorization-code flow, S256 PKCE, state and nonce binding,
asymmetric ID-token verification through JWKS, encrypted session creation, one-time code rejection,
and bearer forwarding without exposing the browser cookie upstream. This is deployment-contract
coverage, not evidence that any future hosted provider has been configured correctly; staging must
repeat the flow against the selected provider.
