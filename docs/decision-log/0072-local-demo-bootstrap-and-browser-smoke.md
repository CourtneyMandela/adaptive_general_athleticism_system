# 0072: Local demo bootstrap and browser smoke

- Status: accepted provisionally
- Date: 2026-08-30
- Extends: Decisions 0013, 0056, 0067, and 0071
- Decision version: `local-onboarding-demo@1.0.0`

## Decision

Provide one development-only, idempotent CLI bootstrap that imports the reviewed repository
catalog, creates the existing repository-owned synthetic traveler as an owned athlete, records the
profile and two equipment environments as one explicitly synthetic direct observation, and grants
the separate local reviewer identity its append-only planning-reviewer role. Stop the fixture at
the derived `capability_estimate_required` boundary.

Use deterministic identifiers for fixture-owned records and reject immutable-content collisions.
Refuse to run when production environment or external authentication is configured. Return the
athlete UUID, local development tokens, planning boundary, and PWA/reviewer paths as machine-readable
JSON. Let the PWA consume `?athleteId=` so that output is directly navigable.

Add a Playwright navigation smoke suite. It verifies the reviewer queue and athlete deep link in a
real browser with contract-valid mocked reads. Keep real persistence, authentication, queue, and
empty-week behavior covered by the demo-bootstrap API integration test rather than manufacturing
scientific approvals inside an end-to-end browser fixture.

## Reason

The application had a real athlete UI and reviewer workbench, but a developer still had to import
catalog data, create an athlete, discover its UUID, grant ownership, and grant reviewer authority
across several commands. A deterministic onboarding fixture makes the honest product boundary
repeatable without weakening the evidence and planning gates.

Browser-level coverage catches routing, query-parameter, rendering, and link regressions that
typed request-unit tests cannot. Splitting browser navigation from the real backend bootstrap keeps
the test fast while the integration test proves that the same fixture is persisted and authorized.

## Alternatives considered

- Persist the complete synthetic vertical-slice test as demo data. Rejected because its fixture
  thresholds, estimates, policies, doses, and approvals are deliberately non-operational.
- Generate a generic first workout after bootstrap. Rejected because absence of a governed
  capability estimate and planning authorities is a real blocked state, not a UI inconvenience.
- Use random fixture identifiers. Rejected because repeated local setup would create duplicate
  athletes and make deep links unstable.
- Make the browser smoke suite run a live PostgreSQL backend. Deferred because the persistence/API
  contract is already exercised transactionally and adding database orchestration would obscure
  the narrow navigation regression this suite owns.

## Evidence

This is a development workflow and evaluation decision implementing blueprint sections 64, 65,
74, 83, and 89. It introduces no scientific claim, capability estimate, training threshold,
exercise equivalence, prescription, or dose.

## Assumptions and uncertainty

- The repository-owned traveler is appropriate non-sensitive demo identity data; it remains
  labeled synthetic in both observation context and provenance.
- Local development bearer strings are selectors, not production credentials.
- A mocked browser transport plus real API integration test is sufficient until reviewed planning
  authorities allow a production-like live-browser vertical slice.
- Re-running the bootstrap must preserve later athlete history and must not silently reactivate an
  explicitly revoked reviewer role.

## Consequences

- A new contributor can reach the same truthful athlete and reviewer state with one command after
  migration.
- The demo displays why planning is blocked instead of appearing to be a finished workout app.
- Browser navigation is now part of CI and requires the pinned Playwright Chromium runtime.
- Production-like assessment, planning, training execution, and response review still require
  governed source data and are not supplied by this fixture.
