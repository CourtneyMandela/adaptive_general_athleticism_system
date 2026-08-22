# Decision 0027: Governed profile and environment onboarding

- Status: accepted provisionally
- Date: 2026-08-22
- Decision version: `profile-environment-onboarding@1.0.0`

## Decision

Add one transactional onboarding boundary that creates an athlete, one direct user-report
observation, one or more athlete-owned environments, and the corresponding equipment-availability
events. The command accepts structured profile preferences, goals, environmental constraints, and
equipment selections. Equipment must already exist in the validated global catalog; onboarding
does not create arbitrary ontology records.

The direct observation preserves the exact submitted goals, preferences, environment constraints,
equipment identities, report reliability, timestamp, and provenance. Athlete preferences are a
small operational projection of that report, not a capability estimate. Environment and equipment
records remain separate from athlete identity and can change later through append-only events.

Expose a narrow read projection for available persisted equipment so the PWA can present named
choices instead of accepting raw equipment UUIDs. Add a responsive create-profile path alongside
the existing connect-existing path. A successful browser submission retains the opaque athlete ID
in the current application session and opens the authoritative current-week projection; it does not
invent a plan when no plan exists.

This slice intentionally does not collect date of birth, health screening, injury history, current
symptoms, or assessment results. Authentication, authorization, data-deletion obligations, and
appropriate protection for sensitive intake data must be decided before those fields become an
ordinary browser workflow. Safety-policy assignment also remains governed setup rather than a
user-selectable onboarding preference.

## Reason

The PWA currently requires users to locate an athlete UUID before they can enter the daily flow.
Creating the basic profile and real equipment environments is the smallest useful step toward the
blueprint's onboarding milestone while preserving the observation-to-state boundary. It also avoids
turning the global equipment ontology into per-user free text.

## Alternatives considered

- Collect the complete blueprint intake immediately. Rejected because the current API has no
  identity or authorization boundary for sensitive health and injury information.
- Store the whole onboarding form only on `Athlete`. Rejected because user-reported inputs must
  retain timestamp, reliability, source, and provenance as an observation.
- Let the browser create arbitrary equipment records. Rejected because catalog semantics and
  exercise-resolution references require controlled, reviewed identities.
- Automatically create a strategy, block, or workout. Rejected because onboarding alone contains
  no governed capability estimates, evidence-linked planning inputs, dose, or safety assignment.
- Let the user choose any safety policy. Rejected because policy applicability is not a preference
  and no reviewed assignment workflow exists yet.

## Assumptions and provisional choices

- Goals and activity preferences are non-clinical profile inputs suitable for the current
  unverified-user development boundary.
- At least one environment is required, but an environment may intentionally contain no catalog
  equipment.
- Optional floor area, noise constraint, outdoor access, equipment capabilities, and load limits
  preserve the existing environment ontology without claiming equivalence.
- Retaining an opaque athlete ID in browser state is convenience, not authentication or proof of
  ownership.
- The onboarding observation type and client rule version are explicit and versioned so later
  authenticated onboarding can supersede this boundary without rewriting history.

## Evidence and uncertainty

This is a product architecture and provenance decision implementing blueprint sections 8--12, 29,
55, 61, 77, and 78. It adds no medical rule, capability estimate, scientific claim, training
threshold, exercise equivalence, or workout logic.

Authentication provider choice, account-to-athlete ownership, deletion/export obligations,
time-zone ownership, reviewed safety-policy assignment, sensitive intake, adaptive assessment
orchestration, and first-plan generation remain unresolved.

## Consequences

- A test user can create a persisted athlete and honest equipment environments without handling
  raw equipment identifiers.
- Onboarding state is traceable to the direct report that created it.
- The API remains unsuitable for sensitive or production user data until identity and authorization
  are implemented.
- A newly created athlete correctly lands on an empty current-week state; later milestones must
  add safety assignment, assessment, and first-plan orchestration rather than filling the gap with a
  generic workout.
