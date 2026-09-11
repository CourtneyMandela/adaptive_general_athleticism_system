# 0101 — Data-loaded competency-floor batches

Date: 2026-09-11

Status: accepted

Decision version: `competency-floor-candidate-batch@1.0.0`

## Decision

Move prepared competency-floor candidate content from Python literals into reviewed JSON documents
under `data/governance_candidates/competency_floors/`. Validate every document into the existing
typed domain records at startup and reject unknown fields, inconsistent presentation/release
values, duplicate identities, or a stale SHA-256 content digest.

Expose the sorted current candidate catalog as a content-addressed batch manifest. A planning
reviewer may attest to that exact manifest once. Ratification remains all-or-nothing in one database
transaction and still creates or verifies the evidence chain, floor review, immutable decision,
and digest for each individual artifact before creating a separate batch decision record. Retain
the single-candidate endpoint for compatibility and targeted review.

Candidate presentation must separately disclose the origin of the numeric value and the origin of
the decision to use it operationally. The first candidate therefore identifies `11` as a direct
study result while identifying its use as a competency floor as evidence-informed engineering
judgment. A pure professional-judgment floor is not forced through the current scientific-claim
chain; it remains ineligible until a distinct governed authority model is designed.

## Reason

The end-to-end governance pattern was proven with one chair-stand floor, but repeating a large
Python module and one network round trip for every future parameter would add review friction and
make content unnecessarily expensive to maintain. A validated data boundary makes a new candidate
a reviewable data addition without weakening the product's provenance or atomicity requirements.

The earlier candidate digest was produced with `json.dumps(default=str)`. Nested Pydantic records
were therefore hashed through a Python display representation rather than canonical structured
JSON. Version 1.1 hashes the complete structured presentation and release with sorted JSON keys.
The historically ratified digest is recognized only for idempotent inspection of the same persisted
release; it cannot authorize different content or a new batch.

## Alternatives considered

- **Continue one Python module and request per floor.** Rejected as avoidable implementation and
  review overhead now that the invariants are proven.
- **Approve a batch with one unstructured digest only.** Rejected because it would obscure which
  artifact was reviewed and weaken per-floor history.
- **Permit partial batch success.** Rejected because a reviewer attests to one exact manifest; a
  stale or conflicting member must invalidate the whole transaction.
- **Treat every floor as scientifically established when it cites a paper.** Rejected because a
  paper may support the reported number without validating AGAS's operational interpretation.
- **Allow uncited professional judgment through the existing `EvidenceClaim` requirement.**
  Rejected because that would dress judgment up as scientific evidence. A separate typed authority
  path can be added when a concrete candidate requires it.

## Evidence

This is an engineering and governance transport decision. Its authority comes from the blueprint's
requirements for versioned rules, explicit provenance, preserved uncertainty, and traceable
scientific claims. It makes no new training or scientific claim.

## Assumptions and uncertainty

- Batch approval is appropriate only when the reviewer can inspect all members together. The UI
  retains item-level content, status, limitations, and individual approval.
- The catalog is small enough to load and validate synchronously. A database-backed editorial
  workflow may become appropriate later without changing the batch contract.
- The current catalog still contains only one floor. This milestone reduces the cost of adding the
  next researched set; it does not invent the remaining thresholds.
- Historic digest compatibility is narrowly scoped to the exact existing candidate identity and
  persisted domain content.

## Consequences

- Future competency floors can be prepared in coherent researched batches as validated data.
- One exact attestation and HTTP request can approve a batch without losing per-artifact digests,
  evidence reviews, decision records, or rollback behavior.
- A conflict or stale manifest leaves every member unmodified.
- Reviewers can see which part came from evidence and which part is an AGAS operational judgment.
- Other governance candidate families remain Python-backed until their own content patterns are
  stable enough to justify the same migration.
