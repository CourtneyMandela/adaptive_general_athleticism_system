# 0067: Required vertical-slice demonstration

- Status: accepted provisionally
- Date: 2026-08-29
- Decision version: `required-vertical-slice@1.0.0`

## Decision

Add one automated integration scenario that composes the existing deterministic domain services
across the blueprint's required first loop. The scenario begins with an explicitly synthetic
sedentary four-day athlete, direct intake and assessment observations, derived capability
estimates, identified needs, and a long-range strategy. It then creates a four-week block,
schedules home, travel, and return weeks, records safety-gated performance and adherence, applies
one versioned progression decision, reassesses the athlete, reviews delivered response, replans,
and creates a response-dependent successor block.

Keep every threshold, score, dose, and progression increment inside the test fixture and label it
as synthetic. The demonstration exercises architecture and lineage; it does not make those values
available as production training rules. Use the real seed exercise/equipment ontology and resolver
so the hotel week must retain the adaptation objective while exposing lower strength-stimulus
fidelity.

## Reason

The repository already tested travel resolution and the post-block feedback loop in separate
places. Those tests could pass independently without proving that one athlete can traverse the
complete invariant. Blueprint sections 64 and 65 require both an end-to-end first vertical slice
and an automated travel scenario before additional features take priority.

## Alternatives considered

- Treat the existing separate travel and persistence tests as the demonstration. Rejected because
  no single contract connected intake, planning, travel, performance, reassessment, and the next
  block.
- Add a production demo-data generator. Rejected because fixed synthetic thresholds and doses must
  not become application behavior or appear to be reviewed programming rules.
- Drive the scenario entirely through HTTP. Deferred because several scientific-governance inputs
  intentionally remain operator-reviewed and unseeded; manufacturing approvals would weaken the
  governance boundary the test is meant to protect.
- Add new planning heuristics to make the scenario pass. Rejected because the milestone should
  compose existing engines, not invent training logic.

## Evidence

This is an evaluation and architecture decision implementing blueprint sections 64, 65, 74, 83,
88, and 89. It adds no scientific claim. The repository's seed claims remain provenance inputs,
while all fixture thresholds and doses explicitly state that they are not operational evidence.

## Assumptions and uncertainty

- A domain-service integration test is the smallest honest demonstration while production
  governance authoring remains intentionally incomplete.
- Successful completion means the real deterministic components preserve lineage and produce the
  expected structural branch; it does not validate the physiological quality of fixture values.
- The fixture executes all sixteen scheduled session occurrences, but only one ordinary
  repetition progression is materialized because a second unreviewed progression policy would add
  no architectural coverage.

## Consequences

- One failing test now identifies a break anywhere from intake provenance through successor-block
  allocation.
- Hotel travel changes exercise selection and records insufficient heavy-load fidelity without
  changing athlete identity or goals; returning restores the full-gym strength exercise.
- The successor strategy moves the now-above-floor synthetic strength capability to maintenance
  while continuing aerobic development, and the second block inherits those changed states.
- Product-facing reviewer and athlete workflows can now advance against an explicit end-to-end
  regression contract rather than isolated component assumptions.
