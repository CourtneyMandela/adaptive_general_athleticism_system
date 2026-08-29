# Decision 0053: Operator-reviewed exercise re-resolution

- Date: 2026-08-28
- Decision version: `exercise-reresolution-operator-review@1.0.0`
- Status: accepted

## Decision

Add an operator-only transaction that resolves an existing immutable `StimulusRequirement` against
a different athlete-owned `Environment` snapshot. The command supplies the environment, an
explicit reviewed set of exercise candidates, an existing resolver policy, a timezone-aware
resolution instant, reviewer identity, applicability rationale, and uncertainty.

The service loads the original requirement without rebuilding it, derives the effective equipment
snapshot at the requested instant, runs the existing deterministic resolver, and appends a new
`ExerciseResolution` plus a `DecisionRecord` atomically. The result remains honestly `FULL`,
`PARTIAL`, or `INFEASIBLE`; partial limitations and the controlling availability event identifiers
are retained.

This boundary does not replace the earlier resolution, change the adaptation or stimulus, create a
dose, revise a resource demand or block allocation, or rewrite an immutable weekly plan. A later
reviewed weekly-authoring action may reference the new resolution only under the existing same-
stimulus, same-adaptation and partial-resolution policy guards.

Until administrative identities and roles exist, re-resolution is available through the local
planning-authoring CLI and is deliberately absent from the athlete HTTP API.

## Reason

Equipment is temporal and travel may change the available training means without changing the
developmental goal. Equipment reporting now preserves observation-backed temporal state, and the
resolver already evaluates a fixed stimulus against an environment snapshot. A transactional,
reviewed application boundary is needed to connect those capabilities without silently treating
an arbitrary exercise as an equivalent substitution.

## Alternatives considered

- Mutate the existing resolution. Rejected because it destroys the planning-time decision and its
  environmental provenance.
- Rebuild the stimulus for the travel environment. Rejected because environment constrains the
  means; it does not itself change the identified adaptation need.
- Automatically search the whole exercise catalog. Rejected because catalog inclusion does not
  establish athlete-specific applicability or make every candidate reviewed.
- Let the athlete select a substitute directly in the PWA. Rejected because that would delegate a
  governed equivalence and safety decision to an unqualified client action.
- Immediately rewrite the active weekly plan. Rejected because plans are immutable and the new
  resolution may be partial or infeasible; prescription revision is a separate decision.

## Evidence

This is a product-governance and provenance decision implementing blueprint sections 10–13, 56,
65, 72, 77–78, and 83. It introduces no scientific relationship, exercise-equivalence claim, or
training dose.

## Assumptions

- Candidate selection is an explicit operator-reviewed input for this milestone.
- The existing resolver policy is already governed; the decision record captures exactly which
  versioned policy was applied.
- Multiple re-resolutions of one requirement are legitimate append-only history when time,
  environment, candidates, policy, or review context changes.
- Effective equipment state at `resolved_at` is authoritative for this decision, including future
  and temporary availability events.

## Unresolved questions

- Production reviewer authentication, authorization, and approval workflows.
- How an active immutable weekly plan requests and records a reviewed prescription revision.
- Whether catalog-candidate discovery should become a separate explainable recommendation step.
- Notification and escalation behavior when the only honest result is `INFEASIBLE`.
- Correction or supersession semantics for erroneous operator decisions.

## Consequences

- Environment changes can produce a new resolution without erasing the original plan rationale.
- Availability, candidate, policy, requirement, observation, and evidence lineage are auditable.
- Travel substitutions remain impossible to present as full fidelity when the resolver finds only
  a partial match or no feasible candidate.
- A new resolution is planning input, not an automatic workout change.
