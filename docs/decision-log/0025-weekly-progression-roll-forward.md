# Decision 0025: Weekly progression roll-forward lineage

- Status: accepted provisionally
- Date: 2026-08-22
- Decision version: `weekly-progression-roll-forward@1.0.0`

## Decision

Add one transactional application boundary that prepares the immediately following week of an
existing block from a persisted weekly plan. The caller supplies only the next week's explicit
availability and preparation timestamp. The service carries forward the source plan's versioned
scheduling policy and session structure, resolves each template item to the latest immutable
prescription revision available at preparation time, and runs the existing deterministic weekly
scheduler.

Unchanged prescriptions and templates are reused. When at least one template item has a newer
prescription revision, the service appends a new immutable `SessionTemplate` whose
`previous_template_id` identifies the source template. A generated successor `WeeklyPlan` records
`previous_weekly_plan_id`. Both links are database-enforced, and one source object may have at most
one automatic successor.

The persistence boundary verifies that a carried prescription is the same prescription or a true
revision descendant of the corresponding source-template item. It also verifies that week lineage
stays within one athlete and block and advances exactly seven days and one block-week. The prior
template, prescription, and weekly plan remain unchanged.

## Reason

The progression engine already produces evidence-linked, immutable prescription revisions, but
new weekly plans currently accept fresh dose drafts and do not consume those revisions. That leaves
the daily performance-to-future-prescription loop open. A narrow roll-forward boundary closes the
gap without adding a workout generator, inventing progression values, or allowing a client to
rewrite an approved revision.

## Alternatives considered

- Mutate the prior session template or weekly plan. Rejected because completed and scheduled
  history must remain reproducible.
- Let the browser submit a revised dose for the next week. Rejected because it could bypass the
  progression decision and provenance chain.
- Automatically create an entire future block. Rejected because block review, reassessment, and
  next-block planning are separate higher-level decisions.
- Select prescriptions only by resource allocation. Rejected because it could choose an unrelated
  prescription with the same allocation instead of following revision lineage.
- Clone every unchanged prescription and template. Rejected because it adds history without a new
  decision or changed state.
- Reuse the previous week's availability. Rejected because availability and environment are
  changing observations; the next week must provide its own explicit record.

## Evidence and uncertainty

This is an orchestration and provenance decision implementing blueprint sections 35--38, 47--48,
58, 64, and 73. It introduces no scientific claim, threshold, increment, exposure cap, fatigue
model, or scheduling heuristic. All dose changes must already have been authorized by an existing
versioned progression policy and immutable progression decision.

The V1 boundary advances only one consecutive week within the same block. It does not decide
whether a block should continue, replace a safety policy, re-resolve exercises for a changed
environment, correct historical decisions, or create the next block. A later weekly-review workflow
may orchestrate those separate governed actions before calling this service.

## Consequences

- Approved progression revisions can affect future scheduled work without changing history.
- A future plan can be traced through its template items to prescription revisions, progression
  decisions, executions, observations, policies, and evidence.
- Duplicate successor creation fails rather than producing competing next weeks.
- Environment changes that invalidate an existing exercise resolution fail explicitly; they still
  require the existing governed re-resolution path rather than an alleged equivalent substitute.
