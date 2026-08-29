# Decision 0051: Provenance-first athletic dashboard

- Date: 2026-08-28
- Decision version: `athletic-dashboard-projection@1.0.0`
- Status: accepted

## Decision

Add an athlete-owned, read-only dashboard projection over persisted capability estimates. The
projection returns every capability domain, but it does not manufacture a normalized score or
select one number as authoritative domain state.

Within each domain, estimates are separated into measurement series by exact
`(estimate_scope, unit_or_scale)`. The latest estimate at or before the requested instant is shown
for each series with:

- its explicit `kind=derived` classification;
- value and unit/scale;
- confidence;
- current/stale validity state;
- calculation method and rule version;
- source-observation identifiers;
- estimation and validity timestamps; and
- the number of historical estimates retained in that series.

Future-dated estimates are excluded. A domain reports `not_estimated`, `current`, `stale`, or
`mixed` from its visible series, and retains a total visible history count. The PWA presents these
facts as measurement cards rather than precision bars.

## Reason

Blueprint section 59 requires a confidence-bearing athletic dashboard, while sections 8–10 and 83
forbid treating estimates as ground truth or unsupported numbers as athlete state. Current records
can use protocol-specific scopes, incompatible units, and different methods. A generic percentage
bar would imply a shared scale and normative interpretation that the repository does not possess.

This projection makes useful progress toward the PWA without weakening the observation-to-estimate
boundary or inventing scientific normalization.

## Alternatives considered

- Convert every estimate to a 0–100 score. Rejected because no reviewed conversion or population
  norm exists.
- Select the newest estimate in each domain regardless of scope. Rejected because a newer
  protocol-specific result may not supersede a different measurement series.
- Show only assessment-workflow results. Rejected because later governed estimates and imported
  estimates also belong in athlete history.
- Hide unmeasured domains. Rejected because absence is important state and must not look like a
  complete profile.

## Evidence

This is a read-model and provenance decision implementing blueprint sections 8–10, 59, 64, 69,
74, 77–78, and 83. It introduces no scientific claim, competency threshold, norm, or training rule.

## Assumptions

- Exact scope and unit equality identifies a measurement series provisionally.
- An estimate without `valid_until` is not automatically stale; its uncertainty remains visible
  through confidence, method, and rule provenance.
- `valid_until <= as_of` is stale at the requested instant.

## Unresolved questions

- Reviewed cross-protocol comparability and conversion policies.
- Population-relative visualization where verified normative evidence exists.
- User-facing correction/voiding for erroneous source observations.
- Whether future versions should distinguish expired validity from method supersession.

## Consequences

- Users can inspect capability coverage and confidence without false precision.
- Multiple incompatible estimates remain visible instead of being silently collapsed.
- Historical estimates remain append-only and summarized rather than overwritten.
- Dashboard state can update after reassessment without coupling it to workout generation.
