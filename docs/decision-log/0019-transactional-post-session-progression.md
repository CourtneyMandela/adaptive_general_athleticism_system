# 0019: Transactional post-session progression

- Status: accepted provisionally
- Date: 2026-08-22
- Decision version: `transactional-post-session-progression@1.0.0`

## Decision

Add
`POST /v1/session-executions/{session_execution_id}/prescriptions/{prescription_id}/progression`
as the application boundary from recorded performance to one immutable progression decision.

The service loads the execution, prescription, derived adherence, progression policy, and every
persisted post-session safety decision for the execution. At least one post-session safety decision
is required, including when it simply records that no configured concern was present. The service
does not accept a caller-selected subset, so an escalation cannot be omitted from progression.

When the policy declares a separately tracked exposure type, the request must identify a persisted
exercise exposure definition and exposure-progression policy plus an explicit proposed dose and
date. The service derives the completed exposure entry, evaluates the proposal against persisted
history, and gives the resulting validation decision to the progression engine. Policies without
an exposure type reject exposure inputs.

One transaction appends the optional exposure entry and validation, the progression decision, and
an immutable revised prescription when a `PROGRESS` decision uses an automatically supported typed
dimension. Repetitions and load use their existing typed fields. Set and duration changes also
require an explicit revised planned duration. Unsupported typed dimensions retain the inspectable
progression decision but do not manufacture a prescription revision.

Database constraints permit only one adherence record, exposure entry per definition, and
progression decision for a given execution/prescription chain.

## Reason

The deterministic calculators and persistence mappings already exist, but manual orchestration can
omit safety decisions, select mismatched evidence, create duplicate derived facts, or leave a
partially persisted exposure/progression chain. This boundary makes the safe legal sequence
available without embedding a new progression rule or scientific threshold in the API.

## Alternatives considered

- Let clients submit complete decisions or revised prescriptions: rejected because authoritative
  links and derived outcomes must come from persisted state and deterministic rules.
- Accept caller-selected post-session safety decision IDs: rejected because omission could bypass a
  hold or escalation.
- Progress without a post-session check: rejected at this application boundary because the
  post-workout workflow explicitly collects unusual symptoms and safety precedes progression.
- Infer exposure from exercise names: rejected because only a reviewed `ExposureDefinition` may
  classify exposure.
- Silently cap an excessive exposure proposal: rejected because the rejected proposal and configured
  cap must remain visible.
- Create a free-text revision for unsupported adjustment dimensions: rejected because it would not
  be deterministic or typed.

## Evidence and uncertainty

This is an orchestration and provenance decision implementing blueprint sections 37–42 and 57–58.
It introduces no production thresholds, increments, exposure definitions, or scientific claims.
All such values remain versioned, persisted, evidence-linked policy inputs.

## Assumptions and unresolved questions

- One progression decision per execution and prescription is a provisional V1 invariant. A future
  correction workflow must use explicit supersession rather than competing decisions.
- A post-session safety check closes the ordinary progression workflow, but later safety reports
  remain possible immutable history. Future prescription selection must still consider newer safety
  state before use.
- The exposure lookback query is scoped by athlete and exposure type; the deterministic validator
  further filters dose unit and target-relative time.
- Multi-session progression aggregation, manual approval states, progression-decision correction,
  and automatically wiring a revision into a later session container remain unresolved.

## Consequences

- Performance can now produce an inspectable, persisted adaptation decision through a narrow API.
- Safety and exposure constraints cannot be omitted by transport input.
- Rejected or held progressions remain explicit and do not revise dose.
- Supported revisions preserve the original prescription and full decision lineage.
- Late failures roll back the complete exposure-to-revision chain.
