# 0066: Structured first-week authoring workflow

- Status: accepted provisionally
- Date: 2026-08-29
- Extends: Decision 0065
- Decision version: `structured-first-week-authoring@1.0.0`

## Decision

Extend `/review/weeks` from preparation inspection to a complete field-by-field authoring workflow
over the authenticated atomic Week 1 boundary. Create one blank prescription editor for every
active block allocation, while leaving all scientific and scheduling values unset. Support all
existing discriminated intensity targets, explicit repetitions-or-duration dose, rest, progression
reference, substitution class, duration, fatigue cost, observation/evidence lineage, and rule
version.

Let the reviewer add zero or more session templates and availability windows. Session membership,
order, section, frequency, duration, fatigue, provenance, environment, and timestamps are explicit.
Scheduling policies remain unselected and only an exact current approved review is selectable.
Reviewer identity and preparation timestamp remain server-owned or mechanically recorded rather
than editable planning judgments.

Client validation mirrors the domain shape for usability, but is not authoritative. The backend
continues to reload role authority, block lineage, resolutions, scheduling policy review, and all
referenced records before the atomic transaction.

## Reason

The governed API could create a real first week, but reviewers still needed external JSON. A
structured form makes the vertical slice operable without introducing a workout generator or
narrowing the domain to one generic session and intensity style.

## Alternatives considered

- Prefill common sets, repetitions, intensity, or rest. Rejected because convenience defaults would
  become unreviewed training rules.
- Automatically create one template containing every allocation. Rejected because session grouping
  affects fatigue, scheduling, and interference.
- Restrict the form to one intensity target. Rejected because the domain explicitly supports
  combined load, effort, pace, heart-rate, and technique constraints.
- Hide provenance behind one block-level selection. Rejected because prescriptions, templates, and
  availability have distinct source requirements.
- Treat browser validation as authority. Rejected because clients are untrusted and can be bypassed.

## Evidence

This is a workflow and provenance decision implementing blueprint sections 33–36, 52, 60, 64, 73,
77, and 89. It creates no scientific claim, dose rule, progression rule, or scheduling policy.

## Assumptions and uncertainty

- A reviewer may intentionally submit no availability windows, producing an inspectable infeasible
  result rather than a fabricated schedule.
- Browser `datetime-local` values are interpreted in the reviewer's current timezone and converted
  to explicit UTC timestamps before submission.
- Progression references and substitution classes remain reviewed versioned text references; richer
  governed catalogs are unresolved.
- Author/approver separation and qualified-reviewer credentials remain unresolved.

## Consequences

- A reviewer can now create a real deterministic Week 1 entirely through the PWA.
- No material prescription or grouping field is silently inferred.
- Invalid dose shape, duplicate intensity kinds, missing provenance, non-contiguous ordering, and
  malformed availability fail in the browser and again at the backend.
- The next milestone is an automated full vertical-slice demonstration fixture through execution,
  progression, reassessment, block review, and response-dependent replanning.
