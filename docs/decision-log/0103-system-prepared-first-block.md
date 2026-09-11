# 0103 — System-prepared first block

Date: 2026-09-11

Status: accepted

Decision version: `prepared-first-block@1.0.0`

## Decision

Add an athlete- and strategy-specific, content-addressed first-block candidate after the exact
resource-demand and training-construction authority batches are ratified. The owner selects only a
Monday start date. The server selects every strategy priority's sole immutable resource demand, the
exact ratified allocation policy, a weekly budget equal to the selected target-minute total, and a
four-week first-alpha horizon.

The server previews the existing deterministic `BlockPlanner` and offers ratification only when
every exercise resolution and the resulting block are FULL. Candidate identity and digest bind the
strategy, demands, resolutions, policy, reviewer assignment, both authority-batch digests, date,
constraints, and explanatory boundaries. Ratification reprojects current state, requires the exact
version/digest/date/attestation, and writes deterministic block, allocation, and decision IDs in one
transaction. Repeated submission returns the existing structurally verified result.

The previous technical block form remains available only as a collapsed advanced recovery path.

## Reason

The generic block workflow correctly refuses to infer demand history or planning choices, but it
therefore asks a non-technical owner to author policy selection, budget, duration, constraints,
applicability, and uncertainty. Those choices are now determined for the already narrow owner-alpha
path. This converts ratified inputs into useful planning state without weakening provenance or
pretending that a resource envelope is an executable workout.

## Alternatives considered

- **Keep the blank expert form as the primary path.** Rejected because it transfers technical
  authorship to the owner and makes the governed end-to-end path impractical.
- **Create the block automatically when resource demand is accepted.** Rejected because the start
  date is a genuine scheduling fact and the resulting boundary deserves a separate exact review.
- **Create Week 1 and sessions in the same transaction.** Deferred. Availability windows and
  prescription construction are separate factual and safety boundaries.
- **Use a scientifically presented four-week duration.** Rejected. The current duration is openly
  labeled a replaceable engineering horizon; the evidence does not establish it as universally
  optimal.
- **Allow partial exercise resolutions.** Rejected for the first owner-alpha block. Lower-fidelity
  substitutions require their own explicit reviewed path.

## Assumptions and provisional choices

- Training weeks begin Monday so availability and block-week arithmetic share one boundary.
- The first block lasts four weeks, the shortest duration already allowed by the domain model.
- Weekly budget equals the sum of the already ratified target minutes. It is not expanded merely
  because more time could be available.
- Exactly one demand record per strategy priority is required. Ambiguous history fails closed.
- The current owner-alpha strategy has one DEVELOP priority and one fully resolved chair
  sit-to-stand demand. The mechanism remains structurally multi-priority but does not invent future
  domain content.

## Consequences

- The owner can create the first governed block by choosing a date and reviewing one prepared card.
- Historical blocks remain append-only; an unrelated existing block prevents silent replacement.
- Accepted retries cannot duplicate a block.
- No week, session, repetitions, workout, readiness decision, or permission to train is created.
- The next milestone is a prepared Week 1 candidate that consumes factual availability and the
  ratified dose, scheduling, progression, and safety authorities.
