# 0102 — Governed first-session construction authorities

Date: 2026-09-11

Status: accepted as a prepared owner-alpha candidate; not ratified by this change

Decision version: `training-construction-candidate@1.0.0`

## Decision

Introduce a narrow `RepetitionDosePolicy` domain record and prepare one data-loaded,
content-addressed first-session construction bundle. The bundle contains four individually
versioned artifacts:

1. an assessment-calibrated repetition-dose policy for the existing muscular-endurance path;
2. a conservative weekly-scheduling policy and its explicit approval review;
3. a repetition-only progression policy; and
4. a non-diagnostic session-readiness modification policy.

The candidate is one atomic review batch: the planning reviewer submits only its exact version,
digest, and attestation. The backend validates the already-reviewed resistance-training claim and
its source, persists every exact artifact and the scheduling review, and appends one actor-bound
decision record. A conflict leaves the entire bundle unchanged.

The dose policy remains adaptation- and estimate-scope-based rather than exercise-named. It uses a
matching current chair-stand estimate to calculate `floor(estimate × 0.50)`, bounded to 1–8
repetitions, for two bodyweight sets with 90 seconds rest and an RPE 5–7 target. Estimates below one
repetition are ineligible. The first progression policy adds one repetition per set only after full
set and dose completion, reported technique compliance, session RPE no higher than 7, and no
post-session safety interruption.

## Reason

The application already has deterministic scheduling, safety, workout logging, adherence, and
progression engines, but its owner-alpha path has no production authority records that can drive
them. The owner-facing Week 1 editor correctly leaves every value blank, yet asking the owner to
invent dose and policy constants would transfer engineering responsibility to the stakeholder.

A typed dose policy makes the calculation inspectable and historically reproducible before a
prepared Week 1 workflow consumes it. Grouping the four tightly related authorities into one exact
candidate reduces repetitive review work without collapsing their separate domain identities.

## Alternatives considered

- **Prefill the existing Week 1 form without a persisted rule.** Rejected because a convenient
  default would become hidden training authority.
- **Prescribe a fixed repetition count for every athlete.** Rejected because it would ignore the
  actual assessment-derived estimate and could exceed a low performer’s demonstrated capacity.
- **Use the assessment maximum as every training set.** Rejected as an unnecessarily aggressive
  and test-specific first exposure.
- **Claim that the cited position stand validates the exact 0.50 fraction, RPE range, rest,
  scheduling spacing, or progression increment.** Rejected; it does not.
- **Add load, duration, set-count, or impact progression in the first policy.** Deferred because
  only low-complexity repetition progression is needed for this path and broader automation needs
  distinct governance.
- **Let routine concerning-symptom text enter the deterministic policy.** Rejected. The phone UI
  pauses ordinary training before transport because AGAS does not yet classify symptoms or provide
  medical guidance.

## Evidence

The bundle reuses the exact reviewed claim extracted from the 2026 ACSM resistance-training
position stand (PMID 41843416, DOI 10.1249/MSS.0000000000003897). That claim supports the broad
direction that resistance training can improve muscular endurance and function and the general
at-least-twice-weekly recommendation. It does not establish any exact bundle constant.

Every numerical dose, scheduling, modification, and progression value in this candidate is labeled
as a conservative, replaceable engineering prior for the owner-only alpha. Ratification approves
the product interpretation, not a claim that the values were scientifically validated.

## Assumptions and uncertainty

- The policy applies only to the matching governed chair-stand estimate, muscular-endurance
  adaptation, bodyweight prescription, and a currently FULL exercise resolution.
- One to eight repetitions per set is deliberately conservative. It has not been validated as an
  optimal or minimum-effective dose.
- RPE 5–7 deliberately prioritizes first-exposure control over the source’s broad high-effort
  recommendation; response and adherence should inform replacement.
- The scheduling constants matter little for the current low-fatigue single-exercise session but
  fail closed for future high-fatigue or partial-resolution use.
- Readiness modifications are operational safeguards, not medical advice, injury prediction, or a
  substitute for assessment of concerning symptoms.
- A later athlete-specific preparation step must still select the exact estimate, block,
  environment, availability, safety assignment, and session times.

## Consequences

- Dose becomes a versioned domain authority rather than an untracked form value.
- The existing deterministic engines gain a real candidate path without fabricating a workout.
- The owner reviews one understandable construction bundle instead of authoring four policy files.
- Ratification alone still creates no block, week, session, prescription, or permission to train.
- The next milestone can prepare the athlete-specific first block and Week 1 candidate from these
  authorities and current factual availability.
