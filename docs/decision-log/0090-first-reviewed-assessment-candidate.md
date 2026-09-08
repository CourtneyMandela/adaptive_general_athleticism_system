# 0090 — First reviewed assessment candidate

Date: 2026-09-08

Status: accepted as a prepared owner-alpha candidate; not ratified by this change

Decision version: `assessment-governance-candidate@1.0.0`

## Decision

Ship one server-owned, immutable candidate for the 30-second chair stand. Present its meaning,
non-meaning, exact setup and procedure, stop conditions, operational choices, primary evidence,
conflicts, and unresolved limitations in the assessment-governance workbench. The owner can either
leave it pending or explicitly approve the exact content digest. The browser cannot edit or author
the scientific records.

Candidate ratification supplies only the candidate version, exact digest, and a true approval
attestation. The server resolves the known content, supplies the ratification time, binds the
authenticated assessment-reviewer account and current role assignment, and uses the existing
atomic release service. Exact retries return the original authority record. A changed digest fails
closed and requires the candidate to be reviewed again.

The release includes a specific stable armless-chair equipment definition in the same transaction.
The assessment requires the `chair` category, so a later athlete selection remains excluded until
the athlete reports that exact equipment available in the selected environment. Protocol approval
still does not establish athlete eligibility.

Interpret the result only as an assessment-specific count in the `muscular_endurance` domain. The
initial estimation policy preserves the direct repetition count, gives one observation low
confidence, uses no norms, and authorizes no conversion to maximum strength, power, sport
performance, injury risk, a universal athleticism score, or a training prescription.

## Scientific basis

- Lein et al. (2022), PMID 35949374, studied 81 healthy adults aged 19–35. Chair-stand count was
  associated with five-times sit-to-stand time and lateral step-up performance. This was a single
  cross-sectional, investigator-administered, two-trial study and did not establish sport
  performance prediction.
- Dahlberg et al. (2025), PMID 40330808, directly studied digital self-administration. Test-retest
  ICC was 0.88 in 54 older adults with hip or knee osteoarthritis. In a separate 18-person
  comparison, self-reported counts averaged 1.5 repetitions above physiotherapist counts. The
  population, sample size, wide inter-rater interval, prior app familiarity, and disclosed author
  relationships materially limit transfer.

Both extracted claims are graded low strength and low athlete applicability. The candidate does not
use the young-adult reference mean or create normative categories.

## Protocol choices

- Require a stable straight-backed armless chair with a firm 43–45 cm (17 inch) seat, secured
  against a wall on a nonslip surface.
- Use a 10-second familiarization, at least 60 seconds seated rest, then one recorded 30-second
  trial. This is a conservative AGAS operational adaptation, not an exact reproduction of either
  paper.
- Count controlled full stand-and-sit repetitions without arm assistance. A stopped or changed-
  setup attempt is not entered as completed.
- Set a provisional 28-day reassessment interval and estimate validity window. This is a cautious
  product choice intended to limit practice-heavy retesting, not a validated optimal cadence.
- Require the separate athlete-specific eligibility authority and display conservative stop
  conditions; do not treat candidate approval as medical clearance.

## Alternatives considered

- **Two-minute step test.** Deferred. It reduces chair dependency, but the current evidence review
  did not find a stronger direct self-administered protocol basis for this first slice.
- **Use a generic `support` equipment category.** Rejected because a squat rack or other support
  would falsely satisfy a chair-specific setup.
- **Treat a chair as untracked prose.** Rejected because environment constraints must affect
  selection rather than relying on an instruction the planner cannot enforce.
- **Automatically approve the candidate during deployment.** Rejected because deployment is not a
  human authority decision.
- **Ask the owner to author JSON or scientific fields.** Rejected because engineering and evidence
  synthesis belong to the agent workflow; the stakeholder reviews the resulting decision.
- **Convert the count to a reference percentile or strength rating.** Rejected because the evidence
  does not justify a universal interpretation for this athlete.

## Assumptions

- An owner-alpha reviewer may deliberately ratify a transparent candidate while the system records
  that application access is not proof of scientific or clinical qualification.
- A within-person assessment-specific count is useful enough to unlock measured-state plumbing even
  when population transfer is weak, provided the weakness remains visible and no norms are used.
- The athlete can accurately report whether the specified chair is available in an environment.

## Unresolved questions

- Independent domain-expert or clinician review has not occurred.
- Reliability and validity of this exact one-recorded-trial protocol in the current athlete are
  unknown.
- The optimal familiarization and reassessment schedule are not established.
- The current eligibility workflow still needs an owner-appropriate, evidence-aware review
  experience before the athlete can run the test.
- Additional domains require separate evidence and protocol candidates; this test does not stand in
  for a complete athletic assessment.

## Consequences

- The owner sees a concrete, understandable choice instead of an empty governance console or raw
  scientific payload.
- Approval creates evidence sources, claims, evidence reviews, chair ontology, protocol review,
  estimation policy, and decision audit atomically.
- The app moves closer to a first measurement without generating a workout or weakening the
  evidence, environment, eligibility, or safety gates.
