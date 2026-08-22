# Decision 0022: Daily safety and execution PWA

- Status: accepted
- Date: 2026-08-22

## Decision

Connect the current-week PWA to the existing transactional pre-session safety and session-execution
endpoints. After every successful write, reload the authoritative current-week projection instead
of predicting the resulting safety, adherence, or progression state in the browser.

The safety form collects only inputs the deterministic gate already understands: readiness,
unusual soreness, major sleep disruption, major schedule limitation, a note, and report
reliability. It sends no classified signals. A separate concerning-symptom control pauses ordinary
submission because the repository has no reviewed browser-facing signal taxonomy or classifier.

The execution form preserves the exact ordered persisted prescriptions. It pre-fills prescribed
sets and dose for explicit review, accepts actual sets, one actual dose per set for each exercise,
optional item/session RPE, actual timestamps, a note, and report reliability. The client expands
those entries into set-level performance records and carries every safety-required modification
unchanged. The backend remains authoritative for execution validity and derived adherence.

Until authentication, onboarding, and athlete-policy assignment exist, local setup requires an
explicit athlete ID and reviewed safety-policy ID. Optional environment variables only prefill
those values. Browser provenance is deliberately recorded as `unverified-athlete-user`.

## Reason

The read projection made a persisted week visible but did not complete a daily feedback-loop action.
These two writes create the smallest usable safety-before-performance vertical slice without adding
generic workout generation or duplicating domain decisions in React.

## Alternatives considered

- Add generic policy-list or raw CRUD endpoints. Rejected because policy applicability is not a
  generic selection problem and raw records would bypass use-case boundaries.
- Automatically choose the newest safety policy. Rejected because recency is not an approved
  athlete-policy assignment rule.
- Classify symptom text or checkbox input in the browser. Rejected because no reviewed taxonomy,
  medical threshold, or qualified signal-classification workflow exists.
- Record only a one-click “completed as prescribed” result. Rejected because it could silently
  assert work, dose, and effort that were not actually reported.
- Calculate adherence in the browser. Rejected because adherence is derived domain state already
  appended atomically by the backend.

## Assumptions and provisional choices

- A single dose-per-set entry per prescription is sufficient for the first low-friction UI. The
  backend model already supports per-set variation, which a later detailed editor can expose.
- Prescribed values may be pre-filled because the user must still submit the form and can change
  them; they are not stored as actual work before that explicit action.
- Report reliability defaults to `moderate` but remains visible and editable.
- Actual workout start must not predate the latest safety decision. The UI exposes that boundary and
  does not support retrospective workout logging through a newly created safety authorization.

## Unresolved questions and consequences

Production identity, authorization, athlete onboarding, athlete-to-policy assignment, policy
discovery, time-zone ownership, offline write queues, correction/supersession, per-set load entry,
and governed symptom classification remain unresolved. A completed execution is immutable in V1;
the PWA cannot edit it. Post-session safety closure and progression are not yet exposed, so the
full daily-to-progression workflow still requires API use after workout logging.
