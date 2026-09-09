# Safety Policy

## Boundary

AGAS is a training-planning product for generally healthy adults. It is not a diagnostic, rehabilitation, medical-triage, or injury-prediction system and must not promise injury prevention.

## Deterministic precedence

Safety validation executes before LLM discretion and ordinary planning. The LLM cannot override a hard safety outcome.

## Assessment boundary

An assessment protocol must have a current evidence-linked approval before it can enter persisted
athlete selection. Approval records exact instructions, applicability, uncertainty, and whether
self-administration was reviewed; it is not a medical clearance or a substitute for athlete-level
screening. Unreviewed or withdrawn definitions fail closed, and intake must not
infer health, injury, or symptom classifications from free text.

Assessment selection additionally requires a current, time-bounded eligibility review linked to
the observations and exact process used. In the owner alpha, a deterministic current-state rule
accepts only grouped factual answers, treats “yes” and “unsure” conservatively, expires after 24
hours, and caps selection at moderate intensity. The athlete cannot submit an outcome or intensity
ceiling. Allowed, blocked, and review-required outcomes are preserved as append-only history. This
authority controls selection only; it is not a diagnosis or medical clearance. The ordinary
athlete-facing assessment-run request contains no health,
injury, symptom, or raw screening fields and cannot override its eligibility or persisted equipment
state.

Result recording is allowed only for a selected decision while its exact self-administered protocol
approval and athlete eligibility remain current and active. It rejects future performance times,
deferred decisions, missing or invalid reviewed measurement schemas, values outside the reviewed
contract, unit mismatches, and duplicates without retaining partial observations. Browser controls
do not replace server enforcement. The result is historical reported evidence, not a safety
decision, diagnosis, medical clearance, or capability estimate.

Capability interpretation remains a separate action and requires a current evidence-linked policy
for the exact current protocol review. It cannot admit manual same-type observations, accept a
browser-supplied formula, or reinterpret a withdrawn protocol. Its output remains a bounded,
protocol-specific derived record and is not a diagnosis, medical clearance, or safety decision.

Date of birth is an authenticated, ownership-protected applicability input. Corrections append a
new observation rather than erasing the earlier report. Age may block an age-bounded assessment or
planning authority, but it must not be treated as a capability score, diagnosis, clearance, or
standalone safety decision. Exact date of birth must not appear in public or operator-wide queues.

Ordinary self-service reassessment is unavailable until the exact historical protocol review's
recommended interval ends. This is a conservative cadence boundary, not a medical judgment or a
claim that earlier testing is universally unsafe. Any early-retest path requires separate governed
authority; browser input cannot override the interval. A selected result awaiting completion also
blocks a competing run.

## Policy classes

### Assessment candidates

Protocol ratification and athlete eligibility are separate. The first prepared chair-stand
candidate requires a stable armless 43–45 cm chair against a wall on a nonslip surface and remains
environment-ineligible until that exact `chair` category is reported available. Its athlete-facing
procedure requires a clear area, controlled movement without arm assistance, and an invalid/stopped
result rather than a guessed count when the setup changes or the attempt cannot continue.

The candidate tells the athlete not to start without a current eligibility decision and to stop for
pain, dizziness, chest discomfort, unusual shortness of breath, loss of balance, or uncontrolled
movement. These are conservative stop boundaries, not symptom classification, diagnosis, medical
clearance, or proof that self-administration is suitable for a particular person. Candidate
ratification cannot bypass the separate eligibility gate.

### Planning-policy candidates

Approving a priority policy authorizes only deterministic ranking of later reviewed inputs. It is
not medical clearance, athlete-specific safety approval, or permission to train. A policy
ratification cannot create a competency floor, strategy, block, exercise, dose, session, or bypass
the current safety-policy assignment and session-safety checks.

### Escalation

Concerning or unexplained symptoms must be able to interrupt ordinary programming and advise
appropriate professional evaluation. In Milestone 5B, a governed upstream workflow supplies only
preclassified escalation signals. The gate records `STOP_AND_ESCALATE`; it does not infer severity,
diagnose a condition, or generate medical advice from raw text. Concrete signal tags and
user-facing language remain unseeded pending qualified review.

The first daily PWA therefore does not translate free text or a symptom checkbox into a classified
signal. If the athlete selects the concerning-symptom control, ordinary submission is paused and
the interface explains that it cannot classify symptoms or provide medical guidance. This is a
conservative product boundary, not a triage decision, and the missing governed symptom-reporting
workflow remains explicit.

The same boundary applies to the post-session recovery form. A report of unusual soreness can be
submitted through the reviewed deterministic policy and can hold later progression. Selecting the
separate concerning-symptom control pauses normal progression without converting the report into
an unreviewed diagnostic or escalation classification.

### Modification

Preclassified safety input, limited readiness, unusual soreness, major sleep disruption, or a
schedule constraint may require an explicit versioned modification set. The gate never silently
rewrites the prescription. A `MODIFY` decision can authorize logging only when the execution
acknowledges every required modification exactly. `NOT_READY` produces `HOLD`; hold and escalation
outcomes cannot authorize ordinary session execution.

The current exercise resolver can enforce explicit, preclassified contraindication tags and upper
bounds for skill, impact, stability, fatigue, soreness, noise, space, and outdoor access. It does
not infer diagnoses, classify raw symptom text, or manufacture medical thresholds. When a hard
constraint cannot be satisfied, the resolver returns an infeasible result instead of silently
relaxing it.

The weekly scheduler can enforce explicit daily session limits, high-fatigue daily limits,
and a configured recovery interval. Those policy values are provisional constraints supplied by a
governed workflow, not medical or physiological thresholds inferred by the scheduler.

A temporary environment may trigger a newer exercise resolution for the same block stimulus.
Partial fidelity is allowed only by an explicit weekly policy and must retain every unresolved
mismatch. Re-resolution cannot bypass contraindication, skill, impact, space, noise, fatigue, or
other hard constraints, and an infeasible resolution can never authorize a prescription.

The current safety gate applies fixed precedence: escalation, not-ready hold, explicit
modification, then proceed. Pre- and post-session reports remain immutable observations with
provenance. A post-session decision references the completed execution and informs later review; it
does not alter history or automatically modify the next session.

Policy applicability is an explicit governed input. Each athlete's active policy is resolved from
an immutable, sequenced assignment chain with reviewer/operator rationale. The browser cannot pick
a policy per report, and policy replacement does not rewrite earlier assignments or safety
decisions. An athlete without an assignment cannot submit an ordinary safety check.

Execution authorization uses the latest persisted pre-session decision for the planned occurrence.
An earlier `PROCEED` or `MODIFY` decision cannot be reused after a newer `HOLD` or
`STOP_AND_ESCALATE`. A later decision requires a new explicit report; restrictive history is never
overwritten. Safety observation and decision persistence is atomic, as is the separate chain from
workout-result observation through execution and derived adherence.

A pre-session decision authorizes or blocks the whole scheduled `SessionTemplate`, not one exercise
at a time. The execution must preserve every ordered template item and any required session
modifications exactly. Item-level completion and adherence remain visible without weakening the
session-level hold or escalation boundary.

Block review may preserve post-session safety decisions as context, but it does not reinterpret
their signal tags, infer a condition, or diagnose why a response occurred. Safety history and
measurement uncertainty remain visible for a later governed state-update decision.

### Exposure progression

Running, high-speed running, jumping, landing, change of direction, and high-impact plyometrics require separate exposure histories. Cardiovascular readiness must not be treated as tissue readiness. Large unearned jumps in novel loading or impact must fail validation.

The current validator derives entries only from actual workout-result observations and applies
configurable initial, relative, and absolute caps. Rejected targets hold progression; no universal
“10% rule” or cardiovascular proxy is used.

The persisted progression boundary requires at least one post-session safety decision and loads
every such decision for the execution. Callers cannot select a favorable subset. An escalation
requires review, other configured post-session modifications hold progression, and the progression
decision cannot predate any safety decision it cites.

Completed-block review applies the same completeness rule across the block: each recorded execution
must have post-session safety closure, and every post-session decision is loaded automatically.
The review preserves those decisions as context without reclassifying signals or making a medical
inference.

### Re-entry

Illness, injury, prolonged interruption, or major detraining can place an athlete in a re-entry state. Prior prescriptions must not resume automatically at full dose.

## Deferred detail

This milestone implements the policy boundary without inventing medical thresholds. Versioned
signal categories, user guidance, escalation review, and production exposure policies still require
qualified review and evidence provenance before production policies are seeded.
