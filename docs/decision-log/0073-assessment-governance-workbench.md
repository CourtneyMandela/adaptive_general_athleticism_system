# 0073: Assessment governance workbench and distinct authority

- Status: accepted provisionally
- Date: 2026-08-30
- Extends: Decisions 0030, 0034, 0036, 0056, and 0072
- Decision version: `assessment-governance-workbench@1.0.0`

## Decision

Introduce an append-only `assessment_reviewer` application role distinct from
`planning_reviewer`. Protect a new point-in-time assessment-governance projection with that role.
The projection lists every assessment definition created by the requested instant, its complete
protocol-review and capability-estimation-policy histories available at that instant, current
records, referenced evidence claims, and explicit readiness issues.

Treat the governance chain as operational only when the current protocol review is approved, has a
versioned measurement schema, authorizes self-administration, and has a current approved estimation
policy bound to that exact review. Keep athlete-specific eligibility separate. Provide a read-only
`/review/assessments` workbench and grant the dedicated local demo identity its role, but add no
browser or public approval endpoint.

## Reason

Assessment definitions, reviews, measurement contracts, and estimation policies already existed as
strong persistence contracts, but an operator could not see why a definition was absent from the
athlete workflow. Reusing planning authority would collapse scientific protocol governance into
training-plan authority. A derived workbench makes missing review, schema, self-administration, and
policy lineage visible while preserving the system's fail-closed boundaries.

## Alternatives considered

- Reuse `planning_reviewer`. Rejected because planning decisions and scientific protocol review are
  materially different responsibilities.
- Add protocol-approval forms immediately. Rejected because authentication role assignment does not
  establish scientific qualification, separation of duties, or an approved evidence-review process.
- Seed a realistic assessment and evidence claim for demonstration. Rejected because doing so would
  manufacture scientific authority.
- Report only the current record. Rejected because superseded and withdrawn reviews are important
  provenance and point-in-time inspection must not reveal future history.

## Assumptions and unresolved questions

- `assessment_reviewer` is an application permission only, not a professional credential.
- The definition/review/policy records continue to enter through governed local data operations
  until reviewer qualification, author/approver separation, and source-ingestion controls are
  specified.
- Requiring `self_administered` for workbench readiness is appropriate for the current athlete-facing
  PWA. A future supervised-assessment workflow may expose a separate readiness class.
- Athlete eligibility remains an independent, time-bounded safety decision and is intentionally not
  summarized as protocol readiness.

## Consequences

- A reviewer can diagnose the scientific-governance chain without querying database tables.
- Planning-only accounts cannot inspect the assessment-governance operator projection.
- Immutable histories and evidence provenance remain visible; the workbench creates no authority.
- No assessment becomes selectable merely because this feature exists.

## Evidence boundary

This is an architecture, authorization, and inspection decision. It adds no scientific claim,
protocol approval, capability interpretation, safety clearance, training prescription, or exercise
equivalence.
