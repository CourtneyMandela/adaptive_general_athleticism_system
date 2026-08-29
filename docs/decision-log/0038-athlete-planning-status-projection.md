# Decision 0038: Athlete planning-status projection

- Status: accepted provisionally
- Date: 2026-08-27
- Decision version: `athlete-planning-status-projection@1.0.0`

## Decision

Add a separate authenticated, read-only planning-status projection for an athlete. At an explicit
time, it reports how many persisted capability estimates are current or stale and whether an
initial long-range strategy exists. The projection uses four states:

- `capability_estimate_required`
- `capability_estimate_stale`
- `governed_strategy_inputs_required`
- `initial_strategy_created`

When a strategy exists, the projection exposes a narrow summary of its identity, generation and
review times, horizon, rule version, and priority count. It does not expose a write action or accept
competency floors, priority policies, relevance scores, evidence choices, or scientific claims.

The PWA renders this projection as an informational handoff beside assessment. It explains the next
governed boundary without pretending that a completed assessment is already a workout.

## Reason

The system now has a transactional initial-strategy boundary, but the athlete-facing no-plan state
cannot tell whether the athlete still needs assessment interpretation or whether reviewed planning
inputs are the remaining dependency. A small read model closes that communication gap while
keeping expert governance out of the athlete interface.

## Alternatives considered

- Add planning fields to `AssessmentWorkflowProjection`. Rejected because assessment selection and
  planning governance are separate application concerns and will evolve independently.
- Add a PWA button that submits initial-strategy candidate scores. Rejected because those scores are
  not ordinary athlete preferences and currently require a governed source.
- Return every capability estimate or the complete strategy. Rejected because this screen needs
  readiness and provenance summaries, not raw planning internals.
- Infer missing floors or policy from estimate domains. Rejected because domain equality does not
  establish metric applicability, population fit, scientific support, or athlete relevance.

## Assumptions and provisional choices

- An estimate is current when it was estimated no later than the projection time and its optional
  validity end is later than that time. A known estimate whose validity ended is stale.
- An estimate with no validity end remains current; this reflects the persisted contract rather
  than inventing a universal staleness interval.
- The initial strategy summary identifies the root of strategy history. Successor strategy and
  block-cycle presentation remain a later projection.
- The PWA may show that governed inputs are required, but only an operator/application workflow may
  supply them.

## Evidence and uncertainty

This decision concerns application-state presentation and introduces no training claim. Estimate
validity comes from each persisted estimate. Software tests use synthetic non-operational records.

## Consequences

- Athletes can see honest progress between assessment interpretation and a scheduled plan.
- Missing scientific/planning governance stays visible instead of becoming a generic error.
- A later operator workflow can satisfy the same boundary without changing the athlete projection.
- Current-block, successor-strategy, and complete first-plan readiness remain separate future work.
