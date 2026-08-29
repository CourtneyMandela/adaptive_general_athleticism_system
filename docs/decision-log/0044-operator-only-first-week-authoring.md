# 0044 — Operator-only first-week authoring

- Status: accepted provisionally
- Date: 2026-08-28
- Decision version: `operator-only-first-week-authoring@1.0.0`

## Decision

Keep the existing atomic first-week application service, but remove its athlete-authenticated HTTP
write route. Require every first-week command to include a non-empty reviewer, applicability
rationale, and uncertainty statement. The transaction that appends prescriptions, session
templates, dated availability, and the resulting weekly plan must also append one `DecisionRecord`
that cites the exact block, allocations, resolutions, exercises, adaptations, observations,
evidence claims, scheduling policy, and newly created records.

Expose this boundary through a local operator CLI that consumes one reviewed JSON file. Keep the
athlete PWA read-only at this boundary until an administrative identity and authorization model can
prove who is allowed to author dose and session-composition decisions.

The workflow accepts explicit structured prescriptions and session composition; it does not infer
sets, repetitions, intensity, rest, progression, grouping, frequency, or availability from an
adaptation name or allocated minutes.

## Reason

Omitting controls from the PWA is not an authorization boundary. The existing HTTP route accepted
material training decisions from any client that could authenticate as the athlete. Those inputs
determine exercise dose, intensity, progression references, session order, fatigue classification,
and calendar placement and therefore require the same explicit review and audit discipline already
used for initial strategy creation.

The persisted weekly-plan service already supplies the correct atomicity and deterministic
scheduling boundary. Hardening its command and transport is smaller and safer than introducing a
parallel draft schema or a generic session generator.

## Alternatives considered

- Leave the route public because the athlete PWA does not render it. Rejected because transport
  contracts, not UI visibility, determine authorization.
- Add a shared administrator secret or development bearer token. Rejected because that would be an
  ad hoc security model without verified roles or identities.
- Generate prescriptions automatically from block allocations. Rejected because allocation minutes
  do not establish valid dose, intensity, exercise grouping, rest, or progression rules.
- Persist independently editable prescription and session drafts. Deferred until a reviewed draft
  aggregate, approval lineage, and supersession model are defined.
- Store reviewer metadata only in CLI logs. Rejected because terminal output is not authoritative,
  transactional history.

## Evidence and uncertainty

This is an authorization, provenance, and application-boundary decision implementing blueprint
sections 33–36, 52, 60, 64, 73, and 89. It introduces no scientific dose or scheduling claim.
Operators remain responsible for the legitimacy, applicability, and evidence support of every
submitted prescription and policy.

## Assumptions and unresolved questions

- The existing generic `DecisionRecord` is sufficient for the first operator workflow; typed
  identifier prefixes preserve machine-readable provenance until a dedicated weekly-plan review
  aggregate is justified.
- Local operator access is a development/review workflow, not production administration.
- Scheduling-policy scientific review and approval lineage remain unresolved. The decision record
  pins the selected immutable policy but does not claim that its parameters are universally valid.
- First-week supersession/current-plan semantics remain unresolved; a second Week 1 plan still
  creates an ambiguity state in the athlete projection.
- Administrative authentication, roles, draft review, and approval separation are required before
  a production authoring UI can be exposed.

## Consequences

- Athlete clients can no longer author their own expert prescription or scheduling inputs.
- Every supported first-week creation is atomically traceable to its reviewer and complete input
  lineage.
- Failed scheduling remains a persisted, audited infeasible result rather than being hidden.
- The next vertical-slice boundary can safely consume a feasible Week 1 for pre-session safety and
  execution without weakening prescription provenance.
