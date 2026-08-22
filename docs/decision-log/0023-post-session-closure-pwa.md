# Decision 0023: Post-session closure in the PWA

- Status: accepted
- Date: 2026-08-22

## Decision

Extend the current-week PWA with a low-friction post-session safety report after an execution has
been recorded. The report uses the existing transactional session-safety endpoint, identifies the
related immutable execution, and collects only structured fields already understood by the
deterministic safety gate. After the write, the browser reloads the authoritative current-week
projection.

The PWA will also present persisted progression outcomes per prescription. It will not initiate
progression in this slice. The progression endpoint requires a persisted progression policy and,
for exposure-governed prescriptions, reviewed exposure definitions, exposure policies, and an
explicit proposed target. The repository has no athlete-policy assignment or unambiguous policy
discovery contract, so the browser cannot select those inputs without inventing governance.

As with the pre-session form, a concerning-symptom control pauses ordinary form submission. It is
not translated into a classified safety signal. The browser records its actor as
`unverified-athlete-user` until production identity exists.

## Reason

Post-workout reporting closes the direct daily observation path required before deterministic
progression can run. Showing already-persisted progression decisions gives the athlete an honest
view of whether the configured engine chose to progress, repeat, hold, or require review without
duplicating those rules in TypeScript.

## Alternatives considered

- Ask the athlete to enter progression-policy and exposure-policy UUIDs. Rejected because these are
  system-governance inputs, not meaningful daily-user choices.
- Select the newest policy or the first policy matching a reference. Rejected because neither
  recency nor database order is an approved policy-assignment rule, especially when immutable
  versions coexist.
- Recalculate progression from adherence in the browser. Rejected because it would bypass safety,
  exposure constraints, evidence-linked policy, and backend provenance.
- Convert a pain checkbox or free text into a safety signal. Rejected because no reviewed
  classification taxonomy exists.
- Hide progression until the PWA can create it. Rejected because persisted decisions already exist
  in the read projection and are important feedback to the athlete.

## Assumptions and provisional choices

- A post-session `readiness` value is omitted; the report uses unusual soreness, an optional note,
  and reliability because readiness is principally a pre-session input.
- Existing post-session decisions are presented in persisted order as historical safety context.
- Progression text describes the stored outcome and adjustment only. It does not predict the next
  scheduled prescription or claim that a revised prescription is already scheduled.

## Unresolved questions and consequences

A purpose-built policy-assignment/discovery contract is still required before the PWA can invoke
progression safely. That contract must distinguish active versions, handle exposure-governed
prescriptions, and explain when manual review is required. Authentication, correction/supersession,
offline idempotency, and governed symptom classification also remain unresolved.

This slice closes post-session observation collection and outcome visibility, but it does not claim
that every logged session automatically advances its prescription.
