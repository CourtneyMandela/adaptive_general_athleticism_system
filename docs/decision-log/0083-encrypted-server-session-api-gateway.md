# 0083 — Encrypted server-session API gateway

Date: 2026-08-31

Status: accepted for this milestone

## Decision

Use the Next.js application as a narrow backend-for-frontend gateway for production browser API
requests. Production browser code calls same-origin `/api/agas`; the gateway reads one encrypted,
`HttpOnly` session cookie, validates its local expiry, and attaches the contained OAuth access token
only to an internal FastAPI request. Browser JavaScript does not read or submit the access token.

Encrypt the stateless session envelope with compact JWE using direct 256-bit key management and
AES-256-GCM from the maintained `jose` library. Require a server-only, base64url-encoded 32-byte
key. Keep session creation private to server code; this milestone does not add an endpoint that can
mint a session or choose an identity provider.

The gateway will use an explicit internal API origin, reconstruct only encoded path segments and
query parameters, allow only the application's current HTTP methods, forward an allow-list of
request and response headers, bound request size and upstream duration, disable response caching,
and return generic failures. State-changing methods require the configured public web origin and
same-origin Fetch Metadata where supplied.

Development mode retains the explicit `dev.*` selectors and direct API origin. A public build-time
authentication mode chooses between that local transport and the production session transport.

## Reason

The FastAPI resource server can validate production access tokens, but the PWA currently embeds a
development bearer selector and sends authorization headers from JavaScript. Connecting a provider
directly to that shape would make bearer material accessible to client code and require cross-origin
API exposure.

A small same-origin gateway creates the server-session seam recommended by the chosen Next.js
runtime without replacing FastAPI or duplicating domain authorization. It lets a later OIDC adapter
perform authorization-code-with-PKCE, encrypt the resulting short-lived access token, and set the
cookie without changing every application use case.

## Major implementation choices

- Keep FastAPI authoritative for JWT validation, account identity, athlete ownership, and reviewer
  roles. The gateway establishes no domain authorization.
- Use compact JWE (`alg=dir`, `enc=A256GCM`) rather than custom cryptography or a signed plaintext
  token.
- Store only access token, provider expiry, and envelope version. Do not store profile, email,
  athlete IDs, roles, or refresh tokens in the first envelope.
- Use the `__Host-` cookie naming contract so a future login adapter must set `Secure`, root path,
  and no `Domain` attribute.
- Treat every route handler as public: validate session and request properties inside the handler.
- Buffer at most one MiB because all current API commands are bounded JSON documents; streaming and
  file upload are not product requirements.
- Require exact configured public origin for state-changing browser requests. SameSite cookies are
  defense in depth, not the sole cross-site request defense.
- Keep upstream errors generic and never return cookie, token, key, or internal host details.
- Do not expose the FastAPI port in the production Compose reference; the web gateway reaches it on
  the private Compose network.

## Alternatives considered

- **Browser-held access token with PKCE.** Rejected as the default because any executing browser
  JavaScript can access the bearer and the API remains cross-origin.
- **Select a commercial identity SDK now.** Deferred because provider, cost, recovery, privacy, and
  account-lifecycle requirements remain undecided.
- **Implement passwords in AGAS.** Rejected because password verification, reset, MFA, compromise
  detection, and identity assurance are not this product's domain.
- **Store an opaque session in Redis or PostgreSQL immediately.** Deferred. It improves revocation
  but adds schema and operational state before the provider/session lifetime contract is known.
- **Put a raw access token in an `HttpOnly` cookie.** Rejected because browser storage would contain
  directly reusable bearer material without confidentiality at rest.
- **Forward all incoming headers and bodies without limits.** Rejected because the gateway is a
  public security boundary, not a transparent network tunnel.
- **Replace FastAPI with Next.js route handlers.** Rejected because it would duplicate or move the
  existing transactional domain and authorization boundaries.

## Assumptions

- The eventual provider supplies a short-lived asymmetric JWT access token accepted by decision
  0080.
- The deployed web runtime can reach FastAPI through a private HTTP origin.
- Production uses one public HTTPS web origin and the access-token audience remains the FastAPI API.
- Logging out or rotating the first encryption key invalidates the stateless session immediately.

## Unresolved questions

- Identity provider and provider-specific authorization, token, logout, and recovery behavior.
- Authorization-code state, nonce, PKCE, callback, refresh, and session-renewal implementation.
- Whether production requires server-side session revocation and rotation-key overlap.
- Consent, account linking, export/deletion, lost-device, and administrator lifecycle workflows.
- Gateway rate limiting and abuse controls supplied by the eventual ingress/host.

## Consequences

The production PWA can be built without public development tokens or a public API origin, and its
client modules no longer need direct bearer access. An encrypted cookie alone cannot be obtained
through normal application behavior until a reviewed OIDC login adapter is added, so the hosted UI
will truthfully receive `401` rather than impersonating a development user.

This milestone materially narrows the remaining phone-login work but does not complete login. It
also does not change scientific governance, create training authorities, or make the application
ready for production athlete data.
