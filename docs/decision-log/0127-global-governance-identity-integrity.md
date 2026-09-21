# Decision 0127: Global governance identity integrity

- Date: 2026-09-21
- Status: Accepted
- Decision version: `global-governance-identity-integrity@1.0.0`

## Context

Prepared governance candidates are authored in several modules and data files, but their evidence
sources, evidence claims, evidence reviews, and ratification decisions all persist into shared
tables. Earlier candidates allocated visually related UUID sequences within each module without a
repository-wide collision check. As the prepared assessment, planning, competency-floor, and
resource paths began to coexist, inspection found that different immutable records had reused the
same UUIDs.

This was an integrity defect, not merely a naming problem. Depending on ratification order, a valid
candidate could encounter an existing row or decision with different content and correctly refuse
to proceed. The refusal protected history, but it also made independent reviewed releases mutually
exclusive.

## Decision

Reassign identities on prepared artifacts that had not been able to coexist with the already
established planning/resource lineage:

- the standard-push-up and countermovement-jump assessment claims use a distinct claim namespace;
- the chair-stand competency-floor candidate receives a distinct release/decision identity;
- that candidate's source, claim, and evidence-review records receive distinct identities.

Keep exact reuse of an identical immutable source snapshot valid. For example, multiple candidates
may reference the same ACSM source record when the complete source object is identical. Reuse of an
identity for different source or claim content is forbidden. Evidence-review identities are always
unique because the persisted reviewer and review time are created at ratification.

Add a repository-wide regression test that inventories prepared assessment, planning,
competency-floor, and resource candidates and fails when different immutable content shares a
persistence identity or when evidence-review IDs repeat.

## Alternatives considered

- **Rely on database conflicts.** Rejected because detection at ratification is late and makes
  otherwise independent releases order-dependent.
- **Forbid all repeated UUIDs.** Rejected because exact reuse of one immutable evidence-source
  snapshot is intentional provenance, not a collision.
- **Rewrite already persisted history.** Rejected. The fix changes prepared candidate identities;
  it does not mutate existing rows or silently reinterpret a historical decision.
- **Build the jump-exposure candidate first.** Rejected because adding another governed release on
  top of a known global-identity defect would compound the problem.

## Consequences

- Prepared governance paths can be ratified in either order without competing for different rows
  under the same primary key.
- Future candidate work has a cheap automated check for this cross-module invariant.
- Candidate digests that include reassigned IDs change, as they must; reviewers must approve the
  exact corrected candidate content.
- The chair-stand path remains historical scaffolding and is not promoted as an owner-appropriate
  training target by this identity repair.
