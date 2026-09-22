# 0131 — Versioned session-execution guidance

Status: accepted

Date: 2026-09-22

## Decision

Attach optional, structured `ExerciseExecutionGuidance` to each immutable
`SessionPrescription`. A complete guidance snapshot contains:

- a semantic version;
- setup instructions;
- ordered execution instructions;
- technique cues;
- explicit stop conditions;
- the authority used to prepare it; and
- uncertainty and scope limits.

The first reviewed entry covers the owner-alpha standard push-up. It reuses the exact setup and
movement standard from the approved push-up assessment protocol and the ratified training
construction authority. The athlete PWA renders the stored snapshot under **How to perform this**.
Because guidance now participates in the reviewed first-week payload and content digest, that
candidate advances to `prepared-first-week@1.2.0` and its prescription rule to version `1.1.0`.

## Why

A dose and exercise name do not make a workout safely or practically executable for a person using
a phone. At the same time, generating instructions from an exercise name would create unreviewed
content and could silently change historical sessions. Snapshotting the guidance on the
prescription makes the instructions that the athlete saw inspectable and stable.

This guidance explains execution. It does not choose the exercise, authorize the dose, provide
medical clearance, or claim that the movement is universally optimal. Those responsibilities
remain with the separate resolution, construction, evidence, and safety chains.

## Alternatives considered

### Store guidance only on the mutable exercise catalog

Rejected for session display. A later catalog edit could change instructions for a prescription
that was already created or completed. The catalog may eventually own reviewed guidance releases,
but each prescription still needs an immutable snapshot.

### Generate instructions at request time

Rejected. This would make an exercise name a hidden prompt, provide no stable version or authority,
and risk presenting plausible text as reviewed fact.

### Require guidance for every prescription immediately

Rejected for migration compatibility and honesty. Existing historical prescriptions do not have
reviewed guidance, and the current exercise catalog is intentionally sparse. The UI states that
guidance is unavailable instead of inventing it. Future authoring gates may require guidance before
an exercise can enter an athlete-facing plan.

## Provenance and revision behavior

- Ordinary first-week construction copies the reviewed guidance into the prescription.
- Progression revisions retain the exact snapshot because the exercise and technique standard do
  not change.
- Environment-driven substitutions resolve guidance for the replacement exercise; they never copy
  the predecessor's instructions.
- Missing registry content remains `null` and visible.
- Updating guidance requires a new version and affects only newly created prescriptions.

## Provisional choices

- Guidance is a versioned in-code reviewed registry for the single executable owner-alpha exercise.
  If coverage expands, content should move to validated reviewed data files without changing the
  prescription snapshot contract.
- Text and simple ordered steps are sufficient for the first usable alpha. Media, accessibility
  variants, and localization are deferred until their provenance and lifecycle are designed.
