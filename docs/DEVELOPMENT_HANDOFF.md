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
- Local branch state: the baseline commit plus this final handoff commit are expected to leave
  `main` two commits ahead of `origin/main`; nothing has been pushed.
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

### AGAS-0002 — Verify hosted owner-alpha readiness

- Status: `ACTIVE`
- Type: deployment and read-only live-state verification

#### Objective

Confirm that the exact committed AGAS baseline is deployed, establish an owner-authenticated browser
session, and inspect `/review/readiness` against the hosted database. Record the exact candidate,
ratification, athlete, current-week, and reviewer-queue state without automatically changing it.

#### Why this is next

Source, tests, public API health, and database connectivity do not prove that the hosted owner has
the intended ratifications or a current persisted week. The repository now has a stable local
baseline, so the next uncertainty is operational rather than architectural.

#### In scope

- inspect Git status and confirm the local baseline and whether it has been pushed/deployed;
- follow `docs/deployment.md` and existing provider gates without changing plans or adding payment;
- use the owner-controlled Auth0 sign-in flow; request interactive owner action when credentials or
  consent are required rather than automating or exposing them;
- inspect the authenticated `/review/readiness` route and its underlying read-only projections;
- record exact deployed revision when observable, prepared candidate IDs/digests and ratification
  states, owned-athlete visibility, current-week identity/state, safety assignment state, and the
  current planning-review boundary;
- distinguish unavailable, unauthorized, missing, conflicting, and genuinely absent state;
- update this handoff with evidence and define the next bounded ticket from observed state.

#### Out of scope

- automatic candidate ratification or approval;
- manufacturing an athlete, plan, week, or readiness state to make the screen look complete;
- bypassing Auth0 or handling owner credentials outside the provider flow;
- changing provider plans, adding payment details, or moving to paid infrastructure;
- product code changes unless a separately approved follow-up ticket is created;
- treating deployment success, HTTP health, or database connectivity as live-data readiness.

#### Authoritative references

- `AGENTS.md`
- `docs/deployment.md`
- `docs/decision-log/0086-no-card-single-user-alpha-hosting.md`
- `docs/decision-log/0108-allowlisted-owner-alpha-operator-access.md`
- `docs/decision-log/0144-owner-alpha-live-readiness-audit.md`
- `apps/web/app/review/readiness/`
- current Git state and the actual hosted UI/API responses

#### Acceptance criteria

- The exact source revision serving the owner alpha is confirmed, or inability to confirm it is
  recorded precisely.
- Owner authentication succeeds through the normal provider flow, or the exact owner-action blocker
  is recorded without exposing credentials.
- `/review/readiness` is inspected while authenticated.
- Candidate, ratification, athlete, week, safety-assignment, and reviewer-boundary results are
  recorded as observed facts with failures kept distinct from empty state.
- No candidate is ratified and no athlete/training state is written merely to satisfy this ticket.
- This handoff is updated and the next ticket reflects the observed live blocker or next product gap.

#### Validation

- capture Git revision and deployment evidence available from the configured providers;
- verify authenticated navigation to `/review/readiness`;
- compare visible state with the route's fail-closed semantics from decision `0144`;
- perform no write-based validation unless a new owner-approved ticket explicitly authorizes it.

#### Blockers or owner decisions

Interactive Auth0 sign-in may require the owner. If the local checkpoint has not reached the remote
or hosting providers, pushing or deploying is a consequential operation: report the exact state and
obtain owner confirmation before performing it unless the owner explicitly starts this ticket with
deployment authorization.

## Ordered queue

### AGAS-0003 — Reconcile descriptive documentation

- Status: `QUEUED`
- Depends on: `AGAS-0001` and the observed result of `AGAS-0002`
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
