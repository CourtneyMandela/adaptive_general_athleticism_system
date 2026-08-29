# Decision 0050: Server-enforced weekly advancement readiness

- Date: 2026-08-28
- Decision version: `weekly-advancement-readiness@1.0.0`
- Status: accepted

## Decision

Make the backend-derived weekly review an authoritative precondition of automatic weekly
roll-forward. The roll-forward service must reconstruct the exact source plan's review and proceed
only when its status is `ready_to_prepare_next_week`.

The same projector used by the athlete-facing current-week read model owns the closure semantics.
Roll-forward does not duplicate those rules and does not trust a client-submitted readiness flag.
All other states fail closed with the structured status and reason included in the application
error. Existing unique-successor conflict handling remains separate and retains conflict semantics.

The required closure state continues to mean:

- every scheduled occurrence has an explicit execution outcome;
- every execution has post-session safety/recovery closure;
- every prescription occurrence has a deterministic progression decision or a true immutable
  revision descendant;
- no hold, review-required, unsupported, missing-policy, ambiguous-policy, or infeasible state
  remains; and
- the source week is not the block's final week.

## Reason

The PWA already hides roll-forward until the projected week is ready, but UI gating is not an
authorization or domain boundary. Another API client could previously call roll-forward directly
and create a successor from incomplete performance, recovery, or progression history. The write
service must enforce the same closure state it presents to the athlete.

## Alternatives considered

- Continue relying on the PWA button state. Rejected because transport clients can bypass React.
- Accept a client `ready=true` assertion. Rejected because readiness is derived server state.
- Reimplement completion checks inside roll-forward. Rejected because two rule implementations
  would drift and could authorize different weeks.
- Permit final-week roll-forward and let block bounds fail later. Rejected because the correct next
  boundary is block review, which should be explicit.

## Evidence

This is a workflow-integrity and safety-orchestration decision implementing blueprint sections
35, 37, 41–42, 47, 58, 64, 73–74, and 83. It introduces no scientific threshold, progression
increment, fatigue inference, or training recommendation.

## Assumptions

- The existing weekly-review status ordering in Decision 0026 remains the canonical closure rule.
- An explicit non-completed session execution is still a recorded outcome; downstream review
  remains descriptive and progression/safety state determines whether automatic advancement is
  allowed.
- A prescription revision descendant can resolve repeated occurrences of the ancestor only under
  the existing provisional multi-session rule documented in Decision 0026.

## Unresolved questions

- Multi-session aggregation before one progression decision.
- Operator resolution workflows for hold, review-required, missing-policy, and unsupported
  progression states.
- Correction or voiding of incorrectly recorded execution and safety history.
- Production event-time trust and concurrency beyond the existing unique successor constraint.

## Consequences

- An incomplete week cannot be advanced by calling the API directly.
- PWA and write-service readiness cannot drift because they share one projector.
- Existing roll-forward tests must close source-week execution, recovery, and progression history.
- The full governed vertical-slice scenario can rely on automatic advancement as a real invariant.
