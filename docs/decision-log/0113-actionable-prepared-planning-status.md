# 0113 — Actionable prepared-planning status

Date: 2026-09-12

Status: accepted

Decision version: `actionable-prepared-planning-status@1.0.0`

## Decision

When a current capability estimate exists and the planning-readiness projection reports that
planning authorities are still required, the athlete-facing first-session path may read the
existing role-protected candidate projections for planning strategy, competency floors, resource
allocation, and training construction.

At least one available candidate makes planning review the owner's next action. Candidate
conflicts remain system work and are labelled as conflicts. If no candidate status can be read,
the path retains the conservative planning-governance state. Each candidate endpoint remains
independently optional so one forbidden or unavailable projection cannot hide the ordinary
athlete status or an available candidate from another authority family.

Candidate status is presentation context only. It does not ratify an authority, create a plan,
change athlete state, or authorize training.

## Reason

The planning pipeline already distinguishes missing, prepared, conflicting, and ratified
authorities. The athlete path previously collapsed the first three states into one link labelled
“Review the prepared planning authorities,” even when nothing was prepared or a conflict required
engineering work. This could send the owner to a screen without an actionable decision and make
the path to the first session appear less trustworthy than the underlying governance state.

## Alternatives considered

- **Automatically ratify every available planning candidate.** Rejected because preparation is
  not approval and the digest-bound owner attestation is an intentional authority boundary.
- **Add candidate state to the athlete planning-readiness API.** Rejected because prepared
  governance artifacts are operator data and future athlete accounts may not hold reviewer roles.
- **Load all planning candidate projections for every athlete-page visit.** Rejected because the
  information is relevant only after a current estimate exists and readiness specifically reports
  missing planning authorities.
- **Require all four candidate projections to succeed.** Rejected because permission or a
  temporary failure in one authority family must not erase accurate status from another.

## Assumptions and provisional choices

- The owner-only alpha account currently has the reviewer roles needed to inspect these candidate
  projections; backend authorization remains the source of truth.
- A count of available artifacts is sufficient for path selection. Candidate content and exact
  ratification scope remain on the dedicated review surfaces.
- Blocked candidates do not become an owner action. Their specific remediation remains visible on
  the review surface while the first-session path conservatively reports governance work.

## Consequences

- After an assessment produces a current estimate, the phone UI can identify a genuinely prepared
  planning review as the next concrete step.
- Conflicts and absent governance are no longer described as ready for owner review.
- Planning remains evidence- and policy-gated; this change improves navigation without creating
  workout logic or bypassing any ratification invariant.
