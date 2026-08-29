# 0057: Authenticated environment-review writes

- Status: accepted
- Date: 2026-08-29
- Decision version: `authenticated-environment-review-write@1.0.0`

## Decision

Expose the existing reviewed exercise re-resolution and environment-prescription revision use
cases through two narrowly scoped operator HTTP endpoints. Both require the current authenticated
account to hold an active `planning_reviewer` assignment.

The public request contracts omit reviewer identity and authorization-assignment fields. After
authorization, the server binds `account:<account-id>` and the exact active account-role assignment
to the immutable decision record. A decision timestamp cannot predate the assignment that
authorized it. Athlete ownership alone does not authorize either write.

Keep the local operator CLIs compatible. CLI-authored decisions may continue to omit the account
role assignment because their authority boundary is the local administrative process rather than
an authenticated HTTP account.

## Reason

Decision 0056 established a durable role and a derived review queue but intentionally stopped
before writes. Reviewers now need a complete application workflow without allowing a browser to
assert who reviewed a decision. Reusing the deterministic services from Decisions 0053 and 0054
preserves their validation and transaction behavior while adding authentication provenance at the
transport boundary.

## Major implementation choices

- Return an authorization value containing the account, role, exact assignment, and grant time.
- Use separate operator request models instead of weakening the existing CLI command models.
- Reject client-supplied extra fields, including `reviewed_by` and
  `review_authority_assignment_id`.
- Add the assignment reference to `DecisionRecord.evidence`; do not mutate planning aggregates to
  carry authentication state.
- Keep role administration local and append-only. No public self-elevation endpoint is added.
- Preserve all-or-nothing transactions in the existing persisted application services.

## Alternatives considered

- Accept `reviewed_by` from the client. Rejected because it permits trivial identity spoofing.
- Copy the role into the decision reason without referencing its assignment. Rejected because a
  later revocation would make the historical authority impossible to reconstruct precisely.
- Add a generic approval engine. Deferred because the present workflow has only two concrete
  governed writes and no settled multi-party approval requirements.
- Automatically select an exercise or dose when the reviewer opens a queue item. Rejected because
  the blueprint requires explicit, evidence-aware authority and the current milestone does not
  establish generic substitution or dosing logic.

## Evidence

This is an application-security and auditability decision. It makes no scientific claim and the
`planning_reviewer` role must not be interpreted as proof of a professional credential.

## Assumptions

- The first application workflow uses one authorized reviewer to author and approve each change.
- Development authentication bypass may use a synthetic zero-valued authority only in explicitly
  configured test/development contexts.
- External authentication remains fail-closed until a verified provider adapter is configured.
- Existing deterministic re-resolution and prescription-revision validation remains authoritative.

## Unresolved questions

- Which verified credentials and organizational controls qualify a production reviewer?
- Which deployments require separate authors and approvers, and for which change classes?
- Should a role revocation invalidate already-open forms or only subsequent submissions?
- What assignment, notification, escalation, and service-level behavior should the queue gain?

## Consequences

An authorized reviewer can now complete environment-review work through the API with durable,
server-owned identity provenance. Revocation blocks later submissions without rewriting earlier
decisions. This is sufficient for a provisional internal workflow, but not a claim that production
credentialing or dual-control approval has been solved.
