# Decision 0032: Governed assessment-performance recording

- Status: accepted provisionally
- Date: 2026-08-27
- Decision version: `governed-assessment-performance@1.0.0`

## Decision

Record a performed assessment as both an immutable direct `Observation` and an immutable
`AssessmentPerformance` lineage record. The performance names the athlete, selection run,
selected decision, definition, exact protocol review, exact eligibility review, result observation,
performance time, and recording-rule version.

Expose one authenticated athlete endpoint beneath that complete lineage. The request contains only
the performed time, reported measurement, protocol unit, reliability, and provenance. Server-owned
context adds the run, selection, and authority identifiers. Free-form result context, screening,
symptom, injury, and health fields are not accepted.

Only a `SELECTED` decision may be performed. At recording time, the exact protocol review must
still be the current approved self-administered review, and the exact eligibility review must still
be current, allowed, and active at `performed_at`. The performance cannot predate selection or lie
in the future. The result unit must exactly match the definition. One initial result is allowed per
selection; a duplicate conflicts and the whole transaction, including its tentative observation,
rolls back.

This transaction does not create a capability estimate or interpret the measurement.

## Reason

The existing result recorder correctly separated observations from estimates, but a caller could
use it without proving that the assessment was selected through the governed workflow. The new
lineage record makes that authority inspectable and lets persistence enforce it independently of
the API service.

Requiring the current exact authorities is conservative. It prevents a user from performing a
protocol after its approval or athlete applicability was replaced or withdrawn. A previously
completed result remains historical even when authority changes later.

## Alternatives considered

- Store the result only as an observation. Rejected because the run, selected decision, and exact
  authorities would then be encoded only in JSON context rather than enforceable relational state.
- Create a capability estimate in the same request. Rejected because estimation requires its own
  evidence-reviewed policy, calculation method, confidence, validity, and source selection.
- Permit results for deferred decisions. Rejected because deferral means a named prerequisite was
  not satisfied.
- Accept arbitrary result context from the browser. Rejected because it would bypass the narrow
  non-medical contract and allow reserved lineage fields to become client-controlled.
- Continue honoring a superseded approval because it authorized the original selection. Rejected
  for self-administered performance; current withdrawal must fail closed.
- Silently overwrite or upsert a duplicate result. Rejected because historical athlete reports are
  append-only and correction semantics have not been reviewed.

## Assumptions and provisional choices

- A selection represents one assessment opportunity and therefore accepts one initial result.
- The definition's `unit_or_scale` is the machine-enforced result contract currently available.
  Structured measurement schemas and protocol-specific value constraints are future governance.
- A user-entered correction, explicit invalidation, multi-attempt protocol, incomplete attempt, or
  abandonment needs a separate append-only model; none is inferred here.
- `performed_at` is athlete-reported but may not be in the future according to the API clock.
- Reliability and provenance describe the report; they do not make it authoritative capability
  state.

## Evidence and uncertainty

This decision governs lineage, authorization, and transaction behavior. It approves no assessment
protocol, measurement range, reliability claim, norm, interpretation, or capability formula. The
repository still contains no operational assessment protocol.

## Consequences

- A guided client can eventually submit a selected protocol result without bypassing authority.
- Duplicate, deferred, mismatched, future, or no-longer-authorized results fail without partial
  history.
- Result history remains explicitly distinct from derived capability state.
- Correction, attempt-state, structured measurement schema, estimation, and PWA result UI remain
  future milestones.
