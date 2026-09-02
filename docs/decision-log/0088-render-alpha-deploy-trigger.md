# 0088 — Render alpha deploy trigger

Date: 2026-09-02

Status: accepted for the owner-only hosted alpha

Decision version: `render-alpha-deploy-trigger@1.0.0`

## Decision

Set the root free-alpha Render Blueprint to `autoDeployTrigger: commit` so each accepted commit on
`main` triggers an API deployment.

Keep `checksPass` in the future paid topology. Before that topology is activated, add required
continuous-integration checks and verify that Render recognizes them.

## Reason

The free alpha was configured with `checksPass`, but the repository has no GitHub Actions or other
GitHub Checks producer. Render therefore detected zero checks and deliberately did not deploy new
commits. GitHub and Vercel advanced while the API remained on an older contract, creating an
avoidable frontend/backend version mismatch.

Deploying on commit restores working continuous delivery for the current single-owner alpha. The
repository's local release validation remains mandatory; this choice does not redefine untested
code as acceptable.

## Alternatives considered

- **Add CI solely to preserve `checksPass`.** Deferred. CI is valuable, but introducing and
  debugging a hosted workflow is a separate reliability milestone and should not be fabricated as
  a prerequisite for deploying the already validated alpha.
- **Continue manual Render deploys.** Rejected because it makes every GitHub push capable of
  leaving the production PWA and API on incompatible contracts.
- **Disable Vercel auto-deploy.** Rejected because synchronizing two manual deploys does not solve
  the missing API deployment trigger.

## Evidence

- Render's Blueprint reference defines `commit` as deployment on every linked-branch commit and
  `checksPass` as waiting for linked CI checks.
- Render's deployment documentation states that zero detected checks do not trigger a deployment
  and instructs repositories without CI to use On Commit.
- The service dashboard showed `d8dc4be` as the last successful API deployment while GitHub and
  Vercel had advanced to `b61ef28`.

## Consequences

- New commits to `main` automatically rebuild and deploy the free API.
- The PWA and API are less likely to remain on incompatible commits after a push.
- A future CI milestone should switch the trigger back to `checksPass` only after required checks
  are present and proven on `main`.
