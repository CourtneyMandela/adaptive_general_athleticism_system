# 0111 — Explicit signed-out PWA state

Date: 2026-09-12

Status: accepted

Decision version: `explicit-signed-out-pwa-state@1.0.0`

## Decision

Resolve hosted browser-session presence on the server-rendered home route and pass that state into
the athlete dashboard. When no valid encrypted session exists, the PWA renders a single sign-in
action and does not request the athlete directory or current-week projections. Valid athlete and
calendar-date query context is preserved in the OIDC return path; malformed context is discarded.

Development authentication remains unchanged and continues to load fixture-backed athlete state
without a browser session.

## Reason

Session expiry is expected on the free hosted alpha. Previously the client attempted account data
recovery anyway, received a 401, and presented that ordinary authentication boundary as “We
couldn’t recover your profiles.” That implied data loss or backend failure and offered a retry that
could not succeed before authentication.

## Alternatives considered

- **Interpret every 401 inside the directory client.** Rejected because the server already has the
  authoritative encrypted-session boundary and can avoid the unnecessary request entirely.
- **Silently redirect to the identity provider.** Rejected because an explicit sign-in action is
  less surprising and avoids involuntary cross-site navigation.
- **Lengthen the session indefinitely.** Rejected because it weakens the existing credential
  lifetime boundary and does not solve clear expiry handling.

## Assumptions and provisional choices

- Hosted session presence means the cookie decrypts and has not expired; the API still performs
  authoritative authentication and resource authorization on every request.
- The same sign-in state can later include account-recovery help without changing domain state.

## Consequences

- A signed-out or expired phone session looks intentional rather than broken.
- Athlete APIs receive no avoidable unauthenticated traffic from the home dashboard.
- A user who followed an athlete/week deep link resumes that validated view after authentication.
