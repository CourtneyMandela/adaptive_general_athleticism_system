# Decision 0021: Current-week read projection

- Status: accepted
- Date: 2026-08-22

## Decision

Add `GET /v1/athletes/{athlete_id}/current-week?on=YYYY-MM-DD` and a matching responsive PWA screen.
The endpoint returns a purpose-built, read-only projection assembled from persisted domain history;
it does not expose raw ORM records and does not mutate athlete or planning state.

The projection includes the athlete display name, matching weekly plan, dated planned sessions,
session-container name, environment, exercise and adaptation labels, prescribed dose and intensity,
reason for inclusion, latest pre-session safety outcome, execution, adherence, post-session safety
outcomes, and progression result where those records exist. A compact display status is derived
deterministically from execution first and safety second.

The query requires an explicit date. No matching plan returns a successful empty-week projection.
More than one plan covering the date returns a conflict; V1 does not silently choose a current plan
without explicit supersession semantics.

## Reason

The backend can now complete the first feedback loop, but the PWA exposed none of it. A current-week
projection is the smallest useful read boundary for the blueprint's daily UX and establishes a
stable contract before adding safety and logging writes to the browser.

## Alternatives considered

- Expose raw domain models and let the browser join them. Rejected because it leaks persistence
  navigation, increases round trips, and encourages frontend business logic.
- Add generic CRUD/list endpoints. Rejected because they bypass use-case boundaries and make
  provenance relationships optional.
- Select the most recently generated plan when dates overlap. Rejected because generation time is
  not an approved plan-supersession rule.
- Build onboarding and workout logging in the same milestone. Deferred to keep the first browser
  contract narrow and avoid presenting unvalidated write workflows.

## Evidence and uncertainty

This decision adds presentation and data-access behavior, not a scientific training rule. It uses
only existing versioned prescriptions and decisions. The athlete-ID setup field is provisional and
not an authentication model. Production identity, authorization, time-zone ownership, offline
behavior, and plan supersession remain unresolved.

## Consequences

An existing athlete can now inspect a real persisted week in the PWA, including why each exercise
exists and what was actually completed. The next web milestone can add pre-session safety and
performance logging against stable plan/session/prescription identifiers. Until onboarding exists,
the user must enter an athlete ID or prefill it through local environment configuration.
