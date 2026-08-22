# 0018: Transactional safety and session recording

- Status: accepted provisionally
- Date: 2026-08-22
- Decision version: `transactional-session-recording@1.0.0`

## Decision

Expose two narrow application boundaries for an immutable planned-session occurrence:

- `POST /v1/weekly-plans/{weekly_plan_id}/sessions/{planned_session_id}/safety-checks`
  evaluates an explicit pre- or post-session report with a persisted safety policy and atomically
  appends the direct observation and deterministic safety decision.
- `POST /v1/weekly-plans/{weekly_plan_id}/sessions/{planned_session_id}/executions` accepts explicit
  performed-set data, requires the latest pre-session safety decision, records one workout-result
  observation and one execution, and derives per-prescription adherence in the same transaction.

Path and persisted-plan state determine athlete, weekly-plan, planned-session, session-template,
and prescription identity. Clients cannot submit alternative values for those authoritative links.
A later pre-session safety decision supersedes an earlier decision for authorization purposes even
though all decisions remain immutable history. A planned-session occurrence may have at most one
execution record; the database enforces this invariant in addition to the application check.

## Reason

The safety gate, execution recorder, adherence calculator, and persistence mappings already exist,
but callers currently have to assemble and persist their outputs manually. That permits partial
writes and could let an old `PROCEED` decision authorize work after a newer `HOLD` or escalation.
These services complete the first operational planning loop from scheduled dose through actual
performance to a new observation without making the API itself a training engine.

## Alternatives considered

- Record execution without a persisted safety decision: rejected because safety must precede
  programming discretion and execution authorization.
- Let the client supply complete observations, decisions, or execution records: rejected because
  their authoritative identities and derived fields must come from persisted state and deterministic
  rules.
- Persist only the execution and calculate adherence later: rejected for V1 because a partial write
  would leave a completed workout without the descriptive feedback required by the closed loop.
- Allow multiple executions for one planned occurrence: rejected provisionally because they create
  ambiguous adherence and exposure history. A future correction workflow should use explicit
  supersession rather than competing facts.
- Combine pre-session safety and execution into one request: rejected because the safety decision
  occurs before training and must remain independently inspectable.

## Evidence and uncertainty

This is an application-consistency and safety-precedence decision implementing blueprint sections
41–42 and the required first vertical slice. It adds no diagnostic behavior or scientific training
claim. Signal classification and safety-policy content remain governed upstream inputs linked to
reviewed evidence.

## Assumptions and unresolved questions

- "Latest" pre-session authorization is ordered by decision time, then record creation time and ID
  for deterministic ties.
- Per-prescription adherence is calculated at one explicit timestamp supplied with the execution.
- Execution corrections, offline idempotency keys, cancellation semantics, and post-session
  follow-up workflows remain unresolved rather than being approximated.
- V1 preserves the existing requirement that even a `NOT_STARTED` execution record references a
  pre-session safety decision. A separate missed-session workflow without a pre-check remains
  unresolved.
- A `HOLD` or `STOP_AND_ESCALATE` record remains historical and cannot be overwritten; a later
  independently reported and evaluated pre-session check is required before execution can proceed.

## Consequences

- Safety reports, safety decisions, performance observations, execution, and adherence retain
  separate semantics and provenance.
- An earlier permissive decision cannot bypass a newer restrictive decision.
- Late persistence failures roll back the entire observation-to-adherence chain.
- One planned occurrence cannot silently accumulate conflicting execution histories.
