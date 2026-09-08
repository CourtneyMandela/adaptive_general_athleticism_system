# 0089 — Authenticated assessment-governance releases

Date: 2026-09-08

Status: accepted for the owner-only alpha

Decision version: `assessment-governance-release@1.0.0`

## Decision

Add one assessment-reviewer-only production boundary that atomically ratifies a complete,
externally prepared assessment-governance release. A release contains exact publication snapshots,
evidence claims, claim-review content, one self-administered assessment definition, its protocol
review content, and its capability-estimation policy. The request cannot supply approval decisions,
reviewer identities, or record creation times for authority records. The API creates only approved
authority records and binds their reviewer to the authenticated account's exact current
`assessment_reviewer` assignment.

Every authority record is append-only and uses caller-stable UUIDs. Exact retries are idempotent;
reuse of an ID with altered content fails. The complete chain, a canonical SHA-256 content digest,
and a `DecisionRecord` carrying the account and role-assignment identifiers commit in one
transaction only after point-in-time evidence and assessment projections report the chain ready.

The role remains an application permission, not proof of a scientific or professional credential.
For the single-owner alpha, the intended process is: Codex retrieves and prepares exact evidence
and conservative candidate content; the owner sees the complete release and explicitly ratifies
it; the software records that literal authority without describing either party as a clinician or
qualified professional. The endpoint supplies the governed persistence boundary. A later web
workbench must provide the understandable review experience before a real release is submitted.

## Reason

The deployed PWA correctly refuses to invent assessments, estimates, or workouts, but production
had no safe way to move reviewed scientific content into the database. Development bundle importers
are intentionally disabled with external authentication, and automatic production seeding would
make prepared content authoritative without a human decision. Requiring the owner to author raw
JSON, scientific extractions, or policy values would also put the wrong work on the stakeholder and
would be error-prone.

This boundary separates authorship from authority. It lets engineering and research prepare exact,
versioned content while preserving a deliberate human ratification, immutable history, scientific
provenance, and fail-closed runtime behavior.

## Alternatives considered

- **Automatically import approved bundles during deployment.** Rejected because deployment is not
  a scientific-review decision and would make prepared model output authoritative by default.
- **Enable the development CLI in production.** Rejected because it lacks authenticated account and
  role-assignment provenance and weakens the existing production boundary.
- **Ask the owner to author records or edit spreadsheets/JSON.** Rejected because the owner is the
  product stakeholder, not the project's technical or scientific data-entry operator.
- **Persist unreviewed candidates only.** Kept as a possible later workflow, but insufficient alone
  because another safe boundary would still be required to make a reviewed chain operational.
- **Create a general-purpose scientific CRUD API.** Rejected because it would permit partial,
  incoherent authority states and greatly broaden the attack and validation surface.
- **Treat account access as evidence of qualification.** Rejected. The product records literal
  ratifier identity and uncertainty and makes no credential claim.

## Evidence

- `AGENTS.md` requires exact evidence provenance, explicit uncertainty, versioned scientific rules,
  non-LLM authority, and inspectable decisions.
- The existing evidence and assessment projectors already define the point-in-time readiness
  contract used by athlete-facing assessment selection and interpretation.
- The existing operator architecture binds reviewer accounts and exact append-only role assignments
  on the server rather than accepting identity fields from request bodies.

This is an architecture and governance decision, not a scientific training claim.

## Uncertainty

Owner ratification is a practical alpha control and does not substitute for domain-expert review.
The first real release still requires primary-source retrieval, careful extraction, scoped
applicability and uncertainty, and an understandable UI review. No real assessment is approved by
this code change.

## Consequences

- A complete assessment evidence-to-estimate chain can be promoted under external authentication
  without enabling raw production imports or automatic approval.
- Partial failures roll back; exact retries cannot duplicate or rewrite history.
- The release request deliberately supports one assessment at a time, keeping review scope small.
- The next milestone is to research one conservative self-administered assessment, package its exact
  source and candidate content, and build the ratification presentation. Submission remains a
  separate explicit owner action.
