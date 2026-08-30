# 0061: Governed initial-planning context artifacts

- Status: accepted
- Date: 2026-08-29
- Decision version: `initial-planning-context-artifact@1.0.0`

## Decision

Persist initial-planning candidate inputs as a purpose-specific, append-only draft and require a
separate immutable review decision before that exact draft can create a root strategy. A draft
pins the athlete, policy and policy review, capability estimate, competency floor and floor review,
adaptation, explicit scoring components, flags, provenance, horizon, rationale, uncertainty,
author account, and author role assignment. A review pins its decision, rationale, uncertainty,
reviewer account, reviewer role assignment, and time.

An approved review may create a strategy only from the exact stored draft. The server reconstructs
the existing deterministic planning command, revalidates current authorities and estimate
freshness at creation time, and records both artifact identifiers in the strategy decision audit.
Rejected or needs-revision drafts cannot create strategies. Accepted records are never edited;
revision means authoring a new draft.

V1 permits the same active `planning_reviewer` account to author and approve. Authoring and review
remain separate operations and store separate actor fields so a later deployment can require
separation of duties without rewriting historical records.

## Reason

The preparation projection makes eligible state inspectable, but candidate component values are
still transferred through an external JSON document. Those values materially affect DEVELOP,
MAINTAIN, EXPOSE, and DEFER assignments. Persisting the exact proposal and its decision prevents an
unreviewed or modified browser payload from masquerading as an approved planning judgment.

## Major implementation choices

- Add narrow draft/review application boundaries instead of generic planning CRUD.
- Normalize candidate component values and provenance links in PostgreSQL-oriented tables.
- Treat every draft as immutable; a rejected proposal is replaced, not overwritten.
- Validate eligible inputs when authoring, again when approving, and again when creating strategy.
- Require the approving account and exact active assignment to perform strategy creation.
- Preserve the legacy reviewed-document endpoint and CLI temporarily for compatibility.

## Alternatives considered

- Store only a JSON blob. Rejected because candidate components and provenance are important domain
  semantics that require constraints and queryable lineage.
- Let a review contain replacement values. Rejected because it would obscure what was reviewed;
  changed values require a new draft.
- Require two accounts immediately. Deferred because production qualification and organization
  policy remain unresolved, and development currently has one provisioned reviewer.
- Automatically populate scores from estimates or policy weights. Rejected because no governed
  scientific mapping establishes those athlete-specific judgments.

## Evidence

This is a provenance, authorization, and auditability decision. It introduces no scientific claim
or training relationship.

## Assumptions and uncertainty

- An active planning-reviewer assignment provisionally authorizes both operations.
- Explicit unit-interval component values remain human-reviewed judgments, not measurements.
- A future organization policy may require author and approver separation.
- Draft search, queues, comments, and collaborative editing are intentionally deferred.

## Consequences

Initial planning can move from eligible persisted inputs to an exact auditable proposal, review,
and strategy without external JSON being the authoritative handoff. This adds a migration and
purpose-specific API surface. Legacy direct submission remains available during transition but is
not the preferred PWA workflow.
