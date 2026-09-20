# 0123 - Countermovement-jump assessment without normative overreach

Date: 2026-09-20

Status: accepted

Decision version: `countermovement-jump-assessment@1.0.0`

## Decision

Prepare a third immutable assessment-governance candidate for a wall-marked countermovement
vertical jump. The assessment records the best valid jump-height difference across three trials to
the nearest 0.5 centimeter and derives only a low-confidence, 28-day, assessment-specific
explosive-power estimate using the existing latest-matching-observation method.

Use ACSM's *Guidelines for Exercise Testing and Prescription*, 12th edition, ISBN 9781975219246,
Chapter 3, Box 3.11 and Table 3.12 for the protocol and descriptive-reference context. Preserve this
as the second immutable retrieval snapshot in the ISBN's source lineage rather than modifying the
earlier push-up snapshot. Also preserve Payne et al., *Canadian musculoskeletal fitness norms*,
PMID 11098155 and DOI 10.1139/h00-028, as the primary source identified for the reference
population.

Do not activate the source table's age/sex categories and do not convert them into a competency
floor. The release records the reference population and its mismatch explicitly: the sample spans
the athlete's age range but is not established as recreationally trained, construction-working, or
otherwise equivalent to the owner-alpha athlete.

Model the wall, marking method, centimeter measurement, clear overhead space, and nonslip landing
surface as one `vertical_jump_measurement_setup` equipment category. Selection must defer when the
active environment does not report that setup as available.

Expand the current athlete readiness report with a factual controlled two-foot jump-and-landing
pre-check and bump its rule to `assessment-readiness-screen@1.2.0`. Missing, negative, or uncertain
answers produce `controlled_jump_landing_not_confirmed`, which excludes only assessment definitions
that declare that flag. The existing lower-body/balance concern also blocks this jump assessment.

## Reason

The product needs useful measurements beyond muscular endurance before it can support broad general
athleticism. A countermovement jump is a practical low-equipment field assessment for explosive
performance, and the supplied ACSM source gives a concrete repeatable procedure. It also provides a
useful test of a core AGAS invariant: descriptive population norms may inform review without being
silently promoted into athlete truth, a universal floor, or a workout prescription.

The readiness and environment additions make the measurement honestly conditional. A jump is a
high-effort impact task, and a result from an unavailable or uncontrolled setup would be less useful
than no result.

## Alternatives considered

- **Activate the age-30-to-39 source category as a floor.** Rejected because a descriptive norm is
  not a validated minimum for this athlete's goals, safety, or training decisions.
- **Estimate mechanical power from jump height.** Rejected because body mass and a reviewed
  calculation model would be required, and the inexpensive wall method directly observes height,
  not force or velocity.
- **Treat the wall and tape as informal instructions only.** Rejected because environmental
  availability is a first-class constraint and the selection engine can already defer honestly.
- **Reuse the chair-stand movement pre-check.** Rejected because a controlled chair stand does not
  establish comfort with takeoff, impact, or two-foot landing.
- **Require a force platform or commercial jump device.** Deferred because that would make the
  owner-alpha path less accessible without eliminating the need to govern protocol and
  interpretation.

## Assumptions and unresolved questions

- The ACSM textbook is authoritative for the procedure it prints. Its cited validation literature
  has not been independently appraised for this release, so evidence strength remains low.
- Wall marking can be self-administered but may introduce reach, parallax, fingertip-mark, and
  observer errors. A validated device-specific protocol may later supersede this one.
- The warm-up, practice jump, controlled-landing rule, 0.5-centimeter resolution, and 28-day
  interval are conservative AGAS operating choices, not source-derived biological thresholds.
- This assessment does not yet affect a training priority or exercise dose. A separately governed
  competency interpretation and planning path must cite this exact estimate scope before doing so.
- Ratification still requires the existing authenticated assessment-reviewer attestation.

## Consequences

- The review queue can present a complete evidence-to-protocol-to-estimate candidate for explosive
  power alongside the existing chair-stand and push-up candidates.
- Approval can add the measurement setup to the equipment catalog without modifying athlete
  identity; each environment reports its own time-bounded availability.
- Existing readiness reports remain historical but owner-readiness versions before 1.2.0 cannot
  authorize the expanded assessment set.
- Tests cover candidate meaning, textbook-source lineage in either ratification order, equipment
  requirements, measurement resolution, readiness provenance, and movement-specific exclusion.
