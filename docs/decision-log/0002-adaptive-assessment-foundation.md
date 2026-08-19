# 0002: Adaptive assessment foundation

- Status: accepted
- Date: 2026-08-19
- Decision version: `adaptive-assessment@1.0.0`

## Context

The blueprint requires assessment to adapt to training history, symptoms, health screening,
equipment, skill, and recent exposure. It also requires measured observations to remain distinct
from inferred athlete capabilities. This milestone must establish those semantics without adding
workout generation or fabricating scientific norms.

## Decision

Assessment protocols are immutable, versioned `AssessmentDefinition` records. A deterministic
selector compares an explicit `AssessmentContext` to each definition and produces an append-only
`AssessmentSelection`. Every selection records its rule version, reason codes, rationale, and the
ordered intake-observation references used to reach the decision.

Constraint tags use exact matching. Incomplete health screening, a health-screening match, a
current-injury match, or a current-symptom match excludes an assessment; missing required body
mass, equipment, training history, skill, or recent exposure defers it. Exclusion has
precedence when both kinds of constraint apply. These are routing semantics, not medical
interpretation.

Performed assessments are recorded as direct observations with protocol and ingestion provenance.
The first estimation policy creates an assessment-specific capability estimate from the latest
matching result in a bounded window. It retains all matching observation references in
chronological order, derives staleness from the latest observation timestamp, returns unknown
confidence if any source is unknown, low confidence for one known source, and at most moderate
confidence for repeated known sources. It assigns no normative band or population ranking.

## Alternatives considered

- A generic score such as `power = 74`: rejected because its meaning and evidence cannot be
  inspected and it can masquerade as ground truth.
- A probabilistic or LLM-driven selector: deferred because deterministic constraints are safer,
  explainable, and sufficient for this milestone.
- Hard-coded tests in selector code: rejected in favor of versioned protocol records that can later
  be reviewed and changed without rewriting history.
- Automatic medical interpretation of symptom text: rejected; safety classification requires a
  separately governed workflow and evidence.
- Population norms and test-specific formulae: deferred until scientific claims and applicability
  are curated through the evidence system.

## Assumptions and provisional choices

- Upstream intake normalizes tags; synonyms and free-text classification are not handled here.
- Missing domain training age is treated as zero months.
- Definitions are versioned by adding new records. Slugs may repeat across versions; record IDs are
  authoritative.
- Capability validity windows and observation windows are policy inputs, not embedded scientific
  truths.
- Confidence rules are deliberately conservative and provisional pending calibrated validation.

## Unresolved questions

- Which intake taxonomy and controlled vocabularies should be adopted for symptoms, health flags,
  skills, and exposures?
- Which assessment protocols and reassessment intervals have evidence strong enough for initial
  seed data?
- How should qualified human review and medical referral states connect to assessment eligibility?
- Which capability estimators can be scientifically supported for particular populations?

## Consequences

Different athlete histories and environments can now produce different test selections with a
fully inspectable explanation. Assessment results and estimates cannot silently collapse into one
record. The system remains intentionally unable to prescribe workouts or claim population-relative
athletic ability.
