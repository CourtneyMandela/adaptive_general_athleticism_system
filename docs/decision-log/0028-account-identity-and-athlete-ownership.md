# Decision 0028: Account identity and athlete ownership boundary

- Status: accepted provisionally
- Date: 2026-08-22
- Decision version: `account-athlete-ownership@1.0.0`

## Decision

Represent an authenticated account as an immutable `(issuer, subject)` identity and connect it to
an athlete through a separate immutable ownership record. Athlete identity remains a training-domain
concept; authentication-provider identity is not added to `Athlete`. V1 permits exactly one owner
record per athlete. Transfer, delegation, coaching access, household access, and revocation require
later explicit models rather than overloading ownership.

Every athlete-scoped API use case must authenticate a principal and resolve the target aggregate to
its athlete before reading or writing it. Cross-account access returns the same not-found response
as an absent aggregate so the boundary does not reveal another account's athlete identifiers. The
global equipment catalog and health/readiness endpoints remain public because they contain no
athlete data.

Provide a replaceable token-verifier interface. The current implementation supports only a
development bearer token shaped as `dev.<subject>`, with a fixed development issuer. This token is
an explicit local-development identity selector, not a password, production credential, or proof
of real-world identity. Configuration rejects development authentication in a production
environment. An external mode fails closed until a cryptographically verifying OIDC/OAuth adapter
is implemented.

Transactional onboarding creates or reuses the authenticated account and appends the athlete owner
record in the same transaction as the athlete, direct observation, environments, and equipment
availability. No athlete may be left ownerless by a successful onboarding request. A local operator
CLI may grant ownership of pre-existing fixture athletes; no public claim-arbitrary-athlete endpoint
is exposed.

## Reason

The PWA now creates durable athlete records, but an opaque athlete UUID is neither authentication
nor authorization. Sensitive assessment work cannot begin honestly until reads and writes have an
account ownership boundary. Separating provider identity, athlete identity, and ownership keeps the
training model provider-neutral and permits a later authentication service without rewriting
athlete history.

## Alternatives considered

- Store provider subject directly on `Athlete`. Rejected because account identity and athlete state
  have different lifecycles and one account may eventually manage more than one athlete.
- Trust an `X-User-ID` request header. Rejected because an arbitrary header has no verifier boundary
  and could be mistaken for production authentication.
- Choose and integrate a production identity vendor now. Deferred because provider, deployment,
  recovery, consent, and data-residency requirements are not yet selected.
- Leave existing endpoints unauthenticated until sensitive intake. Rejected because current-week,
  safety, execution, and progression data are already athlete-specific.
- Add a public endpoint that claims an existing athlete UUID. Rejected because possession of an
  identifier is not authorization.
- Add speculative roles and sharing permissions. Deferred until an actual ownership/delegation use
  case is defined.

## Assumptions and provisional choices

- An issuer and subject are case-sensitive opaque identifiers and are never treated as an email or
  display name.
- One account may own multiple athletes; one athlete has exactly one immutable V1 owner.
- Development subject `local-browser` is the PWA default so the local application works without an
  external provider. It provides no isolation between people sharing the same development server.
- Existing test suites use an explicit internal bypass principal; dedicated authorization tests run
  through the real verifier and ownership checks.
- Authentication establishes request identity only. Consent, export, deletion, retention,
  recovery, and provider account lifecycle remain separate obligations.

## Evidence and uncertainty

This is a security and data-ownership architecture decision implementing the blueprint's persistent
athlete identity boundary and the unresolved identity questions in decisions 0001, 0021, 0022, and
0027. It makes no scientific, medical, or training claim.

The production authentication provider, token claims and scopes, account recovery, ownership
transfer, delegated access, administrative access, row-level security, audit-event retention,
privacy jurisdiction, and deletion/export policy remain unresolved.

## Consequences

- Athlete-scoped API access is no longer authorized by knowledge of a UUID alone.
- Onboarding cannot commit an ownerless athlete.
- Local development remains runnable, while production configuration cannot silently use the
  development token verifier.
- A production-ready PWA still requires a verified external identity adapter and account lifecycle
  UX before sensitive athlete intake is appropriate.
