# 0016: Governed resource-demand preparation

- Status: accepted provisionally
- Date: 2026-08-22
- Decision version: `governed-resource-demand-preparation@1.0.0`

## Decision

Add `POST /v1/strategies/{strategy_id}/priorities/{priority_id}/resource-demands` as the
transactional application boundary between a persisted strategy priority and the inputs consumed
by block creation.

An active-priority request must provide an explicit `StimulusSpecification`, environment identity,
candidate exercise identities, resolver-policy identity, minimum and target weekly minutes,
session frequency, provenance, rationale, version, and preparation time. The service derives the
effective environment snapshot from persisted availability history, invokes the deterministic
stimulus builder and exercise resolver, and appends the stimulus requirement, resolution, and
resource demand atomically.

A deferred-priority request supplies provenance, rationale, and version only. It appends a
zero-resource demand and cannot create a stimulus or exercise resolution. Conversely, an active
request is invalid for a `DEFER` priority.

The service persists `FULL`, `PARTIAL`, and `INFEASIBLE` resolutions honestly. It does not change
the strategy, replace an infeasible result with an allegedly equivalent exercise, or infer dose.

## Reason

The block-creation endpoint intentionally consumes already-governed resource demands. Without a
coherent upstream boundary, clients would need to persist a stimulus, environment resolution, and
demand manually and could leave partial state or accidentally mix identities from different
athletes and strategies.

This service makes the legal sequence atomic while preserving the blueprint chain from adaptation
target to stimulus to available exercise to explicit resource demand. All scientific and dose
inputs remain visible rather than becoming application defaults.

## Alternatives considered

- Infer a stimulus from adaptation ontology metadata: rejected because preferred stimulus metadata
  is not an operational scientific prescription.
- Search every exercise in the catalog automatically: deferred because candidate eligibility and
  catalog review boundaries are not yet sufficiently governed. V1 requires explicit candidates.
- Infer maintenance, exposure, or development dose from priority state: rejected because no
  reviewed dose policy currently authorizes those values.
- Reject infeasible resolutions without persistence: rejected because infeasibility is an
  important planning result that the downstream block planner must be able to explain.
- Create separate endpoints for stimulus, resolution, and demand CRUD: rejected because callers
  could create incomplete or mismatched planning chains.

## Evidence and uncertainty

This is an architecture and provenance decision implementing blueprint sections 11–13, 33–37,
56, 65, 72–74, and 89. It establishes no scientific stimulus, exercise-equivalence, or dose rule.

Candidate exercises, stimulus specifications, resolver policies, and resource amounts require
reviewed upstream sources before production use. The current endpoint records the supplied
evidence and observations but does not claim that their presence constitutes domain approval.

## Assumptions and unresolved questions

- One preparation timestamp is used for the stimulus, environment snapshot, and resolution in V1.
- Candidate exercise IDs are explicit and ordered; the resolver still ranks deterministically.
- Multiple historical demands may exist for a priority. The block request explicitly selects the
  intended demand, so no unversioned "current demand" pointer is introduced.
- Catalog-wide candidate eligibility, demand approval states, overlap policy, and idempotency keys
  remain unresolved and should be added only with explicit product rules.

## Consequences

- Strategy-to-block orchestration can now use only coherent persisted planning inputs.
- Equipment changes affect the resolved means while leaving the strategy priority unchanged.
- Partial and infeasible substitutions remain visible and policy-gated downstream.
- Invalid requests roll back without leaving orphaned stimuli or resolutions.
- `DEFER` remains an explicit zero-resource planning decision rather than a missing record.
