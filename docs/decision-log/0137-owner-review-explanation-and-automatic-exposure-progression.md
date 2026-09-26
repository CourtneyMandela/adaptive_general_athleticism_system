# 0137 — Owner review explanation and automatic exposure progression

Status: accepted

Date: 2026-09-23

Decision version: `owner-review-and-automatic-exposure-progression@1.0.0`

## Decision

Present the provisional countermovement-jump planning chain as one read-only owner-review summary
while retaining the separate content-addressed floor, resource, and construction approvals. The
summary exposes the 20 centimeter comparison, evidence-supported intervention direction,
24-minute/two-session resource envelope, fixed 3-by-3 starting dose, jump-contact progression
boundary, current candidate statuses, and the distinction between scientific support and
engineering judgment. It creates no new ratification endpoint and cannot approve any candidate.

After a governed exposure-sensitive prescription is performed, allow the existing athlete-facing
progression action to resolve its exposure configuration automatically only when all of the
following are unique:

1. one progression policy matching the immutable prescription reference;
2. one exposure definition matching the prescription exercise, declared exposure type, and exact
   ordered evidence-claim lineage; and
3. one exposure-progression policy matching that exposure type, dose unit, and exact ordered
   evidence-claim lineage.

For a supported repetition adjustment, derive the completed exposure from actual set performance
and propose the next total as `sets × (current repetitions per set + reviewed adjustment)`. Use the
progression decision time as the target time. Persist the derived exposure entry, exposure-cap
validation, progression decision, and optional revised prescription in the existing atomic
transaction. Continue to fail closed for missing, ambiguous, unsupported, or mismatched authority.

Expose the completed dose, exposure type, proposed next dose, configured maximum, and validation
outcome in the current-week projection so the athlete can see that ordinary jump contacts were
recorded and bounded rather than silently inferred.

## Reason

Decision 0136 prepared a complete explosive-power authority chain, but the owner had to reconstruct
its meaning across three distant governance sections. The new explanation improves reviewability
without weakening independent approval or disguising engineering constants as scientific findings.

The ordinary phone workflow could already persist actual performance, but its convenient
progression endpoint deliberately refused every exposure-sensitive policy. The lower-level service
could record exposures only when a caller supplied internal authority identifiers and a target.
That left the owner-alpha jump path unable to close its ordinary session-to-contact-ledger loop.

The repository can now resolve the already reviewed authority from immutable prescription and
provenance links. Exact evidence lineage is part of resolution because the introductory jump
exposure and ordinary explosive-power training intentionally use the same exercise and exposure
type but different dose and progression authorities.

## Alternatives considered

- **Combine the three governance candidates into one approval.** Rejected because floor,
  resource, and construction authority have different meanings, prerequisites, and immutable
  histories.
- **Ask the athlete to select exposure-definition and cap identifiers.** Rejected because those are
  governed system authorities, not athlete-authored workout choices.
- **Choose the newest jumping policy.** Rejected because recency is not provenance and could apply
  the six-contact introductory-assessment cap to ordinary training or vice versa.
- **Resolve only by exercise and exposure type.** Rejected because both owner-alpha jump pathways
  deliberately share those values.
- **Record contacts during session submission without evaluating progression.** Deferred. The
  current atomic progression transaction already derives the exposure from the immutable workout
  observation and prevents duplicate ledger entries. A future design may record exposure before a
  progression decision, but it must preserve idempotency and authority resolution.
- **Let the client submit a proposed contact total.** Rejected for the owner workflow because the
  reviewed typed repetition adjustment and current prescription already determine it.

## Evidence

This decision introduces no new scientific claim or numeric training constant. It operationalizes
the reviewed authorities recorded by decisions 0007, 0019, 0135, and 0136. Oxfeldt et al. (2019),
PMID 31136014, continues to support only the broad plyometric-training direction; it does not
validate the floor, starting contacts, effort, rest, or progression caps.

## Uncertainty

- Exact evidence-claim lineage is a conservative existing provenance discriminator, not a general
  substitute for an explicit authority-bundle identifier. If future governed policies legitimately
  share the same exercise, type, unit, and evidence lineage, automatic resolution will become
  ambiguous and stop until the model gains a stronger explicit link.
- The target time is the progression decision time rather than a future scheduled-session time.
  This is adequate for the current immediate in-week decision, but future delayed scheduling may
  need a separately persisted target date.
- A recorded contact count does not measure force, jump height, asymmetry, landing quality beyond
  the structured technique confirmation, tissue tolerance, or medical safety.
- Personal response calibration still requires reassessment and a reviewed expected-versus-observed
  response comparison.

## Consequences

- The owner can understand the complete provisional jump path on a phone before reviewing the
  separate exact candidates.
- Individual and batch ratifications remain explicit, content-addressed, prerequisite-ordered, and
  non-automatic.
- A completed ordinary jump session can record actual contacts, validate the next total against the
  matching reviewed cap, and create an immutable revision through the existing phone action.
- Current-week history shows the completed contact dose, proposed next dose, and cap.
- Missing or competing definitions and caps remain visible manual-configuration failures rather
  than hidden selection heuristics.
- The next product task is to connect governed explosive-power reassessment to training-response
  comparison and successor-block planning using these real contact and performance observations.
