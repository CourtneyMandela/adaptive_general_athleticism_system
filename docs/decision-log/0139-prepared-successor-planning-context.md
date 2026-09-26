# 0139 — Prepared successor planning context

Date: 2026-09-24

Status: accepted provisionally

Decision version: `prepared-successor-planning-context@1.0.0`

## Decision

Prepare a successor-replanning context from the exact approved initial-planning context that
produced the immutable prior strategy. Resolve that source through its decision audit, require one
approved context draft and review, and verify that its athlete, policy, horizon, review interval,
adaptations, estimates, competency floors, and retained benefit components still match the prior
strategy.

For each actively trained adaptation, replace only the source context's capability-estimate ID with
the exact follow-up estimate referenced by its reviewed `TrainingResponse`. Retain every other
reviewed score, cost, floor, prerequisite, state flag, observation reference, and evidence reference.
For an untrained adaptation, retain its prior estimate only while that estimate remains eligible.
Missing, ambiguous, stale, incompatible, or mismatched history makes the prepared path unavailable
and exposes an issue; it does not cause the system to invent a replacement.

Content-address the resulting candidate contexts, source draft and review, review interval,
applicability rationale, uncertainty, and transformation statement. Pre-populate the reviewer form
from that exact artifact, but keep explicit owner confirmation. Editing any prepared field clears
the binding and enters the existing manual expert path.

When a prepared binding is submitted, the server must reconstruct it at the requested generation
time and require an exact match for both source identities, digest, candidate contexts, review
interval, rationale, and uncertainty before invoking the deterministic replanner. The successor
decision audit retains the source context draft, source review, and prepared digest. Initial-strategy
decisions now also include the created strategy as an explicit evidence reference; older immutable
decisions remain resolvable through their exact decision text.

## Reason

The post-block workflow already had a deterministic replanner, but its browser form required the
owner to re-author eight numeric context fields and four planning flags after every block. That
discarded the reviewed context that produced the prior strategy and invited silent planning drift.

The feedback loop should update athlete state from new observations and estimates, not fabricate a
new planning worldview at every review. Carrying the approved context forward and changing only the
reviewed estimate makes the second strategy meaningfully response-dependent while preserving
inspectable provenance and owner authority.

## Alternatives considered

- Reconstruct all context numbers from the prior priority score. Rejected because the combined cost
  component cannot recover the separately reviewed fatigue, time, and interference inputs.
- Copy the prior strategy's priority score and state directly. Rejected because the new estimate
  must flow through competency-floor detection and the versioned priority policy.
- Ask the owner to type all context fields again. Retained only as the explicit manual fallback for
  histories without one exact approved source artifact.
- Automatically create the successor when a block review is stored. Rejected because successor
  planning remains a material owner-reviewed decision.
- Change source observations or evidence references while replacing the estimate. Rejected because
  the replanner already adds follow-up-estimate and block-review provenance; rewriting the approved
  source context would obscure what was retained.

## Evidence

This is an architecture and governance decision, not a scientific training claim. It implements the
blueprint requirements that derived state retain provenance, personal observations update future
planning, history remain immutable, and planning decisions remain distinct from observations and
estimates.

## Uncertainty

Retaining a planning context assumes its non-estimate judgments remain applicable after one block.
That may cease to be true when goals, schedule, symptoms, prerequisites, or other constraints change.
The prepared path therefore remains optional, visibly identifies exactly what it retained, and
falls back to explicit manual review when the immutable source chain is absent or no longer matches.

The current source lookup scans immutable decision records because the first strategy schema does
not contain a direct context-artifact foreign key. The server verifies the resolved artifact and
fails closed on ambiguity. A future schema version may add a typed direct link without changing the
prepared-context semantics.

## Consequences

- A reviewed block can now produce an exact, inspectable successor-planning proposal without asking
  the owner to invent replacement scores or flags.
- Crossing a competency floor or changing normalized deficit recalculates the need, priority score,
  and state through existing deterministic rules.
- Prepared submissions are protected against stale state and one-field browser tampering.
- Manual expert replanning remains available and visibly loses the digest binding when edited.
- The next product task is to prepare the successor resource demand and second block from the
  immutable successor strategy, then prove that transition in the owner-facing workflow.
