# 0003: Planning engine foundation

- Status: accepted provisionally
- Date: 2026-08-19
- Decision version: `planning-engine@1.0.0`

## Decision

Milestone 3 will use a deterministic, versioned planning pipeline:

```text
CapabilityEstimate
  -> configured CompetencyFloor comparison
  -> CapabilityNeed
  -> scored AdaptationPlanningCandidate
  -> DEVELOP / MAINTAIN / EXPOSE / DEFER
  -> revisionable LongRangeStrategy
```

Competency floors are versioned records, scoped to one capability metric and unit, and must cite at
least one evidence claim. The repository will not seed thresholds until those claims are reviewed.
Floor detection supports higher-is-better and lower-is-better metrics, preserves stale and
incomparable states, and records the exact capability estimate and rule version used.

Priority scoring will use a configurable weighted benefit-minus-cost heuristic. Benefits include
deficit severity, general relevance, user-goal relevance, prerequisite value, expected
trainability, and transfer value. Costs include fatigue, time, and interference. Estimate
confidence scales the benefit signal. The formula, weights, confidence multipliers, state
thresholds, and maximum simultaneous development targets belong to an explicit `PriorityPolicy`;
the engine has no hidden scientific defaults.

State assignment is rule based. Safety restriction produces `DEFER`; a required introductory
exposure produces `EXPOSE`; missing prerequisites or unresolved capability information produces
`DEFER`; below-floor needs compete for `DEVELOP`; capabilities at or above a floor default to
`MAINTAIN`. A user-valued comparative advantage may compete for `DEVELOP` only when no severe
deficit remains. Lower-ranked deficits may be deliberately deferred rather than mislabeled as
maintained.

The long-range output records relative development allocation, current states, sequencing groups,
review triggers, a deterministic block hypothesis, source observations, capability estimates,
competency floors, evidence claims, and rule versions. It will not contain exercises, doses,
sessions, or a rigid multi-month workout schedule.

## Reason

This is the smallest coherent implementation of the blueprint's competency-floor, bottleneck,
comparative-advantage, four-state, roadmap, and block-hypothesis requirements. Explicit inputs and
score components make the result inspectable and counterfactually testable while avoiding the
claim that one priority equation is established science.

## Alternatives considered

- LLM-generated priorities: rejected because the LLM cannot be the training engine and the result
  would be difficult to regression-test.
- One opaque athleticism score: rejected because it erases domain differences and provenance.
- Hard-coded universal floors and weights: rejected because applicability and evidence review are
  unresolved.
- Multiplying every factor exactly as shown in the conceptual blueprint: rejected because a single
  zero makes a candidate disappear and implies unjustified mathematical precision.
- Generating exercises or weekly minutes in this milestone: deferred to later resolver and
  scheduling milestones.
- Optimizing only deficits: rejected because the product must preserve competency, introductory
  exposure, and athlete-valued comparative advantages.

## Evidence

This decision implements product architecture from `docs/MASTER_BLUEPRINT.md`, especially sections
6, 17–21, 33–34, and 71. It introduces no scientific floor, training dose, or periodization claim.
Concrete floor thresholds and scientifically informed candidate signals require reviewed
`EvidenceClaim` records before operational use.

## Assumptions

- Capability estimates compared with a floor are numeric, metric-scoped, unit-compatible, and not
  stale. Other estimates produce an explicit incomparable or uncertain need.
- Normalized deficit is a bounded relative gap from the configured floor. It is a ranking aid, not
  a physiological effect size.
- Candidate signals are prepared by upstream athlete-state and evidence-policy workflows and carry
  observation and evidence identifiers.
- Relative development allocation describes emphasis only. It is not a prescribed time or dose.
- Roadmap sequence groups are revisionable ordering hints, not fixed calendar phases.

## Uncertainty

- Competency floors, priority weights, and evidence applicability require domain review.
- Maintenance and exposure doses are not yet modeled, so non-development states receive no numeric
  dose in this milestone.
- Adaptation-graph traversal remains explicit candidate input until relationship direction and
  applicability rules are validated against curated ontology data.
- User goal relevance and general-transfer scoring taxonomies remain to be designed.

## Consequences

- Opposite capability profiles can produce meaningfully different priorities without changing
  exercises or pretending all athletes need the same profile.
- Every major strategy output can answer which athlete observations, estimates, floors, evidence,
  and policy version informed it.
- The planner will refuse incomplete or mismatched inputs rather than fabricate missing capability
  state.
- Exercise resolution, weekly resource conversion, and sessions remain later milestones.
