# 0040 — Reviewed planning authorities

Date: 2026-08-27

## Decision

Keep immutable `CompetencyFloor` and `PriorityPolicy` definitions separate from their governance
state. Add append-only `CompetencyFloorReview` and `PriorityPolicyReview` histories. Each history is
linear, sequence-numbered, evidence-linked, reviewer-attributed, versioned, and records rationale
and uncertainty independently of the reviewed definition.

The operator-only initial-planning command must identify the exact current approved review for its
priority policy and for every candidate competency floor. Initial planning fails closed when a
review is missing, stale because it has been superseded, non-approved, belongs to another
authority, or postdates the requested strategy timestamp. The resulting `DecisionRecord` cites
both the immutable authority IDs and exact review IDs.

## Reasons

The initial planning service currently checks that floors and a policy exist, but existence does
not establish that a qualified reviewer approved their current use. A separate review lineage
preserves rejected and superseded governance decisions without mutating the scientific or rule
artifact. Requiring exact review IDs prevents a caller from relying on whichever approval happens
to be current at execution time and makes the strategy decision reproducible.

## Major implementation choices

- Reuse the existing three-state review vocabulary: `approved`, `needs_revision`, and `rejected`.
- Require at least one persisted `EvidenceClaim` on every review. Floor reviews must include every
  claim cited by the floor; they may include additional review-specific evidence.
- Permit any decision state to supersede the current review. Only the current `approved` state can
  authorize initial planning.
- Keep review creation outside athlete-facing HTTP routes. A narrow operator CLI appends reviews.
- Record review references in the initial strategy's `DecisionRecord`; do not add review foreign
  keys directly to `LongRangeStrategy` in this slice because future strategy revisions have a
  different governance path and should not inherit a misleading initial-only schema.

## Alternatives considered

- Store approval fields on floors and policies. Rejected because updating approval would overwrite
  history or force duplicate authority definitions.
- Accept any historical approved review. Rejected because a later rejection or needs-revision
  decision must revoke authorization for new strategies without destroying old decisions.
- Automatically select the current review. Rejected because the operator input should pin the
  exact authority that was reviewed and because explicit IDs make race and audit behavior clearer.
- Add public review endpoints. Rejected because reviewer identity and authorization are not yet
  backed by an administrative authentication model.

## Assumptions

- Review evidence is governance provenance, not proof that a threshold or weighting is universally
  valid. Applicability and uncertainty remain mandatory text.
- A review timestamp equal to the strategy timestamp is valid; a future review is not.
- The existing `AssessmentReviewDecision` enum supplies the shared decision vocabulary for now.

## Unresolved questions

- Which human roles may review floors and policies once administrative identity is implemented?
- Should review validity have an explicit expiry interval, or remain current until superseded?
- Should replanning require independently reviewed authority snapshots, and how should strategy
  revisions persist those exact references?
- What evidence-review workflow and conflict-of-interest controls are required before production?
