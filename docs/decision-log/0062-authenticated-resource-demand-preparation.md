# 0062: Authenticated resource-demand preparation

- Status: accepted provisionally
- Date: 2026-08-29
- Supersedes: the operator-CLI-only transport boundary in Decision 0045
- Decision version: `authenticated-resource-demand-preparation@1.0.0`

## Decision

Expose the existing deterministic resource-demand preparation service through a narrowly scoped
operator HTTP boundary. The endpoint requires an active `planning_reviewer` assignment, omits
reviewer identity from the untrusted request, and binds the authenticated account and exact current
role assignment on the server. The application service independently revalidates that assignment
and cites it in the immutable decision audit.

Add a role-protected, read-only preparation projection for one persisted long-range strategy. At an
explicit instant it returns the exact strategy and priorities, their adaptations and historical
resource demands, strategy-linked observations and evidence, current environment snapshots,
resolver policies, and the structured exercise catalog. The projection does not select a stimulus,
candidate exercise, environment, dose, or demand history and does not imply that catalog membership
is scientific approval or environmental feasibility.

Keep active and deferred preparation as separate discriminated request shapes. Active requests
must still provide an explicit stimulus specification, candidate set, environment, resolver policy,
weekly resource amounts, provenance, rationale, uncertainty, and version. Deferred requests remain
zero-resource decisions with explicit provenance. Preparation remains append-only and may preserve
`FULL`, `PARTIAL`, or `INFEASIBLE` exercise resolution honestly.

## Reason

The PWA can now create a governed initial strategy, but its next step is still limited to local JSON
and CLI authoring. Resource-demand preparation is the smallest next boundary in the blueprint chain:
it translates one reviewed adaptation priority into an explicit stimulus and feasible means without
also inventing block budgets, dates, allocation policy selection, or weekly scheduling.

Server-owned reviewer attribution closes the identity-spoofing gap while reusing the already tested
transactional service. A purpose-specific projection avoids exposing generic write CRUD and makes
the exact persisted inputs inspectable before a reviewer makes a material decision.

## Alternatives considered

- Automatically derive stimulus and dose from adaptation metadata. Rejected because ontology
  metadata is not an operational prescription or reviewed dose policy.
- Automatically use every matching exercise or choose the highest resolver score. Rejected because
  candidate eligibility is still a reviewed input and infeasibility must remain visible.
- Create the block in the same request. Rejected because resource allocation policy, weekly budget,
  dates, duration, and constraints are separate governed decisions.
- Keep the boundary CLI-only. Rejected because authenticated reviewer authority now exists and can
  safely own identity while the same deterministic service remains authoritative.
- Add generic environment, exercise, evidence, and policy list routes. Rejected in favor of one
  workflow-specific projection with explicit semantics.

## Evidence

This is an authorization, provenance, and interface decision implementing blueprint sections 11–13,
16, 33–34, 52, 60, 64, 71–72, and 89. It introduces no scientific stimulus, dose, substitution, or
periodization claim.

## Assumptions and uncertainty

- One active planning reviewer may provisionally author and approve a resource demand.
- Strategy-linked observations and evidence are the bounded baseline shown by the projection;
  candidate-specific evidence search remains a later governed workflow.
- The current exercise and policy catalogs are small enough for a purpose-specific unpaginated
  projection. Pagination/search will be required as the catalogs grow.
- Multiple historical demands remain legal and are never silently treated as current.
- Production reviewer credentialing and separation of author/approver remain unresolved.

## Consequences

- An authenticated reviewer can advance one strategy priority to an auditable resource demand
  without claiming another identity.
- The athlete-facing API still cannot author scientific stimulus, substitution, or dose choices.
- Environment constraints can change the resolved means without changing the strategy priority.
- Block creation remains a separate future web milestone with explicit demand selection and block
  context.
- No database migration is required.
