# 0120 - Scope-matched push-up training path

Date: 2026-09-17

Status: accepted

Decision version: `owner-alpha-pushup-training-path@1.0.0`

## Decision

Retain the historical chair resource and construction releases unchanged, and add separate
content-addressed standard-push-up releases. Candidate endpoints now expose both releases and their
existing digest-only ratification boundaries. Downstream resource-demand, block, dose, and first-
week preparation select an authority from the exact `CapabilityEstimate.estimate_scope`; there is
no fallback from a push-up estimate to chair sit-to-stand.

The push-up resource release creates no equipment record. It creates a structured standard-push-up
exercise, an exact-match resolver, and a single-active-priority allocator whose DEVELOP and
MAINTAIN weights are both one. A matching push-up construction release defines two sets at 40% of
the current exact estimate, rounded down and bounded to 1–10 repetitions, 120 seconds rest, RPE
5–7, a six-minute session duration, conservative scheduling, one-repetition progression, and the
existing vocabulary of non-diagnostic readiness reductions.

The push-up resource envelope reserves twelve weekly minutes across two six-minute slots so the
persisted block allocation and the separately governed session duration agree exactly. All values
are explicit engineering priors. The ACSM position stand supports only broad resistance-training
direction, muscular-endurance benefit, and at-least-twice-weekly frequency.

## Reason

The owner-relevant assessment and floor could already produce a standard-push-up estimate, but the
remaining path still assumed one chair-specific DEVELOP priority. That meant a result meeting the
provisional floor could not become training, and any naive fallback risked prescribing sit-to-
stands from an upper-body assessment. Scope-matched authority selection closes that lineage gap
without weakening evidence or safety boundaries.

MAINTAIN is deliberately trainable. Meeting a conservative competency floor means that the system
has not identified a deficit relative to that floor; it does not establish that exposure should
drop to zero or that the capability is permanently secured.

## Alternatives considered

- **Change the deficit-only strategy so every result becomes DEVELOP.** Rejected because it would
  falsify the meaning of the floor comparison and priority state.
- **Reuse the chair exercise and dose as a generic muscular-endurance workout.** Rejected because
  the exercise, environment, and estimate scopes are materially different.
- **Mutate the ratified chair artifacts into push-up artifacts.** Rejected because immutable
  history and existing digests must remain valid.
- **Treat floor space as equipment.** Rejected because floor area is an environmental constraint,
  while the standard push-up has no equipment requirement.
- **Attribute the exact dose to ACSM.** Rejected because the reviewed source does not validate the
  exercise choice or operational constants.

## Assumptions and unresolved questions

- The owner must still ratify the exact push-up resource and construction releases before they are
  operational.
- The 40% starting fraction and other constants are deliberately conservative but have no personal
  response calibration yet.
- The current session is assessment-proximal and is not a complete general-athleticism program.
- Wrist, elbow, shoulder, trunk-control, pain, and same-day readiness remain separate gates; a FULL
  resolver result is not safety clearance.
- Longitudinal session response should eventually supersede the provisional dose with a personal-
  calibration authority.

## Consequences

- A 15-repetition estimate against the provisional 10-repetition floor can remain MAINTAIN and
  still produce a no-equipment resource demand, full block allocation, six-repetition-per-set
  first dose, and scheduled Week 1 with exact provenance.
- Candidate batching remains efficient: all currently available resource and construction
  releases can be ratified in the existing cross-group review flow.
- The phone-facing workflow still requires assessment completion, authority ratification, block
  acceptance, availability, and current pre-session safety checks before training.
- Future capability paths can use the same scope registry pattern, but each still needs its own
  reviewed exercise and construction content rather than a generic workout fallback.
