# 0074: Local assessment-governance bundle import

- Status: accepted provisionally
- Date: 2026-08-30
- Extends: Decisions 0030, 0034, 0036, and 0073
- Decision version: `assessment-governance-bundle@1.0.0`

## Decision

Add a development-only command-line import boundary for one exact, versioned assessment-governance
bundle. A bundle contains an immutable `AssessmentDefinition`, an optional exact
`AssessmentDefinitionReview`, and an optional `CapabilityEstimationPolicy` bound to that review.
The policy cannot appear without its review. Every record supplies its own stable ID, timestamps,
evidence links, reviewer attribution, uncertainty, and version metadata.

Import all new records in one transaction, let existing repository constraints validate linear
review/policy history and evidence references, and make exact retries idempotent. Reject reuse of an
existing ID with different immutable content. After flushing, run the same point-in-time governance
projection used by the operator workbench and return its readiness and blockers. Refuse this local
boundary in production or external-authentication mode.

## Reason

The workbench can now explain why an assessment is blocked, but there was no supported way to load
externally curated protocol authority other than direct database code. A narrow import command makes
the required data contract inspectable and repeatable without turning a public API or PWA into a
scientific approval system.

Exact IDs and collision checks matter because retried curation must not append duplicate approvals
or silently change a historical record. Reusing the repository and projector ensures that imported
data passes the same evidence, chronology, lineage, measurement, and readiness rules as runtime
assessment behavior.

## Alternatives considered

- Add authenticated browser approval forms. Rejected until reviewer qualification, organizational
  policy, and author/approver separation are specified.
- Import arbitrary SQL or loosely typed JSON. Rejected because it bypasses domain validation and
  makes immutable-content collisions difficult to detect.
- Include new `EvidenceClaim` records in the same bundle. Deferred because evidence ingestion and
  scientific claim review require their own source-verification workflow.
- Automatically mark a structurally valid bundle approved. Rejected; the bundle carries the explicit
  review decisions prepared by the operator.
- Generate default measurement bounds, reassessment intervals, or formulas. Rejected because each is
  a scientific protocol or interpretation claim.

## Assumptions and unresolved questions

- The command is a provisional local curation transport. A reviewer label is inspectable provenance,
  not a verified professional credential.
- Evidence claims must already exist through separately governed ingestion.
- Definition-only and approved-but-incomplete imports are valid and remain visibly blocked.
- Production evidence curation still requires verified identity, source acquisition controls,
  reviewer qualification, and deployment-specific separation of duties.

## Consequences

- Local installations can load real externally reviewed assessment authority without editing code or
  manufacturing seed data.
- Partial governance remains representable and visible rather than being coerced into approval.
- A failed review or policy insert rolls back a newly inserted definition in the same bundle.
- The PWA remains read-only for scientific governance.

## Evidence boundary

This decision defines a data-ingestion and transaction boundary. It does not validate any imported
claim, qualify a reviewer, approve a protocol, establish athlete eligibility, or create a capability
estimate.
