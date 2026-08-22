# Safety Policy

## Boundary

AGAS is a training-planning product for generally healthy adults. It is not a diagnostic, rehabilitation, medical-triage, or injury-prediction system and must not promise injury prevention.

## Deterministic precedence

Safety validation executes before LLM discretion and ordinary planning. The LLM cannot override a hard safety outcome.

## Policy classes

### Escalation

Concerning or unexplained symptoms must be able to interrupt ordinary programming and advise
appropriate professional evaluation. In Milestone 5B, a governed upstream workflow supplies only
preclassified escalation signals. The gate records `STOP_AND_ESCALATE`; it does not infer severity,
diagnose a condition, or generate medical advice from raw text. Concrete signal tags and
user-facing language remain unseeded pending qualified review.

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
