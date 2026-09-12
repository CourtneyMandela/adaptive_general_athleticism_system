# 0110 — Athlete-aware governance handoffs

Date: 2026-09-12

Status: accepted

Decision version: `athlete-aware-governance-handoffs@1.0.0`

## Decision

Carry an optional, validated athlete identifier through the first-session path's assessment- and
planning-governance links. Reviewer pages use that context only for navigation: they explain why
the owner arrived, preserve it across adjacent reviewer routes, and provide a direct return to the
same athlete's next in-page step after an explicit ratification.

Malformed identifiers are never propagated. Athlete context does not alter candidate content,
authorization, ratification, safety screening, or API resource checks. The API remains responsible
for ownership and reviewer-role enforcement.

## Reason

The governed vertical slice correctly separated athlete actions from review authority, but the
browser handoff discarded the selected athlete. On a phone—especially with duplicate historical
profiles—that made a successful review end in a navigation dead end and forced the owner to recover
context manually. A review can remain explicit while still returning the user to the work it
unlocked.

## Alternatives considered

- **Automatically ratify and redirect.** Rejected because navigation cannot stand in for the exact
  visible, digest-bound attestation.
- **Store a globally selected athlete on the server.** Rejected because view context is not athlete
  state and would create ambiguous cross-device behavior.
- **Use an arbitrary `returnTo` URL.** Rejected because a free-form redirect adds avoidable open-
  redirect and trust-boundary complexity.

## Assumptions and provisional choices

- The UUID in the query string is a navigation hint, not authorization or provenance.
- Returning to the athlete PWA causes its existing projections to re-fetch current persisted state.
- A later guided workflow may replace these separate review surfaces, but should retain the same
  explicit ratification boundary.

## Consequences

- Assessment and planning review routes no longer lose the athlete being prepared.
- The owner has one visible continuation after a successful approval.
- Scientific and safety decisions remain manual, attributable, and versioned.
