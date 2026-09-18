# 0122 - Athlete-specific first-plan handoff

Date: 2026-09-18

Status: accepted

Decision version: `athlete-specific-first-plan-handoff@1.0.0`

## Decision

After an athlete has a current capability estimate and no persisted first week, the phone-facing
first-session path may read the existing role-protected planning-review queue and select only the
item whose `athlete_id` matches the current owned profile. A ready item links directly to its exact
review surface: initial strategy, resource demand, first block, or Week 1 scheduling. A blocked
item remains labeled as AGAS work and includes its first projected prerequisite issue.

Failure or denial of this optional reviewer read does not break the athlete dashboard. The path
falls back to the planning queue with a validated athlete UUID, and that queue filters its visible
items to the selected athlete. Week receipts use one validated navigation helper to preserve both
athlete identity and the persisted `week_start` when returning to the PWA.

## Reason

The governed vertical slice already contained every review boundary needed to create the first
push-up week, but the athlete dashboard sent the owner to a generic operator queue after planning
authorities were accepted. That required the owner to translate internal lifecycle stages and made
it easy to lose profile or week context. Navigation friction was obscuring completed domain work
without adding safety or provenance.

## Alternatives considered

- **Keep the generic reviewer queue as the only handoff.** Rejected because it exposes internal
  workflow selection to a single-athlete phone user and can display unrelated profiles.
- **Automatically ratify every downstream artifact.** Rejected because navigation convenience is
  not authority to accept an immutable strategy, dose, block, or weekly plan.
- **Derive the next route from planning-status labels in the browser.** Rejected because the
  backend queue already owns the lifecycle projection and supplies the authoritative identifiers.
- **Fail the dashboard when reviewer access is unavailable.** Rejected because operator
  convenience is optional and must not suppress athlete-owned status.

## Assumptions and unresolved questions

- The owner-alpha account continues to hold separately activated reviewer roles; an ordinary
  athlete without those roles receives the conservative fallback.
- Direct routing does not collapse the separate confirmations inside each review screen.
- Future multi-athlete reviewer workflows still use the unfiltered queue by omitting `athleteId`.
- A later usability batch may add a compact cross-screen progress header, but it must be derived
  from the same queue rather than duplicated browser state.

## Consequences

- The home screen gives one plain-language next action once planning is ready.
- Strategy, dose, block, and week identifiers come from the backend lifecycle projection.
- Blocked work remains visibly blocked instead of becoming a misleading approval action.
- Accepted and pre-existing Week 1 links reopen the exact calendar week and profile when known.
- Unit and browser tests cover all four direct routes, fallback context, blocked wording, and week
  link validation.
