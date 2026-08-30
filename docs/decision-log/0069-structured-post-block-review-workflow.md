# 0069: Structured post-block review workflow

- Status: accepted provisionally
- Date: 2026-08-30
- Extends: Decision 0068
- Decision version: `structured-post-block-review@1.0.0`

## Decision

Add `/review/post-block` as one structured reviewer workflow over the two authenticated closed-loop
boundaries. The first stage displays the exact completed block history and requires an explicit,
complete, non-overlapping prescription partition plus baseline/follow-up estimates, comparison
direction, meaningful-change threshold, intervention context, applicability, and uncertainty. The
second stage displays the resulting reviewed responses and creates one blank candidate editor for
every prior adaptation. Estimate, floor, eight score/cost components, safety and sequencing flags,
prerequisites, provenance, review interval, applicability, and uncertainty remain unset.

Use server time for calculation/review/submission timestamps and server-authenticated identity for
the reviewer. Client validation is advisory; the existing application services remain authoritative
and transactional. Exclude future estimates from block-review preparation and exclude future or
stale estimates from replanning preparation.

## Reason

The closed loop could be exercised through authenticated HTTP but still required external JSON.
The structured route makes the response-dependent second-block path operable in the PWA without
turning presentation defaults into unreviewed training rules. Temporal filtering keeps the read
contract aligned with the write boundary instead of offering choices that are already invalid.

## Alternatives considered

- Prefill one response per adaptation and select its prescriptions automatically. Rejected because
  grouping delivered interventions is part of the reviewed interpretation.
- Prefill scores from the prior strategy. Rejected because response-dependent replanning must make
  the new judgment visible rather than silently copying it.
- Combine review and replanning in one transaction. Rejected because the derived response and block
  outcome should be inspectable before a successor strategy is authorized.
- Allow arbitrary JSON as the primary UI. Rejected because a field-level workflow can expose exact
  eligible lineage and prevent common structural errors without becoming authoritative.

## Evidence

This is a workflow, authorization, and provenance decision implementing blueprint sections 42,
53, 58, 64, 74, 77, and 89. It creates no scientific threshold, training score, or evidence claim.

## Assumptions and uncertainty

- Server time is appropriate for mechanical calculation and decision timestamps; historical
  backfill remains available through the controlled CLI.
- One candidate editor per prior adaptation is a structural requirement of closed-loop replanning,
  not a recommendation to develop every adaptation.
- Context-specific observation/evidence selections may be empty because the backend always merges
  the reviewed block lineage; reviewers can add narrower support when applicable.
- Qualified reviewer credentials and author/approver separation remain unresolved.

## Consequences

- A reviewer can operate the complete response-to-successor-strategy loop through the PWA.
- Every material scientific or planning judgment begins blank and is confirmed explicitly.
- Derived response arithmetic is shown before replanning and remains server-owned.
- The next block can begin from the newly appended strategy without mutating prior history.
