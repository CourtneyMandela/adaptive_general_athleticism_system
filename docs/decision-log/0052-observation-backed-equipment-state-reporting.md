# Decision 0052: Observation-backed equipment state reporting

- Date: 2026-08-28
- Decision version: `equipment-state-reporting@1.0.0`
- Status: accepted

## Decision

Add an athlete-owned boundary for inspecting and changing equipment state inside an existing
environment. A change request is an explicit, partial set of equipment events. Every listed item
must say whether it is available, when that state becomes effective, and optionally when a
temporary state ends. Unlisted equipment retains its existing or unknown state.

The service first appends one direct user-report `Observation` containing the exact requested
changes, reliability, report time, provenance, and reason. It then appends effective-dated
`EquipmentAvailability` events linked directly to that observation. The observation and every
event commit or roll back together.

Add an optional `source_observation_id` to equipment-availability persistence. Existing historical
records may retain null provenance after migration, but athlete-authored application services must
always set it. Repository validation requires the source observation and environment to belong to
the same athlete.

An owned read projection uses the established `EnvironmentSnapshotBuilder` temporal rule to show
each environment and every catalog equipment item's effective state at a requested instant:
`available`, `unavailable`, or `unknown`. It exposes the controlling availability event and source
observation identifiers. Missing history remains unknown rather than being interpreted as a
negative report.

The PWA may use these owned environments when confirming next week's availability. Recording an
equipment change does not mutate an existing prescription, claim equivalence, or automatically
rewrite an immutable weekly plan. Exercise re-resolution remains a separate governed planning
boundary.

## Reason

The blueprint requires equipment to be a changing environmental constraint, supports temporary
unavailability and load limits, and requires travel to change training means without changing
developmental goals. The existing temporal domain model and resolver already support this, but
athletes could only create initial availability during onboarding and later events had no direct
observation foreign key.

This slice closes the reporting and provenance gap without pretending that any available exercise
is an equivalent substitute.

## Alternatives considered

- Replace one mutable equipment inventory document. Rejected because it destroys effective-dated
  history and temporary-state semantics.
- Treat every omitted catalog item as unavailable. Rejected because omission is not a report and
  would turn unknown into false certainty.
- Store observation identity only in free-text `reason`. Rejected because provenance should be
  relationally verifiable.
- Immediately rewrite sessions after any equipment report. Rejected because existing plans are
  immutable and substitution requires the original stimulus, reviewed candidates, policy, and an
  honest FULL/PARTIAL/INFEASIBLE result.
- Let the athlete describe arbitrary equipment names. Rejected because resolution depends on the
  controlled catalog ontology.

## Evidence

This is a product workflow and provenance decision implementing blueprint sections 8, 10–13, 56,
65, 72, 77–78, and 83. It adds no exercise-equivalence claim, training dose, or scientific rule.

## Assumptions

- A partial change set is safer than complete-snapshot replacement for V1.
- Multiple active temporal records are resolved by the existing latest-effective-event rule.
- A temporary event may reveal an older still-active state after its `effective_until`.
- Catalog equipment capabilities remain ontology defaults; an event may add environment-specific
  capabilities and load limits without modifying the catalog record.

## Unresolved questions

- Athlete creation of additional environments after onboarding.
- A governed in-block prescription re-resolution and template-revision workflow.
- Typed validation and comparison of equipment capability/load-limit schemas.
- Correction or voiding of an incorrectly reported availability event.
- Production notification and review behavior when an active plan becomes infeasible.

## Consequences

- Equipment changes become direct observations with verifiable temporal lineage.
- Availability history remains append-only and can represent planned travel or temporary outages.
- Unknown equipment state is displayed honestly.
- Weekly availability can switch among existing athlete-owned environments.
- Exercise changes still require an explicit resolver decision and cannot silently alter the goal.
