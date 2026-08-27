# Decision 0034: Governed assessment measurement schemas

- Status: accepted provisionally
- Date: 2026-08-27
- Decision version: `assessment-measurement-schema@1.0.0`

## Decision

Place an optional, machine-readable measurement schema inside each append-only
`AssessmentDefinitionReview`. Support three initial entry types: number, integer, and category.
Each schema retains a display label and its own version. Numeric contracts may declare minimum,
maximum, and step; categorical contracts must declare exact allowed values.

An approved review without a schema remains visible in the global reviewed catalog so historical
and incomplete governance records stay inspectable. It is not eligible for self-service selection.
The selection service, deterministic reviewed selector, repository persistence boundary, result
service, and performance persistence boundary all fail closed when the required schema is absent.

Project the exact review schema to the PWA. The browser uses it to render an appropriate control and
provide immediate feedback, then submits the raw value to the API. The backend reloads the current
authority and validates the value again before appending either an observation or performance.

## Reason

Human-readable result instructions and a unit do not determine whether a result is a decimal,
count, bounded scale, or category. A universal field would invite ambiguous data and could silently
convert unsupported input into athlete history. Keeping the contract in the reviewed protocol
authority makes changes versioned, evidence-linked, and historically attributable.

Multiple enforcement layers protect direct repository callers and transactional rollback behavior,
not just the HTTP path. Client validation remains a usability feature and cannot become authority.

## Alternatives considered

- Infer controls from a unit or observation-type name. Rejected because names do not define shape,
  bounds, precision, or allowed categories.
- Store one mutable schema on the assessment definition. Rejected because schema changes would lose
  the exact contract approved for historical selections and results.
- Add a separate schema authority aggregate. Deferred because the schema changes with protocol
  review and does not yet need an independent lifecycle.
- Accept arbitrary JSON Schema. Rejected for this milestone because it would expose substantially
  more expressiveness than the domain and PWA can safely interpret and test.
- Make every approved review require a schema. Rejected to preserve readable legacy/governance
  records while failing closed specifically at operational self-service boundaries.

## Assumptions and provisional choices

- Category matching is exact and case-sensitive.
- Numeric step alignment starts at the reviewed minimum when present, otherwise zero.
- Duration, composite, repeated-trial, and structured measurements require explicit future schema
  types; they must not be encoded as misleading numbers or free text.
- The schema validates entry shape only. It does not create norms, reliability, capability scores,
  or scientific interpretation.
- No production bounds, choices, or measurement schemas are seeded in this milestone.

## Evidence and uncertainty

Labels, types, bounds, steps, and allowed categories can materially change a protocol and therefore
require qualified review and evidence support. This implementation supplies only the governance and
validation mechanism. Tests use conspicuously synthetic software fixtures with no athlete or
scientific applicability.

## Consequences

- The PWA can record governed numeric, integer, and categorical assessment results.
- Invalid values fail before any partial direct observation is retained.
- Historical review records preserve the exact measurement contract and its version.
- Real assessment protocols, correction/attempt workflows, structured measurement types,
  reassessment scheduling, and capability interpretation remain future work.
