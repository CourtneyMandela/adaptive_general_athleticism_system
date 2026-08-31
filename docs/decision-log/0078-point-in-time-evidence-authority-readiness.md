# 0078 — Point-in-time evidence readiness for scientific authorities

Date: 2026-08-31

Status: accepted for this milestone

## Decision

Introduce one reusable, read-only evidence-authority evaluator that resolves a set of exact
`EvidenceClaim` identifiers at a timezone-aware authority timestamp. A claim is ready only when it
already existed, retained at least one exact source snapshot available by that timestamp, and had a
current approved `EvidenceClaimReview` by that timestamp.

Use the evaluator in two bounded places:

1. the assessment-governance projection, where evidence defects become explicit readiness blockers
   for the exact current protocol review and capability-estimation policy; and
2. the guarded local assessment-governance importer, where a new `approved` review or policy is
   rejected unless every cited claim was ready at that authority record's own review time.

Later evidence approval does not retroactively authorize an older scientific authority. A new
authority review version is required so its timestamp truthfully follows the evidence review.

## Reason

AGAS now distinguishes source snapshots, claims, and claim-review decisions, but assessment
authority could still cite a structurally valid claim that had no approved scientific review. The
first production-facing enforcement should be small, inspectable, and point-in-time correct rather
than a repository-wide switch that silently invalidates historical fixtures and prior decisions.

## Major implementation choices

- Return typed per-claim results containing the exact claim, sources, current review, history,
  readiness, and issues.
- Version the reusable evaluation as `evidence-authority-readiness@1.0.0` and bump the expanded
  assessment projection contract to `assessment-governance-workbench@1.1.0`.
- Treat unknown, future-dated, source-less, unavailable-source, unreviewed, and non-approved claims
  as blocked rather than guessing.
- Require at least one evidence claim when evaluating an approved scientific authority.
- Preserve `needs_revision` and `rejected` authority imports without demanding approved evidence;
  those records do not grant operational authority.
- Keep athlete-facing assessment selection unchanged in this increment. The workbench and guarded
  import boundary close the authoring gap first; runtime enforcement requires a deliberate fixture
  and data migration.

## Alternatives considered

- **Check only the claim's current status at request time.** Rejected because a later approval would
  rewrite the apparent basis of an older authority.
- **Require approved evidence inside every repository evidence foreign-key write immediately.**
  Deferred because evidence links also occur on historical outputs and non-authorizing records, and
  current software fixtures intentionally use non-scientific claims.
- **Treat source identifiers as sufficient.** Rejected because identifier strings do not prove which
  metadata snapshot was reviewed or whether the interpretation was approved.
- **Automatically supersede an authority after evidence approval.** Rejected because that would
  fabricate a new human governance decision.

## Assumptions

- Scientific authority review time is the appropriate cutoff for its evidence basis.
- Structural readiness is necessary but not proof of reviewer qualification or scientific truth.
- Local development imports remain an administrative transport, not an approval interface.

## Unresolved questions

- Which existing assessment authorities should be replaced before runtime catalog and selection
  enforce this same boundary?
- Which planning, safety, progression, exposure, and block-review authority should adopt the
  evaluator next, and in what migration order?
- Should evidence reviews later carry explicit validity intervals or withdrawal reasons beyond
  linear supersession?

## Consequences

New approved assessment-governance imports cannot cite evidence that was unapproved at the time of
the authority decision, and reviewers can see exact evidence blockers in the workbench. Historical
records are preserved and no training rule, assessment protocol, or scientific claim is invented.
