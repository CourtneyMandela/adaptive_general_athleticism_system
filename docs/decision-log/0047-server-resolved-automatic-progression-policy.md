# 0047 — Server-resolved automatic progression policy

- Status: accepted provisionally
- Date: 2026-08-28
- Supersedes: the client-selected policy transport in Decision 0019
- Decision version: `server-resolved-automatic-progression-policy@1.0.0`

## Decision

Keep the athlete-facing action that requests a deterministic post-session progression evaluation,
but remove all policy, exposure, target-dose, and prescription-revision choices from its command.
The athlete command contains only a timezone-aware decision timestamp.

Resolve progression authority on the server from the immutable prescription's
`progression_rule_reference`. Automatic evaluation requires exactly one matching persisted policy,
no exposure type, and an adjustment dimension limited provisionally to load or repetitions. The
service supplies the resolved policy identity and revision time internally, then uses the existing
transactional progression application boundary. Missing, ambiguous, exposure-sensitive, or other
manual policies fail closed.

Continue exposing the resolved policy identity in the read projection for provenance, but do not
send it back as writable command input. Keep the richer internal progression command for governed
application-service tests and future operator tooling; it is not an athlete HTTP contract.

## Reason

An athlete's performed work, effort, technique report, and recovery report are valid observations.
Choosing adherence thresholds, session-RPE limits, adjustment sizes, exposure caps, or the policy
that interprets those observations is a training-model decision. Aggregate ownership does not
authorize policy selection.

The prescription already carries an operator-authored, immutable progression rule reference. An
exact-one lookup provides a narrow provisional authority without silently choosing the latest
record. Preserving deterministic automatic evaluation for the two already-supported low-complexity
dimensions moves the PWA toward daily usefulness while keeping exposure and manual dose decisions
behind governed configuration.

## Alternatives considered

- Remove the progression endpoint entirely. Rejected because simple deterministic evaluation can
  be made safe without forcing routine completed-work interpretation into an operator queue.
- Continue accepting a policy ID supplied by the PWA. Rejected because a hidden or prefilled ID is
  still client-controlled authority.
- Select the newest policy with a matching reference. Rejected because recency is not approval or
  applicability and would make history-sensitive behavior implicit.
- Automatically resolve exposure definitions, caps, and next targets. Rejected because the system
  has no reviewed applicability assignment connecting those authorities to this athlete and
  prescription.
- Automatically handle sets and duration because the applicator supports them. Rejected because
  the current PWA readiness contract only establishes load and repetition automation; broader dose
  changes need an explicit governed workflow.

## Evidence and uncertainty

This is an authorization and transport decision implementing blueprint sections 38–42, 52, 60,
64, 71–73, and 83–84. It adds no universal progression percentage, exposure limit, RPE threshold,
or dose rule. The persisted policies remain synthetic or externally governed inputs.

## Assumptions and unresolved questions

- The prescription reference is a sufficient provisional binding only when exactly one policy
  matches. A production system should use explicit current approved policy assignments.
- The domain-specific `ProgressionDecision` already stores the exact policy, observations, safety
  decisions, rationale, rule version, and outcome, so a duplicate generic `DecisionRecord` is not
  added for this deterministic evaluation.
- Decision timestamps are currently client-clock inputs and must not predate recorded safety
  history. Trusted server time may replace them in a deployed environment.
- Exposure-policy, progression-policy, and definition review/supersession histories remain future
  governance work.

## Consequences

- Athlete clients can request evaluation but cannot choose the policy or next dose.
- The PWA still supports a truthful one-click action for ready load/repetition prescriptions.
- Ambiguous policy references and exposure-sensitive progression remain visible but unavailable.
- Existing immutable progression, revision, observation, safety, and rollback behavior is retained.
