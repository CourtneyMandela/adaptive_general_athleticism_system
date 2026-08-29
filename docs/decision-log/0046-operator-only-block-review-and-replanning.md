# 0046 — Operator-only block review and replanning

- Status: accepted provisionally
- Date: 2026-08-28
- Supersedes: the athlete-accessible transport choices in Decisions 0014 and 0020
- Decision version: `operator-only-block-review-and-replanning@1.0.0`

## Decision

Keep `PersistedBlockReviewService` and `PersistedReplanningService` as the deterministic,
transactional application boundaries for closing a completed block and deriving its successor
strategy, but remove their athlete-authenticated HTTP write routes.

Require both commands to include a non-empty reviewer, applicability rationale, and uncertainty
statement. Completed-block review must append its derived `TrainingResponse` records,
`BlockReview`, and one `DecisionRecord` atomically. Replanning must append its new
`CapabilityNeed` records, successor `LongRangeStrategy`, and one `DecisionRecord` atomically. The
audits must identify the exact policy, thresholds, observations, estimates, delivered history,
review lineage, candidate contexts, evidence, and created records used at each boundary.

Expose both boundaries through one local operator CLI with `review-block` and `replan` commands,
each consuming an explicit reviewed JSON file. The athlete PWA remains read-only for post-block
interpretation and long-range strategy revision.

## Reason

Grouping performed prescriptions into adaptation responses and describing measurement uncertainty
require expert review. Comparison direction and minimum meaningful change are scientific
interpretation inputs, not athlete preferences. Replanning candidate relevance, trainability,
transfer, cost, prerequisite, safety, and comparative-advantage values materially determine the
next strategy. Athlete ownership authorizes access to the athlete aggregate; it does not establish
authority to approve those inputs.

The existing services already reconstruct immutable execution history, reject incomplete or
inconsistent chains, and delegate calculations to versioned engines. Adding reviewer attribution,
transactional audits, and a truthful operator transport closes the authorization gap without
inventing response thresholds, scoring policies, or generic programming logic.

## Alternatives considered

- Leave the routes authenticated because only the owning athlete can call them. Rejected because
  aggregate ownership is not scientific-review authority.
- Infer meaningful-change thresholds from raw measurement units. Rejected because no reviewed
  metric-specific threshold catalog exists.
- Derive replanning scores directly from one block outcome. Rejected because a single response
  cannot establish broad relevance, safety, recovery cost, or long-term transfer.
- Prevent an inconclusive or unsupported review from triggering any replanning. Rejected because
  an independently valid follow-up estimate may still change current athlete state; the successor
  audit must preserve that uncertainty instead of asserting causality.
- Add provisional administrator HTTP authentication. Rejected until production administrative
  identities, roles, and approval responsibilities are designed.

## Evidence and uncertainty

This is an authorization and provenance decision implementing blueprint sections 45–48, 52, 60,
64, 71–73, 83–84, and 89. It introduces no scientific meaningful-change threshold, causal claim,
response-profile inference, or replanning score. The operator remains responsible for the quality
and applicability of the supplied interpretations.

## Assumptions and unresolved questions

- `DecisionRecord` plus typed identifiers is sufficient provisional audit storage; dedicated typed
  review aggregates may be warranted when an operator interface is designed.
- `BlockReviewPolicy` and `PriorityPolicy` are versioned and evidence-linked, but block-review
  policy approval history is not yet modeled and successor replanning currently reuses the exact
  priority policy from the prior strategy.
- A completed review remains descriptive. It does not overwrite observations, estimates,
  prescriptions, or the prior strategy.
- Local CLI access is development administration, not production reviewer authentication.
- Separation of author and approver, reviewer qualifications, threshold catalogs, and policy
  supersession remain unresolved production requirements.

## Consequences

- Athlete clients can no longer submit response interpretations or successor-strategy scores.
- Every supported completed-block review and replanning write has an atomic reviewer-attributed
  decision trail.
- The immutable strategy chain and the distinction between observed change and causal attribution
  remain intact.
- The PWA can display future post-block status without becoming an ungoverned training-model editor.
