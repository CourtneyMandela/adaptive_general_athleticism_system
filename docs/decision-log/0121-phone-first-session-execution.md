# 0121 - Phone-first session execution

Date: 2026-09-17

Status: accepted

Decision version: `phone-first-session-execution@1.0.0`

## Decision

Replace the athlete-facing aggregate after-the-fact workout form with a live, set-by-set execution
flow for the exact persisted planned session. A user first completes the existing pre-session
safety check, explicitly starts the workout, marks each prescribed set after it is performed,
records that set's actual repetitions or duration, optional effort and technique result, reviews
session timestamps and effort, and explicitly saves the final record.

An unfinished workout is stored as a versioned browser-local draft keyed to the planned-session
ID. Resume requires the same pre-session safety-decision ID and the same ordered prescription/set
signature. The draft is not sent to the API and is deleted only after the authoritative execution
write succeeds. Final submission retains one performance record per prescribed set and continues
through the existing atomic workout-observation, immutable execution, and derived-adherence path.

## Reason

The backend already supported trustworthy execution history, but the PWA asked the athlete to
reconstruct a workout afterward and copied one dose and effort value across every completed set.
That was technically functional but poor training software and discarded real within-session
variation. A phone workout can be interrupted or reloaded, so an unsaved local draft materially
improves usability without weakening the authoritative record boundary.

## Alternatives considered

- **Keep aggregate post-workout entry.** Rejected because it is easy to forget, cannot represent
  different set results, and is not a practical screen to train from.
- **Write every checked set immediately to PostgreSQL.** Rejected for this milestone because it
  would create partial authoritative executions and require new abandonment, revision, and
  concurrency semantics.
- **Use browser storage as execution history.** Rejected. It is explicitly temporary,
  device-specific, and non-authoritative.
- **Add a generic workout player independent of the scheduled prescription.** Rejected because it
  could silently diverge from the governed exercise, dose, safety, and provenance chain.

## Assumptions and unresolved questions

- V1 stores an unfinished draft only on the current device; it does not synchronize live progress
  across devices.
- V1 does not provide audio cues, a rest countdown, wake-lock management, or offline API write
  queuing. Those are usability improvements, not permission to alter prescribed work.
- A changed safety decision or prescription signature intentionally prevents silent draft resume.
- The current backend still owns validation and may reject a locally drafted result that no longer
  satisfies authoritative invariants.

## Consequences

- Different repetitions, duration, effort, and technique outcomes are preserved per set.
- A page reload can resume the same authorized workout without claiming it was completed.
- A not-started session remains an explicit final record with no fabricated timestamps or effort.
- Browser smoke coverage exercises the complete safety-check, live logging, reload/resume, review,
  and exact execution-submission path.
