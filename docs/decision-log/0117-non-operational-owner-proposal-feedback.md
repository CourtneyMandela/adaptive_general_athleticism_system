# 0117 — Non-operational owner proposal feedback

Date: 2026-09-13

Status: accepted

Decision version: `competency-floor-proposal-review@1.0.0`

## Decision

Allow the planning reviewer to record one of three product decisions on each exact competency-floor
research proposal: `advance`, `needs_revision`, or `rejected`. A review is tied to both the proposal
UUID and digest and the containing batch UUID and digest. It retains the reviewer account, exact
planning-reviewer assignment, rationale, timestamp, attestation, sequence number, and supersession
lineage. Reviews are append-only.

The action is explicitly non-operational. It does not create or approve an evidence claim,
professional-judgment authority, competency floor, assessment, estimate, plan, or workout. An
`advance` decision instructs engineering to prepare the missing governed artifacts; those artifacts
must still pass their ordinary evidence, applicability, and ratification boundaries. If a proposal
or batch changes, feedback on the prior digest is presented as stale and is not transferred.

The owner UI provides the three decisions beside the source table, source population, proposed
threshold, population-match assessment, gaps, and release prerequisites. A rationale is required for
revision or rejection. Advancing without a custom note uses a narrow standardized rationale so the
owner is not made responsible for authoring technical policy.

## Reason

The 15-item proposal batch created in decision 0116 was inspectable but offered no way to preserve
the owner's direction. Requiring feedback through code or free-form technical documents would make
the stakeholder perform engineering work and would lose exact provenance. Directly ratifying the
proposals would be unsafe because several lack governed assessments, demographic applicability, or
an adopted evidence-or-judgment authority.

This boundary captures the decision needed to choose the next vertical slices while preserving the
separation between product feedback and training authority.

## Alternatives considered

- **Ratify proposals directly.** Rejected because a preliminary threshold could enter planning
  without its required assessment and authority chain.
- **Keep proposal review outside the product.** Rejected because chat or issue comments are not
  content-addressed, role-bound, append-only records and are easy to detach from the exact proposal.
- **Require a detailed note for every decision.** Rejected for `advance`; the proposal already
  contains the technical rationale and the owner should not have to rewrite it. Revision and
  rejection still require an explanation so engineering knows what must change.
- **Overwrite the prior response.** Rejected because changing owner judgment is meaningful history.

## Assumptions and unresolved questions

- Planning-reviewer authorization is sufficient to record product feedback. It does not certify a
  credential or confer scientific authority.
- The current owner-alpha release has one planning reviewer, but the record model remains actor-bound
  and supports later assignments.
- Advancing a proposal does not yet prioritize it relative to other advanced proposals. Engineering
  will choose an order that produces the shortest safe path to a useful first session.
- Demographic and assessment-specific applicability questions remain unresolved until their input
  and interpretation paths are implemented.

## Consequences

- The owner can direct the research batch from the deployed PWA without editing code or policy.
- Engineering can batch work around accepted proposals while retaining exact feedback provenance.
- Proposal changes cannot silently inherit approval-like feedback.
- The database gains one append-only table and migration, but no new training-planning input.
- The next work should convert selected proposals into governed assessment-to-floor vertical slices,
  rather than expand the proposal mechanism further.
