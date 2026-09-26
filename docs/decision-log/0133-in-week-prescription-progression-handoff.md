# 0133 — In-week prescription progression handoff

Status: accepted

Date: 2026-09-23

Decision version: `in-week-prescription-handoff@1.0.0`

## Decision

Treat each prescription ID stored by a `SessionTemplate` as the immutable root of the dose lineage
for every planned occurrence of that template. For an unperformed planned session, the effective
prescription is the newest persisted descendant in that lineage. For a completed planned session,
the effective prescription is the exact descendant recorded by its immutable execution.

Session execution may therefore reference an ordered descendant of each template item without
rewriting the template or weekly plan. The execution service resolves the complete persisted
lineage, validates the submitted performance against its current leaf, and calculates adherence
against that same effective prescription. Persistence independently verifies that every executed
item matches the current leaf of its corresponding ordered template lineage.

The current-week projection follows the same boundary: unperformed occurrences display the newest
dose, while performed occurrences continue to display the dose actually executed. A progression
decision from the effective descendant can append the next descendant, allowing repeated in-week
performance and progression to form one linear immutable chain. Existing weekly roll-forward then
carries the final leaf into the next week's template as before.

## Reason

Progression already created an immutable prescription revision, but only weekly roll-forward used
it. Repeated occurrences inside the source week continued to display and record the template's
original dose. That broke the performance-to-next-prescription feedback loop and prevented a second
in-week progression from using the first revised dose.

## Alternatives considered

- Rewrite the current `SessionTemplate` or `WeeklyPlan`: rejected because completed and scheduled
  planning history must remain reproducible.
- Clone a new template immediately after every progression: rejected because the plan still points
  to the original template and occurrence-level supersession semantics do not otherwise exist.
- Let the athlete client choose an arbitrary revised prescription: rejected because prescription
  lineage and progression authority are server-owned.
- Project the newest revision for completed sessions too: rejected because it would misstate the
  dose that produced the recorded performance and adherence.
- Wait until the next week to apply every progression: rejected because multiple governed training
  exposures may occur within one week and the next unperformed exposure should consume the latest
  authorized dose.

## Evidence and owner-review boundary

This is an orchestration, persistence-integrity, and provenance decision implementing blueprint
sections 35–37, 47, 52, 58, 64, and 73. It introduces no exercise, dose, threshold, increment,
scientific claim, safety rule, or automatic owner approval. A descendant can exist only through an
already-authorized immutable progression or reviewed environment-planning decision. Existing
policy review and athlete-safety gates remain unchanged.

## Assumptions and uncertainty

- Prescription revision lineage remains linear; competing descendants continue to fail closed.
- Environment-driven revisions are currently prepared only after source-week closure, so ordinary
  in-week leaf changes are progression-authorized. If mid-week environment substitution is added,
  it must preserve the same explicit reviewed authorizer and occurrence-history rules.
- A stale client submitting an ancestor after a newer leaf exists is rejected rather than silently
  translating its performance payload.
- Correction or voiding of an erroneous progression decision remains unresolved.

## Consequences

- Session 1 can progress the dose displayed and executed by session 2 in the same week.
- Session 2 can create a further immutable revision from the dose it actually performed.
- Completed-session projection, adherence, and progression remain bound to historical execution.
- Weekly roll-forward consumes the final lineage leaf without a second progression mechanism.
