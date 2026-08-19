# 0006: Session execution logging and deterministic safety gates

- Status: accepted provisionally
- Date: 2026-08-19
- Decision version: `session-execution-safety@1.0.0`

## Decision

Milestone 5B will preserve this boundary:

```text
PlannedSession + SessionPrescription
  -> pre-session user-report Observation
  -> deterministic SessionSafetyDecision
  -> authorized SessionExecution
  -> direct workout-result Observation
  -> derived SessionAdherence
  -> optional post-session safety Observation and decision
```

Safety input contains only structured readiness fields and preclassified `SafetySignal` values.
This subsystem does not interpret free text, diagnose a condition, or decide that a symptom is
medically concerning. Each signal is classified upstream as modification-required or escalation-
required and retains its normalized tag and required modifications.

The deterministic gate applies fixed precedence:

1. any escalation-class signal produces `STOP_AND_ESCALATE`;
2. pre-session `NOT_READY` produces `HOLD`;
3. limited readiness, unusual soreness, major sleep disruption, major schedule limitation, or a
   modification-class signal produces `MODIFY` with the policy/signal modifications;
4. otherwise the decision is `PROCEED`.

Policy-supplied modification sets are explicit and versioned. They may include reducing volume or
intensity, removing high-impact or high-speed work, shortening the session, restricting range, or
requiring a reviewed substitution. The gate never silently changes a prescription. Execution after
a `MODIFY` outcome must record that every required modification was applied. `HOLD` and
`STOP_AND_ESCALATE` cannot authorize ordinary performance logging.

`SessionExecution` records actual set-level repetitions or duration, optional load, reported
effort, technique-constraint result, completion status, applied modifications, session RPE, notes,
timestamps, and the authorizing pre-session decision. The recorder creates a direct
`WORKOUT_RESULT` observation carrying the actual report and provenance.

`SessionAdherence` is a separate derived record. It references the workout-result observation and
stores prescribed and completed set/dose totals, bounded completion ratios, calculation time,
method, and rule version. It cannot masquerade as a directly measured fact. No progression decision
is produced in this slice.

Post-session checks use the same gate and may reference the completed execution. Their outcome is
historical input for later progression, weekly review, and replanning; it does not rewrite the
completed session.

## Reason

The blueprint requires low-friction workout logging, explicit symptom handling before LLM
discretion, and progression based on completed work rather than planned work. Separating direct
performance observations from derived adherence creates a safe, inspectable input boundary for the
next progression slice.

## Alternatives considered

- Parse symptom free text and infer severity: rejected because that would create unreviewed medical
  interpretation.
- Treat every pain report identically: rejected because upstream governance must distinguish
  modification and escalation classes without this engine inventing taxonomy.
- Automatically rewrite prescriptions inside the gate: rejected because modifications must remain
  explicit and inspectable; exercise substitution still belongs through the resolver.
- Log only a completed boolean: rejected because progression requires actual reps/load/time,
  effort, technique, symptoms, and partial completion.
- Store adherence as a user-reported observation: rejected because adherence is calculated from the
  prescription and execution.
- Implement progression simultaneously: deferred so progression rules can consume stable execution
  and adherence records rather than being coupled to logging.

## Evidence

This is a product and safety architecture decision implementing `docs/MASTER_BLUEPRINT.md`
sections 37, 40–42, 45, 57–58, 73, and the core invariant. It establishes no medical symptom
taxonomy, readiness threshold, progression increment, or universal training rule. Operational
signal classification and modification policies require qualified review and evidence governance.

## Assumptions

- An upstream governed workflow classifies normalized safety signals before they reach this gate.
- Readiness uses categorical `READY`, `LIMITED`, and `NOT_READY` states to avoid false precision.
- Exactly one repetitions-or-duration value represents each performed set in V1.
- Adherence ratios are descriptive bounded calculations, not judgments of athlete behavior or
  training effectiveness.
- A post-session escalation records guidance to stop ordinary future programming and seek the
  appropriate evaluation; it does not diagnose the reported signal.

## Uncertainty

- Concrete signal tags, escalation language, and reviewer roles require qualified safety review.
- Multi-exercise sessions and mid-session prescription changes need richer execution structure.
- Technique-constraint reporting is a structured input, not automated form analysis.
- Load units and modality-specific performance dimensions need a controlled-unit policy.
- Progression, exposure ledgers, and response interpretation remain subsequent slices.

## Consequences

- A blocked or escalation-gated session cannot be logged as an ordinary completed session.
- Required modifications are visible and must be acknowledged as applied before execution.
- Actual performance and symptom reports become immutable observations with provenance.
- Adherence can be recalculated under a new method without destroying the original performance.
- The next progression engine can consume explicit prescription, performance, effort, technique,
  symptom, and adherence inputs without relying on an LLM summary.
