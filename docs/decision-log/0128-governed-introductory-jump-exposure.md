# Decision 0128: Governed introductory jump exposure

- Date: 2026-09-21
- Status: Accepted
- Decision version: `governed-introductory-jump-exposure@1.0.0`

## Context

The countermovement-jump assessment has a governed recent-exposure prerequisite. When the athlete
reports no qualifying recent jumping exposure, AGAS derives an explicit introductory-exposure need
instead of treating the athlete as cleared for a maximal test. Decision 0126 added the typed policy
and deterministic derivation mechanism, but no ratifiable operational authority existed to satisfy
that need.

The ACSM assessment source defines the target jumping task. It does not establish a universally
safe number of introductory contacts, effort range, rest interval, or progression cap. Those exact
values therefore cannot honestly be labeled scientific findings.

## Decision

Add a data-loaded training-construction candidate that can be ratified in one review pass after the
countermovement-jump assessment evidence is approved. It bundles:

- the existing countermovement-jump exercise record as a jumping exposure measured in repetitions;
- an introductory dose of two sets of three separately reset, easy jump-and-stick repetitions;
- a six-contact maximum initial dose, 90 seconds rest, RPE 2-4, and an eight-minute planned window;
- a progression rule requiring complete technique-compliant work at RPE 4 or below;
- an exposure cap allowing no more than a 25 percent relative or two-contact absolute increase;
- conservative scheduling and non-diagnostic readiness-reduction policies.

The dose policy stores no evidence claim IDs and labels `numeric_value_origin` as
`engineering_judgment`. The bundled assessment claim supports only the target-task and exposure
definition. Candidate presentation text explicitly lists every unsupported numeric choice.

The existing construction-candidate loader and ratification path now accepts exactly one of a
capability-estimate repetition policy or an introductory-exposure policy. Exposure-specific
definition and progression artifacts are optional for older releases and persisted atomically when
present. This preserves the previously ratified chair-stand and push-up releases without creating a
second hidden candidate mechanism.

## Alternatives considered

- **Run the maximal jump assessment without prior exposure.** Rejected because it would bypass the
  governed prerequisite and conflate missing history with readiness.
- **Claim a published universal starting dose.** Rejected because the reviewed assessment source
  does not establish one and population studies do not guarantee individual tissue readiness.
- **Ask the owner to choose contacts, rest, and progression values.** Rejected because these are
  technical product decisions that should be explicit, inspectable, and replaceable.
- **Use continuous rebound jumps.** Rejected for the first exposure because separate resets make
  each contact easier to observe and reduce pressure to maintain reactive rhythm.
- **Build a separate exposure-candidate subsystem.** Rejected because the existing atomic
  construction release already provides digest, attestation, persistence, and review semantics.

## Consequences

- The review queue can expose one honest, bounded authority for the missing jump-exposure step.
- Ratification still does not schedule a session or authorize exercise; current readiness,
  athlete-specific derivation, planning review, and execution logging remain required.
- Completion of one introductory exposure does not automatically establish readiness for maximal
  jumping. The recent-exposure rule must recompute from the recorded observation history.
- Exact dose and progression constants must be recalibrated from observed response or superseded by
  better evidence; they are deliberately not disguised as ACSM recommendations.
