# Decision 0054: Reviewed environment prescription revisions

- Date: 2026-08-28
- Decision version: `environment-prescription-revision@1.0.0`
- Status: accepted

## Decision

Add an operator-only transaction that converts one or more reviewed exercise re-resolutions into
immutable successor `SessionPrescription` records for the next week of an existing block. The
source weekly plan must already be closed and report `ready_to_prepare_next_week`. Each requested
replacement identifies a prescription used by that source plan, a newer resolution for the same
stimulus and adaptation, and a complete explicit replacement dose. The service never copies an
exercise-specific dose silently.

Extend prescription-revision lineage so a revision is authorized by exactly one of:

- an immutable `ProgressionDecision`; or
- an immutable operator `DecisionRecord` for environment-driven planning.

The database association stores nullable progression and planning decision foreign keys with an
exclusive-or check constraint. The domain model and repository enforce the same rule. A planning
revision decision must cite the athlete, source weekly plan, block, allocation, immediate
predecessor prescription, new resolution, new prescription, scheduling policy, and exact current
approved policy review. Repository validation verifies those references before accepting the
lineage edge.

Environment revisions are appended to the latest prescription descendant available at the review
time, so an already-authorized progression is preserved rather than branched. One predecessor may
still have only one successor. The next-week roll-forward service then consumes the resulting
lineage and creates any needed successor session template and weekly plan.

`INFEASIBLE` resolutions cannot produce prescriptions. `PARTIAL` resolutions require the source
plan's current approved weekly scheduling policy to permit partial exercise re-resolution. Every
affected session template must still resolve to one environment after all replacements; otherwise
the transaction fails before creating mixed-environment session structure.

## Reason

The equipment and resolver workflows can now record changing constraints and determine honest
exercise fidelity, but a resolution alone is not a dose or scheduled workout. Progression lineage
already provides the append-only path consumed by weekly roll-forward, yet claiming that a
`ProgressionDecision` authorized an equipment substitution would corrupt provenance. A distinct
reviewed planning authorizer closes the travel-week gap without mutating history or inventing dose.

## Alternatives considered

- Reuse `progression_decision_id` for substitutions. Rejected because session performance did not
  authorize the change of exercise.
- Create an unrelated prescription without revision lineage. Rejected because roll-forward could
  not prove that it was a legitimate successor of the source plan.
- Copy the predecessor's sets, intensity, and rest automatically. Rejected because exercise-
  specific dose may not transfer safely or honestly to a partial substitute.
- Let the athlete submit replacement dose through the PWA. Rejected because dose and substitution
  fidelity remain governed planning inputs.
- Rewrite the current weekly plan immediately. Rejected because it destroys scheduled history and
  bypasses the existing consecutive-week roll-forward boundary.
- Add a second parallel revision table. Rejected because one linear prescription history with an
  explicit authorizer type is smaller and prevents competing descendants consistently.

## Evidence

This is a product-governance, persistence, and provenance decision implementing blueprint sections
11–13, 35–37, 52, 56, 65, 72–73, 77–78, and 83–84. It introduces no scientific equivalence,
training dose, or progression threshold.

## Assumptions

- A generic `DecisionRecord` is a sufficient provisional operator authorization while exact
  required lineage references are repository-validated.
- Environment replacements are prepared only after the source week's execution, recovery, and
  progression decisions are closed.
- Replacement dose is reviewed and explicit; this service does not infer it from exercise names or
  resolver scores.
- The existing approved weekly scheduling policy is the governing authority for accepting a
  partial resolution.

## Unresolved questions

- Production reviewer authentication, role authorization, and approval UI.
- Whether future correction workflows may supersede a not-yet-used environment revision.
- Athlete-visible workflow for requesting travel review before the source week closes.
- Whether a future dose-transfer policy can safely derive bounded replacement doses for specified
  exercise relationships.
- Mid-week emergency substitutions for an already scheduled but unperformed session.

## Consequences

- Prescription history distinguishes performance progression from environment planning.
- A travel replacement can flow into the existing next-week scheduler without changing the block's
  adaptation or stimulus.
- Prior prescriptions, templates, weekly plans, resolutions, and decisions remain immutable.
- Partial substitutions stay policy-gated and carry their limitations; infeasible resolutions
  remain unschedulable.
- The workflow remains operator-assisted until governance and safe dose-transfer rules mature.
