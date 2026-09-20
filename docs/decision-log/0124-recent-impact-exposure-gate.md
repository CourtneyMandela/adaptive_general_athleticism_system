# 0124 - Recent impact-exposure gate for maximal jump assessment

Date: 2026-09-20

Status: accepted

Decision version: `recent-impact-exposure-gate@1.0.0`

## Decision

Revise the prepared countermovement-jump protocol to version 1.1 before athlete ratification. A
current readiness report must now confirm both:

- one comfortable low-effort two-foot jump and controlled landing; and
- intentional two-foot jumping and controlled landing on at least two separate days during the
  preceding 28 days.

Missing, negative, or uncertain recent-exposure answers create the explicit screening flag
`recent_jump_exposure_not_confirmed`. The countermovement-jump assessment declares that flag as a
blocker. Unrelated assessments do not.

Bump the owner readiness rule to `assessment-readiness-screen@1.3.0` so earlier reports remain
historical but cannot silently authorize the expanded assessment meaning.

The two-days-in-28-days boundary is an explicitly provisional engineering safety rule. It is not
presented as a validated injury-prevention threshold, medical clearance, proof of tissue readiness,
or a scientific optimum.

## Reason

The previous candidate required a recent moderate-activity base and one controlled low-effort jump.
That does not establish recent impact exposure. A maximal best-of-three jump assessment can be a
large intensity change for someone who has not jumped recently, even when their cardiovascular
fitness is adequate. The repository rules explicitly require exposure history to remain separate
from general fitness.

The gate is intentionally factual and narrow. It prevents one practice repetition from being
treated as an impact-training history while avoiding a diagnosis or unsupported readiness score.

## Alternatives considered

- **Treat general moderate activity as sufficient.** Rejected because cardiovascular activity does
  not establish recent jump or landing exposure.
- **Use the single practice jump as the entire gate.** Rejected because immediate movement control
  and recent repeated exposure answer different questions.
- **Require a source-derived universal volume threshold.** Rejected because the reviewed literature
  does not validate one initial safe dose across ordinary adults.
- **Block every assessment when recent jumping is absent.** Rejected because the constraint is
  specific to the maximal jump assessment.
- **Record arbitrary free-text exposure tags.** Rejected as the safety authority because their
  meaning and time window are not stable enough for a deterministic gate.

## Evidence and uncertainty

Systematic reviews support that multiweek plyometric training can improve jump performance in
healthy adults, but they do not validate this product's two-days-in-28-days assessment gate. The
published training protocols are heterogeneous, and performance-oriented dose comparisons should
not be laundered into an initial safety threshold.

Reviewed context:

- Oxfeldt et al. (2019), PMID 31136014, DOI 10.1111/sms.13487: systematic review and
  meta-analyses of lower-body plyometric interventions lasting at least four weeks in healthy
  adults. This supports trainability of jump performance, not the current readiness boundary.
- Ramirez-Campillo et al. (2023), PMCID PMC10457889: systematic scoping review of plyometric-jump
  exercise prescription variables and reporting gaps. This supports retaining explicit uncertainty
  around exercise type, dose, progression, surface, and rest rather than asserting one universal
  introductory prescription.

The rule therefore remains conservative, replaceable, versioned, and visibly described as an
engineering boundary. Future observed athlete history or stronger applicable evidence may support
a different window or minimum exposure definition.

## Consequences

- The phone readiness form asks one additional plain-language exposure question.
- A user without recent jump practice may still complete unrelated governed assessments.
- The maximal jump assessment remains unavailable until both current movement control and recent
  exposure are confirmed.
- A later introductory jump-exposure pathway can build exposure deliberately before maximal
  reassessment rather than bypassing this gate.
