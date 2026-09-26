# 0134 — PostgreSQL API golden-path boundary

Status: accepted

Date: 2026-09-23

Decision version: `postgresql-api-golden-path@1.0.0`

## Decision

Maintain one integration test that applies the complete Alembic migration chain to a real,
dedicated PostgreSQL database and exercises FastAPI through its normal database-session and
authentication dependencies. The first golden path covers public equipment discovery, authenticated
athlete onboarding, owner-scoped directory and environment reads, cross-owner isolation, and direct
verification of the resulting observation and ownership provenance.

The test database URL is supplied separately through `AGAS_TEST_DATABASE_URL`. The test fails closed
unless the URL uses PostgreSQL and the database name ends in `_test`. It migrates from base to head
before the scenario and back to base afterward. Local suites skip this one test when the variable is
absent; backend CI provisions `agas_test`, supplies the variable, and therefore must execute it.

## Reason

The broad integration suite intentionally uses fast in-memory SQLite fixtures. That suite validates
application behavior but cannot detect PostgreSQL-specific migration, constraint, JSON, transaction,
driver, or session-wiring failures. Separately testing every rule against both databases would add
large duplication without improving the user-facing contract proportionally. One representative
real-stack path establishes that migrations, transport, authentication, persistence, and ownership
compose correctly on the production database family.

## Alternatives considered

- Point the test at the ordinary development `agas` database: rejected because migration cleanup
  would risk developer data and violate the repository's safety constraints.
- Override the FastAPI database dependency with a PostgreSQL session: rejected because it would not
  validate the deployed database-session configuration path.
- Replace all SQLite integration fixtures with PostgreSQL: rejected because it would slow every
  bounded behavior test and make local iteration unnecessarily dependent on an external service.
- Exercise only `/ready`: rejected because connectivity alone does not validate domain persistence,
  provenance, authentication, or owner isolation.
- Keep the test optional in CI: rejected because silent skipping would provide no release signal.

## Evidence and owner-review boundary

This is a test-infrastructure and authorization-boundary decision. It creates no scientific claim,
training rule, dose, safety policy, planning authority, or owner approval. The scenario verifies the
existing immutable self-service ownership grant and onboarding observation provenance rather than
bypassing them with the test principal.

## Assumptions and uncertainty

- PostgreSQL 16 remains the repository's development and deployment compatibility target.
- A single golden path will not cover every PostgreSQL-specific behavior; targeted regression tests
  should be added when a concrete database-family defect is found.
- Alembic downgrade remains part of the supported migration contract. If destructive downgrade is
  intentionally retired, cleanup should move to disposable database creation rather than weakening
  the dedicated-database guard.

## Consequences

- Backend CI now depends on a healthy PostgreSQL service and runs the complete migration chain.
- The ordinary local suite remains fast and self-contained unless a developer opts into the real
  database test.
- A production-family break in migrations, API session wiring, onboarding transactions, provenance,
  or owner isolation fails CI through one coherent scenario.
