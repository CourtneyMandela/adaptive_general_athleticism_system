# 0058: Authenticated initial-planning review

- Status: accepted
- Date: 2026-08-29
- Decision version: `authenticated-initial-planning-review@1.0.0`

## Decision

Expose first-strategy creation through a narrowly scoped operator HTTP endpoint. The endpoint
requires the current authenticated account to hold an active `planning_reviewer` assignment and
reuses the governed, transactional initial-planning service established by Decision 0037.

The public request omits reviewer identity and role-assignment fields. The server binds
`account:<account-id>` and the exact current assignment to the command, and the resulting immutable
`DecisionRecord` cites that assignment. The service independently verifies the assignment, account,
role, status, currentness, and timestamp. Athlete ownership does not authorize this operation.

Keep the reviewed-file CLI compatible. CLI decisions may omit account-role provenance because
their authority boundary is the local administrative process.

## Reason

Initial planning was already deterministic, governed by exact approved policy and competency-floor
reviews, and protected from athlete writes. It remained usable only through a local JSON/CLI path.
An authenticated reviewer needs the same capability through the application without being able to
claim another reviewer's identity or bypass the existing provenance checks.

## Major implementation choices

- Reuse the existing `planning_reviewer` dependency and append-only role assignments.
- Define a separate untrusted HTTP request model with `extra="forbid"`.
- Bind reviewer identity only after authorization and reject decisions predating the grant.
- Validate authority again inside the persisted service as defense in depth.
- Cite the exact role assignment in decision evidence without coupling authentication state to the
  strategy aggregate.
- Preserve the one-transaction creation of capability needs, strategy, and decision audit.

## Alternatives considered

- Accept `reviewed_by` from the browser. Rejected because it enables identity spoofing.
- Add first-strategy creation to the athlete-owned API. Rejected because reviewed policy,
  scientific applicability, and explicit scoring inputs are not athlete self-service decisions.
- Automatically derive candidate scores from observations. Rejected because no governed mapping
  establishes those values and the blueprint prohibits unsupported authoritative state.
- Build a generic approval framework now. Deferred until concrete multi-party requirements exist.

## Evidence

This is an application-security and auditability decision. The `planning_reviewer` role is an
application permission, not evidence of a scientific, medical, or coaching credential.

## Assumptions

- One authorized reviewer may provisionally author and approve an initial strategy.
- The exact current approved priority-policy and competency-floor reviews remain prerequisites.
- Explicit candidate scores remain reviewed inputs; the system does not infer them in this
  milestone.
- Development bearer authentication remains local-only and production authentication fails closed.

## Unresolved questions

- Which verified credentials and organizational controls qualify a production reviewer?
- Which deployments require separate strategy authors and approvers?
- How should a future reviewer UI explain candidate scores and rejected contexts?
- Should in-progress review drafts be invalidated immediately when an assignment is revoked?

## Consequences

An authorized reviewer can create an athlete's first governed strategy through the API, while the
athlete cannot self-author it and the browser cannot spoof review authority. Historical authority is
reconstructable after later role changes. A reviewer UI and production credentialing remain future
work.
