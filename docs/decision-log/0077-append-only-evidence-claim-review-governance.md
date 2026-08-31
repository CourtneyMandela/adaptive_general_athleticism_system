# 0077 — Append-only evidence-claim review governance

Date: 2026-08-31

Status: accepted for this milestone

## Context

AGAS can now retain immutable scientific-source metadata snapshots and link an `EvidenceClaim` to the exact snapshots used to construct it. That provenance is necessary but not sufficient: a structured claim must not become operational evidence merely because it was imported successfully. The system needs a separate, versioned record of the review decision and the reasoning used to verify the source, extraction, strength, applicability, and uncertainty.

## Decision

Add an append-only `EvidenceClaimReview` aggregate with a linear supersession chain. Each record identifies one claim, an explicit decision (`approved`, `needs_revision`, or `rejected`), the exact sequence and predecessor, the review time and reviewer label, and separate rationales for source verification, extraction, evidence strength, athlete applicability, uncertainty, and conflict disclosures.

The database will enforce positive sequence numbers, unique claim/sequence pairs, and one successor per predecessor. Repository validation will additionally enforce same-claim predecessors, exact sequence increments, and nondecreasing review time.

Extend the guarded local evidence-governance bundle to version 2 so externally prepared review records may be imported atomically with exact source snapshots and claims. Version 1 bundles remain valid and import no reviews. Import is idempotent only when persisted immutable content exactly matches the bundle.

Expose a read-only evidence-governance projection and PWA workbench. It will show each claim, exact source snapshots available at the projection time, immutable review history, current decision, and blockers. A claim is operationally ready in this projection only when it has at least one linked source snapshot and its current review is approved.

Reuse the existing `assessment_reviewer` application role for this read-only scientific-governance view. Application access is explicitly not treated as scientific qualification, and the browser will not contain an approval action.

## Major implementation choices

- Keep source metadata, claim content, and review decisions as separate immutable records.
- Model review decisions in a dedicated `EvidenceReviewDecision` enum so evidence governance remains a distinct bounded context even though decision values currently match assessment review values.
- Resolve current state only by projecting the append-only chain at an explicit timezone-aware instant.
- Treat missing source snapshots, unavailable future-dated snapshots, absent reviews, and non-approved current reviews as visible blockers.
- Preserve legacy claims without source-record links; do not backfill provenance or fabricate reviews.
- Keep operational policy enforcement unchanged in this increment. The projection exposes readiness, but existing planning authorities are not retroactively invalidated.

## Alternatives considered

- **Put approval fields directly on `EvidenceClaim`.** Rejected because changing a decision would overwrite claim history and conflate extraction with authorization.
- **Allow approval writes in the browser.** Rejected because an application role cannot establish scientific credentials or replace an external review procedure.
- **Add an `evidence_reviewer` account role now.** Deferred because current functionality is inspection-only and the assessment-governance role already represents access to scientific-governance projections. A distinct role should be introduced only with a defined credentialing and review-assignment process.
- **Immediately require approved claim reviews at every planning write boundary.** Deferred because existing fixtures and provisional policy records predate exact source snapshots. Enforcement needs a deliberate migration and replacement-authority plan rather than silently invalidating historical work.
- **Backfill reviews for existing claims.** Rejected because doing so would invent scientific review history.

## Assumptions

- Qualified review occurs outside the athlete-facing application for now.
- A reviewer label and conflict disclosure are provenance, not proof of qualification.
- Source metadata snapshots support traceability but do not by themselves prove that a claim accurately represents the full publication.
- An approved review applies only to the exact immutable claim version it references.

## Unresolved questions

- What credentialing, conflict-management, and assignment process should authorize human evidence reviewers?
- Which existing planning authorities must be replaced before approved evidence reviews become a universal operational write precondition?
- Should future reviews retain structured risk-of-bias instruments specific to each study design?
- Which publication-content access methods may legally and reliably support full-text verification beyond metadata and abstracts?

## Consequences

AGAS gains an auditable boundary between “a claim exists” and “the current review approved this exact claim.” Historical review decisions remain inspectable, and the athlete PWA still cannot create scientific authority. A later milestone must connect approved evidence-review status to each operational policy boundary after governed replacement records exist.
