# Adaptive General Athleticism System

[![CI](https://github.com/CourtneyMandela/adaptive_general_athleticism_system/actions/workflows/ci.yml/badge.svg)](https://github.com/CourtneyMandela/adaptive_general_athleticism_system/actions/workflows/ci.yml)

AGAS is an evidence-grounded, adaptive system for developing broad general athleticism. This repository is intentionally building the inspectable domain and feedback loop before workout generation or polished product features.

The current foundation includes controlled ontology vocabulary, a cross-reference-validated small
seed catalog, and a tested home/travel/return counterfactual. Temporary equipment changes can
select a newer exercise resolution without changing athlete identity or adaptation intent; partial
fidelity remains explicit and policy-gated. Session templates, safety decisions, execution,
adherence, training response, and block review remain immutable and provenance-preserving.
Reviewed follow-up estimates can regenerate capability needs and a replacement long-range
strategy through an operator-reviewed closed-loop replanning boundary. Each revision retains the exact
prior strategy and triggering review without inferring causation or rewriting athlete history.
An initial or revised strategy can then create a persisted block only from already-governed
resource demands, exercise resolutions, and an explicit allocation policy.
Assessment definitions now have a separate, append-only evidence review history. Only definitions
whose latest review is approved and whose cited claims were evidence-ready at that review time can
appear in the API catalog or authorize a new athlete action. Operational self-service selection
additionally requires a reviewed, versioned measurement schema; no real assessment protocols are
seeded yet.
Assessment interpretation policies are now append-only, evidence-linked records bound to exact
reviewed protocols. An authenticated, idempotent boundary can derive a protocol-specific estimate
from governed performances without treating a result as a direct capability fact or applying norms.
Persisted estimates can now cross a separate governed boundary into identified capability needs
and the athlete's first long-range strategy. The request supplies explicit, inspectable planning
contexts; it does not infer scores, select exercises, prescribe dose, or generate a workout.
An owned athletic-dashboard projection groups estimates by exact domain, scope, and unit, exposes
confidence, validity, method, version, and source lineage, and keeps unmeasured domains explicit.
It deliberately does not normalize unlike measurements into unsupported percentage scores.
Scientific publication metadata can now be stored as immutable, versioned retrieval snapshots.
New governed claim bundles link every claim to the exact source snapshots reviewed, while the
existing small seed remains explicitly provisional and unpromoted.

The blueprint's required first vertical slice is now protected by one automated integration
scenario. A synthetic sedentary four-day athlete moves from intake and assessment-derived state
through strategy, a four-week block, full-gym training, one explicitly lower-fidelity hotel week,
return, safety-gated execution, deterministic progression, reassessment, block review, revised
priorities, and a dependent second block. All fixture thresholds and doses remain test-only and
are explicitly not production training rules.

## Architecture at a glance

- `apps/web`: responsive Next.js interface foundation
- `services/api`: FastAPI application and persistence boundary
- `services/planner`: deterministic assessment, planning, scheduling, execution, and adherence logic
- `services/evidence`: PubMed source retrieval and metadata parsing boundary
- `packages/domain`: versioned domain models and invariants
- `packages/exercise_ontology`: exercise ontology boundary
- `packages/adaptation_models`: adaptation ontology boundary
- `packages/safety`: deterministic safety-policy boundary
- `packages/seed_data`: validated loader for the small versioned repository seed catalog
- `packages/evaluation`: counterfactual and anti-sludge evaluation boundary
- `tests`: domain and persistence tests
- `docs`: product specification, policies, architecture, and decision records

See [docs/architecture.md](docs/architecture.md) for boundaries and data flow.

## Prerequisites

- Python 3.12+
- Node.js 22+
- pnpm 11.19+
- Docker with Compose (for local PostgreSQL)

## Install dependencies

```bash
python -m venv .venv
```

Activate the environment, then:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pnpm install
```

Copy `.env.example` to `.env` if you need to override defaults.

## Start local services

```bash
docker compose up -d postgres
```

Apply the database migration:

```bash
alembic upgrade head
```

The checked-in baseline is frozen. Controlled ontology fields and strategy-revision lineage are
added through incremental revisions; future schema changes must continue to append revisions.

Validate the repository seed catalog without loading it into an athlete database:

```bash
python -c "from agas_seed_data import load_seed_catalog; print(load_seed_catalog().manifest)"
```

After migrating PostgreSQL, import the validated global catalog and its audit receipt:

```bash
python -m agas_api.seed
```

The command is idempotent for the exact catalog version. It does not import the synthetic athlete.

For a deterministic local walkthrough, import the catalog, create the repository-owned synthetic
traveler with its reported home/travel equipment, register its local owner, and grant the separate
planning-reviewer and assessment-reviewer identities in one development-only command:

```bash
python -m agas_api.demo bootstrap
```

The command is idempotent and prints machine-readable JSON containing the athlete ID, local bearer
selectors, direct PWA path, reviewer path, and derived planning status. It refuses production or
external-authentication configurations. It intentionally stops at `capability_estimate_required`:
no capability score, scientific approval, policy, dose, or workout is fabricated for the demo.
After starting both applications, open the returned `athlete_path` under `http://localhost:3000`
or the returned reviewer path.

## Run the backend

```bash
uvicorn agas_api.main:app --reload
```

The health endpoint is available at `http://localhost:8000/health`.

Local development uses the explicit bearer `dev.local-browser` by default. It selects a local
account identity; it is not a password or production authentication. `AGAS_AUTH_MODE=development`
is rejected when `AGAS_ENVIRONMENT=production`. External mode verifies an asymmetric JWT against
one explicitly configured issuer, audience, JWKS endpoint, and algorithm allow-list. Production
startup fails unless that complete configuration uses HTTPS. Browser login and provider selection
are still separate deployment work. Production browser requests use a same-origin server gateway;
its encrypted `HttpOnly` session will hold the provider access token after a login adapter exists.
Do not place provider secrets or access tokens in `NEXT_PUBLIC_*` variables.

The application endpoints are intentionally narrow:

```text
GET  /v1/onboarding/equipment
GET  /v1/assessments/catalog
POST /v1/onboarding/athletes
GET  /v1/athletes/{athlete_id}/assessment-workflow
POST /v1/athletes/{athlete_id}/assessment-runs
POST /v1/athletes/{athlete_id}/assessment-runs/{run_id}/selections/{selection_id}/result
POST /v1/athletes/{athlete_id}/assessment-performances/{performance_id}/capability-estimate
GET  /v1/athletes/{athlete_id}/dashboard
GET  /v1/athletes/{athlete_id}/environments
POST /v1/athletes/{athlete_id}/environments/{environment_id}/equipment-reports
GET  /v1/athletes/{athlete_id}/planning-status
GET  /v1/athletes/{athlete_id}/current-week?on=YYYY-MM-DD
GET  /v1/operator/environment-review-queue
GET  /v1/operator/assessment-governance
GET  /v1/operator/planning-review-queue
GET  /v1/operator/post-block-review-queue
GET  /v1/operator/athletes/{athlete_id}/initial-planning-preparation
POST /v1/operator/athletes/{athlete_id}/initial-planning-context-drafts
POST /v1/operator/initial-planning-context-drafts/{draft_id}/reviews
POST /v1/operator/initial-planning-context-reviews/{review_id}/strategy
POST /v1/operator/athletes/{athlete_id}/initial-strategies
GET  /v1/operator/strategies/{strategy_id}/resource-demand-preparation
POST /v1/operator/strategies/{strategy_id}/priorities/{priority_id}/resource-demands
GET  /v1/operator/strategies/{strategy_id}/block-preparation
POST /v1/operator/strategies/{strategy_id}/blocks
GET  /v1/operator/blocks/{block_id}/first-week-preparation
POST /v1/operator/blocks/{block_id}/first-week-plans
GET  /v1/operator/blocks/{block_id}/review-preparation
POST /v1/operator/blocks/{block_id}/reviews
GET  /v1/operator/block-reviews/{block_review_id}/replanning-preparation
POST /v1/operator/block-reviews/{block_review_id}/replanning
POST /v1/operator/stimulus-requirements/{stimulus_requirement_id}/exercise-reresolutions
POST /v1/operator/weekly-plans/{source_weekly_plan_id}/environment-prescription-revisions
POST /v1/weekly-plans/{weekly_plan_id}/availability-confirmations
POST /v1/weekly-plans/{weekly_plan_id}/roll-forward
POST /v1/weekly-plans/{weekly_plan_id}/sessions/{planned_session_id}/safety-checks
POST /v1/weekly-plans/{weekly_plan_id}/sessions/{planned_session_id}/executions
POST /v1/session-executions/{session_execution_id}/prescriptions/{prescription_id}/progression
```

Onboarding creates one non-sensitive athlete profile, one provenance-bearing direct user report,
one or more environments, and append-only equipment-availability events in a single transaction.
Selections must reference the persisted equipment catalog. It does not create capability estimates,
choose a safety policy, run an assessment, or generate a workout. The authenticated account and
immutable athlete ownership are created in the same transaction.

After onboarding, the owned environment projection reports every catalog item as available,
unavailable, or unknown at an explicit instant. An equipment report is a partial change set: the
backend atomically appends one direct observation and effective-dated availability events linked to
that observation. Omitted equipment is not silently marked unavailable. Temporary events may
expire and reveal older still-effective state. Recording a change does not rewrite an immutable
session or claim an exercise substitution is equivalent; resolver-backed re-authoring remains a
separate governed workflow.

All athlete-scoped endpoints require bearer authentication and verify aggregate ownership. Health,
readiness, the global onboarding equipment catalog, and the reviewed assessment catalog remain
public. The assessment catalog is empty until definitions have current approvals backed by exact
source snapshots and claim approvals that existed at the protocol-review time; the API cannot
approve protocols. To grant a pre-existing local fixture athlete to the default
development account, run:

```bash
python -m agas_api.identity_admin grant --athlete-id YOUR_ATHLETE_UUID
```

There is deliberately no public endpoint for claiming an arbitrary athlete ID.

Planning-reviewer access is separate from athlete ownership. For local development, bootstrap and
later revoke the only current administrative role with append-only assignment history:

```bash
python -m agas_api.identity_admin grant-role \
  --subject local-reviewer \
  --role planning_reviewer \
  --rationale "Local reviewed-planning workflow"

python -m agas_api.identity_admin revoke-role \
  --subject local-reviewer \
  --role planning_reviewer \
  --rationale "Local reviewer access removed"
```

Assessment governance has a separate application role. The demo bootstrap grants it to
`local-assessment-reviewer`; it can also be managed explicitly:

```bash
python -m agas_api.identity_admin grant-role \
  --subject local-assessment-reviewer \
  --role assessment_reviewer \
  --rationale "Local assessment-governance inspection"
```

This permission is not a scientific credential. The role-protected
`GET /v1/operator/assessment-governance` projection and `/review/assessments` workbench are
read-only. They expose point-in-time protocol review, measurement schema, self-administration,
capability-estimation policy, immutable history, and the readiness of every cited evidence claim at
the authority record's own review time. They do not create protocol approvals or athlete
eligibility decisions.

The evidence service can search PubMed and retrieve one reviewable metadata snapshot through
NCBI E-utilities. NCBI requires a developer contact and applies usage limits; the adapter makes one
request per command and caps search output at 100 records:

```bash
python -m agas_evidence.pubmed --email YOUR_DEVELOPER_EMAIL search \
  --query "resistance training[Title] AND systematic review[Publication Type]" \
  --max-results 20

python -m agas_evidence.pubmed --email YOUR_DEVELOPER_EMAIL fetch \
  --pmid PMID_FROM_SEARCH \
  --query "THE_EXACT_SEARCH_QUERY"
```

`AGAS_NCBI_EMAIL` and optional `AGAS_NCBI_API_KEY` environment variables may replace those global
arguments. Search returns PMIDs; fetch returns one structured `EvidenceSource` JSON object. Neither
command persists data, extracts a claim, or rates evidence. Review NCBI's
[E-utilities usage guidance](https://www.ncbi.nlm.nih.gov/books/NBK25497/) and
[disclaimer/copyright notice](https://www.ncbi.nlm.nih.gov/home/about/policies/) before use;
PubMed abstracts can contain copyrighted material.

Externally reviewed scientific metadata and claims can then be loaded in local development
through a separate versioned bundle. Inspect the schema before preparing a file:

```bash
python -m agas_api.evidence_governance_admin schema
python -m agas_api.evidence_governance_admin import-bundle \
  --input-file PATH_TO_EVIDENCE_GOVERNANCE_BUNDLE.json
```

Each claim must cite one or more bundled immutable source snapshots, and its PMID/DOI-style
identifiers must agree with those snapshots. Exact retries are no-ops; identifier lineage,
immutable-content collisions, dangling references, and partial writes fail closed. This command
does not search literature, judge study quality, qualify a reviewer, or grant production approval.
It is disabled in production and external-authentication mode.

Externally curated assessment authority can be loaded in local development through a versioned,
idempotent bundle. First inspect the exact JSON contract, then import a prepared file:

```bash
python -m agas_api.assessment_governance_admin schema
python -m agas_api.assessment_governance_admin import-bundle \
  --input-file PATH_TO_ASSESSMENT_GOVERNANCE_BUNDLE.json
```

The bundle contains one immutable definition, an optional exact review, and an optional estimation
policy. Policy import requires its exact review in the same bundle. A new approved review or policy
must cite claims that already had exact source snapshots and an approved `EvidenceClaimReview` at
that authority's own review time. A later evidence approval is not retroactive; a new authority
review is required. Exact retries are no-ops; an existing ID with different content is rejected,
and any failed insert rolls back the bundle. The command refuses production and external-
authentication configuration. It transports reviewed data but does not verify source authenticity
or reviewer credentials.

An active reviewer may load the read-only initial-planning preparation projection, author an
immutable candidate-context draft, record one immutable review of that exact draft, and create the
root strategy only from an approved review. Draft and review endpoints bind the authenticated
account and exact active role assignment; actor identifiers are not accepted from the browser.
Strategy creation reloads the artifact and revalidates current policy/floor approvals and estimate
freshness. Rejected and needs-revision drafts remain history and require a new draft.

Initial planning requires explicit candidate scores and the exact current approved policy and
competency-floor reviews. The preparation projection returns current estimates, source
observations, compatible approved floors and adaptations, approved policy options, and their
referenced evidence while separating stale state and existing strategy blockers. No boundary
infers scores, selects exercises, or generates workouts. The legacy direct initial-strategy POST
and reviewed-file CLI remain available during transition. The environment queue is derived from
weekly plans whose confirmed next-week environments do not match their effective prescription
resolutions. The environment-review POST routes complete that narrow workflow by invoking the same
deterministic re-resolution and prescription-revision services as the local CLIs. Their request
bodies deliberately omit `reviewed_by` and role-assignment fields: the server binds the
authenticated account and exact current role grant to the immutable decision audit. Athlete
ownership does not grant access, revoked roles fail closed, and a decision cannot predate its
authorizing grant. Same-account authoring and approval is provisional; production credential
validation and author/approver separation remain unresolved, while actor identities are stored
separately.

The same active role may load one strategy-specific resource-demand preparation projection and
submit an active or deferred demand through the operator API. The projection returns exact strategy
priorities, adaptations, prior demand history, strategy-linked observations and evidence, current
environment snapshots, resolver policies, and the structured exercise catalog. It does not select
a stimulus, environment, exercise candidate set, dose, or current demand. The write request also
omits reviewer identity and role-assignment fields; the server binds both to the immutable decision
audit and the application service revalidates the grant.

The reviewer may then load the strategy-specific block-preparation projection and submit one
explicit block context. The projection returns every priority's immutable demand history, allocation
policies, existing blocks, and referenced observations and evidence without marking any history
current. The request selects exactly one demand per priority and supplies the policy, weekly budget,
dates, duration, constraints, applicability, and uncertainty. Reviewer identity remains server-owned
and the application service revalidates the exact role assignment before appending the block and
decision audit.

Safety policy applicability is also governed rather than user-selectable. After a reviewed policy
exists, a local operator can assign it to an owned athlete with:

```bash
python -m agas_api.safety_policy_admin assign \
  --athlete-id YOUR_ATHLETE_UUID \
  --safety-policy-id YOUR_REVIEWED_POLICY_UUID \
  --assigned-by "REVIEWER_OR_OPERATOR" \
  --applicability-rationale "WHY_THIS_REVIEWED_POLICY_APPLIES"
```

Replacements append a sequenced predecessor-linked assignment. The PWA and session API resolve the
current assignment from the athlete; clients cannot choose a policy ID per safety report.

Assessment eligibility is likewise governed outside the athlete-facing API. After reviewing direct
observations through an appropriate process, a local operator can append a time-bounded decision:

```bash
python -m agas_api.assessment_eligibility_admin \
  --athlete-id YOUR_ATHLETE_UUID \
  --outcome selection_allowed \
  --source-observation-id REVIEWED_OBSERVATION_UUID \
  --valid-until 2026-09-30T12:00:00Z \
  --reviewed-by "REVIEWER_OR_OPERATOR" \
  --screening-process-reference "REVIEWED_PROCESS_REFERENCE" \
  --rationale "WHY_ASSESSMENT_SELECTION_IS_ALLOWED" \
  --uncertainty "KNOWN_LIMITS_OF_THIS_REVIEW"
```

This record authorizes assessment selection only; it is not a diagnosis or medical clearance. The
authenticated assessment-run endpoint accepts non-medical body-mass, training-history, skill, and
exposure context plus an owned environment. It derives current equipment availability from the
database and persists the direct context observation, deterministic decisions, exact protocol and
eligibility authorities, and selection run atomically. Clients cannot submit injury, symptom,
health-classification, or equipment-category fields through this endpoint.

A selected decision can record one initial result through its run-scoped endpoint. The server
requires the exact protocol and eligibility authorities to remain current, verifies the definition
unit and reviewed measurement schema, and atomically stores an `AssessmentPerformance` plus a
direct test-result observation.
Deferred decisions, duplicate submissions, future performance times, and stale authority fail
closed. Result recording does not interpret the value or create a capability estimate.

Capability interpretation is a separate request. The server resolves the current approved
`CapabilityEstimationPolicy`; the client cannot send a formula, confidence, source list, or derived
value. Sources are restricted to governed performances of the same exact protocol. Retries under
the same performance and policy return the existing immutable estimate. If no policy exists, the
direct observation remains valid and the workflow reports interpretation as unavailable.

After recording, the backend derives the next self-service reassessment time from the exact review
that authorized the latest performance. Protocols with no performance are due immediately; tested
protocols are withheld until their reviewed interval ends. Early runs and competing runs with a
selected result still awaiting completion fail before a new context observation is stored. Future
selection timestamps cannot be used to bypass the interval.

The authenticated assessment-workflow projection derives readiness and latest-run status from that
immutable history. The PWA renders prerequisite, empty-catalog, deferred, result-ready, blocked,
and completed states and can submit a new non-medical selection context only when the backend
authorizes it. It shows reviewed instructions, uncertainty, and evidence identifiers. Generic PWA
result entry is rendered only for selected protocols with reviewed number, integer, or categorical
measurement schemas; the server validates the same versioned contract again before persistence.
The panel shows due/not-due reassessment state and the next reviewed interval end without treating
that schedule as a capability interpretation. It presents recorded measurement and derived
protocol-specific estimate as separate records, including confidence, validity, method, rule
version, applicability, uncertainty, and evidence count.

Post-block review and replanning reconstruct persisted execution and review history, then
atomically append their derived records and reviewer-attributed decision audits. Their scientific
interpretation and strategy-scoring inputs are operator-only; raw review, strategy, and need CRUD
is not exposed. Resource-demand preparation and block creation are likewise role-protected operator
application boundaries; they do not invent stimuli, exercise candidates, dose-resource targets,
allocation budgets, dates, or constraints.

Initial-strategy creation is similarly narrow: it resolves persisted estimates, evidence-linked
competency floors, adaptations, and a versioned priority policy, then requires the exact current
approved review for every floor and the policy before atomically appending deduplicated needs and
exactly one root strategy. Reviews are append-only, evidence-linked, reviewer-attributed histories;
a later rejection or needs-revision decision fails closed for new strategies. Candidate relevance,
trainability, transfer, and cost values must be supplied by a reviewed operator and retain their
source observations and evidence. The same transaction appends a `DecisionRecord` containing
reviewer, rationale, uncertainty, exact authority-review IDs, and result identity. Competing root
strategies fail at both repository and database boundaries. Athlete-authenticated clients cannot
call this write boundary.

Before initial planning, a local operator records the reviewed authority decisions (repeat the
command with a new decision to append a superseding review):

```bash
python -m agas_api.planning_governance_admin review-floor \
  --competency-floor-id FLOOR_UUID \
  --decision approved \
  --evidence-claim-id EVIDENCE_UUID \
  --reviewed-by REVIEWER \
  --applicability-rationale "Reviewed applicability rationale" \
  --uncertainty "Known uncertainty" \
  --review-version floor-review@1.0.0

python -m agas_api.planning_governance_admin review-priority-policy \
  --priority-policy-id POLICY_UUID \
  --decision approved \
  --evidence-claim-id EVIDENCE_UUID \
  --reviewed-by REVIEWER \
  --applicability-rationale "Reviewed applicability rationale" \
  --uncertainty "Known uncertainty" \
  --review-version priority-policy-review@1.0.0

python -m agas_api.planning_governance_admin review-weekly-scheduling-policy \
  --weekly-scheduling-policy-id SCHEDULING_POLICY_UUID \
  --decision approved \
  --evidence-claim-id EVIDENCE_UUID \
  --reviewed-by REVIEWER \
  --applicability-rationale "Reviewed applicability rationale" \
  --uncertainty "Known uncertainty" \
  --review-version weekly-scheduling-policy-review@1.0.0
```

After preparing and reviewing a JSON document, an active reviewer may submit the same explicit
planning inputs (without `reviewed_by` or `review_authority_assignment_id`) to
`POST /v1/operator/athletes/{athlete_id}/initial-strategies`. The server supplies both fields from
the authenticated account and exact active role grant. The local administrative alternative is:

```bash
python -m agas_api.initial_planning_admin \
  --athlete-id YOUR_ATHLETE_UUID \
  --input-file PATH_TO_REVIEWED_INITIAL_PLANNING.json
```

The request or local document must name the persisted priority policy and its exact current
`priority_policy_review_id`, plus at least one explicit candidate context, `generated_at`,
`horizon_months`, `review_after_days`, `applicability_rationale`, and `uncertainty`; the local
document additionally supplies `reviewed_by`. Each context must name its adaptation, competency
floor, exact current `competency_floor_review_id`, capability estimate, component values, and
provenance identifiers. The HTTP workflow has authenticated application authorization but remains
provisional single-reviewer approval, not production credential verification.

Strategy-to-block authoring uses a second reviewed workflow. The local CLI documents must include
non-empty `reviewed_by`, `applicability_rationale`, and `uncertainty` fields in addition to their
explicit planning inputs:

```bash
python -m agas_api.planning_authoring_admin prepare-demand \
  --strategy-id YOUR_STRATEGY_UUID \
  --priority-id YOUR_PRIORITY_UUID \
  --input-file PATH_TO_REVIEWED_RESOURCE_DEMAND.json

python -m agas_api.planning_authoring_admin reresolve-exercise \
  --stimulus-requirement-id YOUR_STIMULUS_REQUIREMENT_UUID \
  --input-file PATH_TO_REVIEWED_EXERCISE_RERESOLUTION.json

python -m agas_api.planning_authoring_admin create-block \
  --strategy-id YOUR_STRATEGY_UUID \
  --input-file PATH_TO_REVIEWED_BLOCK_PLAN.json
```

Active resource-demand inputs name the stimulus, environment, exercise candidates, resolver policy,
resource amounts, frequency, provenance, version, and preparation time. Deferred inputs preserve
their zero-resource rationale and provenance with the same review metadata and preparation time.
An active reviewer may submit the same active or deferred resource input, without `reviewed_by` or
`review_authority_assignment_id`, to
`POST /v1/operator/strategies/{strategy_id}/priorities/{priority_id}/resource-demands`; the server
owns those authority fields. The block-preparation projection and
`POST /v1/operator/strategies/{strategy_id}/blocks` use the same authority boundary. The block
request omits reviewer fields and explicitly names one demand per priority, allocation policy,
weekly budget, dates, duration, constraints, applicability, and uncertainty.
Re-resolution inputs name a different athlete-owned environment, explicit reviewed candidate set,
resolver policy, and resolution time for an existing immutable stimulus. The command appends an
honest full, partial, or infeasible result and its decision audit; it does not change the stimulus,
prior resolution, demand, block, dose, or weekly plan.
Block inputs name the exact persisted demand history and allocation policy plus budget, dates,
duration, constraints, and generation time. Each command atomically appends its result and a
reviewer-attributed `DecisionRecord`. Athlete-authenticated clients cannot call these boundaries.

The read-only planning-status endpoint and PWA panel make this handoff visible. They distinguish no
estimate, stale estimates, missing approved planning authorities, approved authorities awaiting
athlete-specific context review, and the governed path from a persisted strategy to its first
block. After strategy creation, the projection reports priority demand coverage, policy-gated
exercise-resolution eligibility, pending block-context review, a persisted feasible or partial
block, an infeasible block, or ambiguous multiple-block history. For one feasible block it then
reports current approved scheduling-policy readiness, the remaining explicit
prescription/session/availability
context, a feasible or infeasible first week, and ambiguous duplicate week-one history. It never
silently selects one of multiple demands, blocks, or first-week plans. Explicit checklists report
the unresolved boundary while leaving exact demand history, allocation policy, budget, dates,
duration, prescriptions, session composition, availability, and scheduling policy to the operator.
The panel never treats structural compatibility as athlete applicability or turns missing
governance into an athlete-facing plan-generation control.

Operator-only resource-demand preparation bridges those use cases without exposing raw CRUD.
Active priorities require an explicit stimulus specification, environment, candidate exercises,
resolver policy, resource amounts, and review provenance. Deferred priorities produce a reviewed,
provenance-bearing zero-resource demand. Partial or infeasible exercise resolution remains visible
rather than being replaced silently.

Weekly-plan creation is an operator-only boundary. It accepts explicit prescription doses, explicit
session composition, dated availability, a persisted scheduling policy and its exact current
approved review, reviewer identity, applicability rationale, and uncertainty. It derives exercise
and adaptation identity from the block, schedules deterministically, and atomically appends the
complete chain plus a provenance-bearing `DecisionRecord`. It does not generate a generic workout
from an adaptation name, and athlete-authenticated clients cannot submit these expert inputs. A
persisted policy without a current approved review is not scheduling authority.

After preparing and reviewing a JSON document that satisfies `CreateWeeklyPlanCommand`, a local
operator runs:

```bash
python -m agas_api.weekly_planning_admin \
  --block-id YOUR_BLOCK_UUID \
  --input-file PATH_TO_REVIEWED_WEEKLY_PLAN.json

python -m agas_api.weekly_revision_admin \
  --source-weekly-plan-id YOUR_CLOSED_WEEKLY_PLAN_UUID \
  --input-file PATH_TO_REVIEWED_ENVIRONMENT_REVISIONS.json
```

The document must contain at least one prescription for every active block allocation, one or more
explicit session templates, an observation-backed dated availability record, the exact persisted
`scheduling_policy_id`, its exact current `scheduling_policy_review_id`, a timezone-aware
`prepared_at`, and non-empty `reviewed_by`,
`applicability_rationale`, and `uncertainty` fields. The command persists feasible and infeasible
scheduling results alike so limitations remain inspectable. This local workflow is provisional; it
does not replace production administrative identity and role authorization.

The environment-revision command and role-protected operator endpoint are a separate next-week
planning step. Its source plan must be
fully closed, and the athlete must first persist next-week availability that exposes an unresolved
environment. Each replacement names a source-plan prescription, a newer
full or policy-permitted partial resolution for the same stimulus, and a complete reviewed dose.
It appends a prescription successor authorized by an operator `DecisionRecord`; it does not claim
that workout progression authorized the substitution and does not mutate the source week. The
ordinary roll-forward boundary subsequently consumes this lineage and schedules it only when the
confirmed next-week availability contains the resolved environment.

The HTTP reviewer contracts do not choose candidate exercises or replacement doses. Those remain
explicit reviewed inputs, and the backend continues to validate environment feasibility,
immutable stimulus/adaptation lineage, scheduling policy, source availability, and complete dose
structure. The local CLIs remain available for development administration.

Session recording first appends an explicit user-report observation and deterministic safety
decision. Execution then requires the latest pre-session decision, accepts actual performed-set
data, and atomically appends the workout-result observation, immutable execution, and derived
per-prescription adherence. One planned occurrence cannot acquire competing execution records.

Post-session progression loads the complete persisted execution, adherence, and safety chain. The
athlete action supplies only an evaluation time; the server resolves exactly one policy from the
immutable prescription rule reference. Only non-exposure load and repetition adjustments are
automatically eligible. Missing, ambiguous, exposure-sensitive, duration, set, and unsupported
policies fail closed. The deterministic decision and any supported typed prescription revision are
stored atomically; clients cannot choose thresholds, increments, exposure caps, or policy IDs.

Weekly advancement is two-phase. The availability-confirmation endpoint accepts explicit dated
windows plus direct-report time, reliability, and provenance, then atomically appends the athlete's
observation and a `WeeklyAvailability` linked to the exact source plan. It does not create a plan,
template, prescription, or substitution. The current-week projection then reports either
`environment_revision_required` or `ready_to_finalize_next_week` from persisted resolution and
environment lineage.

Final roll-forward accepts only that persisted availability ID and a preparation time. The server
derives the consecutive week and retains the source plan's scheduling policy, exact approval
review, and session structure; verifies that the review remains current and approved; and
reconstructs the source week's authoritative backend review before writing anything. Only
`ready_to_finalize_next_week` may advance. Incomplete execution, recovery, or progression history,
holds, review-required outcomes, unsupported policies, infeasible schedules, and final block weeks
fail closed even when a caller bypasses the PWA. The service carries the latest immutable
prescription revision into a successor template when one exists and schedules the consecutive
block week. Unchanged prescriptions and templates are reused. A withdrawn, superseded,
future-dated, or missing review blocks the new week without rewriting the source plan. Source plans,
templates, prescriptions, and review history remain immutable, while explicit predecessor IDs
preserve the complete lineage.
Clients cannot submit week identity, source IDs, or software rule versions. One source plan can
have at most one confirmed next-week availability record and one successor plan. Roll-forward does
not generate dose, choose a progression, substitute equipment, or create a new block. A
substitution must already exist as an explicitly reviewed prescription revision before
roll-forward begins.

Completed-block review requires exactly one feasible weekly plan for every block week, a recorded
outcome and adherence for every planned session item, and at least one post-session safety decision
per execution. The caller groups all executed prescriptions into adaptation responses and supplies
explicit comparison directions and meaningful-change thresholds. The operator service derives
training responses, loads all safety history, and appends the immutable review plus a
`DecisionRecord` atomically; it does not update athlete state or infer scientific thresholds.
The review-preparation endpoint assembles the exact persisted weeks, sessions, prescriptions,
execution/adherence/safety history, eligible pre/post estimates, policies, source observations, and
evidence for an authenticated planning reviewer. It reports missing prerequisites and never groups
responses or chooses a threshold.

Successor-strategy replanning is a separate reviewed command. Its candidate contexts must preserve
every prior adaptation and explicitly name each estimate, competency floor, relevance and cost
score, prerequisite/safety state, and provenance. The service uses reviewed follow-up estimates for
trained adaptations, rebuilds capability needs, and appends one lineage-linked successor strategy
plus its decision audit. The replanning-preparation endpoint restricts trained adaptations to their
reviewed follow-up estimate and exposes only compatible competency floors. Both HTTP writes bind
the active reviewer account and role-assignment identity server-side; neither boundary is
athlete-accessible. The local administrative fallback remains:

```bash
python -m agas_api.post_block_admin review-block \
  --block-id YOUR_BLOCK_UUID \
  --input-file PATH_TO_REVIEWED_BLOCK_REVIEW.json

python -m agas_api.post_block_admin replan \
  --block-review-id YOUR_BLOCK_REVIEW_UUID \
  --input-file PATH_TO_REVIEWED_REPLANNING.json
```

Both CLI JSON documents require non-empty `reviewed_by`, `applicability_rationale`, and
`uncertainty` fields. HTTP requests cannot submit `reviewed_by`; the server derives it from the
authenticated role. The CLI remains a provisional recovery/administration path and does not claim
production identity assurance.

The current-week query is a read-only projection for daily use. It assembles athlete, weekly plan,
session container, exercise, adaptation, safety, execution, adherence, and progression records
without changing their meaning or persistence history. An explicit date keeps queries deterministic;
multiple plans covering the same date are rejected until supersession semantics exist.
The same projection derives a typed weekly-review state and descriptive closure counts. It exposes
the persisted source availability so clients can request confirmation without silently copying it
or reimplementing review policy.

## Run the frontend

```bash
pnpm --filter @agas/web dev
```

Open `http://localhost:3000`.

Production builds register an installable PWA shell with ordinary and maskable icons. If an
installed client loses its connection, navigation fails closed to an explicit offline screen. The
service worker caches only the offline/install shell and immutable compiled assets; it does not
cache athlete pages, API responses, credentials, or queue workout writes. A connection is still
required to view or change authoritative training records.

The current PWA screen connects to `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`) and uses
`NEXT_PUBLIC_AGAS_DEVELOPMENT_TOKEN` (default `dev.local-browser`) for local identity. It can
create a basic athlete profile with goals, activity preferences, one or more environments, and
controlled equipment selections. The backend must have imported the seed catalog for equipment
choices to appear. A new profile opens the authoritative empty-week state rather than receiving a
generic workout.

Production images instead compile `NEXT_PUBLIC_AGAS_AUTH_MODE=session` and
`NEXT_PUBLIC_API_URL=/api/agas`. In that mode browser code never constructs an authorization
header. The same-origin gateway decrypts a short-lived server session, applies origin/body/header
controls, and forwards the access token only to private FastAPI. No public route can create that
session yet; a missing or invalid session receives an honest `401` until the OIDC login adapter is
connected.

The provisional reviewer console is available at `http://localhost:3000/review`. Configure
`NEXT_PUBLIC_AGAS_REVIEWER_TOKEN=dev.local-reviewer` and grant that subject the local
`planning_reviewer` role as shown above. The console retrieves eligible estimates, their source
observations, exact current floor and policy reviews, compatible adaptations, and referenced
evidence. It then accepts an externally prepared initial-planning document, rejects reviewer
identity fields, displays exact authority versions, scores, provenance, rationale, and uncertainty
for confirmation, and submits the same parsed document. It shows
the resulting immutable strategy and decision audit. It does not author candidate values, choose
training content, or turn the reviewer role into a claim of professional qualification.

The assessment-governance workbench is available at
`http://localhost:3000/review/assessments`. Configure
`NEXT_PUBLIC_AGAS_ASSESSMENT_REVIEWER_TOKEN=dev.local-assessment-reviewer` or use the demo
bootstrap. It is a read-only explanation of the governed protocol-to-estimate chain; assessment
review records still enter through governed local data operations.

The evidence-governance workbench is available at `http://localhost:3000/review/evidence` and
uses the same read-only scientific-governance token. It traces each claim to exact source snapshots,
shows every immutable claim-review decision, and marks legacy or non-approved claims as blocked.
The browser cannot create or approve evidence. Version 2 evidence-governance bundles may carry
externally prepared `EvidenceClaimReview` records; version 1 source-and-claim bundles remain valid.
The assessment workbench reuses that evaluator at each protocol-review and estimation-policy
timestamp, so the screen cannot present a later evidence approval as the original basis of an older
authority.

After a strategy exists, `http://localhost:3000/review/resource-demands` accepts its UUID and loads
the exact priority, environment-snapshot, resolver-policy, exercise-ontology, observation, evidence,
and prior-demand records available to the reviewer. All stimulus constraints, exercise candidates,
provenance links, and resource amounts begin blank and require explicit selection. A submission may
record an honest full, partial, infeasible, or deferred result; it never creates a block, week,
session, or workout. A newly created strategy links directly to this second review step.

When every priority has demand history, `http://localhost:3000/review/blocks` loads the exact
block-preparation projection. No demand, policy, budget, date, duration, or constraint is
preselected. The reviewer chooses one demand for every priority and confirms the complete context;
the deterministic allocator may truthfully create a full, partial, or infeasible block. The receipt
shows every allocation and immutable audit. Week 1, sessions, prescriptions, and workouts remain a
separate downstream milestone.

`http://localhost:3000/review/queue` is the primary reviewer entry point. It derives one current
pre-block planning item per athlete from immutable history and links directly to initial planning,
resource-demand preparation, block creation, or Week 1 authoring. Ready and blocked work remain
visible; no queue task record is persisted.

After a block exists, `http://localhost:3000/review/weeks` accepts its UUID and exposes the exact
allocation, stimulus, exercise-resolution, selected-exercise, environment, scheduling-policy
review, observation, and evidence lineage needed for Week 1. The structured form supports every
current intensity-target type, explicit dose, rest, progression reference, session membership and
order, dated environment availability, policy review, and per-record provenance. Every material
field begins blank; the form does not infer prescription dose, session composition, availability,
or policy selection. The backend records server-owned reviewer-role authority and remains the
authoritative validator and deterministic scheduler.

After every block week and session outcome has been recorded and a post-block estimate exists,
`http://localhost:3000/review/post-block` closes the feedback loop. Its authenticated work queue
derives every due block-review or replanning item from immutable history, keeps blocked items and
their exact issues visible, and removes the need to discover internal UUIDs manually. Opening an
item first displays the complete persisted execution, adherence, safety, estimate, policy,
observation, and evidence history. The
reviewer explicitly partitions prescriptions into adaptation responses and selects comparable
baseline/follow-up estimates, comparison direction, meaningful-change threshold, applicability,
and uncertainty. After the backend derives and persists the response review, the same route exposes
the reviewed response and eligible successor-strategy inputs. Every estimate, compatible floor,
score, prerequisite, safety/sequencing flag, provenance selection, and review interval begins blank.
The resulting strategy links back to the prior strategy and exact block review and can continue to
resource-demand preparation for the next block.
Manual block and review ID lookup remains available as a deep-link and recovery path.

The secondary development path accepts an existing owned athlete ID or an `?athleteId=UUID` deep
link. Set
`NEXT_PUBLIC_AGAS_ATHLETE_ID` in `.env` to prefill it for a local demo. The backend projection
reports whether a reviewed safety policy is assigned; no policy UUID is entered in the browser.
After connecting, an athlete with an assignment can append a pre-session readiness report,
receive the backend's deterministic safety result, and log actual sets, dose, effort, timestamps,
and notes. The screen then collects a short post-session recovery report and displays persisted
progression outcomes per exercise. When an exact unique non-exposure load or repetition policy is
resolved from the prescription's versioned rule reference, the athlete can ask the deterministic
backend to evaluate progression without submitting that policy identity. It refreshes from the
authoritative current-week projection after each write.
Once every scheduled occurrence, recovery report, and supported progression is closed, the screen
offers a weekly review. It starts from availability shifted by seven days, requires the athlete to
confirm or edit the actual environments and times, and submits only the windows and direct-report
metadata. The environment panel separately records partial, temporal equipment changes with
reliability and provenance. The
backend owns the consecutive date and lineage and prepares exactly one successor week. Block-end,
hold, review-required, missing-policy, and unsupported-policy states remain visibly blocked.

This setup is provisional: no production identity provider or browser login is connected, and
account recovery, consent/export/deletion workflow, sensitive health intake, assessment
correction/attempt workflow,
qualified protocol-review workflow, complete scientific-governance UI, protocol-specific
structured/duration assessment-result controls, estimation-policy authoring UI, or early-retest
override yet. Governed competency-floor and priority-policy authoring
workflows are also not implemented. Initial planning therefore requires externally prepared,
reviewed authorities even though candidate-context, post-block review, and replanning inputs can be
authored through role-protected structured forms.
No real assessment protocol is seeded, so production assessment runs and result entry remain
unavailable. Crossref/OpenAlex adapters, batch retrieval, automated claim extraction, and qualified
production claim approval are not implemented. PubMed retrieval produces a curation input only;
the evidence bundle transports externally reviewed data. Do not use it for sensitive or production
athlete data.
The browser does not classify raw symptoms. Selecting a concerning symptom pauses the ordinary
workout flow instead of fabricating a safety signal.
Progression remains backend-governed: the PWA never chooses among policies or invents exposure
targets, session-duration budgets, or adjustment values. Unsupported, exposure-sensitive, missing,
and ambiguous configurations are shown as requiring governed setup.

## Run tests

```bash
pytest
pnpm --filter @agas/web test
pnpm --filter @agas/web test:e2e
```

Install the pinned browser runtime once before the browser smoke suite with
`pnpm --filter @agas/web exec playwright install chromium`. The suite starts an isolated frontend
on port 3100 and validates the local-demo athlete and reviewer navigation contracts.

Run only the required end-to-end domain demonstration with:

```bash
pytest tests/integration/test_required_vertical_slice.py
```

## Run static checks

```bash
ruff check .
ruff format --check .
mypy packages/domain/src packages/safety/src packages/seed_data/src services/api/src services/evidence/src services/planner/src tests
pnpm --filter @agas/web lint
pnpm --filter @agas/web typecheck
```

## Build

```bash
python -m build
pnpm --filter @agas/web build
```

## Build deployment images

The repository has vendor-neutral, non-root Linux images for the FastAPI resource server and the
standalone Next.js PWA. Build them from the repository root so both Dockerfiles can use the
monorepo context:

```bash
docker build -f services/api/Dockerfile -t agas-api:local .
docker build -f apps/web/Dockerfile -t agas-web:local \
  --build-arg NEXT_PUBLIC_API_URL=/api/agas .
```

`compose.production.yml` is a single-server deployment reference, not a one-command production
launch. Copy `.env.production.example` to a secret-managed file outside version control, replace
every example, and validate the rendered model before use:

```bash
docker compose --env-file /secure/path/agas.production.env \
  -f compose.production.yml config
docker compose --env-file /secure/path/agas.production.env \
  -f compose.production.yml up -d --build
```

The reference stack keeps PostgreSQL and FastAPI off host ports, runs Alembic as a one-shot
prerequisite, and binds only the PWA to host loopback. A separately operated HTTPS reverse proxy
exposes the web origin. Browser API calls remain same-origin and the web container reaches FastAPI
on the private Compose network. The relative gateway path and session auth mode are compiled at
image-build time; database, identity, internal API, public-origin, and session-encryption settings
remain server-only runtime configuration. A managed PostgreSQL deployment may replace the
reference database by supplying its URL and adapting the Compose topology.

This packaging does **not** complete production deployment: browser login/provider selection,
HTTPS ingress, secret management, backups/restore drills, monitoring, account lifecycle, and
production authorization administration remain required. Development bearer selectors must never
be used for a hosted instance. See [docs/deployment.md](docs/deployment.md).

## Product guardrail

The core chain is:

```text
observation -> athlete state -> identified need -> adaptation target
-> evidence-grounded strategy -> stimulus -> available exercise -> dose
-> performance -> new observation
```

Do not bypass this chain with an LLM-to-workout shortcut.
