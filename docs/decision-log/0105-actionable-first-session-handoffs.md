# 0105 — Actionable first-session handoffs

Date: 2026-09-11

Status: accepted

Decision version: `first-session-handoffs@1.0.0`

## Decision

Make every currently actionable step in the athlete-facing first-session path a precise navigation
handoff. Missing assessment content links to the prepared assessment-governance review; factual
readiness, selection, result, and estimate actions stay anchored to the athlete's assessment panel;
missing planning authorities link to their prepared batch review; and subsequent strategy, demand,
block, or Week 1 work links to the derived planning queue.

After a Week 1 ratification, show a receipt action that opens the exact athlete and persisted week
date in the PWA. Accept an `asOf=YYYY-MM-DD` query on the home route only after strict calendar-date
validation; malformed or impossible dates fall back to the device's local current date. A scheduled
first session is marked as the athlete's next action—not as completed—and links to the session
cards where the separate safety check and performance log occur.

## Reason

The system already derived what was missing but left several status messages as dead ends. That
made the owner discover reviewer routes or navigate week-by-week after accepting a future plan.
Explicit handoffs make the governed path operable on a phone without turning navigation into hidden
approval or asking the owner to author technical values.

## Alternatives considered

- **Automatically ratify the next candidate.** Rejected because navigation is not approval and the
  exact candidate still requires visible digest-bound attestation.
- **Redirect immediately after Week 1 acceptance.** Rejected because the immutable receipt is useful
  confirmation and should remain inspectable before leaving the review surface.
- **Store the selected date as athlete state.** Rejected because it is view context, not a domain
  observation or planning input.

## Consequences

- A newly onboarded owner always has a concrete next route when a prepared review exists.
- Week 1 opens on its actual scheduled date even when that week is in the future.
- Deep links preserve athlete identity and view date but cannot mutate or bypass governance.
- The current vertical slice still requires explicit assessment actions and candidate ratifications.
