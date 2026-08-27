# Decision 0033: Assessment workflow projection and minimal PWA

- Status: accepted provisionally
- Date: 2026-08-27
- Decision version: `assessment-workflow-projection@1.0.0`

## Decision

Derive athlete-facing assessment workflow state from immutable eligibility, catalog review,
selection-run, selection, performance, and observation history. Do not add a separately mutable
workflow-status record.

Expose one authenticated read projection containing an explicit workflow status, safe eligibility
summary, persisted environments, reviewed self-administered protocol count, and the latest run's
ordered decisions. Each projected decision includes protocol instructions, result-entry
instructions, applicability, uncertainty, evidence-claim identifiers, exact versions, and any
recorded direct result observation. Operator identity, screening-process references, source
screening observations, and sensitive intake are not included.

Add a responsive PWA assessment panel that renders honest blocked and empty states, provenance and
uncertainty disclosures, the latest deterministic decisions, and recorded results as observations.
When the backend says selection prerequisites are ready, the panel can submit non-medical context
for a new run. Equipment remains server-derived from the selected persisted environment.

Do not add generic browser result entry yet. A reviewed protocol currently supplies human-readable
instructions and a unit, but no machine-readable measurement schema. The PWA must not guess whether
to render a number, duration, repetition count, categorical scale, or structured measurement.

## Reason

The PWA needs a single coherent view of assessment readiness without reproducing authority rules in
TypeScript or exposing raw persistence objects. Derivation keeps the append-only records
authoritative and makes the projection replaceable.

Rendering blocked states is meaningful functionality: a newly onboarded athlete should see that
operator eligibility and reviewed protocols are missing instead of being offered an invented test
or workout. The same projection can later support reviewed result schemas and reassessment timing.

## Alternatives considered

- Persist a mutable `assessment_status` column. Rejected because it could drift from authority and
  history or erase how the state was reached.
- Let the PWA calculate readiness from the public catalog and local state. Rejected because the
  browser does not own eligibility, equipment history, or authority rules.
- Return raw eligibility reviews and screening observations. Rejected because the user interface
  does not need operator-process details or potentially sensitive source records.
- Render one universal text or number result field. Rejected because protocol measurement shapes
  differ and the current ontology has no reviewed machine-readable result schema.
- Hide assessment until real protocols are seeded. Rejected because honest prerequisite and empty
  states are necessary for the first vertical slice and operational debugging.

## Assumptions and provisional choices

- The projection uses the latest run by evaluation time, creation time, and stable ID ordering.
- A completed run means every selected decision has a linked performance; deferred decisions do not
  require results.
- A deferred-only run may be repeated with materially updated non-medical context.
- A selected incomplete run cannot be replaced from the PWA while its result remains ready.
- Reassessment due dates are not inferred until reviewed scheduling behavior is explicitly modeled.
- Skill and exposure tags remain exact user-reported strings and are presented as advanced inputs.

## Evidence and uncertainty

This decision adds presentation and orchestration, not scientific claims. Evidence identifiers and
reviewed uncertainty are disclosed without summarizing or reinterpreting them. No real assessment
protocol, measurement schema, norm, or capability formula is introduced.

## Consequences

- The PWA now exposes the governed assessment boundary immediately after athlete connection.
- Users can start selection without supplying equipment authority or medical classifications.
- Empty, blocked, deferred, ready, unavailable-authority, and completed states are explicit.
- Generic result entry, correction/attempt workflows, reassessment scheduling, capability
  estimation, and production reviewer identity remain future work.
