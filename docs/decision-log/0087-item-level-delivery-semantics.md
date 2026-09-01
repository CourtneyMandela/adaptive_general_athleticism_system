# 0087 — Item-level delivery semantics

Date: 2026-09-01

Status: accepted; corrects the count labels and mixed-unit aggregation in Decision 0009

Decision version: `item-level-delivery-semantics@1.0.0`

## Decision

Name the delivery counts on `TrainingResponse` and `BlockReview` for what they actually count:

- `prescribed_item_count`
- `completed_item_count`

One item is one `(session execution, session prescription)` pair with one item-level adherence
record. It is not a whole workout session. Preserve the existing normalized prescription,
execution, and adherence identifiers.

Calculate block-level adherence as the prescribed-item-count-weighted mean of the dimensionless
per-response adherence ratios. Do not add raw repetition totals and duration totals across
adaptations, because those dose units are not commensurable.

Rename the persisted columns incrementally and expose the corrected names through the API and
reviewer UI. Advance the calculator rule versions to `training-response@1.1.0` and
`block-review@1.1.0`.

## Reason

The earlier implementation set `prescribed_sessions` to the number of item-level adherence
records. A session containing four tracked prescriptions therefore reported four "sessions." The
ratio remained internally consistent, but the count name was false and could make a future
absolute-count rule incorrect.

The block review also divided the sum of all actual doses by the sum of all planned doses even
when one response used repetitions and another used seconds. A ratio of mixed raw units has no
defensible interpretation.

## Alternatives considered

- **Count unique whole-session executions.** Rejected for these fields. A `TrainingResponse` is
  adaptation- and prescription-specific, and its adherence authority is the set of item-level
  records. Whole-session completion remains available from session execution history and should
  be projected separately when required by athlete UX.
- **Keep the old columns and only change the UI label.** Rejected because misleading semantics
  would remain in the domain and API contracts.
- **Aggregate raw doses across responses.** Rejected because repetitions, seconds, distance, and
  future dose units cannot be added meaningfully.
- **Weight every adaptation response equally.** Rejected because a response representing one
  delivered item should not have the same block-level influence as one representing many items.

## Evidence

This is a domain-semantics and dimensional-consistency correction. It introduces no scientific
threshold, training dose, or causal claim. The authoritative records are the existing immutable
session executions and item-level adherence records.

## Assumptions and uncertainty

- Prescribed item count remains a delivery descriptor, not a scientific minimum-dose rule.
- Item-count weighting is a replaceable V1 aggregation for dimensionless adherence ratios. Future
  policy may evaluate adaptation-specific delivery separately rather than relying on one block
  aggregate.
- Any athlete-facing whole-session count must be calculated from unique session executions, not
  inferred from these item counts.

## Consequences

- A multi-item workout can no longer masquerade as multiple sessions in training-response data.
- Block adherence no longer combines incompatible raw dose units.
- Existing databases upgrade by renaming four columns without rewriting historical values.
- API consumers must use the corrected field names; the coordinated web client is updated in the
  same change.
