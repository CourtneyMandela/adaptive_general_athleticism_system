# 0082 — Installable, fail-closed PWA shell

Date: 2026-08-31

Status: accepted for this milestone

## Decision

Complete the bounded installability contract for production web builds with a scoped manifest,
ordinary and maskable application icons, production-only service-worker registration, and a
pre-cached offline document.

Keep navigations network-first. Cache only the offline/install shell and same-origin compiled
static assets. Do not cache athlete pages, API responses, bearer credentials, assessment results,
training prescriptions, or workout writes. When navigation cannot reach the application, return an
explicit offline page that states no athlete data is displayed, changed, or queued.

## Reason

Independent phone use should feel like an installed application once hosting and login exist, but
installability must not be confused with safe offline training behavior. A generic cache-first PWA
could expose stale prescriptions or sensitive state and an ungoverned write queue could lose
provenance, duplicate performances, or hide conflicts.

The minimal shell provides useful installation and failure behavior now while preserving the
authoritative online data model. It creates an automated boundary that future offline work must
deliberately replace rather than silently expanding browser storage.

## Major implementation choices

- Register the service worker only in a production web build so local development is not polluted
  by persistent caches.
- Use a stable root `id`, `start_url`, and `scope` and provide separate `any` and `maskable` SVG
  icons.
- Precache only the manifest, icons, and a self-contained offline page.
- Delete only superseded caches carrying the AGAS shell namespace.
- Use network-first handling for every navigation and never put a successful page response in the
  shell cache.
- Permit stale-while-revalidate reuse only for same-origin `/_next/static/`, icon, and manifest
  requests.
- Ignore non-GET, cross-origin, API, and other application requests entirely.
- Verify the served manifest and a real offline navigation with Playwright, plus a static regression
  contract that rejects an athlete-data cache/outbox.

## Alternatives considered

- **Cache rendered athlete and current-week pages.** Rejected because stale plans or safety state
  could appear authoritative and sensitive athlete content would persist in a broadly scoped cache.
- **Queue workout writes with Background Sync.** Deferred. Correct implementation needs stable
  command IDs, observation/performance timestamps, authentication expiry behavior, conflict and
  supersession semantics, user-visible pending state, and tests across reconnect/retry cases.
- **Use a third-party PWA wrapper.** Rejected for this narrow shell because the explicit service
  worker is small, inspectable, and intentionally does much less than generic runtime caching.
- **Register in development.** Rejected because old development assets and routes can survive code
  changes and produce misleading local failures.
- **Claim full offline support from installability.** Rejected. The offline page is deliberately a
  connectivity boundary, not a training mode.

## Assumptions

- Hosted production traffic uses HTTPS, which is required for ordinary service-worker operation.
- Current authoritative reads and all writes continue to require API connectivity.
- SVG manifest icons are accepted by the initial target browsers; platform-specific PNG/touch
  assets may be added after real-device staging acceptance.

## Unresolved questions

- Whether a future training session must remain fully readable and recordable offline.
- Which records may be encrypted/stored locally and how account logout/deletion clears them.
- Idempotency, chronological provenance, authentication renewal, merge/conflict, retry, and
  correction semantics for an offline command outbox.
- iOS/Android install affordance, touch-icon, splash-screen, and notification requirements after
  testing on actual supported devices.

## Consequences

A production-hosted AGAS frontend now satisfies a basic installable-shell contract and degrades
truthfully when disconnected. The service worker does not make the current application usable for
offline workouts and cannot present stale athlete data as current.

Independent phone training still depends on hosted HTTPS, real browser authentication, and governed
training content. If offline workouts become a product requirement, the next implementation must
introduce an explicit local-data and synchronization architecture rather than broadening this cache
opportunistically.
