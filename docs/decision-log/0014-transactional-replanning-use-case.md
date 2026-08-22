# 0014: Transactional persisted replanning use case

- Status: accepted provisionally
- Date: 2026-08-22
- Decision version: `persisted-replanning-use-case@1.0.0`

## Decision

Add an application service that accepts one persisted `BlockReview` identity plus explicit
`ReplanningCandidateContext` inputs. The service follows stored lineage to load the completed
block, prior strategy, priority policy, ordered training responses, selected capability estimates,
competency floors, and adaptations. It invokes the deterministic closed-loop replanner and appends
the resulting capability needs and strategy in one service-owned database transaction.

Expose this use case as `POST /v1/block-reviews/{block_review_id}/replan`. Do not expose raw write
endpoints for capability needs or strategies. Transport validation errors return 422, missing
persisted dependencies return 404, and an already-consumed review returns 409.

One block review may authorize at most one strategy revision. Enforce that invariant in both the
application query and a database uniqueness constraint on `triggering_block_review_id` so
concurrent calls cannot create competing successors.

## Reason

The domain replanner proved the rule behavior, but callers still had to manually load a large
provenance graph and persist its outputs in the correct order. That is easy to misuse and leaves
the first closed-loop API vulnerable to partial writes or raw CRUD shortcuts. A narrow use case
makes the legal workflow the easiest workflow while keeping training logic in the planner.

## Alternatives considered

- Accept every strategy, block, response, estimate, floor, and policy in the HTTP body: rejected
  because persisted identities could be mixed into a forged or stale chain.
- Expose generic CRUD endpoints: rejected because they bypass domain and repository invariants.
- Infer candidate relevance, trainability, transfer, or cost from one response: rejected because
  that would overinterpret limited personal evidence.
- Allow multiple replacement strategies from one review: rejected because it creates ambiguous
  authoritative succession. A later reconsideration requires another explicit review or decision
  boundary.
- Generate the next block in the same request: deferred until revised priorities can be translated
  through explicit stimuli, resolutions, demands, and dose inputs.

## Evidence and uncertainty

This is an application consistency and provenance decision implementing blueprint sections
45–48, 64, 74, and 88–90. It introduces no scientific training claim. Candidate contexts remain
explicit governed inputs and capability estimates must already exist with observation provenance.

The service owns commit/rollback because this endpoint is currently the terminal application
boundary. If later workflows need to compose replanning with other writes, transaction ownership
should move to a higher orchestration unit without weakening atomicity.

## Consequences

- API clients cannot substitute unpersisted domain objects into the review chain.
- Capability needs and strategy revisions are saved together or not at all.
- Duplicate and concurrent revision attempts fail consistently.
- The resulting strategy still does not silently become a block or workout.
