# Decision 0026: Weekly review and availability confirmation

- Status: accepted provisionally
- Date: 2026-08-22
- Decision version: `weekly-review-pwa@1.0.0`

## Decision

Extend the current-week read projection with a backend-derived weekly review and the source week's
explicit availability windows. The review reports descriptive counts for recorded sessions,
completed sessions, post-session closure, resolved progression items, and persisted progression
outcomes. It also returns one typed next-step state:

- `awaiting_sessions` while any scheduled occurrence lacks an execution record;
- `awaiting_post_session_safety` while any execution lacks a recovery/safety decision;
- `awaiting_progression` while a supported assigned policy is ready but unevaluated;
- `manual_configuration_required` for missing/ambiguous/unsupported policies, infeasible schedules,
  or persisted `HOLD`/`REVIEW_REQUIRED` outcomes;
- `ready_to_prepare_next_week` when the ordinary week is closed and may use roll-forward;
- `next_week_already_prepared` when the plan already has its unique successor;
- `block_complete` after the final block week, where block review replaces weekly roll-forward.

The PWA renders this server-owned state rather than reimplementing closure policy. When ready, it
proposes the source availability windows shifted by exactly seven days. The athlete may edit those
times and must explicitly confirm that they are available before submission. The browser does not
silently reuse availability.

Roll-forward now stores that confirmation as a direct user-report `Observation`, including the
submitted windows, reliability, provenance, source weekly plan, and target week. The new
`WeeklyAvailability` retains both its prior source references and the confirmation observation.

A prescription item is progression-resolved when that execution has a decision or the immutable
prescription already has a true revision descendant. The latter handles repeated occurrences of one
prescription version without manufacturing a second competing successor. It does not claim that the
later occurrence independently caused another progression.

## Reason

The backend can now carry revisions into a future week, but the PWA has no safe way to know whether
the week is closed or to provide new availability with honest provenance. Descriptive server-side
closure states keep business and safety meaning out of React. Explicit confirmation preserves the
blueprint requirement that schedules and environments can change over time.

## Alternatives considered

- Derive readiness from session cards in React. Rejected because other clients could disagree and
  the transport would silently own planning policy.
- Automatically copy availability after the last workout. Rejected because last week's schedule is
  not an observation of next week's availability.
- Show scientific-sounding summaries such as “strength on target” from adherence alone. Rejected
  because the repository has no reviewed rule supporting those interpretations.
- Allow roll-forward despite `HOLD` or `REVIEW_REQUIRED`. Rejected because safety and explicit review
  states take precedence over convenience.
- Require a second progression decision after a prescription already has a successor. Rejected for
  this slice because the database deliberately permits one successor per prescription version and
  multi-session aggregation has no approved policy yet.

## Evidence and uncertainty

This is an orchestration, provenance, and UX decision implementing blueprint sections 35, 37--42,
57--58, 73, and 77. It adds no training threshold, response interpretation, scientific claim,
exposure rule, or symptom classifier.

The review is intentionally descriptive. Multi-session progression aggregation, weekly adaptation
status such as “on target,” changed-environment exercise re-resolution, correction workflows, and
block-end reassessment remain unresolved. The first PWA editor can adjust existing shifted windows
but does not yet create new environments or add arbitrary new windows.

## Consequences

- A normal athlete can close the week and prepare a traceable next week without free-form AI chat.
- The PWA cannot advance through missing performance, recovery, progression, or manual-review state.
- Availability confirmation becomes an athlete observation rather than unproven copied metadata.
- Weekly summaries remain honest about what the system actually knows.
