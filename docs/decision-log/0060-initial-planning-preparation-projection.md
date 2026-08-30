# 0060: Initial-planning preparation projection

- Status: accepted
- Date: 2026-08-29
- Decision version: `initial-planning-preparation@1.0.0`

## Decision

Add a role-protected, read-only preparation projection for an athlete's first strategy. At an
explicit instant it returns current capability estimates with their source observations,
domain-compatible adaptations, compatible competency floors with their exact current approved
reviews, current approved priority policies with exact reviews, and the evidence claims referenced
by those offered authorities and adaptations.

Stale estimates remain visible but are not eligible options. Rejected, needs-revision, future, and
superseded authority reviews are excluded. An existing root strategy is reported as a blocking
state. Missing referenced observations or evidence fail the projection rather than disappearing.
The projection contains no candidate relevance, trainability, transfer, cost, or safety values and
performs no write.

## Reason

Decision 0059 made strategy submission usable but still required manual UUID discovery outside the
application. A reviewer should be able to inspect the exact persisted athlete state and governed
authorities from which an explicit planning document may be prepared without granting raw CRUD or
allowing the client to treat stale or withdrawn inputs as eligible.

## Major implementation choices

- Protect the projection with the existing active `planning_reviewer` role.
- Return composed domain records in one purpose-specific projection instead of adding generic list
  endpoints for estimates, floors, policies, observations, adaptations, and evidence.
- Group compatible floors and adaptations beneath each current estimate.
- Include source observations themselves, not only identifiers, so measurement provenance remains
  inspectable.
- Include only evidence already referenced by the offered policies, floors, reviews, adaptations,
  and relationships.
- Keep the server projection time explicit and the frontend read-only.
- Continue to treat backend creation validation as authoritative after review preparation,
  including rejecting an estimate that has become stale by the strategy generation time.

## Alternatives considered

- Expose raw domain CRUD. Rejected because it would bypass the bounded workflow and make later
  governance difficult to enforce.
- Return every scientific claim in the database. Deferred because a growing evidence catalog will
  need search and pagination rather than an unbounded response.
- Pre-fill candidate scores from policy weights or athlete estimates. Rejected because weights
  score reviewed inputs; they do not establish the athlete-specific inputs themselves.
- Hide stale estimates. Rejected because visible staleness helps explain why planning is blocked.

## Evidence

This is a provenance, authorization, and interface decision. It adds no scientific relationship or
training claim.

## Assumptions

- The adaptation catalog is small enough for the current domain-filtered projection.
- Evidence linked to offered authorities and adaptations is the minimum useful preparation set.
- The reviewer still prepares candidate-context values outside the PWA in this milestone.
- An approved application role does not establish professional qualification.

## Unresolved questions

- How should reviewers search a large evidence catalog for additional candidate-specific claims?
- What governed workflow should author, challenge, and approve candidate-context component values?
- Should preparation snapshots be persisted when separate authors and approvers are introduced?
- Which withdrawn or historical authorities should be available in an audit-only view?

## Consequences

The reviewer console can now retrieve and explain eligible persisted inputs without manual database
lookup. It remains unable to fabricate candidate scores and cannot create a second root strategy.
No database migration is required.
