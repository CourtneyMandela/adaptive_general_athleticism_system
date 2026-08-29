# 0048 — Server-owned weekly roll-forward lineage

- Status: accepted provisionally
- Date: 2026-08-28
- Supersedes: the client-authored availability metadata in Decision 0022
- Decision version: `server-owned-weekly-roll-forward-lineage@1.0.0`

## Decision

Keep weekly roll-forward as an athlete-facing confirmation workflow, but restrict its availability
payload to dated environment windows. Retain a timezone-aware preparation time, reliability, and
explicit user-report provenance because those describe the direct report itself.

Derive the next `week_start` as exactly seven days after the persisted source plan. Load the source
plan's persisted `WeeklyAvailability`, carry its ordered source-observation lineage, append the new
availability-confirmation observation, and stamp a server-owned availability rule version. Reject
client fields for week identity, inherited source observations, or rule version through the
transport model's `extra="forbid"` contract.

Continue retaining the source plan's scheduling policy, template structure, prescription revision
lineage, and explicit `previous_weekly_plan_id`. The deterministic observation, availability,
template revisions, and successor plan remain one atomic transaction.

## Reason

The athlete is authoritative about when and where they are available. They are not authoritative
about which historical observations govern the scheduler, which record is the consecutive week, or
which software rule version produced derived availability state. Allowing those fields in a browser
command lets presentation code masquerade as system provenance even when repository checks prevent
cross-athlete references.

The source plan already pins the exact predecessor availability. Deriving lineage from it removes
duplicate client state and makes the successor reproducible without reducing athlete control over
the actual availability windows.

## Alternatives considered

- Continue trusting the PWA's copied source IDs and fixed rule-version string. Rejected because API
  clients other than this PWA can submit different values and because browser constants are not
  authoritative software provenance.
- Store only the new confirmation observation and discard predecessor sources. Rejected because
  the availability sequence should retain the earlier context that led to the current schedule.
- Require an operator to prepare every next week. Rejected because confirming ordinary availability
  is an athlete report, while dose, exercise, policy, and session composition remain unchanged.
- Copy prior windows automatically with no confirmation. Rejected because future availability is
  not established merely by past availability.
- Use server wall-clock time for preparation. Deferred because current local-development flows use
  explicit client timestamps consistently; deployment-grade trusted timestamping is a broader
  transport concern.

## Evidence and uncertainty

This is a provenance and transport decision implementing blueprint sections 11, 35, 41–42, 52,
60, 64, 71–73, and 83. It introduces no scheduling, dose, progression, recovery, or exercise rule.

## Assumptions and unresolved questions

- `Provenance.recorded_by` remains an unverified report label rather than authenticated identity;
  production ingestion should bind the authenticated account separately.
- Reliability is a self-report metadata value in this provisional workflow and does not elevate the
  report above governed safety or planning rules.
- The source availability must belong to the same athlete and source week; repository integrity
  and the application service both fail closed otherwise.
- Plan supersession beyond the single consecutive automatic successor remains unresolved.

## Consequences

- Athlete clients submit only the new information they actually know: availability windows and
  direct-report metadata.
- Week identity, inherited source lineage, scheduling policy, and rule versions are server-owned.
- Existing daily PWA roll-forward remains usable and continues to require explicit confirmation.
- Historical observations, prescriptions, templates, and plans remain append-only.
