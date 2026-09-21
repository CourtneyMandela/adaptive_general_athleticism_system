# 0126 - Introductory exposure uses a distinct governed dose authority

Date: 2026-09-20

Status: accepted

Decision version: `introductory-exposure-dose-authority@1.0.0`

## Decision

Add `IntroductoryExposureDosePolicy` and `IntroductoryExposureDose` as separate immutable domain
records. The policy governs a fixed starting dose for one exposure type and target scope. The
derived dose must cite one active unmet `ExposureNeed`, the exact policy, its source observations,
its evidence identifiers, its numeric-value origin, and its authority reference.

The deterministic planner permits derivation only when the need is current and has status
`introductory_exposure_needed`. A confirmed, unknown, future, stale, or scope-mismatched need fails
closed. It does not use a capability estimate or infer contacts from jump height.

The policy explicitly separates `numeric_value_origin` from optional supporting evidence. Exact
values may be identified as engineering judgment, professional judgment, or scientific evidence.
A scientific numeric origin is invalid without an evidence claim. Engineering- or
professional-judgment values remain labeled honestly even when broader evidence supports the
direction of training.

## Reason

The existing `RepetitionDosePolicy` calculates a submaximal repetition dose from a measured maximum
for the same task. That is suitable for chair stands and standard push-ups but not for introductory
jump exposure. Jump height does not determine a safe number of contacts, and a user who lacks
recent exposure may not yet have an authorized maximal jump result at all.

A separate fixed-dose authority preserves the actual chain: reported exposure history, derived
exposure need, governed adaptation and starting-dose policy, then a derived dose. It prevents an
engineering starting value from being disguised as a scientific threshold or capability score.

## Alternatives considered

- **Reuse `RepetitionDosePolicy`.** Rejected because multiplying jump height by a fraction to obtain
  repetitions is dimensionally and scientifically invalid.
- **Hard-code a few jumps in the session generator.** Rejected because the numeric authority,
  provenance, uncertainty, and replacement history would be hidden.
- **Treat the readiness answer as a capability estimate.** Rejected because an exposure-history
  answer is not athletic performance.
- **Require every number to be paper-derived.** Rejected because available studies support the
  trainability and reporting dimensions of plyometric exercise but do not establish one universal
  safe introductory dose for this athlete.
- **Create a workout in the same change.** Rejected because a ratified policy, adaptation strategy,
  stimulus, exercise resolution, scheduling, and current session safety still need their own
  governed links.

## Evidence

This change establishes an authority and provenance mechanism; it does not select an operational
dose. Decision 0124 records the reviewed plyometric literature and its limitations. A later
candidate may cite that evidence for the direction and variables of exposure while marking its
exact sets, contacts, rest, effort, and progression values as engineering judgment unless a source
actually supports them.

## Assumptions and uncertainty

- Fixed starting doses are appropriate only for narrowly scoped introductory exposure policies.
- The initial policy schema supports repetitions or seconds. Other exposure units require a new
  version rather than an untyped string.
- A derived dose is a prescription input, not permission to perform it.
- No operational jump-dose policy or exercise is ratified by this decision.

## Consequences

- Future introductory jump, running, landing, or change-of-direction paths need not invent a
  capability floor.
- Exact numeric origins remain visible through persistence and serialization.
- Derived dose history is append-only and cannot silently lose its source readiness observation.
- The next task is a reviewed introductory jump-and-landing policy/resource candidate and its
  integration into strategy, exercise resolution, scheduling, and session safety.

