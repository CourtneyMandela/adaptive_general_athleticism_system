# 0151 — Controlled assessment-attempt reasons

## Decision

Require every new incomplete or safety-stopped `AssessmentAttempt` to carry one controlled,
non-diagnostic reason. The accepted reasons are:

- `setup_or_equipment_issue`;
- `measurement_or_route_issue`;
- `instructions_unclear`;
- `external_interruption`;
- `voluntary_non_safety_stop`;
- `other_non_safety_reason`;
- `listed_stop_condition`.

`listed_stop_condition` is required exactly when the attempt status is `safety_stopped` and is
forbidden for an ordinary `incomplete` attempt. The other six reasons are allowed only for
`incomplete`. The API and domain model enforce that relationship; the browser cannot choose an
inconsistent pair.

The reason does not contain a partial result, free text, symptom narrative, diagnosis, or an
interpretation of why a stop occurred. It is projected with the immutable attempt in both the
current run and longitudinal history, but remains ineligible for capability estimation.

Migration `6b7c8d9e0f1a` preserves existing rows without inventing historical detail. Existing
safety-stopped rows receive `listed_stop_condition`; existing incomplete rows receive the internal
compatibility value `legacy_unspecified`. New commands cannot submit `legacy_unspecified`.

## Reason

The binary attempt status introduced by decision 0149 preserves the result-versus-non-result
boundary, but it cannot distinguish an equipment problem from unclear instructions, a route or
measurement problem, an external interruption, or a voluntary non-safety stop. That distinction
can improve protocol usability and future workflow review without collecting medical detail or
manufacturing a measurement.

A controlled vocabulary keeps the new context inspectable and testable. Coupling the safety status
to one deliberately broad listed-stop reason preserves the existing conservative boundary while
avoiding symptom classification or diagnostic inference.

## Alternatives considered

- Accept free-text explanations. Rejected because they could collect sensitive symptom narratives,
  invite diagnostic interpretation, and make downstream behavior difficult to govern.
- Record the exact listed symptom or stop condition. Rejected because the current product does not
  need that detail to enforce fresh readiness and is not a medical record or triage system.
- Permit a partial measurement alongside the reason. Rejected because it could be misread as a
  completed test result or capability input.
- Infer reasons for historical incomplete rows. Rejected because the source record does not contain
  that fact.
- Leave every attempt reason unspecified. Rejected because known non-medical workflow failures can
  be represented safely and usefully without weakening the result boundary.

## Evidence

No scientific claim, diagnostic interpretation, assessment threshold, or training rule is
introduced. This is a provenance, usability, and deterministic-safety decision. Domain, API,
persistence, migration, and browser tests verify the controlled values, status/reason consistency,
legacy backfill, immutable projection, and exclusion from capability estimation.

## Uncertainty

The selected reason is a direct athlete report and is not independently verified. The broad
`listed_stop_condition` value intentionally does not identify which condition occurred or assess
severity or urgency. `other_non_safety_reason` deliberately retains less detail than free text.
Future expansion requires a new versioned vocabulary and a separate privacy and safety review.

## Consequences

- New incomplete attempts retain useful non-medical context without becoming results.
- Safety-stopped attempts retain the same fail-closed fresh-readiness requirement.
- The browser presents only compatible choices and explicitly warns against entering partial
  results or symptom narratives.
- Existing incomplete rows remain truthful as `legacy_unspecified` rather than receiving an
  invented reason.
- The recording rule advances to `assessment-attempt-recording@1.1.0`.
- Observation, attempt, performance, and derived-estimate records remain distinct.

## Version/date

- Decision version: `controlled-assessment-attempt-reasons@1.0.0`
- Date: 2026-09-26
