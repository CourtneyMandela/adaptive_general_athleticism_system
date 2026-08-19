# 0004: Stimulus-to-exercise resolution

- Status: accepted provisionally
- Date: 2026-08-19
- Decision version: `exercise-resolution@1.0.0`

## Decision

Milestone 4 will preserve this boundary:

```text
LongRangeStrategy priority
  -> versioned StimulusRequirement
  -> effective-dated EnvironmentSnapshot
  -> deterministic exercise matching
  -> FULL / PARTIAL / INFEASIBLE resolution
```

A stimulus requirement references the unchanged adaptation and priority that produced it. It
describes movement patterns, allowed loading types, minimum loadability, velocity characteristics,
and maximum acceptable skill, impact, stability, fatigue, and soreness costs. It also records its
source observations, evidence claims, strategy, rule version, and creation time. It contains no
sets, repetitions, duration, intensity prescription, or weekly schedule.

An environment snapshot is derived at a specific time from one athlete environment, equipment
records, and effective-dated availability history. For each equipment item, the latest active
availability record controls current availability. A temporary record with an end time can expire
and reveal an older still-active state. Missing availability is treated conservatively as
unavailable. The snapshot preserves every availability-record identifier used.

The resolver first applies hard constraints: equipment, explicit contraindication tags, skill,
impact, stability, fatigue, soreness, outdoor access, floor area, and noise. Remaining exercises
receive a configurable weighted score for adaptation role, movement coverage, loading-type match,
loadability, and velocity coverage. Resolver weights and thresholds live in a versioned
`ExerciseResolverPolicy`; there are no hidden operational defaults.

A candidate is `FULL` only when it fully represents the required adaptation, movement, loading,
loadability, and velocity characteristics while satisfying hard constraints. A candidate above the
partial threshold may be returned as `PARTIAL` with explicit limitations. If no candidate reaches
that threshold, the resolution is `INFEASIBLE`. Partial and infeasible outcomes must state what the
environment cannot reproduce.

## Reason

The blueprint requires exercise selection to follow adaptation and stimulus selection, equipment
changes to alter means rather than goals, and inadequate substitutes to be represented honestly.
This design makes that behavior deterministic, versioned, inspectable, and counterfactually
testable without starting session prescription early.

## Alternatives considered

- Resolving directly from capability needs to exercise names: rejected because it skips adaptation
  strategy and stimulus definition.
- Treating any exercise with the same movement pattern as equivalent: rejected because loadability,
  velocity, skill, impact, and equipment can materially change the stimulus.
- Rewriting the strategy when equipment changes: rejected because temporary environment changes
  should not silently erase the athlete's developmental objective.
- Letting an LLM choose substitutions: rejected as the sole mechanism because substitution
  equivalence is a core deterministic decision.
- Adding exact loads, sets, repetitions, or session timing now: deferred to the session and
  progression milestone.
- Seeding an exercise catalog merely to make the resolver appear useful: rejected; tests use
  clearly labeled synthetic fixtures.

## Evidence

This is a product-architecture decision implementing `docs/MASTER_BLUEPRINT.md` sections 11–13,
33, 56, 65, and 72. It makes no scientific claim that a particular exercise, score, or threshold is
universally appropriate. Operational stimulus rules and exercise metadata require reviewed
evidence and domain review where they materially affect training.

## Assumptions

- Exercise equipment requirements identify concrete equipment records. Equipment-category or
  capability alternatives can be represented by separate annotated exercise variants until a
  reviewed equivalence model exists.
- Loadability is an ordered ontology value (`limited < moderate < high`) used only for relative
  fidelity, not as a prescribed load.
- Space is represented provisionally by available/required floor area; noise uses an explicit
  ordinal ceiling; outdoor access is boolean.
- Hard-constraint ceilings are prepared by upstream safety and athlete-state workflows. This
  milestone does not infer diagnoses or medical restrictions.
- Resolver score is a ranking heuristic, not a physiological equivalence percentage.

## Uncertainty

- Equipment capability and load-limit comparison needs richer typed semantics before exact loading
  prescriptions exist.
- Exercise taxonomy completeness and metadata quality will govern resolver quality.
- Valid substitution classes and stimulus-specific scoring policies require evidence review.
- Fatigue, soreness, skill, impact, and stability ordinals are coarse V1 constructs.

## Consequences

- A full gym and hotel environment can select different exercises while retaining the same
  stimulus and adaptation identifiers.
- Reduced loadability or other mismatches remain visible as limitations rather than being presented
  as equivalence.
- An unsatisfied high-force or otherwise constrained stimulus can be explicitly infeasible.
- Every resolution can be traced to the strategy, stimulus, environment, availability events,
  exercises considered, policy, evidence, and athlete observations.
