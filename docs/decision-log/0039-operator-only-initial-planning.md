# Decision 0039: Operator-only initial planning

- Status: accepted
- Date: 2026-08-27
- Supersedes: the athlete-accessible transport choice in Decision 0037
- Decision version: `operator-only-initial-planning@1.0.0`

## Decision

Do not expose initial-strategy creation as an athlete-authenticated HTTP write. Keep the
transactional application service, but require every command to include a non-empty reviewer,
applicability rationale, and uncertainty statement. The same transaction that appends capability
needs and the root strategy must append a `DecisionRecord` identifying the result, reviewer,
selected policy, candidate adaptations, estimates, floors, observations, and evidence claims.

Expose this boundary through a local operator CLI that accepts one reviewed JSON input file. The
athlete API remains read-only through planning status until a verified reviewer authorization model
and governed authoring workflow exist.

## Reason

Hiding expert fields in the PWA is not authorization. An authenticated athlete client could still
call the initial-strategy route directly and choose relevance, trainability, transfer, recovery
cost, floor, evidence, and policy inputs. Those values materially determine priorities and cannot
be treated as ordinary athlete self-report.

The operator CLI follows the existing safety-policy assignment and assessment-eligibility pattern:
governance-sensitive state is created outside the athlete transport boundary and remains explicit
and inspectable.

## Alternatives considered

- Leave the route public because the PWA does not render it. Rejected because transport contracts
  are security boundaries; UI omission is not access control.
- Add a shared reviewer secret or special development bearer. Rejected because it would create an
  ad hoc authorization mechanism before verified role/claim support exists.
- Infer contexts and scores from the latest assessment. Rejected because an estimate does not prove
  floor applicability, goal relevance, trainability, transfer, safety, or recovery cost.
- Persist reviewer metadata only in CLI output. Rejected because output logs are not authoritative
  application history and cannot provide transactional traceability.

## Assumptions and provisional choices

- `DecisionRecord` is the existing generic decision audit contract. Its evidence strings carry
  typed identifier prefixes until a dedicated planning-review aggregate is justified.
- Candidate component values remain preserved in the strategy's score components; identifiers and
  review rationale remain in the decision record and strategy provenance links.
- Local operator access is provisional and appropriate only for development/reviewed administration,
  not multi-user production deployment.
- A future reviewer identity/role system may replace the CLI without changing the deterministic
  planner or athlete-facing planning-status projection.

## Evidence and uncertainty

This is an authorization and auditability decision. It introduces no scientific or training claim.
The operator remains responsible for the legitimacy of supplied scientific and athlete-context
inputs.

## Consequences

- Athlete clients cannot submit their own expert planning scores or scientific authorities.
- Every successful root strategy has an atomic decision audit record when created through the
  supported application service.
- Initial planning is less convenient but truthfully blocked on reviewed operator inputs.
- Reviewer authentication, role-based API authorization, and a structured planning-review aggregate
  remain future production work.
