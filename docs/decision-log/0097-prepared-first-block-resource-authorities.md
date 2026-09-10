# 0097 — Prepared first-block resource authorities

Date: 2026-09-10

Status: accepted as a prepared owner-alpha candidate; not ratified by this change

Decision version: `resource-governance-candidate@1.0.0`

## Decision

Add one content-addressed resource-governance candidate for the narrow muscular-endurance path.
The release includes an evidence claim and review, a stable-chair equipment record, a chair
sit-to-stand exercise ontology record, an exact-primary-match exercise-resolver policy, and a
single-DEVELOP-priority resource-allocation policy. An active planning reviewer accepts only the
candidate version, digest, and attestation; the server creates the bundle and decision audit in one
transaction. Exact retries are idempotent and collisions fail closed.

The candidate reuses the exact ACSM source snapshot already created by the deficit-only planning
authority and requires the controlled muscular-endurance adaptation to exist. It remains blocked
until both prerequisites are present. Ratification does not report the chair as available, prepare
an athlete-specific resource demand, choose weekly minutes, create a block, or prescribe a workout.

## Evidence boundary

The extracted claim retains the position stand's broad findings that resistance training improved
muscular endurance and chair-stand performance and its primary recommendation for high-effort
resistance training at least twice weekly across major muscle groups. The source supports neither
chair sit-to-stand as the optimal exercise nor the numerical resolver/allocation constants. Those
are inspectable, replaceable engineering choices for a one-path alpha.

The resolver gives score only for an exact primary-adaptation link, while every structural and
environmental constraint must still match for FULL status. The allocator refuses partial exercise
resolution and gives all relative weight to the sole DEVELOP priority. Neither policy is a dose.

## Reason

The existing resource-demand screen asks the owner to author exercise metadata, resolver weights,
allocation weights, and scientific rationale. Those are engineering and evidence-synthesis tasks.
Preparing exact authorities removes that responsibility without allowing the runtime or an LLM to
invent invisible defaults.

The chair-based exercise is deliberately conservative and directly inspectable, but its
assessment-proximal nature is a limitation: later improvement can include test familiarity as well
as underlying capacity. Stable-chair availability therefore remains a factual environmental report
that the athlete must make separately.

## Alternatives considered

- **Select an existing push-up because it already targets muscular endurance.** Rejected because it
  does not address the lower-body, chair-stand-specific capability path.
- **Treat a chair as universally available.** Rejected because equipment is changing environmental
  state and must not be inferred.
- **Use the complete exercise catalog and pick the top score.** Rejected because catalog inclusion
  is not candidate eligibility and a partial substitute is not yet governed.
- **Put frequency, weekly minutes, sets, and repetitions into this bundle.** Rejected because
  resource authority, athlete-specific demand, and performed dose are distinct decisions.
- **Silently seed the policies during deployment.** Rejected because deployment is not approval.

## Assumptions and provisional choices

- The owner-alpha already imports the controlled seed catalog before planning.
- One exact exercise is preferable to false choice while only one capability path is governed.
- Same-account preparation approval remains provisional and is recorded through the exact active
  reviewer assignment.
- A generic decision record supplies the review lineage because resolver, allocation, equipment,
  and exercise records do not yet have dedicated review aggregates.

## Unresolved questions

- Should resolver and allocation policies gain typed approval/supersession histories?
- Should exercise ontology assertions gain a dedicated review aggregate?
- Which non-assessment-proximal regression/progression should follow the first exposure?
- What evidence and operational constraints should define the first sets, repetitions, effort, and
  rest targets?

## Consequences

- The owner can inspect and approve exact first-block prerequisites without authoring them.
- No new database schema or generic workout generator is introduced.
- The next coherent milestone is a prepared athlete/environment-specific resource demand that uses
  only this bundle and refuses to proceed until stable-chair availability is explicitly reported.
