# 0085 — Render and Auth0 staging platform

Date: 2026-09-01

Status: accepted provisionally for single-user staging

## Decision

Use Render for the first hosted staging topology and Auth0 for the first real identity authority.
Deploy the existing Next.js container as the only public web service, FastAPI as a private service,
and PostgreSQL as a managed database with public access disabled. Run Alembic as the API service's
pre-deploy command and deploy only after GitHub checks pass.

Use an Auth0 Regular Web Application and a custom API. Request the custom API identifier through an
explicit OAuth audience parameter, require authorization code with S256 PKCE, authenticate the
confidential client at the token endpoint, and continue verifying RS256 access and ID tokens against
the tenant JWKS. Keep Auth0 issuer, endpoints, client credentials, and the browser-session key in
Render secret configuration rather than source control.

## Reason

The current two-container boundary maps directly to Render's public web service, private service,
private network, managed PostgreSQL, Docker, pre-deploy migration, and Blueprint capabilities. This
avoids operating a VM, TLS proxy, container registry, and database backup mechanism merely to get a
single-user staging installation onto a phone.

Auth0 satisfies the existing provider-neutral contract and can issue an asymmetric JWT access token
for a registered API audience. Its hosted recovery and login surface are safer than building
credentials locally. Both choices remain replaceable because domain identity continues to use the
immutable issuer/subject pair and no vendor SDK enters athlete, planning, evidence, or safety code.

## Alternatives considered

- **Railway.** Likely lower-cost at very small usage, but usage-based billing and more manual service
  composition are less predictable for the first deployment.
- **Vercel plus a separate API/database host.** Excellent Next.js hosting, but it adds another vendor
  and public/private network boundary without improving the current alpha.
- **AWS with Cognito and managed containers.** Powerful but operationally disproportionate for a
  one-person staging system.
- **Free Render web and PostgreSQL plans.** Rejected for durable staging because free PostgreSQL
  expires and a free public API would violate the private backend boundary.
- **Self-hosted VM and identity service.** Rejected because patching, TLS, backups, email delivery,
  and identity operations would delay the training product and increase security risk.

## Evidence

- [Render Blueprint specification](https://render.com/docs/blueprint-spec) documents Docker services,
  private services, managed PostgreSQL references, secret prompts, CI-gated deployment, and
  pre-deploy commands.
- [Render private services](https://render.com/docs/private-services) documents that the API remains
  unreachable from the public internet while being reachable from the PWA on the private network.
- [Auth0 authorization with PKCE](https://auth0.com/docs/api/authentication/authorization-code-flow-with-pkce/authorize-with-pkce)
  documents S256 PKCE, audience, state, callback, and authorization-code behavior.
- [Auth0 pricing](https://auth0.com/pricing) currently lists a free B2C tier suitable for staging.
- [Render pricing](https://render.com/pricing) is the authority that must be checked at provisioning;
  the cost here is an estimate, not a contractual quote.

## Assumptions and provisional choices

- The first deployment is staging for its owner, not authorization to store broad public or clinical
  data.
- Virginia is the provisional region because the owner operates in the US Eastern time zone.
- The initial Render footprint uses the smallest paid always-on web, private-service, and PostgreSQL
  plans. Current expected cost is approximately USD 20 per month before overages; pricing must be
  confirmed in the Render checkout before resources are created.
- Auth0's free tier is sufficient for this alpha. Provider MFA, custom-domain, log-streaming, and
  separate tenant policy remain later review items.
- The public staging origin is provisionally
  `https://agas-courtneymandela-staging.onrender.com`; a custom domain is deferred.
- The Auth0 API identifier is `https://api.agas.staging`. It is an audience identifier, not a public
  FastAPI address.

## Unresolved questions

- Backup retention, restore testing, monitoring/alerts, and final data-retention policy.
- Whether the staging hostname is available unchanged when Render creates the Blueprint.
- Hosted email sender, recovery policy, MFA requirement, and production identity tenant separation.
- Production region/data residency, custom domain, formal privacy terms, and incident response.
- Refresh/revocation and provider-wide logout; the current session intentionally expires within one
  hour and local logout does not revoke an Auth0 session.

## Consequences

The repository can express a concrete, reviewable staging topology rather than an abstract container
example. Creating the external accounts and resources still requires the owner's acceptance of
provider terms and the Render billing estimate. A successful staging deploy will make the PWA
reachable from a phone, but it will not manufacture missing scientific governance or make every
training path usable.

This decision changes deployment and authentication configuration only. It creates no athlete
observation, estimate, evidence claim, planning authority, prescription, or scientific assertion.
