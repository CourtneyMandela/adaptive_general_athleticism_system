# Adaptive General Athleticism System

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

The planning write use cases are intentionally narrow:

```text
POST /v1/block-reviews/{block_review_id}/replan
POST /v1/strategies/{strategy_id}/blocks
```

It accepts explicit replanning candidate contexts, reconstructs the persisted review chain, and
atomically appends capability needs and one replacement strategy. Raw strategy/need CRUD is not
exposed. Block creation accepts persisted demand identities plus an allocation policy, dates,
weekly budget, and explicit constraints. It atomically appends the deterministic block but does
not invent stimuli, exercise resolutions, prescriptions, or dose targets.

## Run the frontend

```bash
pnpm --filter @agas/web dev
```

Open `http://localhost:3000`.

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
