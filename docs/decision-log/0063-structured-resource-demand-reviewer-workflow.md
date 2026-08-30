# 0063: Structured resource-demand reviewer workflow

- Status: accepted provisionally
- Date: 2026-08-29
- Decision version: `structured-resource-demand-reviewer-workflow@1.0.0`

## Decision

Add a dedicated `/review/resource-demands` route to the reviewer PWA. The route loads the
role-protected strategy preparation projection from Decision 0062 and provides a structured form
for appending one active or deferred resource demand.

The strategy's immutable priority state determines which request shape is legal. A `DEFER`
priority receives a zero-resource form; all other states receive an active-stimulus form. Every
material active input starts unselected or blank: environment, resolver policy, candidate
exercises, movement/loading/laterality constraints, loadability, cost and impact ceilings,
observation and evidence provenance, resource amounts, rationale, uncertainty, and version. The UI
does not derive these values from adaptation metadata and does not preselect catalog items.

Present the full purpose-specific exercise catalog rather than hiding exercises that lack an
ontology link to the selected adaptation. Show primary, secondary, or unlinked metadata as
description only; candidate inclusion remains an explicit reviewer act and the deterministic
resolver remains authoritative for full, partial, or infeasible outcomes.

After submission, display the immutable stimulus, resolution, demand, and decision-audit receipt.
Refresh the preparation projection so prior history remains visible. Keep block creation out of
this route.

## Reason

The authenticated backend boundary is correct but not yet practically usable without assembling a
large JSON document. A structured form makes the next vertical-slice step operable while retaining
the key product distinction between reviewed inputs and deterministic resolution. Blank material
fields prevent interface defaults from becoming hidden scientific or dosing rules.

## Alternatives considered

- Paste reviewed JSON into the existing reviewer console. Rejected as the primary path because it
  preserves manual identifier discovery and makes omissions difficult to inspect.
- Prefill stimulus fields from adaptation `preferred_stimuli`. Rejected because ontology metadata
  is descriptive, not an operational prescription.
- Filter candidate exercises to adaptation matches. Rejected because catalog linkage is not a
  complete candidate-eligibility policy and would conceal potentially useful partial or infeasible
  comparisons.
- Preselect all strategy observations and evidence. Rejected because provenance inclusion is a
  material review judgment.
- Continue directly into block creation. Rejected because demand-history selection, allocation
  policy, budget, dates, duration, and constraints require a separate governed review.

## Evidence

This is a workflow and provenance decision implementing blueprint sections 13, 33–34, 52, 55,
60, 64, 71–72, and 77. It establishes no scientific stimulus, dose, equivalence, or periodization
rule.

## Assumptions and uncertainty

- The current controlled enum vocabulary can be mirrored in the TypeScript form until a generated
  API client or schema-driven control layer is introduced.
- The catalogs are small enough for checkbox presentation; search and pagination will be required
  later.
- Same-account authoring and approval remains provisional under the existing reviewer role.
- Candidate-specific evidence discovery and dedicated stimulus/dose approval artifacts remain
  unresolved.

## Consequences

- A reviewer can advance an approved strategy toward block readiness without external JSON.
- No field silently becomes a scientific recommendation through a UI default.
- Honest partial and infeasible exercise resolution is visible immediately.
- Historical demands remain append-only and no demand is labeled current.
- Block-context review remains the next governed milestone.
