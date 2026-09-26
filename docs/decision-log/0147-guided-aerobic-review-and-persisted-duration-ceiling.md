# 0147 — Guided aerobic review and persisted duration ceiling

## Decision

Compose the exact owner-alpha aerobic assessment, competency floor, resource authority, and
duration-construction authority into one read-only explanation on the planning-governance page.
The composition requires all four exact candidates and disappears rather than presenting a partial
causal story when any candidate is absent.

Keep approval separate:

- the assessment remains reviewable on the assessment-governance page;
- the floor, resource, and construction candidates retain their own exact cards, digests, statuses,
  dependencies, and ratification actions;
- the composed view performs no ratification and creates no athlete plan;
- readiness, symptoms, route or treadmill feasibility, and modality familiarity remain controlling
  after authority review.

Add a persisted duration-progression acceptance contract that records compliant 600-second work,
appends immutable 660- and 720-second prescription revisions, then persists `HOLD` at the reviewed
720-second ceiling. The contract uses the real execution, adherence, post-session safety,
progression, prescription-revision, and repository boundaries.

## Reason

Decision 0146 prepared a complete but distributed aerobic authority chain. The owner needed a
concise answer to “why might AGAS propose this?” without obscuring that four different decisions are
being reviewed. The progression rules also needed proof beyond an isolated planner unit test: the
ceiling must survive persistence and repeated automatic progression across actual planned-session
executions.

## Alternatives considered

- Merge all four candidates into one approval. Rejected because assessment validity, the numeric
  floor, exercise/resource resolution, and dose construction are different authorities with
  different evidence and dependency boundaries.
- Put an approval button on the composed explanation. Rejected because it would create an easy path
  to broad consent without exact-card review.
- Show whichever candidates happen to load. Rejected because a partial chain could imply a floor
  without a governed measure or a dose without reviewed resource feasibility.
- Test the ceiling only in the pure progression engine. Rejected because repository identity,
  immutable supersession, actual duration adherence, post-session safety, and repeated service
  execution are material product boundaries.
- Build one very large candidate-to-third-session test. Deferred because exact candidate
  ratification and first-duration-week preparation already have focused integration contracts. The
  new persisted regression closes the missing repeated-execution boundary while keeping failures
  locally diagnosable.

## Evidence

No new scientific claim is introduced. The UI displays only the already prepared evidence scopes:

- Mayorga-Vega et al. (2016), PMID 26987118, supports criterion-related validity of the 12-minute
  walk/run distance as a field measure, not laboratory VO2 or the 1200-meter floor.
- Garber et al. (2011), PMID 21694556, supports broad individualized aerobic training for apparently
  healthy adults, not the exact modality, duration, effort range, increment, ceiling, or response
  threshold.

Browser and integration tests verify exact four-candidate joining, refusal of a partial
explanation, owner/athlete-aware navigation to the assessment record, direct-meters/no-VO2 wording,
the separate engineering choices, immutable prescription supersession, persisted progression
decisions, and the final ceiling hold.

## Uncertainty

The composed view improves inspectability but is not independent expert review. All numeric values
remain provisional owner-alpha engineering judgments. The persisted acceptance fixture proves the
software behavior of the reviewed policy shape; it does not establish that the dose or progression
is physiologically optimal or safe for a particular athlete on a particular day.

## Consequences

- The owner can understand the complete aerobic path before visiting its exact approval records.
- The app visibly distinguishes direct measurement, scientific support, and provisional engineering
  choices instead of presenting one undifferentiated “why.”
- Candidate status and dependency order remain visible; composition does not bypass governance.
- Duration work is recorded in seconds, retains actual adherence, and never derives dose from the
  assessment's meter value.
- Repeated automatic progression is now covered through 600 -> 660 -> 720 -> HOLD with immutable
  persisted lineage.
- The remaining operational task is hosted deployment and authenticated live-readiness inspection;
  source tests do not establish the hosted database's ratification or current-week state.

## Version/date

- Decision version: `guided-aerobic-review-and-persisted-duration-ceiling@1.0.0`
- Date: 2026-09-25
