# 0071: Derived planning lifecycle workbench

- Status: accepted provisionally
- Date: 2026-08-30
- Extends: Decisions 0060–0066 and 0070
- Decision version: `derived-planning-lifecycle-workbench@1.0.0`

## Decision

Add one role-protected, read-only planning queue that derives each athlete's next reviewer-owned
boundary across initial planning, resource-demand preparation, block creation, and first-week
authoring. Select only the current leaf of the athlete's append-only strategy lineage and expose at
most one pre-block workflow item per athlete. Keep prerequisite problems visible as blocked items.

Add `/review/queue` as the primary reviewer workbench. Each item deep-links to an existing structured
workflow, which reloads its authoritative preparation projection before allowing any write. Retain
the separate post-block queue because completed-block review is time/history driven and can coexist
with ordinary daily execution state.

## Reason

The structured workflows were individually operable but required reviewers to obtain athlete,
strategy, or block IDs elsewhere. A derived queue closes that navigation gap without duplicating
domain state or allowing the browser to decide which planning stage comes next.

## Alternatives considered

- Persist workflow/task rows. Rejected because they would duplicate immutable planning facts and
  require a synchronization state machine.
- Show every possible workflow for every historical strategy. Rejected because historical records
  are provenance, not pending work; only the current strategy leaf should drive new planning.
- Automatically advance through writes. Rejected because every boundary contains explicit review
  judgments and must remain independently inspectable.
- Fold post-block work into the same one-item-per-athlete queue. Deferred because a due historical
  block and preparation of a newly appended successor have different operational clocks.

## Evidence

This is a workflow and provenance decision implementing blueprint sections 55, 60, 64, 74, 77,
and 89. It creates no training score, scientific claim, dose, or exercise recommendation.

## Assumptions and uncertainty

- Strategy lineage has exactly one current leaf per athlete; ambiguous forks fail queue projection.
- V1 queue volume permits synchronous composition from existing preparation projections.
- Week 2 onward remains governed by the athlete-facing weekly roll-forward path; the reviewer queue
  owns only the explicitly authored first week.
- Reviewer-role specialization and pagination remain future operational concerns.

## Consequences

- Reviewers can enter every pre-block workflow without manually copying internal IDs.
- Missing estimates, authorities, environments, policies, or catalog inputs remain visible.
- Historical strategies and completed Week 1 work do not create duplicate queue items.
- Every write continues through its existing narrow transactional boundary.
