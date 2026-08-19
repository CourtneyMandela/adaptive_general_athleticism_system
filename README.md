# Adaptive General Athleticism System

AGAS is an evidence-grounded, adaptive system for developing broad general athleticism. This repository is intentionally building the inspectable domain and feedback loop before workout generation or polished product features.

The current foundation schedules explicit multi-item session templates, records one session-level
safety decision with ordered item-level performance, and derives adherence and progression per
prescription item. Prescription intensity is structured as typed load, effort, pace, heart-rate,
bodyweight, or technique targets instead of free text. The previously implemented immutable
training-response and block-review chain remains intact; it still does not silently update athlete
state or create the next plan.

## Architecture at a glance

- `apps/web`: responsive Next.js interface foundation
- `services/api`: FastAPI application and persistence boundary
- `services/planner`: deterministic assessment, planning, scheduling, execution, and adherence logic
- `services/evidence`: reserved boundary for evidence retrieval and review
- `packages/domain`: versioned domain models and invariants
- `packages/exercise_ontology`: exercise ontology boundary
- `packages/adaptation_models`: adaptation ontology boundary
- `packages/safety`: deterministic safety-policy boundary
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

The checked-in baseline is for a new pre-production database. Once shared seed or athlete data
exists, schema changes must use new incremental revisions rather than rewriting this baseline.

## Run the backend

```bash
uvicorn agas_api.main:app --reload
```

The health endpoint is available at `http://localhost:8000/health`.

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
mypy packages/domain/src packages/safety/src services/api/src services/planner/src tests
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
