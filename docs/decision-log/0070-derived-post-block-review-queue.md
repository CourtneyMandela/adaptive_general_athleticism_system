# 0070: Derived post-block reviewer work queue

- Status: accepted provisionally
- Date: 2026-08-30
- Extends: Decisions 0068 and 0069
- Decision version: `derived-post-block-review-queue@1.0.0`

## Decision

Add one authenticated, read-only post-block work-queue projection. It scans due, persisted blocks and
derives either a block-review item or a replanning item from the existing preparation projections.
Ready and blocked work remain visible; a block disappears from the queue only after an immutable
successor strategy exists. The queue is not stored as mutable task state.

Make this queue the primary entry point on `/review/post-block`, while retaining manual UUID lookup
as a recovery and deep-link mechanism. Opening an item still loads the complete authoritative
preparation projection before any write.

## Reason

The closed-loop workflow was operable but required reviewers to discover and paste internal IDs.
Deriving work from authoritative history removes that operational gap without adding a second state
machine that could drift from block, review, or strategy records. Showing blocked items also keeps
missing execution, safety, reassessment, or policy history visible instead of silently hiding it.

## Alternatives considered

- Persist mutable queue/task rows. Rejected because task lifecycle would duplicate facts already
  represented by immutable domain history and introduce synchronization failure modes.
- Return only ready items. Rejected because blocked due work requires operator attention and should
  not disappear.
- Let the browser list blocks and determine eligibility. Rejected because authorization, temporal
  filtering, and provenance joins belong at the server boundary.
- Remove manual lookup. Rejected because deep links and controlled recovery remain useful.

## Evidence

This is a workflow and provenance decision implementing blueprint sections 58, 64, 74, 77, and 89.
It creates no scientific claim, training threshold, or planning score.

## Assumptions and uncertainty

- A block becomes review-due on the calendar day after its inclusive `ends_on` date.
- V1 queue volume is small enough for synchronous projection. Pagination and indexed status
  projections may be needed at operational scale.
- `planning_reviewer` remains the provisional authority for both review stages.

## Consequences

- Reviewers no longer need a block UUID to find due closed-loop work.
- Blocked items expose exact preparation issues and remain selectable for inspection.
- Completed review items transition to replanning without rewriting the original queue item.
- Replanned blocks leave the queue because the successor strategy is already discoverable through
  its immutable lineage.
