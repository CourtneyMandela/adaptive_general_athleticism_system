# 0096 — System-prepared initial-planning context

Date: 2026-09-10

Status: accepted for the single-owner alpha

Decision version: `prepared-initial-planning-context@1.0.0`

## Decision

Replace the owner-facing blank initial-planning score grid with a server-prepared, content-addressed
candidate for the one currently governed owner-alpha path. The candidate is available only when the
athlete has exactly one current 30-second chair-stand estimate, the exact current approved age-30-to-
39 floor, the exact current approved deficit-only policy, and the domain-matched muscular-endurance
adaptation.

The eight contextual benefit and cost fields remain explicit zeros, and the selected policy gives
each zero weight. Each field is presented with a basis and limitation explaining that zero means
“unused because no governed magnitude exists,” not “measured as absent.” The exact estimate,
observations, floor and review, policy and review, adaptation, evidence claims, horizon, review
interval, rationale, uncertainty, expected priority state, expected score, and safety boundary are
shown before acceptance.

Acceptance sends only the candidate schema version, SHA-256 content digest, and a true attestation.
The server recomputes current eligibility and stores an immutable draft whose deterministic UUID is
derived from the exact candidate content and active reviewer assignment. Exact retries return the
same draft. A stale digest, changed athlete state, authority change, or occupied identity fails
closed. Draft review and strategy creation remain separate immutable operations; the PWA supplies
prepared review rationale and uncertainty instead of asking the owner to write scientific prose.

## Safety semantics

The legacy field `safe_to_train=true` is retained because it is a hard planner gate, but this
candidate defines it narrowly: no planning-level deferral is asserted for inclusion in a long-range
strategy. It is not medical clearance, an assertion that a workout is safe, or current session
readiness. The existing session safety gate remains mandatory before performance.

`prerequisites_met=true` means the current ontology contains no prerequisite relationship for this
adaptation. It is not a universal biological claim. `introductory_exposure_needed=false` avoids
inferring training inexperience from absent application history; later exercise and dose governance
may still choose an introductory prescription. Comparative advantage is not asserted.

## Reason

The previous UI assigned engineering and evidence-synthesis work to the owner by requiring eight
unexplained numbers, safety and prerequisite flags, and two narrative fields. That path was auditable
but not practically usable and encouraged unsupported values. The new boundary lets engineering
prepare what the system can defend while keeping an explicit human approval and immutable history.

## Alternatives considered

- **Auto-create the strategy when the floor is approved.** Rejected because policy authority,
  athlete-specific context acceptance, context review, and strategy creation are distinct decisions.
- **Keep the editable score grid as an advanced option.** Rejected from the primary path because it
  makes unsupported numbers easy to introduce. The legacy reviewed-JSON endpoint remains only for
  compatibility and controlled testing.
- **Interpret every zero as a neutral score under a nonzero policy weight.** Rejected because that
  would materially suppress ranking while pretending missing evidence is negative evidence.
- **Infer goal relevance from free text with an LLM.** Rejected because no reviewed deterministic
  mapping or provenance structure exists yet.
- **Treat prior assessment readiness as workout clearance.** Rejected because the assessment screen
  explicitly authorizes only a time-bounded low/moderate assessment selection.
- **Create the block and workout in the same acceptance.** Rejected because stimulus, resource,
  exercise, dose, schedule, and session safety remain separate governed layers.

## Assumptions and provisional choices

- The candidate is deliberately hard-coded to exact authority versions and one adaptation identity;
  broader dynamic preparation requires machine-readable policy applicability and richer provenance.
- Twelve months and a 28-day first review interval are operational owner-alpha defaults. The latter
  aligns with the current assessment reassessment cadence but is not a universal programming rule.
- The content identity includes the active reviewer assignment, preventing a different authority
  from silently adopting an earlier account's draft.
- The deterministic draft is append-only; a materially changed estimate or authority produces a new
  candidate identity rather than editing history.

## Unresolved questions

- Should the domain rename `safe_to_train` to distinguish strategic inclusion from session safety?
- What structured evidence object should support nonzero goal, transfer, trainability, and cost
  judgments in future multi-domain planning?
- When should separate author and approver accounts become mandatory?
- Which introductory-dose policy should govern the first block without assuming training history?

## Consequences

- The owner no longer authors planning scores or scientific rationale.
- The app can now move from the governed chair-stand estimate to a reviewed initial strategy through
  visible, resumable PWA steps.
- No workout is generated by this milestone.
- The next practical blocker is a similarly prepared resource-demand and first-block candidate for
  the resulting muscular-endurance priority.
