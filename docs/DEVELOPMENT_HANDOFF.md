# AGAS development handoff

Status date: 2026-09-26

This is the single repository-local ledger for current development state and tickets. Stable
product requirements belong in `docs/MASTER_BLUEPRINT.md`; safety and evidence rules belong in
their policy files; material decisions belong in `docs/decision-log/`; implemented structure
belongs in `docs/architecture.md`. Do not duplicate those sources here.

## Fresh-chat start

1. Read `AGENTS.md` and this file in full.
2. Inspect Git status and confirm it matches the repository state below.
3. Work only the `Active ticket`.
4. Read that ticket's referenced decisions, policies, code, and tests before changing anything.
5. Update this handoff before stopping. Do not begin a queued ticket in the same conversation.

If the active ticket is complete and this file is current, the conversation should report
`Context boundary: GOOD BREAK` and provide the copy/paste prompt required by `AGENTS.md`.

## Product invariant

AGAS is an inspectable, evidence-grounded adaptive system, not an LLM workout generator. Preserve:

```text
observation -> athlete state -> identified need -> adaptation target
-> evidence-grounded strategy -> stimulus -> available exercise -> dose
-> performance -> new observation
```

Observations, derived estimates, evidence claims, planning decisions, prescriptions, and
user-facing explanations remain distinct. Safety, scientific provenance, uncertainty,
append-only history, and owner review fail closed.

## Repository state

- Working directory:
  `C:\Users\Courtney\Documents\Codex\2026-08-19\i\work\adaptive_general_athleticism_system`
- Branch: `main`
- Committed implementation and workflow baseline:
  `19b08006a83ab612ed47a3156ea93e70c99f80e2`
- `origin/main`: `f41516830f61d1c5f6d40b376fdc42b289a8de6f`
- Local branch state: `main` is ahead of `origin/main`; inspect Git for the exact current count and
  revision rather than relying on a copied number. Nothing has been pushed.
- Worktree expectation at conversation boundary: clean.
- Decisions `0133` through `0151` and their associated implementation are tracked in the baseline
  commit above.

If actual Git state differs, stop and reconcile it before starting the active ticket. Do not reset,
check out, stash, clean, delete, or partially discard unexpected work.

## Last verified validation

The current product implementation, before the ticket-workflow-only documentation edit, passed on
2026-09-26:

- full Python test suite, with one intentional skip;
- Ruff check and format check;
- mypy across 172 source files;
- 175 Vitest tests;
- 18 Playwright browser tests;
- ESLint and TypeScript checks;
- Next.js production build;
- isolated Python package build;
- Alembic head check at `6b7c8d9e0f1a`;
- `git diff --check`.

The production-shaped real-stack Playwright lane exists and is mandatory in CI, but it was not
rerun in the last local validation pass because it requires its dedicated PostgreSQL test database.

## Current product state

| Workflow area | Current boundary |
| --- | --- |
| Onboarding | Profile, ownership, environment, equipment, provenance, and append-only corrections are implemented and tested. |
| Assessment | Reviewable chair-stand, standard-push-up, countermovement-jump, and 12-minute walk/run paths exist. Completed results require exact-protocol and no-stop attestations. Incomplete and safety-stopped attempts remain separate non-results with controlled non-diagnostic reasons. |
| Capability estimation | Reviewed protocol-specific observations can create traceable, expiring derived estimates. Most capability domains still lack operational measurement paths. |
| Initial planning | Narrow standard-push-up, provisional explosive-power, and provisional aerobic-capacity paths have typed, review-gated floor, resource, dose, and progression authorities. They are not a general program. |
| Phone execution | Current-week display, deterministic safety check, reviewed instructions, set logging, local draft recovery, rest timer, submission, and immutable performance history exist. |
| Progression | The next unperformed occurrence consumes the latest eligible prescription descendant; completed sessions retain their executed dose and weekly roll-forward consumes the final leaf. |
| Closed loop | Persisted regressions cover two training cycles, reassessment, block review, successor planning, maintenance, and a third strategy dependent on the second-cycle response. |
| Hosted owner alpha | Vercel, Render, Neon, and Auth0 foundations exist. Public API health was observed on 2026-09-25, but current authenticated athlete, ratification, and week state remain unverified. |

## Recent decision index

The detailed record is the decision log. The current uncommitted slice is:

- `0133`–`0134`: in-week immutable progression handoff and PostgreSQL API golden path;
- `0135`–`0144`: fixed repetition dose, owner-reviewable jump development and maintenance,
  two-cycle successor feedback, production-shaped browser/API/PostgreSQL coverage, and the
  read-only hosted readiness audit;
- `0145`–`0147`: fixed duration dose, owner-reviewable aerobic-base authority, and persisted
  duration ceiling;
- `0148`–`0151`: explicit assessment completion, append-only incomplete/safety-stopped attempts,
  longitudinal assessment history, and controlled attempt reasons.

These records preserve the evidence boundary, numeric-origin labels, safety constraints,
uncertainty, alternatives, consequences, and owner-review requirements. Do not re-express those
details in tickets.

## Active ticket

### AGAS-0002 — Align remote and hosted revision

- Status: `ACTIVE`
- Type: source-control and deployment alignment

#### Objective

Move the exact local ticket-workflow baseline to the configured GitHub remote after explicit owner
confirmation, allow the existing CI/deployment gates to process it, and confirm which revision the
hosted owner alpha serves. Do not inspect or change athlete/governance state in this ticket.

#### Why this is next

The local repository contains the preserved decisions and implementation, but `origin/main` still
points to the older handoff commit. Authenticated readiness inspection would be misleading until
the remote and hosted application are known to serve the intended source revision.

#### In scope

- inspect Git status, local history, remote tracking state, and the exact commits pending push;
- confirm the worktree is clean and no unexpected commit or rewritten history is present;
- obtain explicit owner confirmation before pushing local `main` to `origin/main`;
- push only the reviewed fast-forward commits after confirmation;
- observe the existing GitHub CI and configured deployment gates without bypassing failures;
- identify the revision served by the hosted API/PWA when the providers expose that evidence;
- record success, failure, or inability to prove revision alignment distinctly;
- update this handoff, complete this ticket, and promote `AGAS-0003` without starting it.

#### Out of scope

- owner sign-in or authenticated `/review/readiness` inspection;
- candidate ratification, athlete writes, or training-state changes;
- changing provider plans, adding payment details, or moving to paid infrastructure;
- force-pushing, rebasing published history, or bypassing a failing CI/deployment gate;
- product code changes unless a separately approved follow-up ticket is created;
- treating deployment success as proof of authenticated live-data readiness.

#### Authoritative references

- `AGENTS.md`
- `docs/deployment.md`
- `docs/decision-log/0086-no-card-single-user-alpha-hosting.md`
- `docs/decision-log/0088-render-alpha-deploy-trigger.md`
- `.github/workflows/ci.yml`
- current local and remote Git state and provider deployment evidence

#### Acceptance criteria

- The worktree begins and ends clean.
- The owner explicitly authorizes any push before it occurs.
- `origin/main` contains the intended fast-forward local commits, or the exact blocker is recorded.
- Required CI checks pass, or each failure remains visible and is not bypassed.
- The hosted revision is confirmed when provider evidence permits; inability to prove it is not
  mislabeled as success.
- No authenticated athlete/governance inspection or live-data write occurs.
- This handoff is updated and `AGAS-0003` becomes active but unstarted.

#### Validation

- capture local HEAD, `origin/main`, ahead/behind counts, and clean status before pushing;
- verify the push is a fast-forward update;
- inspect required CI results and configured deployment status;
- record the exact hosted revision when it is observable.

#### Blockers or owner decisions

Pushing changes and triggering deployment are consequential external operations. Starting this
ticket does not itself authorize the push: obtain one explicit owner confirmation after reporting
the exact commits and fast-forward target.

## Ordered queue

### AGAS-0003 — Perform authenticated owner-readiness audit

- Status: `READY`
- Depends on: `AGAS-0002`
- Objective: sign in through the owner-controlled Auth0 flow and inspect the read-only
  `/review/readiness` route against the hosted database.
- Boundaries: do not automatically ratify candidates, manufacture athlete/training state, bypass
  Auth0, expose credentials, or infer readiness from health/connectivity alone.
- Expected output: exact candidate, ratification, athlete, week, safety-assignment, and reviewer-
  boundary facts, with failures kept distinct from genuinely empty state.

### AGAS-0004 — Reconcile descriptive documentation

- Status: `QUEUED`
- Depends on: `AGAS-0003`
- Objective: bring `docs/architecture.md` and the stale package/service boundary READMEs through
  the committed decisions without changing product behavior or policy.
- Boundaries: do not rewrite the blueprint, policies, or historical decision records; keep the
  root README operational rather than turning it into another status ledger.

## Recently completed tickets

### AGAS-0001 — Establish the committed fresh-context baseline

- Status: `COMPLETE`
- Completed: 2026-09-26
- Baseline commit: `19b08006a83ab612ed47a3156ea93e70c99f80e2`
- Result: all intentional implementation, migrations, governed data, tests, policies, decisions
  `0133`–`0151`, and ticket-workflow instructions were reviewed and committed locally.
- Safety checks: 120 staged paths; no ignored/generated artifacts, binary files, suspicious secret
  filenames, private-key markers, or credential-like assignments; `git diff --cached --check`
  passed; Alembic had the single head `6b7c8d9e0f1a`.
- Remote/deployment: not pushed and not deployed by this ticket.

## Known risks and limitations

- The owner-relevant operational paths remain narrow and depend on deliberate ratification.
- Most athletic capability domains still lack complete governed measurement and construction paths.
- The longitudinal assessment projection is intentionally unpaginated for the bounded owner alpha.
- Live hosted ratifications, athlete history, and current-week state have not been authenticated and
  inspected in this repository session.
- Provider free-tier behavior and availability can change; `docs/deployment.md` remains the
  deployment runbook, but live dashboards are the source for current provider state.

## Fresh-chat prompt

When this file reports a stable checkpoint, use:

```text
Read AGENTS.md and docs/DEVELOPMENT_HANDOFF.md in full. Inspect Git status before changing
anything. Work only the Active ticket in the handoff, follow its referenced authorities and
acceptance criteria, update the handoff before stopping, and do not begin another ticket.
```
