# 0150 — Longitudinal assessment history projection

## Decision

Add a read-only longitudinal history to the authenticated athlete assessment-workflow projection.
Project every persisted assessment selection run in reverse chronological order, retaining its
selection context, eligibility review, environment, rule version, and exact selections.

Within each selection, keep these records structurally separate:

- incomplete or safety-stopped `AssessmentAttempt` records and their user-report provenance;
- one completed `AssessmentPerformance` and its direct test-result observation, when present;
- every `CapabilityEstimate` derived from that completed performance, including its source
  observations, calculation method, confidence, validity interval, rule version, and policy ID.

The current actionable run remains a separate projection. The history is explanatory only and
cannot create, edit, delete, retry, interpret, or ratify anything. A historical completed result
reports whether explicit completion and no-stop attestations were actually stored; absence in an
older record is displayed as not historically attested rather than inferred.

## Reason

Decision 0149 made incomplete and safety-stopped attempts immutable, but the athlete-facing
workflow projected them only when they belonged to the latest selection run. Starting a later run
therefore hid earlier attempts even though they remained correctly persisted. Completed direct
observations and derived estimates were also visible only through the latest run.

An athlete and reviewer need to inspect change across reassessments without collapsing an attempt
into a result, a result into an estimate, or a newer estimate into an overwrite of history. Adding
an additive read model closes that visibility gap without changing the authoritative records.

## Alternatives considered

- Replace the latest-run workflow with one generic event stream. Rejected because it would mix
  actionable current state with historical facts and weaken the existing result-entry boundary.
- Copy all records into a new history table. Rejected because it would duplicate authoritative
  data and create avoidable synchronization and provenance risks.
- Show only completed measurements. Rejected because it would erase safety-stopped and incomplete
  events and hide the distinction between observations and derived estimates.
- Show only the latest estimate per assessment. Rejected because superseded or expired estimates
  are still meaningful historical derivations and must remain inspectable.
- Infer modern completion attestations for older performances. Rejected because the absence of an
  explicit historical fact must remain visible as uncertainty.

## Evidence

No scientific or training claim is introduced. This is an athlete-history, provenance, and user-
interface decision. Integration tests verify reverse-chronological multi-run projection and the
separation of safety-stopped attempts, completed direct measurements, and derived estimates.
Browser coverage verifies that the phone UI exposes a persisted safety stop in the longitudinal
view without creating a result.

## Uncertainty

The owner-alpha projection currently returns the complete assessment history without pagination.
That is intentionally small and sufficient for the present single-owner scope, but a larger
multi-athlete deployment would need a stable cursor without dropping or reordering immutable
records. Environment display names are resolved from the persisted environment record; all exact
historical identity and selection-context IDs remain exposed even if presentation labels evolve.

The `valid_as_of` estimate flag is a view-time interpretation of the stored estimate and validity
interval. It does not mutate the estimate or claim that a current planning decision still uses it.

## Consequences

- Older attempts remain visible after a new selection run begins.
- Completed measurements are labeled direct observations and estimates are labeled derived.
- Every assessment-derived estimate for a performance remains inspectable rather than only the
  newest policy interpretation.
- Missing historical attestations remain explicit instead of being silently backfilled.
- The latest-run controls and all readiness, safety, evidence, and owner-review gates are unchanged.
- No migration or new mutable state is required.

## Version/date

- Decision version: `longitudinal-assessment-history-projection@1.0.0`
- Date: 2026-09-25
