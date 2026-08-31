# 0081 — Vendor-neutral container deployment boundary

Date: 2026-08-31

Status: accepted for this milestone

## Decision

Package the existing modular monorepo as two independently deployable OCI-compatible images: one
FastAPI resource-server image that also contains the Alembic migration runtime, and one Next.js
standalone PWA image. Use a separate one-shot migration service before API startup. Run both final
application images as fixed, non-root users.

Add a single-host Compose reference that keeps PostgreSQL private, binds application ports to host
loopback, and leaves public HTTPS termination outside the stack. Validate the Compose model and
both Linux image builds in CI. Do not select a cloud, identity, reverse-proxy, or database vendor in
this milestone.

## Reason

The local development topology cannot make the PWA independently reachable on a phone. Reproducible
runtime images are the smallest provider-neutral step toward staging and hosting. They also reveal
runtime dependencies in CI without changing domain behavior or pretending that the unresolved
browser-login and scientific-governance work is complete.

The conceptual domain, planner, evidence, and safety boundaries do not require separate deployed
microservices. Keeping one backend image preserves transactional behavior and avoids operational
complexity that has no current product benefit.

## Major implementation choices

- Build from maintained official Python and Node base-image families using multi-stage Dockerfiles.
- Install the Python project into an isolated build-stage environment and copy only that runtime,
  migrations, and Alembic configuration into the final API image.
- Use Next.js `output: "standalone"` and explicitly copy `public` and `.next/static` into the traced
  monorepo layout.
- Reuse the exact API image for migrations rather than maintaining a divergent migration artifact.
- Require database readiness, successful migrations, and then API readiness in dependency order.
- Do not publish PostgreSQL. Bind API/PWA ports to loopback so a separately reviewed TLS ingress is
  the only intended public path.
- Compile only the public API URL into the PWA. Keep database and external-JWT settings at runtime.
- Build images in GitHub CI because the current Windows workstation has no Docker runtime.

## Alternatives considered

- **Choose a managed application platform now.** Deferred because cost, region, privacy, identity,
  database, and operations requirements have not been selected.
- **Add Nginx, Caddy, or Traefik to the repository.** Deferred. TLS certificates, public DNS, request
  limits, and proxy trust are deployment-specific security decisions, not safe generic defaults.
- **Run migrations in every API entrypoint.** Rejected because concurrent replicas could race and
  application readiness would no longer distinguish schema preparation from serving traffic.
- **Build one image containing API and PWA.** Rejected because they have different runtimes,
  scaling, health, and public configuration boundaries.
- **Split planner, safety, and evidence into network services.** Rejected as premature operational
  complexity; their code boundaries remain explicit inside the transactional backend.
- **Expose the database for convenience.** Rejected for the deployment reference. Local development
  retains its separate published-port Compose file.

## Assumptions

- The eventual host supports ordinary Linux containers or can consume equivalent build artifacts.
- Public web and API domains terminate HTTPS at a maintained reverse proxy or cloud ingress.
- The eventual identity provider satisfies decision 0080's asymmetric access-token contract.
- The public API URL is known when the PWA image is built.
- A single-host PostgreSQL container is only a topology reference; production may use managed
  PostgreSQL if its durability and security contract is reviewed.

## Unresolved questions

- Hosting provider, region, budget, data residency, domain, and DNS ownership.
- Identity provider and browser authorization/session pattern.
- Reverse proxy or ingress implementation and trusted-forwarded-header boundary.
- Secret manager, encryption, rotation, and production operator access.
- Backup frequency, retention, restore objectives, and migration rollback procedure.
- Logs, metrics, tracing, alerting, service objectives, and incident response.
- Multi-instance requirements and any shared Next.js cache coordination.

## Consequences

CI can now prove that the source produces deployable API and PWA images and that the reference
startup graph is structurally valid. This reduces hosting risk without changing training logic or
claiming the application is production-ready.

Independent phone use still requires hosted HTTPS endpoints plus a real browser login/session. It
also remains scientifically blocked from producing a production training path until governed
assessment, safety, planning, and evidence authorities exist. The container boundary must not be
interpreted as approval to deploy sensitive athlete data.
