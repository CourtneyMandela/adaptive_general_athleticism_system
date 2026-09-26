# 0149 — Append-only incomplete assessment attempts

## Decision

Persist an incomplete assessment as a dedicated immutable `AssessmentAttempt` plus a direct
user-report observation. An attempt may have only one of two explicit states:

- `incomplete`: the reviewed protocol was not completed and no listed stop condition occurred;
- `safety_stopped`: the reviewed protocol was not completed because a listed stop condition
  occurred.

Every attempt retains the athlete, selection run, selected assessment, exact definition review,
exact eligibility review, observation, attempt time, reliability, provenance, and versioned
recording rule. Its observation explicitly records `protocol_completed=false` and
`eligible_for_capability_estimation=false`. It contains no result measurement.

An ordinary incomplete attempt leaves the selected protocol retryable. A safety-stopped attempt
closes that selection to both further attempts and completed results. The athlete must submit a new
current readiness report and start a new governed selection run before another attempt. The browser
shows the immutable attempt history and that boundary directly.

## Reason

Decision 0148 prevented an incomplete or stopped assessment from being submitted as a completed
result, but discarding the event lost material safety and provenance. Reusing
`AssessmentPerformance` or a test-result observation would make the record eligible for result
interpretation. A separate lineage object preserves what happened without manufacturing a score or
weakening the completed-result invariant.

A listed stop condition is also evidence that the readiness state used to authorize the selection
may no longer be sufficient. Allowing the same selection to accept a later result would treat the
stop as advisory text instead of a deterministic safety boundary.

## Alternatives considered

- Store zero or a partial measurement. Rejected because either could be misread as completed
  performance and create a false capability deficit.
- Add a status to `AssessmentPerformance`. Rejected because performances are the exclusive input
  to governed capability estimation and represent completed protocols.
- Store only an unlinked generic observation. Rejected because the exact run, selection, protocol,
  and eligibility authority would not be relationally enforceable.
- Accept free-text symptom or medical explanations. Rejected because this product is not a
  diagnostic record and the current slice needs only the factual stop boundary.
- Let a safety-stopped selection remain retryable while its eligibility review is active. Rejected
  because the stop is a material change that must fail closed to fresh readiness evaluation.
- Allow only one incomplete attempt. Rejected for non-safety incompletion because append-only retry
  history is more truthful than overwriting or prematurely abandoning the selected protocol.

## Evidence

No scientific claim, diagnostic interpretation, or assessment threshold is introduced. This is a
data-lineage and deterministic-safety decision. Integration tests verify append-only persistence,
immutable records, exact authority lineage, ownership isolation, multiple non-result attempts,
non-safety retry followed by valid completion, safety-stop closure, migration parity, and rejection
when an attempt ID is supplied to the capability-estimation endpoint. Browser tests verify the
phone interaction and visible non-estimable history.

## Uncertainty

The binary states intentionally do not explain why a non-safety attempt was incomplete or which
listed condition caused a safety stop. They are athlete reports, not independent verification or a
medical conclusion. A future controlled vocabulary could add useful non-diagnostic context, but it
must not turn partial measurements into result evidence or invite diagnosis.

## Consequences

- Incomplete and safety-stopped events are no longer discarded or encoded as zero results.
- Attempt observations are categorically separate from test-result observations and
  `AssessmentPerformance`.
- Capability estimation continues to require an actual completed-performance identifier.
- Non-safety incompletion can be retried and remains visible in the latest run.
- A safety stop requires fresh readiness and a new selection run; the closed selection cannot be
  reopened by the client.
- Migration `5a6b7c8d9e0f` adds the immutable `assessment_attempts` table without changing historical
  performance rows.

## Version/date

- Decision version: `append-only-incomplete-assessment-attempts@1.0.0`
- Date: 2026-09-25
