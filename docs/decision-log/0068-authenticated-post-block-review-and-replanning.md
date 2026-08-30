# 0068: Authenticated post-block review and replanning

- Status: accepted provisionally
- Date: 2026-08-30
- Decision version: `authenticated-post-block-loop@1.0.0`

## Decision

Expose completed-block review and review-linked replanning as narrow, role-protected operator HTTP
boundaries. Add read-only preparation projections before both writes. The server derives reviewer
identity from the authenticated `planning_reviewer` account and current append-only role assignment;
clients cannot submit or override it. Persist that assignment ID in each decision record's evidence.

The block-review projection reconstructs every planned week, session container, prescription,
execution, adherence result, post-session safety decision, eligible baseline/follow-up estimate,
review policy, observation, and evidence claim. The replanning projection exposes the reviewed
responses, prior priorities, adaptations, eligible estimates, and compatible competency floors. For
an actively trained adaptation, its reviewed follow-up estimate is the only estimate option.

Retain the existing JSON CLI commands as local administration and recovery paths. Their optional
authority assignment preserves compatibility with already reviewed inputs, while every browser/API
write requires authenticated authority.

## Reason

The persisted feedback loop was complete but could be operated only through local JSON files. The
PWA could not safely prepare or submit a review without recreating provenance joins and authorization
rules in the browser. These projections make missing history and exact eligible inputs visible while
keeping response grouping, thresholds, interpretation, and planning scores explicit reviewer work.

## Alternatives considered

- Let the client submit `reviewed_by`. Rejected because identity is an authorization fact owned by
  the server, not a review input.
- Generate response groupings, thresholds, or successor scores automatically. Rejected because no
  reviewed production rules currently justify those decisions.
- Expose raw domain CRUD. Rejected because it would bypass the transactional history and audit
  invariants in the existing application services.
- Remove the CLI. Deferred because it remains useful for controlled local recovery and fixture-based
  engineering workflows.

## Assumptions and uncertainty

- `planning_reviewer` remains the only operator role in V1; finer review/replanning permissions may
  be separated later.
- Preparation eligibility is structural and provenance-based. It does not establish scientific
  applicability or validate the quality of a reviewer-authored threshold or score.
- A dedicated PWA post-block reviewer screen is the next presentation milestone; this decision
  establishes the backend contract it will consume.

## Consequences

- Athlete ownership alone cannot access post-block preparation or writes.
- Successful HTTP decisions cite the exact role assignment that authorized them.
- Historical blocks, reviews, observations, estimates, needs, and strategies remain append-only.
- The PWA can now build an honest reviewer workflow without calculating training logic locally.
