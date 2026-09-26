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
- Pushed ticket-workflow baseline: `6e8dbaf03490644f1e244ba62c024b6cb8a2fcd2`
- `origin/main`: `6e8dbaf03490644f1e244ba62c024b6cb8a2fcd2`
- Local branch state: after the documentation-only AGAS-0002 completion commit, `main` is expected
  to contain the documentation-only AGAS-0003 completion commit on top of AGAS-0002 and to be two
  commits ahead of `origin/main`. Neither completion commit has been authorized or pushed; inspect
  Git for the exact local revisions.
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
GitHub CI run `36233115399` exercised it against pushed commit
`6e8dbaf03490644f1e244ba62c024b6cb8a2fcd2` on 2026-09-26:

- Backend: passed;
- Frontend: passed, including 18 Playwright browser tests;
- Deployment containers: passed;
- Browser + API + PostgreSQL: failed because `apps/web/e2e/real-stack.spec.ts:9` used an ambiguous
  `getByRole("link", { name: "Sign in securely" })` locator after the page exposed two matching
  links. The failure remains visible and was not rerun, bypassed, or repaired in AGAS-0002 or
  AGAS-0003.

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
| Hosted owner alpha | The normal Auth0 flow succeeded on the stable Vercel production origin and `/review/readiness` was inspected on 2026-09-26. Reviewer access is active. The connected live state contains 12 unratified candidates, 2 owned athlete records, and no persisted current week or safety-policy assignment for either athlete on the audit date. Vercel records exact commit `6e8dbaf03490644f1e244ba62c024b6cb8a2fcd2` for its successful deployment; the stable alias served the same hashed Next.js asset set. Render is healthy and ready but exposes no SHA, so PWA/API revision alignment remains unproven. |

## Recent decision index

The detailed record is the decision log. The latest committed slice is:

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

### AGAS-0004 — Restore hosted API alignment and expose the aerobic candidate chain

- Status: `ACTIVE`
- Type: deployment-blocking regression repair and authenticated hosted verification

#### Objective

Repair the known production-shaped browser/API/PostgreSQL CI regression without weakening its
authentication assertion, obtain owner authorization before pushing the exact reviewed range, let
the normal required-check deployment path advance Render, and verify that the hosted authenticated
readiness inventory exposes the committed aerobic assessment, floor, resource, and construction
candidates. Preserve exact revision uncertainty wherever a provider does not expose a SHA.

#### Why this is next

The owner-facing aerobic slice is implemented, committed, locally validated, pushed to
`origin/main`, and present in the Vercel build, but the live readiness audit did not expose its
candidates. Required CI run `36233115399` failed only because the real-stack sign-in locator became
ambiguous, so Render was not proven to advance to the pushed implementation. Until that gate and
hosted mismatch are resolved, the application cannot reliably progress from the aerobic source
slice toward a live owner assessment and first training week.

#### In scope

- inspect the failing real-stack job and the current sign-in DOM before changing the locator;
- make the smallest test-only or UI-semantic correction that uniquely identifies the intended
  sign-in control while retaining the existing authentication contract;
- add or preserve regression coverage for the duplicate-link condition;
- run the relevant frontend and production-shaped real-stack checks, plus proportional static
  validation for changed files;
- commit the bounded repair locally, report the exact range, and request owner authorization before
  any push;
- after an authorized push, observe the complete required CI run and the normal Render deployment
  path without bypassing a failed check or manually forcing deployment;
- authenticate through the normal stable-origin Auth0 flow and verify that `/review/readiness`
  exposes the exact committed aerobic assessment, competency-floor, resource, and training-
  construction candidates;
- update this handoff with exact Git, CI, Vercel, Render, and live candidate evidence, keeping
  unavailable, stale, unauthorized, absent, and conflicting states distinct.

#### Out of scope

- changing aerobic assessment, floor, resource, dose, progression, safety, or planning behavior;
- ratifying any candidate or manufacturing an athlete, estimate, plan, week, or safety assignment;
- weakening, skipping, quarantining, or bypassing the required real-stack check;
- force-pushing, rewriting history, or pushing without explicit owner authorization for the exact
  range;
- manually deploying around the repository's required-check policy;
- changing provider plans, adding payment details, or creating paid infrastructure;
- descriptive architecture or package/service README reconciliation.

#### Authoritative references

- `AGENTS.md`
- `docs/deployment.md`
- `docs/decision-log/0143-browser-api-postgresql-smoke.md`
- `docs/decision-log/0144-owner-alpha-live-readiness-audit.md`
- `docs/decision-log/0146-owner-reviewable-aerobic-base-slice.md`
- `docs/decision-log/0147-guided-aerobic-review-and-persisted-duration-ceiling.md`
- `apps/web/e2e/real-stack.spec.ts`
- `apps/web/e2e/real-stack-global-setup.ts`
- `apps/web/app/review/readiness/`
- current Git, GitHub Actions, Vercel, Render, Auth0, and authenticated readiness evidence

#### Acceptance criteria

- The ambiguous sign-in locator is replaced by a unique, behavior-preserving assertion and the
  regression remains sensitive to a genuinely missing or incorrect sign-in control.
- Relevant local frontend checks pass, including the production-shaped browser/API/PostgreSQL lane
  when its dedicated database prerequisites are available; otherwise the exact external blocker is
  recorded before any push request.
- No push occurs until the owner approves the exact reviewed commit range.
- After an authorized push, every required GitHub CI job passes; a failure remains a failure and is
  not bypassed.
- Render advances through its normal required-check path, or the exact provider-side blocker is
  recorded without claiming alignment.
- The authenticated live readiness inventory exposes all four aerobic authority links: the
  12-minute walk/run assessment, provisional 12-minute walk/run floor, aerobic-base resource
  authority, and aerobic-base duration construction authority, with exact IDs, digests, and
  statuses recorded.
- Vercel and Render revisions are described only to the precision actually proven.
- No candidate, athlete, estimate, plan, week, safety assignment, or training record is written.
- The worktree ends clean and this handoff defines the next product-critical ticket toward a live
  aerobic assessment and first executable week.

#### Validation

- reproduce or inspect CI run `36233115399` and its failing real-stack step;
- run the focused real-stack Playwright specification against its PostgreSQL-backed stack;
- run the relevant Vitest/Playwright, ESLint, and TypeScript checks for changed frontend scope;
- run `git diff --check` and inspect the exact staged range before commit and push authorization;
- after push, verify every required GitHub Actions job and the provider deployment evidence;
- verify authenticated stable-origin navigation to `/review/readiness` and record the exact aerobic
  candidate projections without performing writes.

#### Blockers or owner decisions

An owner decision is required before pushing the exact reviewed commit range. Auth0, GitHub,
Vercel, or Render may require interactive owner authentication. The production-shaped local lane
requires its dedicated PostgreSQL test database. Do not replace any of those boundaries with a
weaker check or a manual deployment bypass.

## Ordered queue

### AGAS-0005 — Reconcile descriptive documentation

- Status: `QUEUED`
- Depends on: `AGAS-0004`
- Objective: bring `docs/architecture.md` and stale package/service boundary READMEs through the
  committed decisions without changing product behavior or policy.
- Priority boundary: documentation reconciliation remains deferred while it does not block the
  owner path to a live aerobic assessment, first executable week, and logged adaptive session. At
  AGAS-0004 completion, define the next product-critical ticket ahead of this one unless the
  documentation discrepancy itself blocks that path.

## Recently completed tickets

### AGAS-0003 — Perform authenticated owner-readiness audit

- Status: `COMPLETE`
- Completed: 2026-09-26
- Source/deployment boundary: local `main` started at
  `d46c8aff4c97dab56ea0e7a059469c73e22f6644`. After this ticket's documentation-only completion
  commit, `main` is expected to be two local commits ahead of `origin/main`; neither local
  completion commit was pushed or authorized for push. `origin/main` remained
  `6e8dbaf03490644f1e244ba62c024b6cb8a2fcd2`. GitHub deployment `6677204808` and status
  `18871521222` still recorded that exact pushed SHA as a successful Vercel Production deployment
  at the deployment-specific URL. The authenticated audit used the configured stable origin
  `https://adaptive-general-athleticism-system.vercel.app`; it served the same nine hashed Next.js
  chunk paths as the exact deployment URL, but the stable alias does not independently expose a Git
  SHA. Render `/health` and `/ready` returned HTTP 200 on 2026-09-26, with API version `0.1.0`, but
  neither exposed a SHA. Required CI run `36233115399` still had the known real-stack job failure,
  so Render's served revision and PWA/API alignment remain unproven.
- Authentication and authorization: the normal stable-origin Auth0 flow completed without
  credential automation. `owner-alpha-operator-access@1.0.0` reported `active`; both
  `assessment_reviewer` (`e26c2d14-b782-4758-8a48-6b49896b28f6`) and `planning_reviewer`
  (`91dcda5d-07dd-45c9-bb52-4c249ea4f6d4`) were already active, and `can_activate` was false. No
  subject, credential, token, or provider secret was recorded. Starting the flow from Vercel's
  deployment-specific hostname returned to the configured stable callback and therefore lacked the
  origin-bound login transaction; restarting from the stable production origin succeeded without
  bypassing Auth0.
- Candidate inventory: the authenticated route reported 0 ratified, 12 available or blocked, and
  0 conflicting candidates. Projection versions were `assessment-governance-candidates@1.0.0`,
  `planning-governance-candidates@1.0.0`, `competency-floor-candidates@1.1.0`,
  `resource-governance-candidates@1.0.0`, and
  `training-construction-candidates@1.0.0`. Exact point-in-time records were:

  | Family | Release label | Candidate | Digest | State |
  | --- | --- | --- | --- | --- |
  | Assessment | Countermovement vertical jump owner-alpha release | `94000000-0000-4000-8000-000000000003` | `sha256:8405a84056c34b478b2566bdc8fe4079eefaed7534af24eee03117b0b28cbfec` | available; not ratified |
  | Assessment | Maximum consecutive standard push-ups owner-alpha release | `94000000-0000-4000-8000-000000000002` | `sha256:65d78f85b93e8d855a0b70d2f18e18f3c9667757e40a58d161cdf892fa5734e7` | available; not ratified |
  | Assessment | 30-second chair stand owner-alpha release | `94000000-0000-4000-8000-000000000001` | `sha256:1fe8fc5ea92e079aa06717c174ead51c99dcf442216b1bcebbfbaf375ed389bb` | available; not ratified |
  | Planning policy | Conservative owner-alpha priority policy | `98400000-0000-4000-8000-000000000001` | `sha256:98642ffa342304f6b79f062469adc928c9f9f570142c66202ba5ba46d6fade89` | available; not ratified |
  | Planning policy | Deficit-only owner-alpha initial policy | `98400000-0000-4000-8000-000000000002` | `sha256:4c0054de09dd785988a5736044673b1ac711c18ca1ac4986d100f156c5268774` | available; not ratified |
  | Competency floor | Age 30-39 chair-stand lower-reference floor | `98310000-0000-4000-8000-000000000001` | `sha256:6315b6bba929a16c6fc1a6ab031b5ef5fc17394f5869e2d4c1ee78c8167e2caa` | available; not ratified |
  | Competency floor | Owner-alpha provisional standard-push-up floor | `98400000-0000-4000-8000-000000000003` | `sha256:a9b28f8a4c6139481c63c00cc9992ca378c9431b6f1242afb8f41cff0b917f7e` | available; not ratified |
  | Resource | First owner-alpha resource authorities | `98600000-0000-4000-8000-000000000001` | `sha256:460bb674bd1919a4570adfae8f089b6464114d80c6b69d3a1f5633ff6a5f9d16` | blocked; not ratified |
  | Resource | Owner-alpha push-up resource authorities | `98600000-0000-4000-8000-000000000002` | `sha256:f4f9e7aafb108acf26e3b8c9838d41c9aa0f65ce7e2ecdc1d1b7a7daa11ec08e` | blocked; not ratified |
  | Training construction | Owner-alpha chair-stand construction authorities | `98900000-0000-4000-8000-000000000001` | `sha256:8129420addb153ac5b1f120235323c45cec5ab2ec66305bc473593cf75add5f6` | blocked; not ratified |
  | Training construction | Owner-alpha push-up construction authorities | `98900000-0000-4000-8000-000000000002` | `sha256:23e01899f37590a70040e4f6d6bc2255c851ba062738bf45a6103da944855c63` | blocked; not ratified |
  | Training construction | Owner-alpha introductory jump-exposure authorities | `98900000-0000-4000-8000-000000000003` | `sha256:74d4610b112ea14f0142b19b1cecf977c2b410665deb5366ad41a654fa9cee19` | blocked; not ratified |

- Candidate blockers: both resource bundles required the deficit-only planning-policy snapshot and
  controlled seed catalog. Chair-stand and push-up construction each additionally required its
  matching resource bundle, the controlled adaptation, and the exact reviewed evidence claim. The
  introductory jump-exposure construction required the controlled exposure exercise, controlled
  adaptation, and exact reviewed evidence claim. Available assessment, planning-policy, and floor
  candidates reported no conflict or prerequisite issue. No candidate was ratified.
- Athlete and planning state: `account-athlete-directory@1.0.0` returned two owned athlete records,
  IDs `0fe4fa6f-d3de-49f8-8d95-239854fb0ecb` and
  `11ed73df-6e13-412e-9d6a-0b9c67d067da`, sharing the same display name. Direct authenticated
  current-week projections for `on=2026-09-26` returned HTTP 200 for both with exact matching
  athlete IDs, `week: null`, and `safety_policy_assignment: null`. These are genuine absent states,
  not unauthorized, unavailable, or conflicting responses; consequently there is no weekly-plan
  identity or review state to record.
- Reviewer boundary: `planning-review-queue@1.0.0` returned one item per owned athlete. Both were
  `workflow_stage=initial_planning`, `status=capability_estimate_required`, `readiness=blocked`,
  with no strategy or block ID and the exact issue/message “No current capability estimate is
  available for initial planning.”
- Safety/write boundary: no candidate ratification, reviewer activation, athlete mutation, plan
  creation, safety assignment, or other live-data write occurred. Validation was entirely
  read-only through the hosted UI, its authenticated projections, Git/GitHub deployment evidence,
  and public Render health/readiness endpoints.
- Local validation: `git diff --check` passed; the ticket changed only this handoff. Product tests
  were not rerun because AGAS-0003 made no product-code, governed-data, or behavior change.

### AGAS-0002 — Align remote and hosted revision

- Status: `COMPLETE`
- Completed: 2026-09-26
- Reviewed fast-forward: `f41516830f61d1c5f6d40b376fdc42b289a8de6f` to
  `6e8dbaf03490644f1e244ba62c024b6cb8a2fcd2`, containing commits `19b08006`, `9a5e8124`, and
  `6e8dbaf0` in that order.
- Authorization and push: the owner explicitly authorized the reported range; `git push origin
  main:main` succeeded without force or history rewrite, and `git ls-remote` confirmed the target.
- CI: run `36233115399` failed only in `Browser + API + PostgreSQL`; Backend, Frontend, and
  Deployment containers passed. The failure was preserved and not bypassed.
- Vercel: GitHub deployment `6677204808` and status `18871521222` record a successful Production
  deployment for exact SHA `6e8dbaf03490644f1e244ba62c024b6cb8a2fcd2` at
  `https://adaptive-general-athleticism-system-miil6x8b3-courtneymandela.vercel.app`.
- Render: `https://agas-api-staging.onrender.com/health` returned API version `0.1.0` and `/ready`
  returned ready, both with HTTP 200. Those endpoints expose no commit SHA. Because the Blueprint
  requires passing checks and CI failed, the target SHA is not claimed as deployed to Render; the
  exact API revision remains unproven.
- Safety boundary: no Auth0 sign-in, authenticated athlete/governance inspection, ratification, or
  live-data write occurred.

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
- The authenticated audit found all 12 prepared candidates unratified, two owned athlete records
  with the same display name, and no current week or safety-policy assignment for either athlete on
  2026-09-26. Both planning-queue items fail closed because no current capability estimate exists.
- Required CI currently fails in the real-stack browser lane because one sign-in locator is
  ambiguous; do not bypass the check or assume Render advanced past its prior accepted revision.
- Vercel's deployment-specific production record is proven at
  `6e8dbaf03490644f1e244ba62c024b6cb8a2fcd2`, and the stable alias served the same hashed client
  chunks during the audit, but the alias does not independently expose its Git SHA. The exact
  Render API SHA is unproven, so hosted surfaces must not be described as revision-aligned.
- Provider free-tier behavior and availability can change; `docs/deployment.md` remains the
  deployment runbook, but live dashboards are the source for current provider state.

## Fresh-chat prompt

When this file reports a stable checkpoint, use:

```text
Read AGENTS.md and docs/DEVELOPMENT_HANDOFF.md in full. Inspect Git status before changing
anything. Work only Active ticket AGAS-0004 — Restore hosted API alignment and expose the aerobic
candidate chain. Follow its referenced authorities and acceptance criteria, update the handoff
before stopping, and do not begin another ticket.
```
