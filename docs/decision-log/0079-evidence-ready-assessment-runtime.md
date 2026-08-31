# 0079 — Evidence-ready assessment runtime authority

Date: 2026-08-31

Status: accepted for this milestone

## Decision

Require point-in-time evidence readiness before an approved assessment protocol review or
capability-estimation policy can authorize a new athlete-facing runtime action.

Apply the rule to:

1. the public reviewed assessment catalog;
2. the athlete assessment-workflow projection and reassessment candidate set;
3. creation and persistence of new assessment selections;
4. recording a selected self-administered assessment result; and
5. creation and persistence of an assessment-derived capability estimate.

Centralize the single-claim temporal evaluation in the domain layer and let persistence load its
exact source snapshots and append-only review history. The API evidence-governance projection will
reuse that result rather than implementing a second readiness algorithm.

Historical definitions, reviews, policies, selections, performances, observations, and estimates
remain readable. This milestone changes authority for new actions; it does not delete, rewrite, or
retroactively relabel stored history.

## Reason

The assessment-governance workbench now identifies protocol and policy evidence that was not ready
at the authority's own review time. The athlete runtime still treated the same records as
operational based only on their `approved` decision. That allowed the public catalog and selection
workflow to disagree with the scientific-governance view.

One temporal evaluator keeps the authoring, inspection, API, and repository boundaries consistent.
Layered enforcement is necessary because application services are the normal path while repository
checks protect internal callers from persisting unsupported athlete history.

## Major implementation choices

- Evaluate evidence at the protocol or policy review timestamp, not the athlete request time.
- Require every cited claim to have existed, retained an exact available source snapshot, and had a
  current approved `EvidenceClaimReview` by that timestamp.
- Filter unsupported authority from the public catalog instead of exposing scientific-governance
  diagnostics through a public route; the protected workbench remains the place for exact blockers.
- Keep structurally approved but evidence-unready authority stored and visible to governance tools.
- Version new selections as `assessment-selection-run@3.0.0`; older run versions remain readable.
- Migrate only isolated software fixtures by adding explicitly non-scientific source and claim-review
  records. Do not create a real protocol or scientific claim.

## Alternatives considered

- **Enforce only in the browser.** Rejected because the browser is not an authority boundary.
- **Change `list_approved_assessment_definitions` to hide unsupported records everywhere.** Rejected
  because governance and historical inspection must still see structurally approved records.
- **Check only current evidence state.** Rejected because later review would rewrite the apparent
  basis of older protocol and policy decisions.
- **Delete or downgrade older unsupported approvals.** Rejected because that would destroy or alter
  historical governance records.
- **Apply the rule only when starting a selection run.** Rejected because direct persistence,
  in-flight result recording, and capability estimation are also new authoritative actions.

## Assumptions and unresolved questions

- Structural readiness is necessary but does not prove scientific truth, source authenticity, or
  reviewer qualification.
- A later evidence withdrawal does not silently rewrite an older authority's historical basis; a
  replacement protocol or policy review is required to change that authority explicitly.
- No production assessment authority currently needs migration; repository fixtures are software-
  only and will remain labeled as such.
- Planning, safety, progression, exposure, and block-review authorities still require their own
  deliberate enforcement migrations.

## Consequences

The athlete PWA can no longer offer, perform, or interpret an assessment whose scientific authority
was unsupported at its decision time. Governance records and prior athlete history remain intact,
and no workout, assessment protocol, measurement rule, capability norm, or scientific conclusion is
invented.
