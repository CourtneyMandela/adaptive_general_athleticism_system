# 0109 — Authenticated cross-device athlete directory

Date: 2026-09-12

Status: accepted

Decision version: `account-athlete-directory@1.0.0`

## Decision

Expose a read-only `GET /v1/athletes` projection containing only athlete profiles owned by the
exact authenticated issuer and subject. The projection includes enough persisted context to make
an explicit choice—profile creation time, reported goals, environment names, and ownership
provenance—but no inferred preferred profile and no cross-account records.

The PWA loads this directory when it starts. Exactly one owned profile is recovered automatically.
More than one profile requires a visible user choice and suppresses new-profile onboarding so a
new device cannot accidentally create another duplicate. Zero profiles exposes first onboarding.
An unavailable or invalid directory fails closed instead of presenting onboarding. Explicit
athlete deep links remain supported, and the raw UUID connector remains development-only.

Existing duplicates are neither merged nor deleted. Their immutable observations and planning
histories remain independent until a separately designed reconciliation workflow can prove how
records should be handled.

## Reason

The hosted PWA previously knew the current athlete only from a URL or build-time development ID.
Signing in on another phone therefore presented onboarding even though the backend already held an
owned athlete. This made accidental duplicate creation likely and made the app impractical away
from the original device.

Account ownership is already authoritative and is the narrowest reliable cross-device recovery
key. The directory restores usability without weakening ownership authorization or storing athlete
state in browser persistence.

## Alternatives considered

- **Store the athlete ID in local storage.** Rejected because it does not follow the user to a new
  device and stale browser state is not authorization.
- **Automatically choose the newest or most complete profile.** Rejected because recency and record
  count do not prove which duplicate represents the intended athlete history.
- **Merge or delete the duplicate automatically.** Rejected because observations, estimates, and
  decisions are historical records whose identity and provenance cannot be guessed.
- **Make every account own exactly one athlete in the database.** Deferred because the domain may
  later support coaches or multiple managed athletes; this milestone only needs honest selection.

## Assumptions and uncertainty

- The owner-alpha has a small number of profiles, so listing compact owned summaries is sufficient.
- Profile creation time, reported goals, and environment names will usually distinguish accidental
  duplicates. A richer comparison projection may be needed before reconciliation.
- Directory contents are account data and therefore remain authenticated, same-origin, and
  `no-store` at the web gateway.

## Consequences

- The same sign-in can recover an athlete on a phone or computer without UUID copy and paste.
- Multiple profiles are explicit and non-destructive instead of being silently collapsed.
- First onboarding appears only after an authoritative empty directory response.
- Duplicate reconciliation, archival, and account lifecycle remain separate future work.
