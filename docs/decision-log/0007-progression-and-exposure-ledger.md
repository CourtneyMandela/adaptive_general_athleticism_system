# 0007: Deterministic progression and exposure ledger

- Status: accepted provisionally
- Date: 2026-08-19
- Decision version: `progression-exposure@1.0.0`

## Decision

Milestone 5C preserves this boundary:

```text
Prescription + execution + adherence + post-session safety
  -> versioned ProgressionPolicy
  -> immutable ProgressionDecision

Direct workout-result Observation
  -> versioned ExposureDefinition
  -> derived ExposureEntry
  -> versioned ExposureProgressionPolicy + proposed target
  -> immutable ExposureValidationDecision
```

A progression decision can `PROGRESS`, `REPEAT`, `HOLD`, or require `REVIEW`. Progress requires a
completed execution, configured set/dose adherence, acceptable effort, required technique
constraints, no post-session safety interruption, and—when configured—an approved exposure target.
The output records one explicit adjustment dimension, amount, unit, rationale, policy, evidence,
source observations, and rule version. It never rewrites the completed prescription.

Exposure is not inferred from cardiovascular fitness or exercise names. A reviewed
`ExposureDefinition` classifies an exercise as running, high-speed running, jumping, landing,
change of direction, or high-impact plyometrics and declares whether repetitions or seconds are
the dose. An `ExposureEntry` is derived from actual performance and retains the workout-result
observation. The validator compares a proposed target with a configurable initial cap or with both
relative and absolute caps over a stated lookback using the maximum recent exposure baseline.
Exceeding the cap is rejected, not silently reduced.

## Reason

The blueprint requires predictable progression from completed work and separate impact/speed
exposure history. Explicit policies and immutable decisions make both behaviors inspectable while
avoiding unsupported universal increments.

## Alternatives considered

- Mutate the current prescription: rejected because it destroys planning history.
- Progress solely from completion: rejected because effort, technique, safety, and exposure matter.
- Infer exposure from fitness or free text: rejected because it creates unsupported state.
- Hard-code a universal percentage rule: rejected because scope and evidence are unresolved.
- Automatically regress failed sessions: deferred; regression needs its own reviewed policy.

## Evidence

This implements blueprint sections 37–42 and 73. Operational thresholds and increments require
reviewed `EvidenceClaim` links. No production rule or scientific claim is seeded here.

## Assumptions

- One prescription currently represents one exercise and one repetitions-or-duration dose.
- Maximum recent exposure is a conservative, replaceable V1 baseline method.
- A post-session `MODIFY`, `HOLD`, or `STOP_AND_ESCALATE` outcome prevents progression.
- Missing required technique reporting produces `REPEAT`, not a favorable inference.
- An exposure rejection holds progression and preserves the rejected proposal for review.

## Uncertainty

- Modality-specific dose metrics, acute/chronic workload models, and re-entry policies remain open.
- Concrete exposure definitions, caps, increments, and effort thresholds require qualified review.
- Applying a decision to generate the next immutable prescription is a later slice.

## Consequences

- Completed work produces a predictable, versioned progression decision.
- Large unearned exposure jumps fail validation independently of general fitness.
- Historical prescriptions, executions, ledgers, and decisions remain append-only.
- The next slice can create revised prescriptions from approved decisions without recomputing or
  erasing the evidence chain.
