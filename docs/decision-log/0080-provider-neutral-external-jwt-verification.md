# 0080 — Provider-neutral external JWT verification

Date: 2026-08-31

Status: accepted for this milestone

## Decision

Implement a provider-neutral production authentication boundary for asymmetric, signed JWT access
tokens. Configure the exact issuer, API audience, JWKS endpoint, allowed asymmetric algorithms,
clock-skew allowance, network timeout, and JWKS cache lifetime through server-only environment
settings.

The verifier must validate the cryptographic signature, issuer, audience, expiration, issued-at
time, and non-empty subject. It must obtain signing keys from the configured JWKS endpoint, support
ordinary key rotation through bounded caching and refresh, and never derive its allowed algorithms
from an untrusted token header.

Keep browser login/session acquisition and identity-provider selection outside this milestone. The
backend contract will accept a standards-based access token once a provider is selected and the
PWA obtains it through a reviewed authorization-code-with-PKCE or server-session flow.

## Reason

Development bearer tokens are intentionally rejected in production, so the current PWA cannot be
safely hosted for independent phone access. Choosing a commercial identity vendor now would create
an unnecessary product dependency. Verifying a narrowly configured issuer/audience/JWKS contract
creates the required resource-server boundary without deciding the eventual login provider.

## Major implementation choices

- Use PyJWT's maintained JWKS client and asymmetric signature verification.
- Require `iss`, `aud`, `exp`, `iat`, and `sub`; do not accept an email address as identity.
- Persist the stable `(issuer, subject)` pair through the existing account boundary.
- Return `401` for invalid credentials and `503` when signing-key retrieval is unavailable, without
  exposing token contents or provider internals.
- Require complete external configuration in production. Development external mode may remain
  unconfigured so fail-closed tests and disabled administrative transports can run locally.
- Permit only an explicit allow-list of asymmetric algorithms; symmetric `HS*` and unsigned tokens
  are not accepted.

## Alternatives considered

- **Deploy with development tokens.** Rejected because they are public identity selectors, not
  credentials.
- **Choose Auth0, Clerk, Cognito, or another vendor now.** Deferred until hosting, cost, account
  recovery, and privacy requirements are selected.
- **Trust identity headers from a reverse proxy.** Rejected as the default because it silently
  depends on correct network isolation and proxy configuration.
- **Discover all provider metadata dynamically.** Deferred. Explicit issuer and JWKS configuration
  reduces ambiguity at the resource-server boundary; provider setup may still derive these values
  from reviewed OpenID Connect metadata.

## Assumptions and unresolved questions

- The eventual provider issues asymmetric JWT access tokens for the AGAS API. Opaque tokens would
  require an introspection adapter rather than this verifier.
- The browser session design, provider choice, login UI, logout, account recovery, consent,
  deletion/export, and production authorization administration remain unresolved.
- A deployment must use HTTPS for both the issuer and JWKS endpoint.

## Consequences

The API can become a safely configured OAuth/OIDC resource server, but this alone does not make the
PWA deployable or authorize production athlete data. A later milestone must connect a real identity
provider and browser session, then validate the full hosted flow on a phone-sized client.
