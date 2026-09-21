# Decision 0129: Athlete-facing introductory exposure preview

- Date: 2026-09-21
- Status: Accepted
- Decision version: `athlete-facing-introductory-exposure-preview@1.0.0`

## Decision

Project the exact ratified introductory jump dose into the athlete assessment workflow when the
latest exposure need is current and explicitly requires introductory exposure. The projection is
available only when the candidate digest, persisted dose policy, exposure definition, and exercise
record all match the reviewed release.

The phone UI shows the exercise, sets, repetitions, total contacts, rest, and RPE range. It also
states that the values are provisional engineering choices and that the dose is ready for
scheduling—not yet a session or clearance for maximal jumping.

Do not create or persist a workout during this read projection. Session construction still requires
a distinct reviewed scheduling and persistence step. This keeps a useful athlete-facing next step
without forcing an exposure prerequisite into the capability-deficit block model.
