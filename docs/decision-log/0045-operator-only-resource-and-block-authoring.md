# 0045 — Operator-only resource-demand and block authoring

- Status: accepted provisionally
- Date: 2026-08-28
- Supersedes: the athlete-accessible transport choices in Decisions 0015 and 0016
- Decision version: `operator-only-resource-and-block-authoring@1.0.0`

## Decision

Keep `PersistedResourcePreparationService` and `PersistedBlockCreationService` as the deterministic,
transactional application boundaries for strategy-to-block planning, but remove their
athlete-authenticated HTTP write routes.

Require active and deferred resource-demand commands and block-creation commands to include a
non-empty reviewer, applicability rationale, and uncertainty statement. Resource-demand creation
must append its stimulus requirement, exercise resolution when active, resource demand, and one
`DecisionRecord` atomically. Block creation must append its block and one `DecisionRecord`
atomically. Each audit record cites the exact strategy and priority lineage, observations, evidence,
policies, environment/candidate/resolution records where applicable, explicit resource choices,
and created result identities.

Expose both boundaries through a local operator CLI with separate `prepare-demand` and
`create-block` commands that each consume one reviewed JSON file. The PWA remains a read-only
readiness projection at these expert planning boundaries.

## Reason

Stimulus selection, exercise candidacy, substitution policy, minimum and target resource amounts,
session frequency, allocation policy, block budget, dates, duration, and constraints materially
shape training. Athlete ownership proves which records a user may see; it does not authorize the
user to act as the scientific or planning reviewer for those values.

The existing services already prevent partial persistence and delegate only to deterministic,
versioned engines. Adding review metadata, transactional audits, and a truthful operator transport
closes the authorization gap without inventing a generic planner or duplicating domain logic.

## Alternatives considered

- Leave the routes public because the current PWA does not render them. Rejected because hidden UI
  fields are not authorization controls.
- Add a development administrator token. Rejected because it would create an ad hoc production-like
  security boundary without verified administrative identities or roles.
- Automatically derive stimuli, candidate exercises, doses, or block budgets. Rejected because the
  repository has no reviewed policies that authorize those inferences.
- Merge resource preparation, block creation, and Week 1 creation into one command. Rejected because
  each boundary has independent inputs, can produce meaningful infeasibility, and should remain
  inspectable.
- Reject infeasible exercise resolution rather than recording it. Rejected because infeasibility is
  an authoritative planning outcome that downstream readiness must preserve.

## Evidence and uncertainty

This is an authorization and provenance decision implementing blueprint sections 11–13, 16,
33–35, 52, 60, 64, 71–73, and 89. It introduces no scientific stimulus, dose, exercise-equivalence,
or periodization claim. The operator remains responsible for the quality and applicability of each
submitted scientific and athlete-context input.

## Assumptions and unresolved questions

- The generic immutable `DecisionRecord` is sufficient for this provisional workflow; typed
  identifier prefixes preserve inspectable lineage until dedicated review aggregates are needed.
- Existing immutable resolver and allocation policies are pinned by identity but do not yet have
  their own approval/supersession histories.
- Multiple historical demands and multiple blocks remain legal. Exact selection is explicit, while
  the athlete readiness projection continues to report ambiguity rather than choosing by recency.
- Local CLI access is development administration, not production reviewer authentication.
- Administrative roles, separation of author and approver, policy review histories, and draft
  supersession remain required before an operator web interface is appropriate.

## Consequences

- Athlete clients can no longer submit expert stimulus, exercise-resolution, dose-resource, or
  block-allocation choices.
- Every supported strategy-to-block write has an atomic reviewer-attributed audit trail.
- Existing deterministic infeasibility and anti-equivalence behavior remains unchanged.
- The planning-status PWA can continue showing exact readiness without gaining a workout-generator
  control.
