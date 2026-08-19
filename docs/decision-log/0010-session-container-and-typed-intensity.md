# 0010: Session container and typed intensity

- Status: accepted provisionally
- Date: 2026-08-19
- Decision version: `session-container@1.0.0`

## Decision

Correct the provisional one-exercise session model before extending the closed loop. A
`SessionPrescription` remains an immutable prescription for one exercise and adaptation. A new
versioned `SessionTemplate` owns an ordered tuple of prescription items and an explicit weekly
frequency. `PlannedSession` schedules one occurrence of that container in one availability window.
Safety decisions remain session-scoped; execution stores ordered per-prescription item results;
adherence and progression remain prescription-item scoped.

Replace free-text prescription intensity with a discriminated, typed target collection. V1 target
types cover absolute load, relative load, bodyweight, effort RPE, repetitions-in-reserve, heart-rate
zone, pace, and technique constraints. Automatic `LOAD` progression is permitted only when the
policy adjustment is compatible with a typed absolute or relative load target.

The existing initial migration may be regenerated for this correction because no production,
seed, or personal athlete database exists. After this structural correction and the first verified
seed set, schema history becomes incremental.

## Reason

One exercise is not a normal workout session. The provisional shape forced scheduling, safety,
execution, and adherence to operate at exercise granularity and would make the required vertical
slice misleading. Prescribed load also cannot remain free text if strength progression is expected
to be deterministic and auditable.

## Alternatives considered

- Treat each exercise as a separate adjacent session: rejected because safety, completion, and the
  user's calendar would operate at the wrong granularity.
- Embed exercise prescriptions directly inside a session: rejected because progression must create
  new immutable prescription versions independently from the session container.
- Generate session grouping automatically now: rejected because no reviewed grouping policy or
  seed data exists. V1 accepts explicit templates and only validates/schedules them.
- Keep intensity as text and add a numeric load column: rejected because relative, bodyweight,
  effort, pace, and technique targets are distinct concepts.

## Evidence, assumptions, and uncertainty

This is a product-model correction derived from blueprint sections 35–37, 64–65, and the explicit
`Session`/`Prescription` distinction in `AGENTS.md`. It creates no training dose, grouping rule, or
scientific threshold. Template composition remains a governed input until real seed data supports
a deterministic generator.

## Consequences

- A safety hold applies to the whole scheduled workout.
- One execution can contain warm-up, primary, accessory, carry, or conditioning prescriptions in
  order while each item retains independent provenance and progression.
- Availability windows represent actual workout opportunities rather than exercise slots.
- Persistence and existing execution-chain tests require a coordinated schema correction.
- Controlled exercise vocabulary and laterality remain the next prerequisite before seed data.
