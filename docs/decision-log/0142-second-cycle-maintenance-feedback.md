# 0142 — Second-cycle maintenance feedback

Date: 2026-09-25

Status: accepted provisionally

Decision version: `second-cycle-maintenance-feedback@1.0.0`

## Decision

Complete the persisted owner-alpha acceptance path through all four weeks of the successor
`MAINTAIN` block. Every scheduled session passes through the current assigned pre-session safety
policy, structured set-level execution, derived adherence, post-session safety review, explicit
jump-contact exposure calculation, deterministic progression evaluation, confirmed next-week
availability, and immutable weekly roll-forward. A completed two-by-three session records six
actual contacts. An otherwise compliant session at RPE 6 repeats the maintenance dose; progression
requires RPE 5 or below and still remains subject to the separate contact-exposure cap.

Add a block-review policy and response-evaluation authority to the maintenance construction
candidate. The review requires at least 80 percent adherence and low response confidence. Its
`higher_is_better` threshold is zero: a governed follow-up at or above the successor strategy's
baseline is provisionally consistent with maintenance. This is explicitly an engineering judgment
and not a validated equivalence, non-inferiority, reliability, or causal threshold.

At completed-block review, use only prescriptions, executions, adherence records, post-session
safety decisions, and reassessment observations belonging to the reviewed second block. The
response baseline must be the capability estimate carried by the second strategy, not the initial
block's baseline. The next replanning preparation must replace that second-strategy estimate with
the second-cycle follow-up.

Resolve approved initial planning-context provenance by walking an immutable strategy's
`supersedes_strategy_id` ancestry to its root strategy. Reject missing, cyclic, cross-athlete,
policy-changing, horizon-changing, or time-reversing ancestry. Validate the original context
against the root strategy, then use the current reviewed response to prepare the next successor.
Version this projection as `replanning-preparation@1.2.0`.

## Reason

Decision 0141 created a separately governed successor week but stopped before that cycle produced
evidence. Without executing the full block, the system could not prove that contact exposure,
adherence, and safety observations survive into a second review. Without a maintenance-specific
response rule, review would either fail closed or incorrectly borrow the development threshold.

The completed second review also exposed a real multi-cycle provenance gap: successor preparation
looked for an initial-context decision attached directly to the current strategy. A second strategy
properly points to a block review and predecessor instead, so the third strategy could not be
prepared even though the full immutable ancestry existed. Root traversal preserves the reviewed
initial assumptions while allowing current observations to replace only the active estimate.

## Alternatives considered

- Reuse the development response threshold for maintenance. Rejected because improvement and
  maintenance answer different questions and require separately reviewable assumptions.
- Treat an unchanged measurement as proven equivalence. Rejected because the measurement pathway
  has uncertainty and no validated equivalence margin.
- Progress a completed RPE 6 maintenance exposure. Rejected provisionally so the upper edge of the
  prescribed effort range records useful work without automatically increasing contacts.
- Build the second response from the athlete's entire execution history. Rejected because it would
  mix interventions and violate block-scoped causal provenance.
- Copy the first successor's prepared context into the third strategy. Rejected because it would
  retain a stale estimate and omit the second-cycle response.
- Attach the initial planning-context decision to every successor strategy. Rejected because it
  duplicates provenance and obscures the immutable predecessor chain.

## Evidence

The existing cited Oxfeldt et al. review supports only the broad direction that lower-body
plyometric training can affect jump performance. It does not establish a maintenance dose, an RPE
5 progression gate, an 80 percent adherence cutoff, or a zero-change maintenance threshold.

The block-scoped response construction, actual-contact calculation, immutable strategy ancestry,
and exact prepared-context replacement are software architecture and provenance rules. The numeric
maintenance rules remain owner-reviewable engineering priors.

## Uncertainty

No measured decline can conceal a real decline or improvement inside measurement error. It is not
proof that the maintenance dose is sufficient, that physiology was unchanged, or that the
intervention caused the result. Repeated personal observations may justify a future separately
versioned margin or dose change, but this release does not infer one.

The acceptance path remains a narrow single-adaptation owner-alpha fixture. Multi-adaptation blocks
will need explicit response partitioning and may require different maintenance semantics.

## Consequences

- The maintenance construction candidate now has a separately ratifiable review policy and
  response authority in addition to dose, exposure, scheduling, progression, and safety authority.
- Eight completed sessions in the four-week fixture persist 48 actual jump contacts, eight
  adherence records, eight post-session safety decisions, and repeat-dose progression outcomes.
- The second response excludes the first block's execution and uses the second strategy estimate as
  baseline.
- The third strategy uses the second-cycle follow-up and cites the second block review, not the
  first review, in its direct decision provenance.
- Prepared successor planning now works across multiple immutable strategy generations and fails
  closed when ancestry cannot be trusted.
- The next product task is to expose and exercise this second-cycle boundary through an unmocked
  browser-to-API smoke path without duplicating deterministic domain rules in Playwright.
