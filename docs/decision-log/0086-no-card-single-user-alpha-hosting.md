# 0086 — No-card single-user alpha hosting

Date: 2026-09-01

Status: accepted for the first owner-only hosted alpha; supersedes decision 0085's paid topology as
the immediate deployment target

## Decision

Deploy the owner-only alpha with services that can be created without a payment method:

- Vercel Hobby hosts the Next.js PWA and its encrypted server-session gateway.
- One Render Free public web service runs the FastAPI container.
- Neon Free supplies authoritative PostgreSQL using its direct TLS connection string.
- Auth0 Free remains the OpenID Connect authority.
- Provider-issued hostnames are used instead of a paid or card-verified custom domain.

Keep the browser on the same-origin `/api/agas` gateway. Configure that server-side gateway to call
the public Render API over HTTPS. FastAPI continues to require an Auth0 access token with the exact
issuer and audience on athlete and operator routes; CORS remains empty because browsers do not call
FastAPI directly.

The root `render.yaml` describes only the free API. Preserve the previously accepted private
Render topology as `deploy/render-paid.yaml` for a later deliberate upgrade, not for immediate
provisioning.

## Reason

The approximately USD 20 monthly Render topology reserved three always-on managed resources even
though the first alpha has one user and long idle periods. That is a reliability-oriented staging
shape, not a product requirement. A no-card free topology makes the financial failure mode service
suspension instead of an unexpected usage bill and lets actual use determine whether faster wake-up
is worth purchasing.

This change does not alter athlete data, scientific governance, planning, safety, or prescription
behavior. It changes where the existing web, API, database, and identity boundaries run.

## Major implementation choices

- Keep PostgreSQL authoritative and external to Render; do not store athlete records on Render's
  ephemeral filesystem.
- Use Neon's direct, TLS-required connection string for this low-concurrency alpha so the same URL
  can run Alembic and serve the application without introducing a second migration secret.
- Because Render Free does not support pre-deploy commands, allow an explicit
  `AGAS_MIGRATE_ON_STARTUP=true` container mode. It runs Alembic before Uvicorn only for the single
  free instance. The default remains disabled, and multi-instance/paid deployments retain a
  separate pre-deploy migration step.
- Permit the Vercel gateway timeout to be configured from 1 to 55 seconds, retaining 15 seconds by
  default. The free deployment uses 55 seconds to accommodate a sleeping API while remaining below
  the route's 60-second duration ceiling.
- Keep the FastAPI audience identifier `https://api.agas.staging`; it is an OAuth identifier, not
  the public Render hostname.
- Do not add a payment method. If any provider requires one during provisioning, stop and review the
  provider and controls rather than silently enabling usage billing.

## Alternatives considered

- **Activate the paid Render topology.** Rejected for the first owner-only alpha because its fixed
  cost is disproportionate to current use.
- **Google Cloud Run plus Neon.** Technically suitable and likely within free allowances, but it
  requires a billing account. Ordinary budget alerts are not hard caps; Cloud Run spend caps are
  currently a preview feature.
- **A small Fly.io machine.** Potentially a few dollars monthly, but it adds a card, usage billing,
  and more operational responsibility before cold-start inconvenience has been measured.
- **Railway Hobby.** Predictable minimum spend is lower than the original topology, but charges can
  exceed the included usage and there is no current evidence that paid wake-up is necessary.
- **Render Free PostgreSQL.** Rejected because it expires after 30 days and has no backups.
- **Combine web, API, and PostgreSQL into one free container.** Rejected because ephemeral storage
  would risk athlete history and combining runtimes would weaken the existing replaceable boundary.

## Evidence

- [Render free services](https://render.com/docs/free) documents idle spin-down, approximately
  one-minute wake-up, 750 monthly instance hours, ephemeral filesystems, suspension without a
  payment method, and the 30-day lifetime of free Render PostgreSQL.
- [Render deploy steps](https://render.com/docs/deploys) documents that pre-deploy commands are
  available only for paid web/private/background services.
- [Vercel Hobby](https://vercel.com/docs/plans/hobby) documents the personal, non-commercial free
  plan and pause behavior at included limits.
- [Vercel monorepos](https://vercel.com/docs/monorepos) documents selecting a workspace package as
  the project root.
- [Neon pricing](https://neon.com/pricing) documents a no-card, no-time-limit free PostgreSQL plan,
  0.5 GB storage, scale-to-zero compute, and limited restore history.
- [Auth0 pricing](https://auth0.com/pricing) documents the no-card free identity tier.

## Assumptions and uncertainty

- The deployment is personal, non-commercial, owner-only alpha usage and therefore fits Vercel
  Hobby's stated scope.
- One athlete's structured records remain well below Neon's 0.5 GB storage limit during the alpha;
  usage must still be monitored rather than assumed indefinitely.
- Render's external-database traffic remains ordinary for one user. Render may suspend a free
  service with unusually high outbound traffic.
- A cold start or transient free-provider outage is acceptable while evaluating the application.
- The actual Vercel and Render hostnames must be known before Auth0 callback/origin settings are
  finalized.
- Free-plan terms and limits can change. Provisioning must recheck provider dashboards and must not
  opt into a paid trial.

## Consequences

The expected recurring infrastructure charge is zero and no provider should have a payment method.
The PWA should load promptly from Vercel, but its first authenticated data request after inactivity
may wait or fail once while Render and Neon wake. Free services can pause at quota and have no
production uptime commitment.

The public FastAPI hostname increases reachability but not authority: protected endpoints still
require the exact asymmetric Auth0 token contract, and browser requests remain same-origin through
the encrypted gateway. A future paid upgrade can move the same container behind private networking
without changing domain behavior.

Before irreplaceable real training history accumulates, implement and test owner data export plus a
restore procedure. Free hosting is not a substitute for data portability or backup.
