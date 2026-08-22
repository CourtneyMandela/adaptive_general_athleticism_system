# Decision 0029: Governed athlete safety-policy assignment

- Status: accepted provisionally
- Date: 2026-08-22
- Decision version: `athlete-safety-policy-assignment@1.0.0`

## Decision

Represent the applicability decision between an athlete and a reviewed `SessionSafetyPolicy` as an
immutable `AthleteSafetyPolicyAssignment`. Each athlete has one linear assignment history with a
positive sequence number. The first assignment is sequence one; each replacement must use the next
sequence number and explicitly reference the current assignment as its predecessor. The database
prevents duplicate sequence numbers and branching replacements.

An assignment records the policy, assignment time, reviewer/operator identity, applicability
rationale, predecessor, and rule version. Policy content and evidence provenance remain on the
policy; the assignment explains why that reviewed policy was selected for this athlete. Replacing
a policy appends history and never alters prior safety decisions or observations.

The ordinary athlete API has no policy-selection write endpoint. A narrow local operator CLI
creates assignments until a properly authenticated reviewer workflow exists. The current-week
projection exposes the active assignment for inspection. Session safety commands no longer accept
a client-supplied policy ID; the backend resolves the athlete from the persisted weekly plan and
uses that athlete's current assignment.

New `SessionSafetyDecision` records retain both the policy ID and assignment ID. The assignment
reference is nullable in storage only so decisions created before this migration remain readable;
the governed API always supplies it.

## Reason

The daily PWA previously required a user to paste any persisted policy UUID. Possession of a UUID
does not establish applicability, and selecting the newest policy by date would silently turn
recency into a safety rule. An explicit assignment closes that authority gap and prevents the
browser from switching policy semantics per request.

This is also a prerequisite for adaptive assessment and first-plan orchestration. The existing
assessment engine requires reviewed definitions and normalized screening inputs that do not yet
exist as a safe browser workflow. This milestone deliberately does not collect health screening,
injury history, current symptoms, or assessment results.

## Alternatives considered

- Let the athlete select a policy in onboarding. Rejected because applicability is governed, not a
  preference.
- Keep accepting a policy ID and compare it with an assignment. Rejected because the value is
  redundant and retains an unnecessary client-controlled safety input.
- Select the latest policy globally. Rejected because creation time is not an applicability rule.
- Store one mutable policy ID on `Athlete`. Rejected because changes would destroy review history
  and conflate athlete identity with a governed decision.
- Implement sensitive screening and assessment orchestration in the same milestone. Deferred until
  reviewed definitions, taxonomies, storage/privacy obligations, and escalation ownership exist.

## Assumptions and provisional choices

- One assignment is active at a time. Revocation without replacement requires a later explicit
  event type and is not represented by deletion or a null policy.
- `assigned_by` is an inspectable reviewer/operator label, not yet a foreign key to an account or
  professional credential.
- Reassigning the same currently active policy through the CLI is idempotent and does not append a
  duplicate review event.
- Sequence and predecessor constraints prevent ordinary concurrent branches; a database conflict
  fails closed and requires the operator to re-read current state.

## Evidence and uncertainty

This is a safety authority, provenance, and data-integrity decision. It makes no medical or
scientific claim and does not approve any particular safety-policy content. Policy evidence remains
subject to `docs/evidence-policy.md` and qualified review.

Production reviewer authorization, credential verification, assignment revocation, emergency
policy withdrawal, applicability review intervals, athlete notification, and jurisdiction-specific
health-data obligations remain unresolved.

## Consequences

- The PWA can no longer choose a safety policy by UUID.
- Every new session safety decision traces to the policy selected by current persisted assignment.
- Policy replacement is auditable and historical decisions keep their original policy reference.
- Athletes without an assignment can view persisted schedules but cannot submit a safety check or
  authorize ordinary training.
- Assessment intake remains visibly blocked instead of being approximated with unreviewed medical
  or scientific rules.
