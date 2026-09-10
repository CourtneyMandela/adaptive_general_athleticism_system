# 0095 — Deficit-only initial priority policy

Date: 2026-09-10

Status: accepted as a prepared owner-alpha candidate; not ratified by this change

Decision version: `owner-alpha-deficit-only-priority@1.0.0`

## Decision

Prepare a second, narrower priority-policy candidate for the first owner-alpha strategy. The policy
uses only the normalized difference between an exact current capability estimate and its reviewed,
compatible competency floor. Estimate confidence still discounts that signal. General relevance,
goal relevance, prerequisite value, expected trainability, transfer, fatigue, time, and interference
receive zero policy weight because AGAS does not yet possess governed athlete-specific inputs for
those values.

A nonzero normalized deficit with known confidence may cross a `0.01` DEVELOP threshold, and at most
one adaptation may receive DEVELOP status. The threshold is an engineering guard against zero and
floating-point noise, not a clinically meaningful difference. Unknown-confidence state receives no
benefit and cannot cross the threshold. Current safety, prerequisite, and introductory-exposure flags
remain separate hard gates.

The prior multi-factor candidate remains immutable and available for audit. This release uses new
policy, review, claim, and decision identities, so an already ratified earlier policy is never edited
in place.

## Reason

The earlier policy made deficit the strongest of six benefit signals but still required a reviewer
to supply five unsupported benefit numbers and three cost numbers. A low-confidence first estimate
could also fail to reach DEVELOP even when every unsupported input was omitted. Asking the owner to
invent those values would weaken the provenance system and would not improve the eventual product.

The narrower policy lets the next athlete-context workflow state unavailable values explicitly as
unused. Richer policies can supersede this operational role after structured goals, adaptation
relationships, stimulus-specific resource costs, and personal response data exist.

## Evidence

The candidate retains the 2026 ACSM resistance-training position stand (PMID 41843416) and extracts a
narrow claim that progressive resistance training improved muscular endurance among the overview's
reported outcomes. That evidence supports population-level trainability directionally. It does not
validate the chair-stand floor, `0.01` threshold, athlete-specific response, exercise, or dose.

## Alternatives considered

- **Fill all eight context scores with neutral or optimistic constants.** Rejected because a number
  such as `0.5` still asserts a magnitude without a governed basis and materially changes ranking.
- **Treat missing scores as zero under the earlier nonzero weights.** Rejected because zero would be
  interpreted as negative evidence and the confidence discount would usually suppress the actual
  measured deficit.
- **Remove confidence discounting.** Rejected because the first self-administered estimate is
  intentionally low confidence and that uncertainty should remain visible in ranking.
- **Make costs an adaptation-level constant.** Rejected because fatigue, time, and interference
  depend materially on the later stimulus, exercise, dose, and schedule.
- **Replace the earlier immutable policy.** Rejected because accepted authority history must not be
  rewritten.

## Assumptions and provisional choices

- The policy is limited by review text and workflow to the single-owner initial-planning slice; the
  current `PriorityPolicy` model does not yet encode a machine-readable domain scope.
- One development slot is appropriate while only one evidence-ready capability path exists.
- Integer chair-stand counts make `0.01` safely smaller than the minimum one-repetition normalized
  deficit for the current floor, but future domains must not reuse that interpretation blindly.
- Goal and recovery tradeoffs are deferred, not deemed irrelevant.

## Unresolved questions

- Should a later policy applicability model enforce allowed domains, estimate scopes, and planning
  phases at runtime?
- What provenance structure should accompany each future nonzero contextual judgment?
- Which personal-response observations should trigger recalibration or replacement of this policy?

## Consequences

- The owner can review a policy that uses only information AGAS actually has.
- Existing policy history remains append-only.
- Ratification still does not create athlete context or a strategy.
- The next coherent milestone is a server-prepared athlete-specific context that uses this exact
  policy, preserves the unused fields as explicit zeros, and refuses to infer medical clearance.
