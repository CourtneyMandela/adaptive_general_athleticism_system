# Decision 0049: Reviewed weekly-scheduling policies

- Date: 2026-08-28
- Decision version: `weekly-scheduling-policy-review@1.0.0`
- Status: accepted

## Decision

Treat a persisted `WeeklySchedulingPolicy` as a versioned policy proposal, not as permission to use
it. Add an immutable `WeeklySchedulingPolicyReview` chain containing the decision, ordered evidence
claims, review time and reviewer, applicability rationale, uncertainty, and review-rule version.

Operator-authored first weeks must name both the policy and its exact current approved review. The
server rejects missing, withdrawn, superseded, future-dated, or mismatched reviews. Athlete-requested
weekly roll-forward accepts neither identifier: it inherits the source plan's exact policy and review
and confirms that the review remains the current approval before creating another week.

New weekly plans retain `scheduling_policy_review_id`. The database column is nullable only so plans
created before this governance boundary remain readable with explicitly unknown review provenance;
all production creation paths introduced by this decision require a review identifier.

The existing operator-only planning-governance command gains a scheduling-policy review operation.
The athlete-facing API gains no policy administration or selection surface.

## Reason

Scheduling limits affect fatigue spacing, daily session density, and whether partial exercise
resolution is allowed. Database existence and a version string establish identity, but do not show
that qualified review approved the rule for use. Preserving the exact approval alongside each plan
makes the scheduling decision reproducible and prevents a later withdrawal from silently authorizing
new weeks.

## Alternatives considered

- Treat every persisted scheduling policy as approved. Rejected because persistence is not review.
- Add a mutable `approved` flag to the policy. Rejected because withdrawal would erase approval
  history and the exact authority used by prior plans.
- Select the newest approved policy globally. Rejected because recency is not an applicability or
  supersession rule.
- Let the PWA submit a review identifier during roll-forward. Rejected because policy authority is
  not an athlete preference and the source plan already carries the governing lineage.
- Introduce one generic review table for every policy family now. Deferred because cross-type
  referential integrity would be weaker and the other policy families need separate applicability
  decisions before their semantics are generalized.

## Evidence

This is an architecture and provenance decision, not a scientific training claim. A review must link
to persisted `EvidenceClaim` records, but this milestone does not fabricate or approve any scheduling
rule or scientific evidence.

## Assumptions

- `approved`, `needs_revision`, and `rejected` retain the existing governed-review meanings.
- A later review supersedes the immediately previous review for the same policy; only the database-
  current review can authorize a new week.
- A future-dated current review cannot authorize planning at an earlier preparation time.
- Existing plans without a review ID are historical pre-governance records and cannot be rolled
  forward through the governed boundary.

## Unresolved questions

- Which populations and operating contexts require distinct scheduling policies.
- Qualified-reviewer identity, credentials, authorization, and electronic-signature requirements.
- Review expiry intervals and proactive athlete notification when a policy is withdrawn.
- Governance models for resolver, resource-allocation, progression, exposure, block-review, and
  safety-policy content.

## Consequences

- New first-week and roll-forward plans are traceable to an exact current approval.
- Withdrawing a scheduling policy preserves prior plans but blocks new weeks under that policy.
- Roll-forward may require operator intervention after a policy review changes; the system will not
  silently substitute another policy.
- Historical null review provenance remains visible rather than being backfilled with an invented
  approval.
