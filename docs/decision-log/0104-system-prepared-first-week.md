# 0104 — System-prepared first week

Date: 2026-09-11

Status: accepted

Decision version: `prepared-first-week@1.0.0`

## Decision

Add a content-addressed owner-alpha Week 1 preparation boundary. The owner supplies only factual
availability windows. The server follows the block's sole active allocation through its strategy
priority and capability need to the exact source capability estimate, derives the bounded
repetition dose with the ratified `RepetitionDosePolicy`, uses the FULL exercise resolution, builds
one low-fatigue session template, and schedules its two occurrences under the exact approved
weekly-scheduling policy.

Preview persists nothing. It returns either explicit blockers or the exact exercise, sets,
repetitions, effort range, rest, technique constraints, and scheduled times. Ratification requires
the candidate version, digest, preparation time, unchanged availability, and attestation. It then
atomically appends the availability as a direct user-report observation, prescription, template,
weekly availability, weekly plan, and audit decision under deterministic identities. A matching
retry returns the verified existing result.

## Reason

The prior general Week 1 editor exposed every technical field because no real dose authority
existed. Those blanks were correct at that stage but made the owner responsible for authoring a
workout. Ratified construction authorities now permit AGAS to do that engineering work honestly.
Availability remains a user fact; training values do not become user preferences.

Deterministic identities make mobile retries safe and keep preview identical to the persisted
result. Recording availability as an observation preserves the distinction between what the owner
reported and what the planner derived.

## Alternatives considered

- **Prefill the general editor.** Rejected because editable defaults obscure authority and allow
  the owner to accidentally change a governed value.
- **Store availability when previewing.** Rejected because preview must remain read-only and the
  owner has not yet accepted the resulting week.
- **Schedule arbitrary times to make the app look complete.** Rejected because calendar
  availability is factual athlete state, not a planning inference.
- **Create safety clearance with the weekly plan.** Rejected. Readiness is time-sensitive and must
  be reported immediately before each session.
- **Generalize to every adaptation and dose type now.** Deferred. Only the exact governed
  chair-stand path is supported; future adaptations require their own evidence and rule artifacts.

## Assumptions and provisional choices

- The current owner-alpha block has exactly one active allocation and one FULL exercise
  resolution.
- At least two non-overlapping windows in that resolved environment are needed for the two planned
  sessions. Extra offered windows may exist; the deterministic scheduler chooses applicable ones.
- The source estimate referenced by the strategy's capability need must still be current at
  preparation time.
- Availability-report reliability is `unknown`: the system preserves the owner's report without
  claiming independent verification.
- Candidates expire after 30 minutes unless already accepted, limiting the chance that a stale
  browser screen is used as current planning authority.

## Consequences

- The owner can reach a scheduled Week 1 without entering sets, reps, RPE, rest, policy UUIDs,
  provenance IDs, or rule versions.
- Every displayed session is tied to an offered window and the resolved training environment.
- A double tap or network retry does not duplicate a plan.
- The general editor remains collapsed as an advanced recovery path.
- A scheduled session still cannot be performed until its athlete-facing pre-session safety gate
  returns an allowed outcome and any required modifications are acknowledged.
