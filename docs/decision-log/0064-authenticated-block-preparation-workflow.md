# 0064: Authenticated block-preparation workflow

- Status: accepted provisionally
- Date: 2026-08-29
- Supersedes: the block-creation CLI-only transport boundary in Decision 0045
- Decision version: `authenticated-block-preparation-workflow@1.0.0`

## Decision

Expose the existing deterministic block-creation service through one role-protected operator HTTP
boundary. The untrusted request supplies the exact resource-demand IDs, resource-allocation policy,
weekly budget, start date, four-to-six-week duration, constraints, generation time, applicability
rationale, and uncertainty. It cannot supply reviewer identity or authority. The server binds the
authenticated account and exact current `planning_reviewer` assignment, and the application service
revalidates that assignment before atomically appending the block and decision audit.

Add a companion read-only projection for one strategy. It returns the immutable strategy and
priorities, every historical demand with its stimulus and exercise resolution, all allocation
policies, existing blocks, and the full observation/evidence records referenced by the strategy and
demand histories. The projection groups history by priority but does not mark any demand current,
preselect a policy, calculate a budget, choose dates or duration, or invent constraints.

Add a structured `/review/blocks` PWA route. The reviewer must select exactly one demand for every
priority, including an explicit zero-resource demand for `DEFER`; select one policy; enter every
block-context value; and confirm the complete review. The resulting receipt preserves full,
partial, or infeasible block status and its immutable allocation and decision lineage. Week,
session, and prescription creation remain separate downstream workflows.

## Reason

The strategy-to-stimulus workflow is now operable, but block creation still requires external JSON
and local CLI access. This boundary completes the next link in the vertical slice while retaining
the blueprint hierarchy: reviewed demands are selected before the deterministic allocator runs,
and block creation remains distinct from weekly scheduling and exercise prescription.

Explicit history selection avoids introducing an unsupported “latest means current” rule. Explicit
budget, dates, duration, and constraints prevent interface defaults from silently becoming
periodization or dose policy.

## Alternatives considered

- Automatically select the newest demand for each priority. Rejected because demand supersession
  and approval semantics do not exist.
- Choose the first policy or infer one from block status. Rejected because policy selection changes
  whether partial exercise resolution is acceptable and how surplus time is allocated.
- Derive weekly budget from summed targets. Rejected because available training time is a distinct
  reviewed athlete constraint.
- Default to four weeks or the next calendar Monday. Rejected because either would silently create
  planning behavior not authorized by a reviewed rule.
- Create Week 1 in the same request. Rejected because prescription construction, session grouping,
  availability, and scheduling policy are separate governed inputs.

## Evidence

This is an authorization, provenance, and workflow decision implementing blueprint sections 16,
33–35, 52, 60, 64, 71–73, and 89. It establishes no scientific dose, periodization, exercise
equivalence, or scheduling rule.

## Assumptions and uncertainty

- One active planning reviewer may provisionally author and approve a block context.
- Existing allocation policies are immutable and versioned but do not yet have approval or
  supersession histories; their presence is not represented as scientific endorsement.
- Multiple blocks per strategy remain legal and are never silently labelled current.
- Production credential verification and author/approver separation remain unresolved.
- The current history and policy collections are small enough for one purpose-specific projection;
  search and pagination will be needed later.

## Consequences

- An authenticated reviewer can advance exact reviewed demands into an auditable block without
  impersonating another reviewer.
- Infeasible and partial outcomes remain first-class results rather than triggering generic
  replacement programming.
- Every material block-context choice stays inspectable and replaceable.
- The next governed milestone is block-to-prescription preparation, not automatic workout
  generation.
