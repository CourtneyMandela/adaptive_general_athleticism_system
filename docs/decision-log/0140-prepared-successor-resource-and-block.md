# 0140 — Prepared successor resource demand and block

Date: 2026-09-24

Status: accepted provisionally

Decision version: `prepared-successor-resource-and-block@1.0.0`

## Decision

Extend the prepared resource-demand and block workflows to distinguish an initial strategy from a
review-derived successor strategy. A successor candidate must reconstruct and retain the exact
predecessor strategy, triggering block review, reviewed predecessor block, predecessor block end
date, and predecessor priority records. Missing or contradictory lineage blocks preparation.

The prepared resource candidate exposes both the prior and current priority state and binds the
complete cycle lineage into its content digest. Ratification continues to re-project the candidate
server-side and accepts only the exact candidate version and digest after explicit owner
attestation. The resulting stimulus requirement, exercise resolution, resource demand, and
decision record remain new immutable artifacts under the successor strategy; no first-block demand
is copied or mutated.

The prepared block candidate binds the same cycle lineage, the successor strategy and capability
need, its separately ratified resource demand, exact exercise resolution, allocation policy, and
current priority state. A successor block must begin on a Monday strictly after the reviewed
predecessor block ends. The owner must separately attest to the exact block candidate before it is
persisted.

Preserve the historical `prepared-resource-demand@1.0.0` and
`prepared-first-block@1.0.0` identities for existing initial chair and push-up records. Use the
content-addressed `@1.1.0` contracts for successor candidates and the new jump pathway.

Add a separate owner-reviewable explosive-power MAINTAIN resource authority rather than changing
the existing DEVELOP-only authority. It retains the same reviewed source and scientific direction
through a separately identified claim/review pair, reuses the exercise ontology and resolver, and
has a new candidate ID, allocation-policy ID, decision record, and provisional 12-minute weekly
scheduling envelope across two 6-minute slots. The original DEVELOP envelope remains 24 minutes
across two 12-minute slots. Both envelopes are engineering scheduling choices, not
literature-derived physiological doses.

## Reason

The immutable successor strategy already changes its capability need and priority from reviewed
post-block evidence, but the downstream prepared workflows did not identify the planning cycle or
prove that a second block followed the reviewed predecessor. Their first-block wording also made a
successor proposal misleading.

The jump authority had a more serious fail-closed gap: its allocation policy assigned zero weight
to MAINTAIN. A successful reassessment could therefore cross the provisional floor and correctly
produce a MAINTAIN strategy, only for resource preparation to become unavailable. A distinct
maintenance authority preserves explicit owner review and immutable rule history while allowing
the feedback loop to continue.

## Alternatives considered

- Reuse the first block's resource demand. Rejected because demands are strategy-, priority-,
  need-, observation-, and environment-specific immutable decisions.
- Treat every block prepared by the existing route as an untyped continuation. Rejected because it
  would not establish which review caused the successor or prevent overlap with the predecessor.
- Change the existing jump DEVELOP policy in place. Rejected because a material rule must not
  silently change under the same identity and version.
- Automatically ratify the successor demand and block after replanning. Rejected because each is a
  material owner-reviewed planning decision.
- Use the full DEVELOP resource envelope for MAINTAIN without a separate decision. Rejected because
  that would hide a new scheduling assumption and make the changed priority operationally inert.

## Evidence

This is primarily an architecture, provenance, and engineering-governance decision. The existing
reviewed plyometric evidence supports only the broad training direction. It does not establish the
12-minute maintenance envelope, two-session frequency, or exact exercise as an optimum; those
remain explicit owner-reviewable engineering choices.

## Uncertainty

The 12-minute maintenance envelope has not yet been calibrated from this athlete's repeated
response and does not establish a maintenance dose. It reserves scheduling resource only. The
current fixed jump dose authority is deficit- and DEVELOP-specific, so a separately reviewed
maintenance prescription authority is still required before a successor week can be generated.

The current owner-alpha projector supports one governed active priority. Broader multi-adaptation
successor blocks will require explicit rules for competing resource envelopes rather than extending
this narrow path by implication.

## Consequences

- The owner can see a DEVELOP-to-MAINTAIN transition and the exact review/block lineage before
  accepting the successor resource demand.
- The server rejects a second block that overlaps or predates its reviewed predecessor.
- The successor block consumes new successor demand and allocation records; it does not copy the
  first block.
- Existing initial chair and push-up candidate identities remain compatible.
- Jump maintenance requires ratification of its distinct resource authority before it becomes
  operational.
- The next task is a separately governed successor-week construction path, including a MAINTAIN-
  applicable dose authority and proof that the first successor week consumes the second block.
