# AGAS development handoff

Status date: 2026-09-22

This document is a concise starting point for a new engineering conversation. Verified facts below
come from the repository at commit `40c928ddcdf64f7256696ec9400ae0c62ac6d301` unless explicitly
marked otherwise. Read `AGENTS.md` and `docs/MASTER_BLUEPRINT.md` before changing behavior, then
consult the relevant records in `docs/decision-log/`.

## Product intent and current objective

AGAS is intended to develop broad general athleticism through an inspectable, evidence-grounded,
adaptive loop. It is not an LLM workout generator. It must preserve the chain from observation to
athlete state, need, adaptation, strategy, stimulus, feasible exercise, dose, performance, and a new
observation. The long-term product should learn from an athlete's measured response without
inventing capability scores, scientific support, safety conclusions, or genetic explanations.

The current objective is the first usable owner-only training loop on a phone: onboard, assess,
derive a capability estimate, construct a governed plan, perform and record sessions, progress from
actual performance, reassess, and make the next block depend on the observed response. Prefer
finishing this loop over expanding infrastructure or adding polished but nonfunctional breadth.

## Verified architecture and technologies

AGAS is a modular monorepo with one deployable backend and one web application, not a collection of
microservices.

- `apps/web`: Next.js 16, React 19, TypeScript 6 responsive PWA; Vitest and Playwright.
- `services/api`: FastAPI application and use-case orchestration.
- `services/planner`: deterministic assessment, planning, execution, progression, and review rules.
- `services/evidence`: source-metadata retrieval/parsing; it does not approve scientific claims.
- `packages/domain`: Pydantic domain contracts plus SQLAlchemy persistence and repositories.
- `packages/safety`: deterministic structured safety gates.
- `packages/evaluation`: counterfactual and anti-sludge evaluation.
- `packages/seed_data`, `data/`: small validated catalogs, synthetic athletes, and reviewed candidate
  data. Candidate data is not automatically operational authority.
- `migrations`: Alembic migrations targeting PostgreSQL.
- `tests`: unit, integration, counterfactual, and anti-sludge suites.

Python is 3.12+. Backend dependencies include FastAPI, Pydantic, SQLAlchemy, Alembic, psycopg,
PostgreSQL, and Uvicorn. The JavaScript workspace uses pnpm 11.19. Exact setup and validation
commands are in `README.md` and summarized in `AGENTS.md`.

The verified deployment design uses a same-origin Next.js gateway and encrypted `HttpOnly` session;
browser code never receives the API bearer token. OIDC uses authorization code flow with PKCE. The
owner-only no-card alpha topology is Vercel Hobby (PWA), Render Free (authenticated FastAPI), Neon
Free (PostgreSQL), and Auth0 Free (OIDC). `docs/deployment.md` is authoritative. Free services may
sleep or pause at quota. Do not add a payment method or silently move to paid infrastructure.

## Decisions future work must preserve

### Verified repository decisions

- Observations are append-only facts. Capability estimates are derived, versioned, confidence- and
  staleness-aware records that retain their source observations.
- History is immutable. Material rules, evidence, professional/engineering judgments, reviews,
  digests, decisions, prescriptions, executions, and revisions retain explicit lineage.
- Evidence strength and athlete applicability are separate. Never attach a general citation to a
  numeric threshold it does not support.
- Scientific evidence, professional judgment, engineering judgment, and personal calibration are
  visibly distinct authority kinds. Professional or engineering choices must not masquerade as
  published findings.
- ACSM and NSCA textbooks are citable for the exact tables and procedures they contain. They are
  not the exclusive evidence sources and do not make a descriptive norm an AGAS competency floor.
- Adaptations and exercises are separate. Equipment changes should re-resolve the means while
  preserving the goal where feasible; inadequate substitutions must be labeled partial or
  infeasible.
- Planning has explicit strategy, block, week, session, safety, execution, progression,
  reassessment, and review boundaries. Do not replace them with generic workout generation.
- Prepared governance content may be reviewed in batches, but every artifact remains versioned,
  content-addressed, authorized, immutable, and fail-closed. Deployment is not ratification.
- Introductory jump exposure is assessment preparation, not proof of a capability deficit and not
  an ordinary training block.
- Exercise instructions are versioned snapshots on immutable prescriptions. Presentation aids such
  as the rest timer are device-local and do not become fabricated performance observations.

### Conversation-established operating decisions

- The product owner is the stakeholder and reviewer, not the technical author. AGAS/Codex should
  research and prepare inspectable candidates; the owner reviews or ratifies exact prepared
  content. Do not ask the owner to invent scores, doses, thresholds, or scientific arguments merely
  to advance the workflow.
- External consultant reviews are advisory input, not project instructions. Reconcile them against
  the blueprint, code, evidence policy, and engineering judgment.
- The supplied ACSM and NSCA PDFs were a strong starting source, not a restriction on future
  research. Their original local PDF files are not stored in this repository; do not assume a new
  environment can access them. Repository records preserve the source identifiers and cited
  locators used so far.
- The app must be usable remotely on a phone; requiring the phone and development computer to share
  Wi-Fi is not an acceptable operating model.
- Cost sensitivity is material for the single-user alpha. The selected free topology is deliberate,
  and avoiding surprise billing is more important than always-on performance at this stage.

## Functional status

| Workflow area | Status | Verified boundary |
| --- | --- | --- |
| Athlete onboarding | Implemented and tested | Profile, environment, equipment, provenance, ownership, and corrections exist. |
| Assessments | Partially implemented and tested | Reviewed chair-stand, standard-push-up, and countermovement-jump paths exist, including readiness and dedicated introductory jump exposure. This is not a broad assessment battery. |
| Capability estimation | Partially implemented and tested | Reviewed assessment-specific observations can create traceable, expiring estimates. Most general capability domains do not yet have operational measurement paths. |
| Initial planning | Partially implemented and tested | Standard push-up can proceed through a provisional judgment-backed floor, priority, resource demand, block, dose, and first week after explicit reviews. This is a narrow training slice, not a general-athleticism program. |
| Phone session execution | Implemented and tested | Current-week display, safety check, reviewed instructions, set-by-set logging, local draft recovery, rest countdown, and final submission exist. |
| Performance recording | Implemented and tested | Actual set performance, effort, technique, timestamps, adherence, safety feedback, and performance observation persist atomically. |
| Progression and next week | Partially implemented and tested | Deterministic performance evaluation creates immutable prescription revisions, and weekly roll-forward consumes the latest revision. The next unperformed session in the same week still uses the original prescription. |
| Reassessment and successor block | Implemented as a synthetic acceptance contract; partially operational | `tests/integration/test_required_vertical_slice.py` proves the full four-week feedback loop with explicit synthetic rules. Those thresholds and doses are test fixtures, not production defaults. |
| Hosted owner alpha | Deployment foundation implemented | Repository deployment configuration and session auth exist. Conversation history reports successful hosted sign-in, but this handoff did not inspect live service health or the current hosted database state. |

Backend integration tests cover the major persistence boundaries, and browser tests cover the phone
UI with mocked service responses. There is not yet one unmocked browser test that traverses the
entire owner path against a real PostgreSQL-backed API.

## Current product task and unresolved problem

The latest read-only workflow audit identified the smallest material gap as **in-week progression
handoff**. Implementation has not started.

Today, completing a session can create an immutable revised prescription, but
`CurrentWeekProjector` reads the original prescription referenced by the shared session template.
`WeeklyPlanRollForwardService` correctly selects the latest revision only when preparing the next
week. Consequently, session 1 can recommend progression while session 2 in the same week still
shows and records the old dose.

The intended next change is to make the newest eligible immutable prescription revision effective
for the next unperformed planned session while preserving completed-session history exactly. It
must also allow execution and further progression from that effective descendant without rewriting
the original weekly plan or template. The exact design remains tentative until the relevant domain
invariants and tests are re-read.

Other known limitations:

- The owner-relevant operational plan is essentially a small standard-push-up slice. Jump testing
  does not yet produce a governed jump-training priority or dose.
- Most capability domains still require assessment, applicability, floor, exercise-resolution, and
  construction authority before they can enter real planning.
- Owner-alpha governance still requires deliberate review/ratification; convenience must not turn
  that into automatic approval.
- Live hosted data may still be missing some ratifications or a persisted week; verify through the
  authenticated UI/API rather than inferring it from source code.

## Next concrete steps

1. Implement the in-week progression handoff with the smallest change compatible with immutable
   prescription lineage. Add integration coverage for: session 1 execution -> post-session safety
   -> progression -> revised session 2 -> second execution/progression -> weekly roll-forward.
2. Add or extend PWA regression coverage so the next unperformed session displays the revised dose
   while completed sessions retain what the athlete actually performed.
3. Add one real-stack golden-path test using PostgreSQL and the API, then keep Playwright focused on
   user-facing transitions rather than duplicating every domain rule.
4. After the narrow loop is reliable, add the next complete capability vertical slice. Select it by
   practical owner value and evidence/applicability quality; do not add disconnected norms or a
   large generic exercise catalog.
5. Continue toward an operational reassessment, response comparison, and successor-block workflow
   using real governed content rather than the synthetic acceptance fixture.

## Git baseline at handoff creation

- Working directory: `C:\Users\Courtney\Documents\Codex\2026-08-19\i\work\adaptive_general_athleticism_system`
- Branch: `main`
- Baseline HEAD: `40c928ddcdf64f7256696ec9400ae0c62ac6d301`
- Remote: `https://github.com/CourtneyMandela/adaptive_general_athleticism_system.git`
- Before this documentation edit, the tree was clean, `main` was 0 ahead / 0 behind
  `origin/main`, and a live read-only GitHub check confirmed the same SHA on `refs/heads/main`.
- This handoff document and the small `AGENTS.md` operational update are intentionally left
  uncommitted pending owner approval.

