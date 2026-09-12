# 0115 — Dependency-aware planning-authority review

Date: 2026-09-12

Status: accepted

Decision version: `dependency-aware-planning-authority-review@1.0.0`

## Decision

Add one optional owner-alpha action that ratifies every currently available prepared planning-
authority group after a single combined attestation. The action covers the priority policy,
competency-floor batch, resource-authority bundle, and training-construction bundle.

The browser submits each candidate's exact server-projected version and digest to its existing
ratification endpoint in dependency order. It re-reads training construction after resource
ratification because that bundle can become available only after its evidence and ontology
prerequisites exist. Every server endpoint retains its own authorization, validation, transaction,
immutable records, and decision history.

This is intentionally not described as one database transaction. A failure stops subsequent
requests, reports how many exact groups were already saved, reloads current status, and permits a
safe retry. Any known conflict disables the combined action before the first write, and a newly
appearing conflict stops the sequence at its authority boundary. The existing individual review
controls remain available.

## Reason

The four governance mechanisms were built separately to prove their invariants, but requiring four
repetitive attestations after the complete content has been reviewed adds friction without adding a
new authority boundary. The first-session path needs all four authority families, and the resource
bundle can unlock construction within the same review visit.

## Alternatives considered

- **Create a new cross-authority backend transaction.** Deferred. The current ratifiers own
  separate validated transactions and share prerequisite records; refactoring all of them into one
  unit of work would add substantial coupling for little owner-alpha benefit.
- **Send all ratifications concurrently.** Rejected because resource and construction authorities
  have an explicit dependency and may share evidence lineage.
- **Hide the individual candidate cards.** Rejected because the combined attestation must still be
  grounded in visible exact scope, evidence boundaries, engineering choices, and limitations.
- **Automatically approve on deployment.** Rejected because software deployment is not owner
  attestation.
- **Continue requiring one checkbox and click per group.** Retained as a recovery path but rejected
  as the only path because it creates avoidable review sludge after the pattern is proven.

## Assumptions and provisional choices

- One owner-alpha reviewer is allowed to attest to all four visible authority families. Future
  independent scientific or clinical reviewer roles may require separate stages.
- “Group” means one candidate transaction; a competency-floor data batch counts as one group even
  when it contains multiple individually provenance-bound floors.
- Partial completion is safe because every ratifier is digest-bound and idempotent, and the UI
  explicitly avoids claiming cross-group atomicity.

## Consequences

- The first governed path can move through planning authority setup with one deliberate owner
  action instead of four repetitive actions.
- Per-artifact provenance, source classification, versioning, and immutable decisions are
  unchanged.
- Conflicts remain visible and fail closed; retry resumes from persisted status rather than
  duplicating history.
