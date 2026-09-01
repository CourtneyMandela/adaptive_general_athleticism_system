# 0084 — Provider-neutral OIDC browser login

Date: 2026-09-01

Status: accepted for this milestone

## Decision

Add a provider-neutral OpenID Connect authorization-code login adapter to the Next.js server. A
login route creates high-entropy state, nonce, and an S256 PKCE verifier and stores them in a
short-lived encrypted `HttpOnly` transaction cookie. The callback exchanges the single-use code at
an explicitly configured token endpoint, verifies the returned ID token against the configured
issuer, client audience, asymmetric algorithm allow-list, JWKS, timestamp, and nonce, then places
only the access token and its bounded expiry in the encrypted server session from decision 0083.

Use explicit authorization, token, issuer, and JWKS settings rather than runtime discovery. Require
a confidential client using `client_secret_basic`. Permit a configured OIDC scope set that must
include `openid`, and an optional RFC 8707 resource URI for the AGAS API. Cap the local browser
session at one hour even when the provider reports a longer access-token lifetime.

Add a same-origin POST logout route that clears both AGAS cookies. Logout ends the local AGAS
session only; provider-wide single logout remains provider-specific and is not implied.

## Reason

The PWA now has an encrypted server session and private API gateway but no standards-based way to
obtain that session. Authorization code with PKCE keeps access tokens out of browser JavaScript,
binds the callback to the initiating browser, and leaves FastAPI responsible for authoritative
access-token validation and athlete authorization.

Validating the OIDC ID token and nonce before creating the local session ensures the callback is
bound to the configured provider and login transaction. Explicit endpoints and algorithms keep the
first adapter inspectable and avoid silently trusting mutable discovery metadata.

## Major implementation choices

- Generate state and nonce from 32 random bytes and the PKCE verifier from 64 random bytes.
- Encrypt a versioned ten-minute transaction envelope with the existing server-session key but a
  distinct JWE type and cookie name.
- Use `Secure`, `HttpOnly`, `SameSite=Lax`, root-path, host-only cookies under the `__Host-` naming
  contract.
- Reject duplicate callback parameters or cookies, stale/tampered transactions, mismatched state,
  token redirects, non-Bearer token responses, malformed lifetimes, and unverified ID tokens.
- Bound token-response size and network duration, suppress provider error details, and mark every
  login response `no-store`.
- Retain no ID token, refresh token, email, profile, roles, or athlete identifiers in the session.
- Accept only a local relative return path captured before redirect; reject external or ambiguous
  return destinations.
- Keep the API's external JWT verifier authoritative for issuer, API audience, signature, subject,
  and ownership on every athlete request.

## Alternatives considered

- **Vendor SDK.** Deferred because hosting, provider, cost, privacy, recovery, and account lifecycle
  decisions remain open.
- **Browser-managed PKCE tokens.** Rejected because bearer material would be readable by executing
  browser JavaScript and the API would need public cross-origin exposure.
- **OAuth code flow without ID-token verification.** Rejected for the OIDC adapter because state
  and PKCE alone do not validate the provider's authentication assertion and nonce.
- **Refresh tokens in the encrypted cookie.** Deferred because renewal, revocation, rotation,
  replay, logout, and lost-device policy require an explicit lifecycle design.
- **Opaque server-side session store.** Deferred until revocation requirements and the production
  hosting topology justify additional persistent or cache infrastructure.
- **Dynamic OIDC discovery.** Deferred; reviewed explicit endpoints are smaller and fail closed.
- **Provider-wide logout.** Deferred because end-session behavior and ID-token hints are not
  portable enough to invent before provider selection.

## Assumptions

- The selected provider supports authorization code, S256 PKCE, `client_secret_basic`, OIDC nonce,
  asymmetric signed ID tokens, and JWT access tokens accepted by decision 0080.
- The configured web OIDC issuer and JWKS describe the same authority configured for FastAPI.
- The deployment has one public HTTPS origin and stores the client secret and encryption key in a
  server-side secret store.
- Reauthentication after at most one hour is acceptable until a refresh-session policy exists.

## Unresolved questions

- Provider choice, tenant configuration, API scopes/resource semantics, and hosted-domain setup.
- Account signup policy, verification requirements, recovery, MFA, consent, account linking, and
  abuse controls.
- Refresh-token rotation, server-side revocation, encryption-key overlap, lost-device response, and
  forced logout.
- Provider-wide logout, deletion/export, retention, and administrator lifecycle workflows.
- Whether production ingress adds stateful rate limiting to login and callback endpoints.

## Consequences

A correctly configured hosted deployment can complete a standards-based phone login, create an
encrypted local session, and call private FastAPI without exposing bearer tokens to JavaScript.
The repository still does not choose or provision an identity provider, hostname, client
registration, recovery workflow, or hosting account, so this code alone is not a production launch.

This milestone changes authentication transport only. It creates no athlete state, scientific
claim, training authority, prescription, or generic workout behavior.
