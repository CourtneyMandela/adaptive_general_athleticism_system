# 0041 — Governed planning readiness

- Status: accepted provisionally
- Date: 2026-08-27
- Decision version: `athlete-planning-status-projection@1.1.0`

## Decision

Extend the authenticated read-only planning-status projection so it distinguishes missing
planning authorities from the remaining operator context review. Before a root strategy exists,
the projection uses these states after capability-estimate readiness:

- `planning_authorities_required` when no current approved priority policy exists or no current
  approved competency floor is compatible with a current estimate;
- `planning_context_review_required` when both authority types exist but candidate relevance,
  costs, adaptation selection, applicability, and uncertainty still require operator review.

The projection returns an explicit checklist with stable requirement codes, satisfaction state,
and matching-record counts. It also reports how many current estimates have a compatible approved
floor and how many remain uncovered. The PWA displays this information but provides no athlete-facing
strategy-generation control.

An authority counts only when its database-current review is approved and no later than the
projection instant. A future review is never exposed as current approval; it also does not cause a
superseded historical approval to masquerade as the authority that initial planning would accept.

## Reason

The previous `governed_strategy_inputs_required` state truthfully avoided generic workout
generation but collapsed two materially different conditions: missing scientific/rule authorities
and an operator decision still awaiting reviewed athlete-specific context. Making those conditions
explicit gives the athlete an honest progress signal and gives operators a deterministic readiness
read model without duplicating planning logic in the frontend.

## Alternatives considered

- Keep one generic state and change only its text. Rejected because clients could not reliably
  distinguish missing authority records from pending contextual review.
- Treat any evidence-linked floor or policy as ready. Rejected because existence is not current
  approval.
- Require every current estimate to have a floor before context review. Rejected because some
  estimates may legitimately provide uncertainty or supporting context without becoming a
  competency-floor candidate. Uncovered estimates remain visible rather than blocking silently.
- Persist readiness as mutable state. Rejected because readiness is a deterministic projection of
  append-only estimates, authorities, reviews, and strategies.

## Evidence and uncertainty

This is application-state presentation and introduces no scientific training claim. Compatibility
uses the same explicit domain, estimate-scope, and unit contract as competency-floor detection.
Whether a compatible floor applies to this athlete remains an operator judgment.

## Consequences

- Clients receive stable, testable reasons for why initial planning has not advanced.
- A compatible approved floor is not presented as an athlete-specific recommendation.
- Operator review remains mandatory even when all representable authority prerequisites exist.
- Future work may add reviewed adaptation-context persistence, at which point the final checklist
  item can become a persisted authority rather than a deliberately pending handoff.
