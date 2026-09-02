# 0088 — Render alpha deployment gate repair

Date: 2026-09-02

Status: accepted for the owner-only hosted alpha

Decision version: `render-alpha-deployment-gate@1.0.0`

## Decision

Keep the root free-alpha Render Blueprint at `autoDeployTrigger: checksPass`. Repair failures in
the repository's existing GitHub CI workflow instead of bypassing the gate. Render should deploy
the API only after the backend, frontend, browser, and container jobs accept the commit.

## Reason

The API stopped advancing because the Backend CI job failed strict type checking in
`test_migration_identifier_lengths.py`. Its runtime assertion called SQLAlchemy's intentionally
dynamic PostgreSQL `dialect` factory directly from typed test code, which mypy reports as an
untyped call. Frontend, browser, and container jobs were green, but Render correctly retained the
last fully accepted API commit.

The failure is repaired by narrowing the dynamic factory to SQLAlchemy's typed `Dialect` class
before construction. This preserves the runtime PostgreSQL identifier-limit assertion while
allowing the same strict type-check command used by CI to pass.

## Alternatives considered

- **Deploy on every commit.** Used briefly to diagnose and roll forward the blocked API, then
  rejected as the steady state because it permits a commit with a failing required check to replace
  a healthy deployment.
- **Remove tests from strict type checking.** Rejected because tests are executable engineering
  code and the CI contract deliberately checks them.
- **Hard-code PostgreSQL's identifier limit in the test.** Rejected because the runtime dialect is
  the more direct authority and avoids duplicating a vendor constant.
- **Continue manual Render deploys.** Rejected because it bypasses the accepted CI gate and makes
  frontend/backend version drift an operator habit.

## Evidence

- Render's Blueprint reference defines `checksPass` as waiting for linked CI checks.
- GitHub Actions run `33618669220` showed successful Frontend and Deployment containers jobs and a
  single Backend failure at the strict type-check step.
- The failing diagnostic was `no-untyped-call` at
  `tests/unit/test_migration_identifier_lengths.py`; no application test had failed.
- The service dashboard showed `d8dc4be` as the last successful API deployment while GitHub and
  Vercel had advanced beyond it.

## Consequences

- Commits to `main` deploy the free API only after all required CI jobs pass.
- A failed check leaves the prior healthy API live and must be investigated explicitly.
- Deployment verification must inspect CI using the full commit SHA; an abbreviated SHA can produce
  a misleading empty result in commit-filtered CLI queries.
