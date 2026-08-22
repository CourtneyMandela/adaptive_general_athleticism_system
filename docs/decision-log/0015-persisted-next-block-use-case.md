# 0015: Persisted next-block use case

- Status: accepted provisionally
- Date: 2026-08-22
- Decision version: `persisted-next-block-use-case@1.0.0`

## Decision

Add a transactional application service and `POST /v1/strategies/{strategy_id}/blocks` endpoint.
The request names already-persisted `AdaptationResourceDemand` records and one
`ResourceAllocationPolicy`, plus the weekly budget, four-to-six-week date window, explicit
constraints, and generation time. The service loads the strategy, demands, policy, and every
referenced exercise resolution; invokes the deterministic `BlockPlanner`; and appends the result
in one service-owned transaction.

The endpoint does not accept a caller-supplied strategy object and does not create stimuli,
exercise resolutions, resource demands, session prescriptions, or progression rules. Those inputs
must cross their own governed boundaries before a block can be built. Missing persisted identities
return 404, incompatible planning inputs return 422, and relational write conflicts return 409.

## Reason

The closed-loop replanning endpoint can now produce an immutable successor strategy, but a caller
previously had to reconstruct and persist a block manually. This application boundary completes
the next structural step in the feedback loop while preserving the distinction between strategy,
stimulus, exercise selection, resource allocation, and workout dose.

The `BlockPlanner` already enforces complete demand coverage for all strategy priorities, exact
strategy/priority/adaptation/state lineage, resolution-to-stimulus correspondence, explicit
partial-resolution policy, finite weekly resources, and four-to-six-week duration. Reusing that
engine keeps transport and persistence free of duplicated training rules.

## Alternatives considered

- Generate stimuli, resolutions, demands, prescriptions, and a weekly plan in the same request:
  rejected because the system has no authorized basis to invent those inputs.
- Accept nested demand and resolution objects over HTTP: rejected because unpersisted or forged
  objects could bypass provenance and repository integrity checks.
- Require this endpoint only for revised strategies: rejected because the same governed boundary
  is valid for an initial strategy and the strategy lineage itself already distinguishes revisions.
- Make strategy creation automatically create a block: rejected because a strategy does not imply
  environment-specific exercise resolution or scientific dose.
- Enforce one block per strategy: rejected because a longer-lived strategy may legitimately govern
  multiple reviewed blocks. Overlap and idempotency policy remain unresolved rather than guessed.

## Evidence and uncertainty

This is a software architecture and provenance decision implementing blueprint sections 47–48,
64, 74, and 88–90. It makes no scientific claim and introduces no dose values. The client remains
responsible for supplying resource demands created through an evidence-governed process.

The current service accepts block start dates that are not earlier than generation, as required by
the planner. It does not yet define a universal calendar alignment, overlap rule, or idempotency
key because the blueprint does not establish those product rules.

## Consequences

- A persisted revised strategy can lead to a second persisted block without rewriting block one.
- The second block retains the exact revised priority, demand, resolution, observations, evidence,
  policy, and planner rule version.
- Failure before commit rolls back the transaction and cannot leave a partial block.
- Exercise choice and training dose remain explicit upstream records rather than API inventions.
