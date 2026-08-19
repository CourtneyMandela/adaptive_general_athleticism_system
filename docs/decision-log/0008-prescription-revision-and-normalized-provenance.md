# 0008: Prescription revision and normalized progression provenance

- Status: accepted provisionally
- Date: 2026-08-19
- Decision version: `prescription-revision@1.0.0`

## Decision

Progression/exposure evidence, observation, exposure-entry, and safety-decision references will use
ordered foreign-key association tables rather than JSON identifiers. JSON remains appropriate only
for the value-shaped adjustment object and rationale.

An approved `ProgressionDecision` may create a new immutable `SessionPrescription`. The new record
links both `supersedes_prescription_id` and `progression_decision_id`; the old prescription remains
unchanged. V1 application supports only integral repetitions, sets, and duration adjustments,
because those are typed prescription fields. Load, density, range, speed, complexity, and modality
decisions remain inspectable but require a richer typed prescription or reviewed manual revision.

## Reason

Important provenance requires referential integrity, and automatic application must not smuggle an
unsupported adjustment into intensity text or overwrite planning history.

## Alternatives considered

- Keep identifiers in JSON: rejected because dangling provenance could bypass the database.
- Update the original prescription: rejected because it destroys history.
- Encode load or speed changes in free text: rejected because it is not deterministic or typed.
- Generate a revision from `REPEAT`, `HOLD`, or `REVIEW_REQUIRED`: rejected because those outcomes
  do not authorize progression.

## Evidence and uncertainty

This is a software/provenance decision implementing the blueprint's versioning and deterministic
progression requirements. It introduces no training threshold. Multi-dimensional and load-based
prescriptions remain unresolved.

## Consequences

- Every major progression source has database-enforced identity.
- A prescription revision can be audited back to the completed session and decision.
- Unsupported dimensions fail explicitly until their typed contracts exist.
