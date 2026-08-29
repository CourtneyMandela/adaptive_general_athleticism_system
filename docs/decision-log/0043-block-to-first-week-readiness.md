# 0043 — Block-to-first-week readiness

- Status: accepted provisionally
- Date: 2026-08-28
- Decision version: `athlete-planning-status-projection@1.3.0`

## Decision

Extend the authenticated planning-status projection from a uniquely identified feasible block to
its first dated week. Derive a read-only checklist across the existing transactional weekly-plan
boundary:

1. at least one versioned `WeeklySchedulingPolicy` is available;
2. an operator must provide explicit prescriptions for every active block allocation;
3. the operator must provide explicit session composition and frequency;
4. the operator must provide dated, observation-backed availability and select the exact policy;
5. the resulting week remains explicitly `FEASIBLE` or `INFEASIBLE`.

Only plans with `block_week == 1` participate in first-week readiness. A single first-week plan is
summarized with its exact availability, policy, session-template, prescription, issue, and rule
lineage. Multiple first-week plans create an ambiguity state; the projection does not choose the
newest plan. Later block weeks do not make first-week selection ambiguous.

Keep the weekly-plan write boundary atomic. Do not add separately persisted draft prescriptions,
draft session containers, or draft availability merely to create intermediate progress states.

## Reason

A persisted block allocates resources but is not a usable training week. The existing
`PersistedWeeklyPlanService` correctly requires explicit dose, session composition, dated
availability, and a scheduling policy before invoking the deterministic scheduler. Making that
boundary visible in the PWA advances the first vertical slice without allowing the browser or LLM
to invent a workout.

## Alternatives considered

- Generate prescriptions from allocation minutes. Rejected because minutes do not authorize sets,
  repetitions, intensity, rest, exercise grouping, fatigue class, or progression behavior.
- Persist prescription, session-template, and availability drafts independently. Rejected because
  the current transactional service intentionally prevents partial authoritative chains; a future
  reviewer workflow may introduce a separate draft aggregate if its governance is defined.
- Treat any weekly plan for the block as proof that week one exists. Rejected because later weeks
  and week one have different calendar meaning.
- Select the newest of several first-week plans. Rejected because no weekly-plan supersession or
  approval rule authorizes that choice.
- Hide infeasible weeks. Rejected because structured scheduling infeasibility is a meaningful
  planning result and must remain inspectable.

## Evidence and uncertainty

This is an application-state and provenance decision implementing blueprint sections 33–36, 58,
64, 73, 77, and 89. It establishes no dose, intensity, recovery interval, exercise grouping, or
weekly schedule. The existence of a scheduling policy means only that a versioned policy is
persisted; scientific review and applicability governance for those policies remain unresolved.

## Assumptions and unresolved questions

- The first week is the persisted plan whose `block_week` is exactly one.
- A feasible or partial block may enter weekly preparation; an infeasible block may not.
- Exact template and prescription counts are reconstructed from the selected plan's scheduled
  sessions and structured issues, then loaded from immutable persistence.
- Multiple first-week plans remain blocked until explicit supersession/current-plan semantics are
  modeled.
- Prescription-authoring and session-composition governance still require a dedicated operator
  workflow; they are not athlete-facing controls in this slice.

## Consequences

- The athlete can see why a block is not yet a usable week.
- A scheduling failure remains distinct from an infeasible block or missing dose inputs.
- The PWA gains no generic workout-generation control.
- The next slice can address governed prescription/session authoring or first-week safety-policy
  readiness without weakening the existing transactional boundary.
