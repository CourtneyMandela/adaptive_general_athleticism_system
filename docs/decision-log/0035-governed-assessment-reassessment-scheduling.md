# Decision 0035: Governed assessment reassessment scheduling

- Status: accepted provisionally
- Date: 2026-08-27
- Decision version: `assessment-reassessment-schedule@1.0.0`

## Decision

Derive reassessment timing from immutable assessment-performance and protocol-review history. Do not
persist a mutable `next_assessment_due` flag or date.

For every currently approved, self-administered protocol with a measurement schema, find the
athlete's latest performance. A protocol with no prior performance is due. Otherwise, calculate its
next self-service time by adding the `recommended_reassessment_days` from the exact historical
review that authorized that performance. A current replacement review does not retroactively change
the interval attached to an already recorded result.

Only due protocols enter a new self-service selection run. The API rejects early requests before
writing a context observation. It also rejects a new run while the latest run has a selected result
awaiting completion and rejects future evaluation timestamps so a client cannot bypass cadence.
Deferred-only runs may still be repeated because no measurement was recorded.

Expose due-protocol count, earliest future reassessment time, schedule-rule version, and the exact
next time for each projected result. The PWA presents this backend-derived state and offers a new
selection form only when a protocol is due and the existing environment and eligibility
authorities are active.

## Reason

The blueprint requires reassessment while warning against excessive testing. Before this decision,
a completed assessment was a terminal PWA state, yet the selection endpoint could also be called
directly without any cadence guard. That prevented the closed loop in one path and allowed noisy,
premature retesting in another.

The reviewed interval is already explicit protocol authority. Using its exact historical version
preserves what governed the recorded result and avoids silently applying a later rule to prior
history. Derivation keeps immutable performances and reviews authoritative.

## Alternatives considered

- Allow reassessment at any time. Rejected because it ignores reviewed cadence and the blueprint's
  instruction to avoid excessive testing.
- Use the current review's interval for every historical result. Rejected because replacement
  governance would silently change the meaning and due date of existing history.
- Persist and update one due-date column. Rejected because it can drift from append-only performance
  and review history.
- Use capability-estimate validity as assessment cadence. Rejected because estimate staleness and
  protocol testing cadence are separate authorities.
- Create background jobs or reminders. Deferred; the current milestone needs deterministic
  availability, not notification infrastructure.

## Assumptions and provisional choices

- The latest performance is ordered by performed time, creation time, and stable identifier.
- The reviewed interval acts as the earliest ordinary self-service reassessment time.
- A newly approved operational protocol with no athlete performance is immediately available.
- A professional or operator early-retest override needs a separate governed record and is not
  inferred from browser input.
- If several protocols are due, the existing adaptive selector still evaluates each against current
  context and may defer it for explicit reasons.

## Evidence and uncertainty

This milestone implements reviewed cadence; it does not supply a scientifically valid interval.
Every operational interval remains a protocol claim requiring evidence and qualified review. Test
intervals are synthetic software fixtures with no athlete applicability.

## Consequences

- Completed assessment history now returns to an explicit due/not-due state instead of becoming a
  permanent dead end.
- Premature self-service retesting and competing incomplete runs fail without partial observations.
- Historical result projections disclose the interval source review and next recommended time.
- Corrections, invalidations, operator overrides, reminders, real protocols, and capability
  interpretation remain future work.
