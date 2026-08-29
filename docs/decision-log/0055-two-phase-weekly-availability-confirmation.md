# 0055: Two-phase weekly availability confirmation

- Status: accepted
- Date: 2026-08-29

## Context

Weekly roll-forward currently accepts an athlete's next-week availability and creates the next
plan in one transaction. That ordering is safe only when every existing exercise resolution still
matches the selected environment. It gives the reviewed environment re-resolution path introduced
by decisions 0053 and 0054 no durable, athlete-authored target week to inspect before the next plan
is scheduled.

The blueprint requires changing environment and equipment constraints to affect exercise means
without silently changing the athlete, goal, adaptation, or dose. Availability is an observation,
while an environment-driven prescription replacement is a governed planning decision. Those two
authorities must be separated.

## Decision

Split weekly advancement into two persisted phases.

1. The athlete confirms dated availability for the next consecutive week. The API appends a
   `weekly_availability_confirmation` observation and a `WeeklyAvailability` record linked to the
   exact source weekly plan. It does not create prescriptions, templates, or a weekly plan.
2. The current-week projection compares the latest immutable prescription descendants with the
   environments in that confirmed availability. It reports either that governed environment
   revision is required or that the week is ready to finalize.
3. Reviewed environment prescription revision must consume the persisted confirmation and may
   only select environments represented by its windows.
4. Final roll-forward accepts the identifier of that persisted availability record. It no longer
   accepts replacement windows, reliability, or provenance, and therefore cannot change the
   athlete's report while scheduling.

`WeeklyAvailability.source_weekly_plan_id` is nullable for initial/manual plans and required for
the new confirmation flow. The database enforces at most one confirmation per source weekly plan.
Historical availability and source observations remain immutable and queryable.

## Major implementation choices

- Reuse `WeeklyAvailability` rather than introduce a parallel draft entity. The record already
  represents dated, observation-backed availability; the new source-plan link supplies the missing
  lifecycle boundary.
- Preserve an explicit finalization action. Confirmation is athlete-authored state; plan creation
  remains server-owned and can be blocked until governed revisions are complete.
- Determine readiness descriptively from persisted resolution environments. The read model does
  not create substitutions or infer equivalent exercises.
- Keep environment prescription revision operator-only. Athlete HTTP routes can report the need
  for review but cannot choose exercises or doses.
- Make the new source-plan link optional so existing initial-week data and historical migrations
  remain valid.

## Alternatives considered

- Keep the one-step roll-forward and ask operators to rely on future equipment reports. Rejected
  because the exact dated availability used for scheduling would still not exist when revisions
  were reviewed.
- Store a client-side draft only. Rejected because it would not be durable provenance and could
  diverge from the eventual scheduling request.
- Automatically substitute exercises after confirmation. Rejected because equivalence and dose
  transfer require reviewed evidence and planning authority that the athlete-facing route does not
  have.
- Add a separate `WeeklyPreparation` aggregate. Deferred because the existing availability model
  can express the required state with less duplication; a richer workflow entity can be added if
  later approval or assignment states require it.

## Assumptions

- A source plan advances to exactly one next-week availability confirmation and one successor plan.
- Availability may contain multiple environments, but every carried session template must resolve
  to one environment and that environment must appear in at least one confirmed window.
- The current week's approved scheduling policy remains the policy authority for its successor.
- Confirmation timestamps and finalization timestamps are server-validated, timezone-aware event
  times supplied by the authenticated client.

## Unresolved questions

- Role-based assignment and notification for the operator review queue are not implemented yet.
- Editing a mistaken availability report is not supported in this slice. A future correction must
  append superseding provenance rather than overwrite the original confirmation.
- The PWA does not yet estimate operator turnaround or send background notifications.

## Consequences

Travel and equipment changes now become durable inputs before exercise selection and scheduling.
The ordinary unchanged-environment path takes a second explicit action, while changed environments
pause with a clear governed-review state. This adds a small interaction cost but removes an
important provenance and authority ambiguity from the weekly lifecycle.
