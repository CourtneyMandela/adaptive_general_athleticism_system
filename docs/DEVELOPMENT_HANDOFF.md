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
- Committed HEAD: `f41516830f61d1c5f6d40b376fdc42b289a8de6f`
- `origin/main`: `f41516830f61d1c5f6d40b376fdc42b289a8de6f`
- Worktree: intentionally dirty. At the workflow transition, it contained 71 tracked change
  entries and 49 untracked entries.
- Decisions `0133` through `0151` and their associated implementation are present but not yet
  committed.

Do not reset, check out, stash, clean, delete, or partially discard this worktree. The active
ticket exists to preserve it as a reviewable committed baseline.

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

### AGAS-0001 — Establish the committed fresh-context baseline

- Status: `ACTIVE`
- Type: repository continuity; no product behavior change

#### Objective

Preserve the complete intentional working tree—including decisions `0133`–`0151`, their code,
migrations, tests, data, and the ticket-workflow documentation—as a reviewable local Git baseline
from which fresh Codex conversations can work safely.

#### Why this is next

The committed branch stops before nineteen material decisions. A fresh conversation could mistake
Git history for current product state or accidentally discard untracked institutional knowledge.
No new product work should start until the repository has an exact committed checkpoint.

#### In scope

- inspect every changed and untracked path;
- verify that no secret, local environment file, generated build output, or transient test output
  would enter the checkpoint;
- confirm decisions `0133`–`0151` correspond to the included implementation and tests;
- run final documentation/diff checks, relying on the recorded full validation only if product code
  has not changed since that pass;
- create one or more local commits that preserve the intentional worktree;
- update this handoff with the resulting commit SHA and exact clean-worktree state;
- mark this ticket complete and promote `AGAS-0002` without starting it.

#### Out of scope

- new product features or refactors;
- changing scientific, safety, planning, or governance behavior;
- owner ratification;
- deployment or live-data writes;
- pushing commits to a remote;
- rewriting or normalizing earlier decision records.

#### Authoritative references

- `AGENTS.md`
- `docs/MASTER_BLUEPRINT.md`
- `docs/decision-log/0133-in-week-prescription-progression-handoff.md` through
  `docs/decision-log/0151-controlled-assessment-attempt-reasons.md`
- the `Last verified validation` section above
- current `git status`, `git diff`, and untracked-file inventory

#### Acceptance criteria

- Every intended source, migration, test, data, policy, decision, and workflow document is tracked.
- No secret or ignored/generated artifact is included.
- Local commit history preserves the current implementation and ticket workflow.
- This handoff names the exact new baseline commit and reports a clean worktree.
- `AGAS-0002` is active but unstarted.
- Nothing is pushed, deployed, or ratified.

#### Validation

- inspect `git status --short` and the complete staged path list;
- run `git diff --check` before committing;
- verify the resulting commit contents and clean worktree;
- rerun product checks only if product code changes after the validation recorded above.

#### Blockers or owner decisions

None. The owner authorized the transition to the ticket-based fresh-context workflow. The ticket
authorizes local checkpoint commits only; it does not authorize pushing or deployment.

## Ordered queue

### AGAS-0002 — Verify hosted owner-alpha readiness

- Status: `READY`
- Objective: deploy the committed source if necessary, sign in as the owner, and inspect the
  read-only `/review/readiness` route against the hosted database.
- Boundaries: do not automatically ratify candidates, manufacture a current week, bypass Auth0,
  or infer readiness from source, CI, health, or connectivity alone.
- Expected output: exact observed hosted state, blockers, and the next bounded ticket.

### AGAS-0003 — Reconcile descriptive documentation

- Status: `QUEUED`
- Depends on: `AGAS-0001` and the observed result of `AGAS-0002`
- Objective: bring `docs/architecture.md` and the stale package/service boundary READMEs through
  the committed decisions without changing product behavior or policy.
- Boundaries: do not rewrite the blueprint, policies, or historical decision records; keep the
  root README operational rather than turning it into another status ledger.

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
