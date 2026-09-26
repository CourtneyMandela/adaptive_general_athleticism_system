# 0144 — Owner-alpha live readiness audit

Date: 2026-09-25

Status: accepted

## Decision

Add one authenticated, read-only reviewer route at `/review/readiness` that composes existing
authoritative projections instead of introducing a new release-approval flag.

The route loads:

- every prepared assessment-governance candidate and its digest-bound status;
- every planning-policy, competency-floor, resource-governance, and training-construction
  candidate and its digest-bound status;
- the signed-in account's owned-athlete directory;
- each owned athlete's current-week projection for an explicit date; and
- the planning-review queue's current boundary for each athlete.

The browser normalizes those responses only for presentation. It does not persist an audit, ratify
a candidate, select a capability path, create a plan, or reinterpret a missing current week as an
approved empty plan.

## Reason

Successful source validation, deployment, API health, and database readiness do not prove that the
hosted owner-alpha database contains the intended ratifications or a usable current week. Before
this decision, verifying that state required visiting several reviewer pages and manually joining
their results. That made an operationally important distinction—code readiness versus live-data
readiness—easy to miss.

The existing candidate and athlete projections already own the relevant semantics. Composing them
in a read-only screen makes the live state inspectable without adding a second, potentially stale
source of truth.

## Alternatives considered

- Add one backend `release_ready` boolean. Rejected because different athletes and capability paths
  require different candidates, and a global boolean would conceal those dependencies.
- Automatically ratify missing candidates from the audit. Rejected because owner review is a
  deliberate authority boundary and deployment is not approval.
- Inspect the database directly. Rejected as the normal workflow because it bypasses account
  ownership, reviewer authorization, response validation, and the same projections the product
  actually uses.
- Continue using several separate reviewer pages. Retained for detailed review and writes, but
  insufficient as the primary point-in-time operational audit.

## Evidence

This is an operational composition decision, not a scientific or training claim. Its inputs are
the existing versioned server projections and immutable decision records. Candidate content
digests, ratification timestamps, issues, weekly-plan identity, safety-policy assignment state, and
projection versions remain visible so the owner can inspect exact lineage rather than trust a UI
summary.

## Uncertainty

- The first hosted inspection still requires the owner to complete Auth0 sign-in; credentials and
  authentication dialogs are not automated.
- A candidate shown as available or blocked is not necessarily required by the athlete's active
  path. The exact prepared planning boundary remains authoritative for dependency selection.
- The audit is point-in-time and read-only. It does not monitor later database drift or provider
  availability.
- Current-week fetch failures are shown per athlete while preserving the authority inventory; they
  are not silently converted to “no week.”

## Consequences

The owner now has one phone-usable place to distinguish ratified, available, blocked, and
conflicting prepared candidates and to confirm whether the authenticated athlete has a persisted
week for a selected date. Reviewer navigation links expose the route from the queue, planning
authorities, and assessment governance.

All writes remain on their existing explicit review or athlete-action routes. No observation,
estimate, evidence claim, planning decision, safety decision, prescription, or performance record
is created by this audit.

Version/date: `owner-alpha-readiness-audit@1.0.0`, 2026-09-25.
