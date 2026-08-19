# 0005: Block, resource, and weekly scheduling foundation

- Status: accepted provisionally
- Date: 2026-08-19
- Decision version: `block-scheduling@1.0.0`

## Decision

Milestone 5A will preserve this boundary:

```text
LongRangeStrategy
  -> explicit AdaptationResourceDemand inputs
  -> versioned ResourceAllocationPolicy
  -> immutable BlockPlan
  -> explicit SessionPrescription templates
  -> effective WeeklyAvailability
  -> deterministic WeeklyScheduler
  -> FEASIBLE / INFEASIBLE WeeklyPlan
```

A block lasts four to six weeks and retains its strategy, priority allocations, stimulus
requirements, exercise resolutions, evidence, observations, hypothesis, constraints, dates, and
rule versions. Every strategy priority receives one resource allocation. `DEFER` receives no
training time. Non-deferred demands state minimum and target weekly minutes plus an explicit
session frequency; the planner does not infer scientific maintenance, exposure, or development
doses.

Minimum demand is a hard planning constraint. If minimum weekly time exceeds the athlete's budget,
or a required exercise resolution is infeasible, the block is `INFEASIBLE` and cannot be scheduled.
After reserving feasible minimums, remaining whole-session minutes are assigned toward targets by
a deterministic weighted policy. Development weight is scaled by the existing long-range
development allocation. Maintenance and exposure weights remain separate and configurable.
Target shortfalls and partial exercise resolutions produce a `PARTIAL` block with explicit issues.

A `SessionPrescription` is a versioned, externally supplied dose template bound to one block
allocation and one selected exercise resolution. It stores the adaptation, reason for inclusion,
sets, either repetitions or duration, intensity target, rest, progression-rule reference,
substitution class, planned duration, evidence, observations, and rule version. Milestone 5A does
not calculate those values or execute progression rules.

`WeeklyAvailability` records dated, timezone-aware windows and their environment. The scheduler
consumes one prescription template per active allocation, repeats it at the block's configured
weekly frequency, and places sessions only in windows with the matching resolved environment. It
enforces window capacity, daily session limits, high-fatigue daily limits, and minimum recovery
between high-fatigue sessions. Any unscheduled required occurrence makes the weekly plan
`INFEASIBLE`; scheduled entries remain visible as tentative diagnostic output, not a valid week.

## Reason

This is the smallest inspectable bridge from adaptation strategy and exercise resolution to dose
and calendar feasibility. It maintains the blueprint's planning hierarchy, prevents the scheduler
from becoming a hidden workout generator, and makes constrained time or schedule failures explicit.

## Alternatives considered

- Generate generic sets, repetitions, durations, and intensities from adaptation names: rejected
  because those are material training rules without evidence or scoped policies.
- Treat the long-range development allocation as literal weekly time: rejected because it excludes
  maintenance and exposure requirements and was explicitly defined as relative emphasis only.
- Silently scale every demand below its minimum when time is short: rejected because minimum dose
  would lose its meaning and infeasibility would be hidden.
- Drop maintenance or exposure automatically to protect development time: rejected because
  priority does not mean exclusivity and minimums must be explicit planning inputs.
- Use an optimizer dependency: deferred; a deterministic weighted whole-session heuristic is
  sufficient and easier to inspect for V1.
- Pack multiple prescriptions into one availability window or multi-exercise session: deferred
  until session composition and within-session interference rules are defined.
- Implement workout logging or automatic progression now: deferred to later Milestone 5 slices.

## Evidence

This is a product-architecture decision implementing `docs/MASTER_BLUEPRINT.md` sections 16,
18–20, 33–37, 54, 60, 73, and 89. It does not establish operational training doses, recovery
intervals, or progression rules. Every such value is an explicit, versioned policy or prescription
input and requires evidence review before production use.

## Assumptions

- Weekly resource accounting uses integer minutes. Minimum and target minutes must divide evenly by
  the required weekly session count so every occurrence has the same planned duration in V1.
- One prescription template represents every weekly occurrence of one allocation during the block.
- One availability window can host at most one session in V1.
- High fatigue is the existing ontology's `HIGH` classification; the scheduling policy's recovery
  interval and daily limits are configurable heuristics, not scientific defaults.
- Calendar windows carry the environment in which the session can occur. A prescription may only be
  scheduled where that environment matches its exercise resolution.
- Weekly plans are immutable planning records. Moving a session creates a new plan rather than
  rewriting history.

## Uncertainty

- Scientifically defensible acquisition, maintenance, and exposure doses remain unseeded.
- Multi-adaptation sessions, supersets, warm-ups, and within-session ordering need explicit models.
- Calendar preference scoring and backtracking may be needed when the initial deterministic greedy
  scheduler encounters more complex schedules.
- Recovery and interference eventually need richer adaptation-relationship and recent-load inputs.
- Progression-rule behavior and symptom modifications remain outside this slice.

## Consequences

- A block cannot appear feasible unless its minimum resource demands and exercise resolutions are
  feasible.
- An athlete with less weekly time can receive a target-short block while preserving declared
  minimums; dropping below minimum is explicitly infeasible.
- Identical training intent can schedule differently when availability changes, while prescriptions
  and adaptation targets remain stable.
- Every scheduled session can be traced to the block, strategy priority, stimulus, exercise
  resolution, prescription rule, athlete observations, evidence claims, availability, and
  scheduling policy.
