# 0125 - Derived exposure needs are separate from capability deficits

Date: 2026-09-20

Status: accepted

Decision version: `derived-exposure-needs@1.0.0`

## Decision

Add an immutable `ExposureNeed` domain record for a narrow exposure-dependent target. It records
the exposure type, target scope, configured lookback and minimum exposure days, status, exact source
observations, confidence, validity, rationale, uncertainty, engineering-authority reference, and
rule version. Its fixed `kind=derived` prevents it from masquerading as a direct measurement.

The owner readiness workflow now derives one jumping need for the maximal countermovement-jump
assessment from the exact readiness observation. A yes answer produces
`recent_exposure_confirmed`, a no answer produces `introductory_exposure_needed`, and an unsure or
missing answer produces `unknown`. The record is persisted atomically with the source observation
and eligibility review. A deterministic identifier makes an exact replay idempotent.

This record does not enter the competency-floor deficit score. It is the first structured bridge
for a later EXPOSE pathway whose purpose is to earn a prerequisite safely, not to claim that the
athlete is weak or below a population norm.

## Reason

The countermovement-jump assessment correctly blocks an athlete who lacks recent jump-and-landing
exposure, but the prior model had no way to represent what the system owed that athlete next.
Forcing the state through a jump-height floor would confuse performance with exposure history. It
would also encourage an unsupported numeric norm merely to unlock planning.

## Alternatives considered

- **Use a jump-height competency floor.** Rejected because no jump has been performed and recent
  exposure is a different fact from jump performance.
- **Treat the readiness flag as a capability estimate.** Rejected because a categorical self-report
  is neither a measured nor calculated physical capability.
- **Keep the flag only inside assessment selection.** Rejected because downstream planning would
  have no durable, traceable need to satisfy.
- **Immediately create a workout from the no answer.** Rejected because exercise resolution,
  introductory dose authority, scheduling, and session safety remain separate governed stages.
- **Require a scientific evidence claim for the two-day boundary.** Rejected because no reviewed
  source establishes that value as a universal safety threshold. The record instead names the
  explicit engineering decision that owns the provisional boundary.

## Evidence

This is an architectural and conservative engineering decision, not a scientific claim about a
validated safe dose. Decision 0124 records the broader evidence review and its limits. The new
record preserves that distinction through `authority_reference` and `uncertainty` rather than
attaching a citation that does not support the number.

## Assumptions and uncertainty

- The current self-report confirms only whether the configured prerequisite was reported as met;
  it does not count contacts or sessions independently.
- The exposure state shares the readiness report's 24-hour validity. Historical records remain
  available after expiry.
- `recent_exposure_confirmed` authorizes nothing by itself. Global readiness, movement checks,
  current protocol authority, environment, and session safety remain independent.
- The two-days-in-28-days boundary remains replaceable engineering judgment.

## Consequences

- The database can preserve exposure needs without inventing capability deficits.
- The phone receives a plain next action specific to maximal jump assessment readiness.
- A later governed introductory-exposure dose policy can cite this need and close the gap through
  an EXPOSE plan.
- The present change still does not prescribe a jump exercise or dose.

