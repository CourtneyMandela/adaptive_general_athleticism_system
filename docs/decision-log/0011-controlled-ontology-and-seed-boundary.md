# 0011: Controlled ontology and seed boundary

- Status: accepted provisionally
- Date: 2026-08-19
- Decision version: `controlled-ontology@1.0.0`

## Decision

Replace free-form values at the stimulus-to-exercise matching seam with controlled enums before
catalog data is introduced. Movement pattern, loading type, velocity characteristic, joint region,
laterality, preferred stimulus, training modality, and dose dimension become typed domain values.
Laterality is an independent exercise and stimulus axis, and the resolver scores it through an
explicit policy weight instead of hiding it inside movement-pattern text.

Create a small, versioned seed catalog with stable identifiers and a loader that validates every
cross-reference before records reach persistence. The first catalog is intentionally much smaller
than the eventual V1 targets: it exists to prove that the ontology can express the required
home/full-gym/travel decisions. Scientific claims are seeded only after their source identifiers
and interpretations are checked against primary publication records. Catalog review status must
distinguish secondary-AI verification from production approval.

Permit a weekly prescription to use a newer exercise resolution than the block's planning-time
resolution only when it preserves the allocation's athlete, adaptation, and stimulus requirement.
A versioned weekly scheduling policy must explicitly allow partial-fidelity re-resolution. The
original block allocation and resolution remain immutable history; the travel-week prescription
links to the newer resolution and carries its limitations.

The baseline migration created before real data remains frozen. This milestone uses an incremental
Alembic revision.

## Reason

Free-form set intersection can silently turn vocabulary drift into a physiological mismatch. That
failure would be especially costly once catalog values and persisted plans depend on the initial
spelling. Laterality is independent from movement pattern and materially affects hotel-equipment
resolution. The blueprint also requires an automated travel scenario in which goals remain stable,
heavy-strength fidelity is downgraded honestly, feasible aerobic work continues, and the original
means become available again after return.

## Alternatives considered

- Normalize arbitrary strings at runtime: rejected because aliases hide authoring errors and make
  the accepted ontology implicit.
- Encode laterality as another movement pattern: rejected because knee dominance and unilateral
  loading are independent axes.
- Seed the full 75–125 exercise and 25–50 claim V1 catalogs now: rejected because metadata quality,
  reviewability, and one working loop matter more than catalog size.
- Seed plausible training rules without citations: rejected as an evidence-policy violation.
- Mutate the existing block allocation when travel begins: rejected because it would destroy the
  planning-time decision and make return behavior unauditable.
- Require a completely new long-range strategy for a temporary environment: rejected because the
  athlete's adaptation objective and goals have not changed.

## Evidence, assumptions, and uncertainty

The controlled vocabulary and weekly re-resolution behavior are product-model decisions derived
from blueprint sections 11–15, 33, 50, 56, 65–67, 72, and 89. They are not scientific claims.
Exercise metadata begins as domain-reviewed catalog annotation, not evidence of exercise
equivalence. Resolver scores remain ranking heuristics.

Seeded scientific claims may support broad adaptation context, but this milestone does not use them
to invent exact dose, maintenance, or progression thresholds. Secondary-AI verification is not a
substitute for owner or qualified-domain review before personal programming rules are activated.

## Consequences

- Invalid vocabulary values fail domain validation instead of degrading resolver scores silently.
- The resolver can state a laterality mismatch separately from loadability or movement mismatch.
- Seed catalog loading fails atomically on dangling adaptation, equipment, exercise, or evidence
  references.
- A travel-week prescription can preserve the block stimulus while recording a partial substitute.
- Seed expansion and production approval remain later, reviewable operations.
