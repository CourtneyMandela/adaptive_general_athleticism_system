# 0012: Closed-loop replanning lineage

- Status: accepted provisionally
- Date: 2026-08-21
- Decision version: `closed-loop-replanning@1.0.0`

## Decision

Add an explicit post-block replanning application boundary between `BlockReview` and a replacement
`LongRangeStrategy`. A revised strategy must identify both the strategy it supersedes and the block
review that triggered reconsideration. Initial strategies identify neither. Historical strategies,
capability estimates, needs, reviews, and blocks remain append-only.

The replanner accepts already-derived follow-up capability estimates; it does not manufacture a
capability value from the block review. Every selected follow-up estimate must be the exact estimate
referenced by one of the review's ordered `TrainingResponse` records. The replanner regenerates
`CapabilityNeed` records through the existing evidence-linked competency-floor detector, converts
explicit context inputs into ordinary planning candidates, and delegates priority assignment to the
existing versioned long-range planner.

A block review's causal conclusion and the athlete's current measured state remain separate. An
`INCONCLUSIVE` or unsupported block hypothesis does not erase a valid follow-up measurement. The
new strategy may use that estimate while retaining the review outcome and lineage; it must not say
the completed intervention caused the observed state change.

Candidate context values such as goal relevance, expected trainability, transfer, and costs remain
governed inputs. This slice does not infer them from one response record, and it does not generate
dose, stimulus, exercises, sessions, or a next block without their existing explicit inputs.

## Reason

The blueprint's closed loop requires reassessment and block review to affect later priorities, but
the current implementation stops after describing the review. Calling the existing planners
directly could produce a second strategy with no auditable connection to the completed block.
Explicit lineage and reviewed-estimate validation close that gap without conflating observations,
capability estimates, causal response interpretation, and planning decisions.

## Alternatives considered

- Mutate the prior strategy: rejected because it destroys the decision that governed the completed
  block.
- Copy the follow-up value directly from `TrainingResponse` into athlete state: rejected because a
  response is a causal/delivery interpretation, not an authoritative measurement.
- Replan only when the block hypothesis is supported: rejected because an inconclusive causal
  interpretation does not invalidate a separately derived follow-up capability estimate.
- Automatically alter candidate costs or trainability from one response: deferred because this
  would overinterpret limited personal evidence.
- Generate the next block inside the replanner: deferred because block resource demands, stimuli,
  resolutions, and dose remain separate governed inputs.

## Evidence and assumptions

This is a product-state and provenance decision implementing blueprint sections 45–48, 64, 73–74,
88–90. It makes no scientific claim. Competency floors and planning candidates still require their
existing evidence and uncertainty fields.

The provisional assumption is that one reviewed follow-up estimate is supplied for every actively
trained adaptation retained from the prior strategy. An inactive adaptation may explicitly retain
a prior-strategy estimate. Every candidate context identifies its selected estimate directly so
multiple adaptations or metric scopes in one broad capability domain are not conflated. Missing,
stale, incompatible, foreign-athlete, or unreviewed estimates fail explicitly rather than silently
carrying an old score forward.

## Consequences

- A second strategy can prove which completed review triggered it.
- Strategy history remains immutable and queryable.
- Updated priorities can depend on follow-up observations without claiming causal certainty.
- The next block can later be built from the revised strategy through the existing stimulus,
  resolver, allocation, and scheduling boundaries.
