# 0130 — Dedicated introductory-exposure execution

Status: accepted

Date: 2026-09-21

## Decision

Record assessment-preparation jump exposures through a dedicated immutable
`IntroductoryExposureExecution` instead of manufacturing a capability-deficit block, weekly plan,
prescription, or ordinary session execution.

The athlete-facing workflow may derive the exact ratified introductory dose, display it, start it,
and append one execution observation. A day counts toward the recent-exposure prerequisite only
when the athlete reports all of the following:

- current pre-session readiness;
- the complete governed set and contact dose;
- controlled, separately reset landings;
- no stop condition; and
- session RPE at or below the governed cap.

Only one introductory exposure may be recorded per calendar day. The existing two-distinct-day,
28-day prerequisite remains controlling. Each qualifying completion appends a new versioned
`ExposureNeed`; it never overwrites the self-report or an earlier derived state.

## Why

This work prepares an athlete for an exposure-dependent assessment. It is not evidence that the
athlete has a capability deficit and therefore must not enter the deficit-only training-block path.
At the same time, a preview without a performance and provenance path is not usable. A dedicated
execution record closes that gap while retaining the distinction between observation, governed
dose, performed work, and derived prerequisite state.

## Safety and provenance boundaries

- A current allowed readiness review and jump-specific movement answers are required.
- The selected environment must belong to the athlete and currently confirm required equipment
  and floor space.
- Pain, dizziness, instability, an uncontrolled landing, unusual symptoms, or inability to keep
  the effort easy are stop conditions.
- Partial and safety-stopped attempts are preserved but do not count.
- Athlete-entered completion does not establish tissue capacity, medical clearance, or proof that
  maximal jumping is risk-free.
- The execution, direct observation, derived dose, and each exposure-need version are append-only.

## Alternatives considered

### Force the exposure through the ordinary block and weekly-plan models

Rejected. Those models require a governed capability-deficit strategy, resource allocation, and
exercise resolution. Creating those artifacts for assessment preparation would misstate why the
work exists.

### Treat the existing self-report as updated after one session

Rejected. The configured prerequisite requires two distinct days. A single completion cannot
silently become a positive 28-day self-report, and historical answers must remain unchanged.

### Store only a generic observation

Rejected. An observation preserves what was reported but does not enforce dose lineage,
environment identity, exact qualification rules, or one-session-per-day scheduling.

## Provisional choices

- Distinct days currently use the stored timezone-aware execution date. A future calendar service
  may make athlete-local day boundaries explicit.
- The workflow starts and completes the short exposure on the assessment screen rather than
  creating a separate calendar appointment. The immutable start and end times still preserve the
  performed-session boundary.
- Exact dose and RPE constants remain the ratified engineering priors documented by decisions 0127
  through 0129; this decision does not upgrade them to scientific findings.
