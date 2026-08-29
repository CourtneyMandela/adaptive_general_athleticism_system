# Decision 0037: Governed initial-strategy creation

- Status: accepted provisionally
- Date: 2026-08-27
- Decision version: `governed-initial-strategy-creation@1.0.0`

## Decision

Add one transactional application boundary from persisted capability estimates to the first
`LongRangeStrategy` for an athlete. The request identifies an existing `PriorityPolicy` and supplies
explicit candidate contexts that each name an adaptation, competency floor, and capability
estimate. It also supplies the bounded long-range horizon and review interval.

The service loads every referenced record, verifies athlete ownership and timestamps, creates one
`CapabilityNeed` per unique floor-estimate pair through `CompetencyFloorDetector`, converts the
explicit contexts into `AdaptationPlanningCandidate` records, and delegates state assignment and
ranking to `LongRangeStrategyPlanner`. It appends all needs and exactly one initial strategy in one
transaction.

Candidate source observations always include the estimate's direct source observations. Candidate
evidence always includes the competency floor's evidence. Extra source or evidence identifiers are
allowed only when their persisted records exist; repository integrity still requires all strategy
observations to belong to the athlete.

An athlete has exactly one root strategy, identified by null revision-lineage fields. A partial
unique database index and repository check reject competing initial strategies. Later strategies
must continue through the existing block-review replanning lineage rather than creating another
root.

The endpoint does not create a block, stimulus, exercise resolution, resource demand, prescription,
or weekly schedule. Those require separate governed inputs and existing application boundaries.

## Reason

The domain planner and persistence model could already represent an initial strategy, but only tests
and direct repository calls assembled it. Assessment can now create governed capability estimates,
so the missing application step in the blueprint's first vertical slice is estimate to identified
need to initial long-range strategy.

Keeping this boundary narrow connects existing engines without inventing exercise selection or
training dose. Explicit context inputs also avoid pretending that goal relevance, transfer value,
trainability, recovery cost, or comparative advantage can be inferred from one assessment number.

## Alternatives considered

- Generate the complete first block and Week 1 in the same request. Rejected because stimuli,
  exercise feasibility, resource amounts, dose, composition, and availability remain separately
  governed inputs.
- Infer every candidate score from athlete goals or an LLM. Rejected because those mappings have no
  reviewed deterministic policy in the current repository.
- Accept caller-created capability needs or a complete strategy object. Rejected because that would
  bypass the existing deterministic detector and planner.
- Permit multiple unrelated initial strategies. Rejected because it creates competing roots with no
  explicit supersession history.
- Automatically choose every persisted competency floor or latest estimate by domain. Rejected
  because metric scope and applicability are material and must not be conflated by recency.

## Assumptions and provisional choices

- Candidate contexts are governed application inputs, not athlete-facing sliders. The current PWA
  does not expose them.
- One capability need may support more than one adaptation candidate, so identical floor-estimate
  pairs are deduplicated within the transaction.
- An incomparable, stale, or uncertain estimate remains explicit in the generated need; the planner
  may defer or limit it rather than silently replacing it.
- The priority policy is already persisted and versioned. A dedicated review/assignment history for
  priority policies remains future governance work.
- Duplicate requests after a root strategy exists return conflict rather than silently returning a
  possibly different prior result because no request idempotency key exists yet.

## Evidence and uncertainty

This is an application architecture decision implementing the blueprint's observation-to-state and
initial-planning chain. It introduces no scientific threshold, candidate score, or training dose.
Software tests use synthetic evidence, floors, estimates, policies, and contexts that are explicitly
non-operational.

## Consequences

- Governed assessment state can now cross a transactional boundary into identified needs and an
  inspectable initial strategy.
- Partial failures cannot leave needs without their strategy.
- Competing root strategies fail at both repository and database boundaries.
- Initial-plan readiness, governed candidate-context derivation, resource preparation, block
  creation, and Week 1 generation remain subsequent slices.
