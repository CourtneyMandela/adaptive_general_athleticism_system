# 0100 — Anti-sludge harness foundation

Date: 2026-09-11

Status: accepted

Decision version: `anti-sludge-analyzer@1.0.0`

## Decision

Introduce an evaluation package that converts long-range strategy, block allocation, exercise
resolution, prescription, and weekly-plan artifacts into identity-free behavioral signatures. A
paired counterfactual supplies an explicit, versioned expectation naming the dimensions that must
change and those that must remain stable. The analyzer reports per-dimension multiset similarity
and raises either a generic-program alert for a missing required response or an invariant-violation
alert for unwanted spillover.

The first executable corpus covers opposite aerobic-versus-strength profiles and full-gym-versus-
hotel equipment. Both tests invoke the real deterministic planner or resolver rather than comparing
handwritten output snapshots.

## Reason

The repository already contained paired counterfactual assertions but `tests/anti_sludge/` was
empty. Direct assertions prove individual rules; they do not create a shared vocabulary for
measuring convergence across planning layers or making generic-program failures visible. A small
signature and expectation boundary provides that vocabulary before the first owner workout exists.

## Alternatives considered

- **Flag every pair over a global similarity threshold.** Rejected because a one-variable change
  should often leave most dimensions stable; high overall similarity is not automatically sludge.
- **Compare database IDs or serialized records directly.** Rejected because generated identities,
  timestamps, and provenance can differ while behavior remains identical.
- **Use an LLM planner critic now.** Deferred because deterministic change expectations are easier
  to inspect and test. A later critic may explain reports but cannot replace them.
- **Wait for a full owner plan.** Rejected because the established planning and resolution layers
  already support real behavioral checks, although prescription and schedule coverage must follow.

## Evidence

This is a software-evaluation mechanism, not a scientific training rule. Its governing requirement
comes from the blueprint's anti-sludge acceptance criterion and the repository invariant that
meaningfully different athlete states must not repeatedly converge on effectively identical plans.

## Assumptions and uncertainty

- Semantic adaptation and exercise names are supplied by the evaluation corpus so generated UUIDs
  do not create false differences.
- Exact match within a dimension is deliberately strict in version 1. Partial similarity is
  descriptive; alerts depend on explicit expectations rather than a universal cutoff.
- The initial corpus is small and does not yet cover symptoms, schedule constraints, body size,
  preference changes, or owner-production prescriptions.

## Consequences

- CI now has a real `tests/anti_sludge/` suite and a reusable generic-program alert mechanism.
- Equipment counterfactuals can require the exercise to change while the adaptation priority stays
  fixed, directly protecting the adaptation-before-exercise invariant.
- Every future governed planning layer can add paired cases without inventing a new comparison
  format.
- Passing this initial suite does not prove that the eventual owner program is individualized; the
  corpus must grow alongside real prescriptions and schedules.
