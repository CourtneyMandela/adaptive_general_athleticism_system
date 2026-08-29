# 0056: Planning-reviewer role and environment queue

- Status: accepted
- Date: 2026-08-29
- Decision version: `account-role-assignment@1.0.0`

## Decision

Add one narrowly scoped administrative role, `planning_reviewer`, as immutable account-role
assignment history. The current assignment for an account and role is the latest item in a linear
sequence and can be active or revoked. Role administration remains a local CLI bootstrap operation.

Add a role-protected, read-only HTTP projection for environment-review work. The projection derives
pending items from source weekly plans whose backend current-week state is
`environment_revision_required`. It exposes the exact confirmed availability, unresolved
prescription/resolution lineage, adaptation and stimulus identifiers, and current exercise and
environment descriptions needed to prepare a review. It creates no planning state and accepts no
exercise, dose, evidence, or approval input.

Do not expose exercise re-resolution or prescription-revision writes over HTTP in this slice.
Authenticated identity plus a role is necessary but not yet sufficient for safe author/approver
separation and reviewer-attributed write contracts.

## Reason

Decisions 0039, 0044–0046, 0053, and 0054 deliberately kept planning authority behind local CLIs
because hiding controls from athletes is not authorization. Decision 0055 now creates an honest
athlete-visible pause when a confirmed environment no longer matches the prescription lineage. A
real operator surface first needs a persisted authorization boundary and a deterministic way to
discover that work.

One explicit role and one read-only queue are the smallest replaceable foundation. The queue does
not invent a new planner, duplicate scientific judgments, or imply that a reviewer has approved a
substitution merely by viewing it.

## Major implementation choices

- Assign roles to persisted `Account` identities, not bearer-token strings or athlete ownerships.
- Represent grant and revocation as append-only sequenced assignments with a unique predecessor.
- Bootstrap assignments through the local identity administration CLI. There is no public role
  claim or self-elevation endpoint.
- Return `401` for an authenticated identity without a registered account and `403` for a
  registered account without an active required role.
- Derive queue membership from authoritative persisted state instead of creating mutable task rows
  that can drift from weekly-plan readiness.
- Limit the initial role vocabulary to `planning_reviewer`; expand it only when a concrete
  responsibility requires another role.

## Alternatives considered

- Reuse athlete ownership as reviewer authorization. Rejected because owning one's athlete record
  does not grant scientific or prescription-authoring authority.
- Use a shared administrator token or development-only header. Rejected because it would be an ad
  hoc credential with no durable account or revocation provenance.
- Expose planning writes as soon as a role exists. Deferred because authenticated writes must also
  bind reviewer identity server-side and define author/approver separation.
- Persist queue items. Deferred because the current task is fully derivable from immutable plan,
  availability, prescription, and resolution state; an assignment aggregate is only warranted when
  ownership, service levels, or multi-step approval are implemented.
- Build a generic RBAC framework. Rejected as unnecessary complexity for the current milestone.

## Evidence

This is an application-security, authorization, and auditability decision. It introduces no
scientific or training claim. The relevant product invariant is that athlete-facing convenience
must not bypass governed planning, evidence, or substitution authority.

## Assumptions

- External token verification remains fail-closed until a verified provider adapter is configured.
- Local development identities are suitable only for development and automated tests.
- Queue consumers are trusted planning reviewers but do not receive medical or unrelated athlete
  data from this projection.
- A revoked current assignment removes queue access without deleting earlier grants.

## Unresolved questions

- Which verified credentials or organizational controls qualify a production planning reviewer?
- Must prescription authors and approvers be different people for every planning change?
- How should queue assignment, escalation, notifications, and service-level expectations work?
- Which fields require additional minimization or consent controls in production?

## Consequences

The backend can now distinguish an athlete owner from an authorized planning reviewer and can show
the latter an exact, non-mutating travel-review queue. Planning writes remain CLI-only until their
authenticated reviewer and approval contracts are designed. This creates one additional migration
and local bootstrap command but avoids treating UI visibility as access control.
