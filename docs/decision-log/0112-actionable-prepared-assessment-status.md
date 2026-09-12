# 0112 — Actionable prepared-assessment status

Date: 2026-09-12

Status: accepted

Decision version: `actionable-prepared-assessment-status@1.0.0`

## Decision

When building the athlete-facing first-session path, optionally read the existing role-protected
assessment-candidate projection. If the signed-in account has permission and at least one exact
candidate is available, describe assessment approval as the owner's current action, link to the
candidate review with athlete context, and place that primary action above the progress list.

Candidate lookup is advisory presentation data. A failed or forbidden operator lookup falls back
to the existing conservative “governance work needed” state without hiding the athlete's ordinary
assessment and planning projections. Ratification still requires the separate digest-bound review
and attestation endpoint.

## Reason

The system had already prepared an evidence-linked assessment release, but the athlete page could
see only that no release was ratified. It therefore told the owner that AGAS still needed to do
unspecified work, even though the actual next step was an explicit owner decision. On a phone the
action also appeared below five progress rows, outside the initial viewport.

## Alternatives considered

- **Automatically ratify the candidate.** Rejected because preparation is not approval and would
  erase the visible authority boundary.
- **Expose candidate status on the general athlete assessment API.** Rejected because candidate
  governance is operator data and future athletes may not have reviewer permission.
- **Make candidate lookup mandatory.** Rejected because ordinary athlete status must remain usable
  for accounts without reviewer roles and during an operator-projection failure.

## Assumptions and provisional choices

- The owner-only alpha account currently holds both athlete ownership and assessment-review roles;
  those authorities remain independently enforced by the backend.
- Candidate count is used only to choose accurate wording and navigation. It is not athlete state,
  evidence authority, or permission to perform an assessment.

## Consequences

- The live state shown in the owner dashboard has one accurate, above-the-fold next action.
- Future non-reviewer athletes still see a conservative system-work state.
- Approval remains deliberate, attributable, immutable, and separate from athlete readiness.
