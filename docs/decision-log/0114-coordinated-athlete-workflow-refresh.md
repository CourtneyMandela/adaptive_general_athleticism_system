# 0114 — Coordinated athlete-workflow refresh

Date: 2026-09-12

Status: accepted

Decision version: `coordinated-athlete-workflow-refresh@1.0.0`

## Decision

Treat successful athlete-authored assessment, demographic, and environment writes as changes to a
shared athlete-workflow revision in the PWA. After the writing panel reloads its own authoritative
projection, the dashboard reloads the current week and remounts the dependent first-session,
athletic-dashboard, and planning-status projections.

When an assessment selection is deferred specifically because required equipment is not reported
available, the first-session path links directly to the environment report instead of sending the
athlete back to the assessment form. The link is selected from persisted assessment reason codes;
the browser does not infer equipment equivalence or change selection state.

## Reason

The backend already appends each fact and derives the correct next status, but the athlete page
loaded its panels independently. Completing a readiness report, recording a result, creating its
reviewed estimate, or correcting equipment could therefore leave adjacent panels and the top next-
action card stale until a manual refresh. That is especially confusing in a phone workflow where
the next step should become visible immediately after a successful submission.

## Alternatives considered

- **Poll every projection continuously.** Rejected because writes are known locally, polling adds
  needless hosted traffic, and background freshness is not required for this single-owner alpha.
- **Optimistically edit adjacent projections in browser state.** Rejected because the server is the
  authority for selection, estimate, planning, and safety status.
- **Perform a full browser-page reload after every write.** Rejected because it discards local UI
  context and is unnecessary when the affected projections can be re-read directly.
- **Infer missing equipment from assessment prose.** Rejected because versioned reason codes are
  the structured, governed explanation of the persisted selection decision.

## Assumptions and provisional choices

- A small number of targeted projection reads after a successful write is acceptable for the
  owner-only alpha and free-tier hosting. Writes are infrequent and no timer-based polling is added.
- Remounting read panels is preferable to building a client-side cache invalidation framework at
  this scale.
- The current workflow has one selected athlete at a time, so a dashboard-local revision counter
  is sufficient.

## Consequences

- The top path, capability history, planning readiness, and current week converge on persisted
  state after each relevant action.
- Assessment equipment problems become a direct, understandable owner action.
- No domain rules move into the frontend, and historical records remain append-only.
