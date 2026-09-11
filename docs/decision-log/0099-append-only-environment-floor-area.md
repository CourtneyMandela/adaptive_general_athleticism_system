# 0099 — Append-only environment floor-area reporting

Date: 2026-09-10

Status: accepted

Decision version: `environment-floor-area-report@1.0.0`

## Decision

Allow an athlete to append a strongly validated `environment_floor_area_report` observation for an
existing owned environment. The report records positive usable square metres, effective time,
report time, reliability, provenance, and reason. It never updates the immutable `Environment`
record created during onboarding.

The current environment projection resolves the latest effective report for each environment,
falling back to the onboarding value when no report is effective. It exposes the controlling
observation ID and effective time. Resource-demand preparation applies the same resolver and adds
the controlling report ID to the stimulus and demand observation provenance.

## Reason

The first prepared chair resource demand requires at least 2 m² of usable floor space. The owner's
existing Home profile omitted that optional onboarding field, and creating a second athlete or
silently editing the environment would both damage the record. A factual append-only observation
provides the missing phone workflow while preserving history.

## Alternatives considered

- **Update `Environment.space_constraints` in place.** Rejected because it erases the original
  reported state and breaks append-only history.
- **Create a new environment with the same name.** Rejected because it fragments equipment history
  and confuses identity.
- **Infer sufficient space from stable-chair availability.** Rejected because equipment possession
  does not prove usable clearance.
- **Add a new database table immediately.** Deferred because `Observation` is already the
  authoritative model for reported facts and the versioned typed command plus resolver creates a
  narrow, inspectable contract without a redundant source of truth.

## Assumptions and provisional choices

- Version 1 reports only positive known area; it cannot intentionally reset area to unknown.
- A report remains controlling until a newer effective report exists.
- The athlete reports usable clear area rather than total room area.
- Reliability is descriptive provenance and does not override the factual value automatically.

## Unresolved questions

- Should later versions support temporary floor-area constraints with an effective-until time?
- Should noise and outdoor-access corrections use the same typed-observation pattern?
- At what point would query volume justify a dedicated indexed projection table while keeping the
  observations authoritative?

## Consequences

- The current owner can unblock the prepared resource demand entirely from the phone.
- Original onboarding state and every correction remain inspectable.
- No database migration or mutable environment update is introduced.
- The next planning boundary is preparation of the first block.
