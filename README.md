# Adaptive General Athleticism System

[![CI](https://github.com/CourtneyMandela/adaptive_general_athleticism_system/actions/workflows/ci.yml/badge.svg)](https://github.com/CourtneyMandela/adaptive_general_athleticism_system/actions/workflows/ci.yml)

AGAS is an evidence-grounded, adaptive system for developing broad general athleticism. This repository is intentionally building the inspectable domain and feedback loop before workout generation or polished product features.

The current foundation includes controlled ontology vocabulary, a cross-reference-validated small
seed catalog, and a tested home/travel/return counterfactual. Temporary equipment changes can
select a newer exercise resolution without changing athlete identity or adaptation intent; partial
fidelity remains explicit and policy-gated. Session templates, safety decisions, execution,
adherence, training response, and block review remain immutable and provenance-preserving.
Reviewed follow-up estimates can regenerate capability needs and a replacement long-range
strategy through an explicit closed-loop replanning boundary. Each revision retains the exact
prior strategy and triggering review without inferring causation or rewriting athlete history.
An initial or revised strategy can then create a persisted block only from already-governed
resource demands, exercise resolutions, and an explicit allocation policy.

## Architecture at a glance

- `apps/web`: responsive Next.js interface foundation
- `services/api`: FastAPI application and persistence boundary
- `services/planner`: deterministic assessment, planning, scheduling, execution, and adherence logic
- `services/evidence`: reserved boundary for evidence retrieval and review
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

## Run the backend

```bash
uvicorn agas_api.main:app --reload
```

The health endpoint is available at `http://localhost:8000/health`.

The application endpoints are intentionally narrow:

```text
GET  /v1/athletes/{athlete_id}/current-week?on=YYYY-MM-DD
POST /v1/block-reviews/{block_review_id}/replan
POST /v1/blocks/{block_id}/reviews
POST /v1/strategies/{strategy_id}/priorities/{priority_id}/resource-demands
POST /v1/strategies/{strategy_id}/blocks
POST /v1/blocks/{block_id}/weekly-plans
POST /v1/weekly-plans/{weekly_plan_id}/roll-forward
POST /v1/weekly-plans/{weekly_plan_id}/sessions/{planned_session_id}/safety-checks
POST /v1/weekly-plans/{weekly_plan_id}/sessions/{planned_session_id}/executions
POST /v1/session-executions/{session_execution_id}/prescriptions/{prescription_id}/progression
```

It accepts explicit replanning candidate contexts, reconstructs the persisted review chain, and
atomically appends capability needs and one replacement strategy. Raw strategy/need CRUD is not
exposed. Block creation accepts persisted demand identities plus an allocation policy, dates,
weekly budget, and explicit constraints. It atomically appends the deterministic block but does
not invent stimuli, exercise resolutions, prescriptions, or dose targets.

Resource-demand preparation bridges those use cases without exposing raw CRUD. Active priorities
require an explicit stimulus specification, environment, candidate exercises, resolver policy,
and resource amounts. Deferred priorities produce a provenance-bearing zero-resource demand.
Partial or infeasible exercise resolution remains visible rather than being replaced silently.

Weekly-plan creation accepts explicit prescription doses, explicit session composition, dated
availability, and a persisted scheduling policy. It derives exercise and adaptation identity from
the block, schedules deterministically, and atomically appends the complete chain. It does not
generate a generic workout from an adaptation name.

Session recording first appends an explicit user-report observation and deterministic safety
decision. Execution then requires the latest pre-session decision, accepts actual performed-set
data, and atomically appends the workout-result observation, immutable execution, and derived
per-prescription adherence. One planned occurrence cannot acquire competing execution records.

Post-session progression loads the complete persisted execution, adherence, and safety chain. It
optionally derives a classified exposure and validates an explicit proposal, then atomically stores
the deterministic progression decision and any supported typed prescription revision. Thresholds,
increments, and exposure caps come only from persisted evidence-linked policies.

Weekly roll-forward accepts only the next week's explicit availability and a preparation timestamp.
It retains the source plan's scheduling policy and session structure, carries the latest immutable
prescription revision into a successor template when one exists, and schedules the consecutive
block week. Unchanged prescriptions and templates are reused. Source plans, templates, and
prescriptions remain historical, while explicit predecessor IDs preserve the complete lineage.
The submitted availability is also stored as a direct user-report observation with reliability and
provenance; the next availability record retains that observation alongside its prior source
references. Roll-forward does not generate dose, choose a progression, substitute equipment, or
create a new block.

Completed-block review requires exactly one feasible weekly plan for every block week, a recorded
outcome and adherence for every planned session item, and at least one post-session safety decision
per execution. The caller groups all executed prescriptions into adaptation responses and supplies
explicit comparison directions and meaningful-change thresholds. The API derives training
responses, loads all safety history, and appends one immutable review atomically; it does not update
athlete state or infer scientific thresholds.

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

The current PWA screen connects to `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`) and asks
for an existing athlete ID plus a reviewed safety-policy ID. Set `NEXT_PUBLIC_AGAS_ATHLETE_ID` and
`NEXT_PUBLIC_AGAS_SAFETY_POLICY_ID` in `.env` to prefill those fields for a local demo. After
connecting, an athlete can append a pre-session readiness report, receive the backend's
deterministic safety result, and log actual sets, dose, effort, timestamps, and notes. The screen
then collects a short post-session recovery report and displays persisted progression outcomes per
exercise. When an exact unique non-exposure load or repetition policy is assigned by the
prescription's versioned rule reference, the athlete can ask the deterministic backend to evaluate
progression. It refreshes from the authoritative current-week projection after each write.
Once every scheduled occurrence, recovery report, and supported progression is closed, the screen
offers a weekly review. It starts from availability shifted by seven days, requires the athlete to
confirm or edit those actual times, and prepares exactly one consecutive successor week. Block-end,
hold, review-required, missing-policy, and unsupported-policy states remain visibly blocked.

This setup is provisional: there is no authentication, athlete onboarding, or athlete-to-policy
assignment workflow yet. The browser does not classify raw symptoms. Selecting a concerning
symptom pauses the ordinary workout flow instead of fabricating a safety signal.
Progression remains backend-governed: the PWA never chooses among policies or invents exposure
targets, session-duration budgets, or adjustment values. Unsupported, exposure-sensitive, missing,
and ambiguous configurations are shown as requiring governed setup.

## Run tests

```bash
pytest
pnpm --filter @agas/web test
```

## Run static checks

```bash
ruff check .
ruff format --check .
mypy packages/domain/src packages/safety/src packages/seed_data/src services/api/src services/planner/src tests
pnpm --filter @agas/web lint
pnpm --filter @agas/web typecheck
```

## Build

```bash
python -m build
pnpm --filter @agas/web build
```

## Product guardrail

The core chain is:

```text
observation -> athlete state -> identified need -> adaptation target
-> evidence-grounded strategy -> stimulus -> available exercise -> dose
-> performance -> new observation
```

Do not bypass this chain with an LLM-to-workout shortcut.
