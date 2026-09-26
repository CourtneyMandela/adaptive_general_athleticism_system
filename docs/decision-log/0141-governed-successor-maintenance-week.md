# 0141 — Governed successor maintenance week

Date: 2026-09-24

Status: accepted provisionally

Decision version: `governed-successor-maintenance-week@1.0.0`

## Decision

Make fixed-repetition dose policies explicitly applicable to one priority state. The supported
states are `DEVELOP` and `MAINTAIN`; historical rows and candidate identities remain `DEVELOP` by
default. A `DEVELOP` policy requires a below-floor capability need. A `MAINTAIN` policy requires a
meets-floor or above-floor need. Both require the exact current capability estimate, adaptation,
priority, observations, progression authority, and policy identity. The estimate value remains
lineage and applicability evidence and is never converted into repetitions.

Add a separately content-addressed owner-alpha jump-maintenance construction candidate. It contains
a fixed two-set by three-contact dose, a six-contact initial cap, target RPE 4–6, 120 seconds rest,
and six scheduled minutes per session. It also contains distinct scheduling, progression,
jump-contact exposure, and non-diagnostic safety authorities. Every exact numeric value is labeled
as provisional engineering judgment. The existing three-by-three `DEVELOP` candidate and its
identity remain unchanged.

Select training-construction authority by both capability-estimate scope and current priority
state. A matching scope alone is no longer sufficient when multiple priority-specific authorities
exist. Block and week preparation fail closed if the exact state-scoped candidate has not been
ratified and persisted.

Version successor first-week candidates as `prepared-first-week@1.3.0`. Bind the exact strategy
cycle, prior and current priority state, predecessor block and triggering review, second block,
new resource allocation, construction candidate identity and digest, current availability, dose,
scheduling review, and safety-policy assignment into the candidate and its content digest. Preserve
the historical `@1.2.0` identity calculation for existing initial weeks.

When the ratified successor construction candidate uses a different session-safety policy, append a
new athlete safety-policy assignment that increments the sequence and explicitly supersedes the
current assignment. Never mutate the predecessor assignment. Ratification re-projects and
exact-matches the candidate before persisting the availability observation and weekly plan.

## Reason

Decision 0140 created a real successor `MAINTAIN` resource demand and second block, but the only
ordinary jump dose authority was deliberately scoped to a below-floor `DEVELOP` need. Reusing it
would erase the meaning of the priority change, hide a new maintenance-dose assumption, and make
the feedback loop appear complete while applying the old developmental rule.

The successor week also needed to prove that it consumed the reviewed second block rather than
merely producing another plausible workout. Explicit cycle and construction lineage makes that
dependency inspectable in the API, owner-review UI, content digest, and persisted plan.

## Alternatives considered

- Reuse the jump `DEVELOP` construction candidate for `MAINTAIN`. Rejected because its applicability
  contract requires a deficit and its three-by-three dose is a different material decision.
- Infer maintenance by reducing the existing dose inside the week projector. Rejected because that
  would hide training logic in orchestration and leave no separately reviewable authority.
- Change the existing fixed-dose policy semantics in place. Rejected because material rules and
  candidate content are immutable and versioned.
- Copy the first block's week into the second block. Rejected because availability, allocation,
  safety authority, priority, and plan identities are current-cycle facts.
- Overwrite the athlete's prior safety-policy assignment. Rejected because assignment history is
  evidence of which policy governed each session and must remain immutable.
- Automatically ratify the maintenance candidate. Rejected because owner review remains required
  for the exact engineering dose and safety choices.

## Evidence

The cited Oxfeldt et al. systematic review supports only the broad direction that lower-body
plyometric training can affect jump performance in healthy adults. It does not establish that this
specific dose maintains performance, nor does it validate the contact count, effort range, rest,
progression caps, scheduling interval, or safety-modification mappings.

The priority-scoped policy, exact-lineage reconstruction, content addressing, immutable assignment
replacement, and fail-closed selection are architecture and provenance decisions. The numeric
maintenance values are owner-reviewable engineering priors, not scientific findings.

## Uncertainty

The six-contact maintenance dose has not been calibrated against repeated personal response and may
be insufficient, excessive, or mainly preserve assessment familiarity. Meeting the provisional
jump floor does not prove a biological ceiling or eliminate future development value. Continued
execution, exposure tracking, reassessment, and reviewed response interpretation are required.

The owner-alpha week projector still supports one governed active allocation. Multi-adaptation
successor weeks need explicit construction and scheduling rules rather than implicit reuse of this
narrow path.

## Consequences

- A reviewed `DEVELOP` to `MAINTAIN` transition now changes both resource allocation and prescribed
  dose through distinct immutable authorities.
- The first week of the second block is content-bound to the reviewed predecessor cycle, second
  block, current availability, and exact maintenance construction release.
- The owner-review page displays current and prior priority, cycle lineage, and the construction
  candidate identity and digest before acceptance.
- A changed session-safety policy creates a sequence-two superseding assignment while preserving
  the prior assignment.
- Existing initial-week content identities remain compatible through the historical `@1.2.0`
  projection path and migration default.
- The next product task is to execute and record the successor maintenance week, capture its contact
  exposure and response, and prove that the next review/replanning decision consumes those new
  observations rather than relying on first-block history.
