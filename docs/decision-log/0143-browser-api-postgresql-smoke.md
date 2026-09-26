# 0143 — Browser-to-API PostgreSQL smoke boundary

Date: 2026-09-25

Status: accepted

Decision version: `browser-api-postgresql-smoke@1.0.0`

## Decision

Maintain one separate Playwright smoke test that runs the actual Next.js application, encrypted
same-origin session gateway, FastAPI application, Alembic migration chain, seed import, and a
dedicated PostgreSQL database. Simulate only the external OIDC authority. Its access token uses the
existing development-bearer contract and is forwarded to FastAPI only by the server-side gateway;
browser code remains in session mode and never constructs an authorization header.

The browser scenario signs in through authorization code flow with S256 PKCE, creates an athlete
profile through the real onboarding UI and API, observes the honest no-plan state, reloads the app,
and recovers the persisted owned profile from PostgreSQL. It does not intercept or fulfill any AGAS
API request and does not reproduce deterministic planning, dose, safety, or response rules.

Run this scenario with `playwright.real-stack.config.ts` and
`pnpm --filter @agas/web test:e2e:real-stack`. Require `AGAS_TEST_DATABASE_URL` to use PostgreSQL and
name a database ending in `_test`. Global setup migrates to head, imports the controlled catalog,
starts FastAPI and Next.js on loopback, and downgrades the dedicated database to base during
teardown. The ordinary mocked browser suite explicitly excludes this spec.

Add a mandatory `Browser + API + PostgreSQL` CI job with its own disposable PostgreSQL 16 service.

## Reason

The prior browser suite proved user-facing transitions and the session gateway against route
intercepts and a private API test double. Decision 0134 proved migrations, FastAPI, authentication,
onboarding, ownership, and PostgreSQL through an HTTP test client. Neither boundary proved that the
deployed browser, gateway, resource server, and production database family compose as one path.

A single narrow scenario provides that signal without moving business-rule assertions into
Playwright or making ordinary frontend iteration depend on PostgreSQL.

## Alternatives considered

- Add more route-intercepted Playwright scenarios. Rejected because interception cannot reveal
  gateway, transport, migration, driver, or real persistence integration failures.
- Point the browser directly at FastAPI with a public development token. Rejected because it would
  bypass the production-shaped encrypted session and same-origin gateway boundary.
- Run the complete governed planning loop in Playwright. Rejected because deterministic rule and
  lineage coverage belongs in Python integration tests; reproducing it would be slow and brittle.
- Use the ordinary development database. Rejected because teardown intentionally removes the
  schema and must be restricted to an explicitly named test database.
- Depend on a real hosted identity provider in CI. Rejected because external credentials and
  network state would make the core integration signal less deterministic. The mock retains the
  exact OIDC protocol boundary while the AGAS stack remains real.

## Evidence

This is an integration-test, authentication, and deployment-boundary decision. It creates no
scientific evidence, training authority, dose, safety conclusion, or owner ratification.

## Uncertainty

The smoke path does not prove hosted provider configuration, production network routing, or the
presence of owner-alpha ratifications in the live database. It also does not exercise the complete
training loop through a browser. Those behaviors remain covered by provider-specific verification
and deterministic backend suites respectively.

Local execution requires a reachable dedicated PostgreSQL database. Environments without one can
still run the mocked browser suite; CI must not skip the real-stack job.

## Consequences

- CI fails if migrations, catalog import, OIDC callback/session handling, same-origin gateway,
  FastAPI authentication, onboarding, ownership persistence, or profile recovery stop composing.
- Browser tests stay focused on observable user transitions while backend tests retain ownership of
  planning and safety semantics.
- The only mocked component in the real-stack lane is the external identity authority.
- The next operational task is to inspect the hosted owner-alpha environment and verify its current
  ratifications and persisted week through authenticated UI/API access.
