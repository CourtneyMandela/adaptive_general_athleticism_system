# 0042 — Strategy-to-block readiness

- Status: accepted provisionally
- Date: 2026-08-27
- Decision version: `athlete-planning-status-projection@1.2.0`

## Decision

Extend the authenticated planning-status projection beyond root-strategy creation. For a persisted
strategy, derive a read-only checklist across these existing boundaries:

1. every strategy priority has at least one historical `AdaptationResourceDemand`;
2. at least one persisted `ResourceAllocationPolicy` is available;
3. every priority has at least one demand that can enter block planning without an infeasible
   exercise resolution, with partial resolutions counted only when some persisted allocation
   policy explicitly permits them;
4. an operator still supplies the exact demand history, policy, weekly budget, dates, duration,
   and constraints before block creation.

Use explicit states for missing demand preparation, missing allocation policy, unresolved exercise
feasibility, pending block context, a persisted feasible/partial block, a persisted infeasible
block, and ambiguous multiple blocks. Do not silently select one of multiple historical demands or
multiple blocks as "current." Report their counts and leave exact selection to the governed write
boundary.

## Reason

`LongRangeStrategy` is not a workout or block. The existing application services correctly require
separate stimulus, environment resolution, resource demand, and allocation inputs, but the PWA
previously stopped at “strategy created.” A deterministic projection can show progress through
that chain without inventing any scientific dose, exercise equivalence, weekly budget, calendar,
or safety rule.

## Alternatives considered

- Automatically create resource demands or a block after strategy creation. Rejected because the
  required stimuli, dose, environment, exercise candidates, and resource amounts are governed
  inputs that the software cannot infer from an adaptation name.
- Treat any historical demand as the current demand. Rejected because demand supersession and
  approval semantics remain intentionally unresolved.
- Treat partial exercise resolution as universally usable. Rejected because the selected resource
  allocation policy explicitly controls whether partial resolution is acceptable.
- Choose the newest block when several exist. Rejected because decision 0015 allows multiple
  blocks per longer-lived strategy and no persisted current-block pointer exists.
- Hide infeasible blocks. Rejected because infeasibility is a meaningful planning result and must
  remain visible.

## Evidence and uncertainty

This decision adds application-state presentation only. It does not establish effective stimuli,
minimum doses, recovery intervals, or exercise equivalence. Counts reflect persisted records, not
scientific approval. Demand approval, supersession, and current-block selection need future
governance models before the projection can make stronger claims.

## Consequences

- The athlete can see why a strategy has not yet become a usable block.
- An infeasible environment resolution remains a blocker rather than becoming a generic substitute.
- Operators retain responsibility for exact historical-demand and block-context selection.
- Weekly prescription and scheduling readiness remain separate downstream milestones.
