# 0108 — Allowlisted owner-alpha operator access

Date: 2026-09-12

Status: accepted

Decision version: `owner-alpha-operator-access@1.0.0`

## Decision

Add a narrow hosted-alpha activation boundary for the one authenticated owner who must review
AGAS-prepared assessment and planning artifacts. The deployment stores exactly one external
identity-provider subject in `AGAS_OWNER_ALPHA_OPERATOR_SUBJECT`; wildcard configuration is
invalid. The API additionally requires the configured authentication issuer, an existing account,
at least one athlete owned by that account, and a literal browser acknowledgement.

Successful activation appends only initial active `assessment_reviewer` and `planning_reviewer`
assignments. It records the issuer, subject, rule version, rationale, and assignment identities in
the existing append-only authorization history. Repeated activation is idempotent. If either role
has been revoked, browser activation fails and an administrator must decide whether a new grant is
appropriate.

Expose a read-only authenticated projection before activation so the owner can copy the exact
verified subject into the deployment configuration. Put one responsive control above all reviewer
routes. State plainly that these are workflow permissions, not scientific or professional
credentials.

## Reason

The hosted app already separates athlete ownership from review authority, but the owner-only alpha
had no usable, safe route to establish those permissions. The local CLI cannot operate the hosted
database, and automatically promoting every signup or every athlete owner would erase an important
authorization boundary. Exact-subject allowlisting preserves the separation while letting the one
intended operator complete the prepared path from onboarding to a first session.

## Alternatives considered

- **Automatically grant reviewer roles during signup or onboarding.** Rejected because any new
  account would gain operator authority and athlete ownership would silently become review
  authority.
- **Trust an email address or Auth0 metadata claim.** Rejected because display identifiers can
  change and introduce a second identity-mapping policy. The already verified opaque `sub` is the
  resource-server identity.
- **Expose general role administration in the PWA.** Rejected because the alpha needs one bounded
  bootstrap, not a browser-accessible privilege-management system.
- **Run a one-off database mutation.** Rejected because it is difficult to reproduce, easy to
  misattribute, and bypasses the append-only domain authorization model.
- **Treat the owner as a scientific reviewer by definition.** Rejected. This grant authorizes use
  of guarded application controls only; it does not establish competence or improve evidence.

## Assumptions and provisional choices

- The first hosted deployment has one owner/operator identity. Multi-user invitations, delegated
  coaching, role-request review, and organization administration remain out of scope.
- The owner first signs in and completes athlete onboarding so the account and ownership records
  exist before role activation.
- The deployer can set one server-only Render environment variable and redeploy after copying the
  exact authenticated subject shown by the API.

## Consequences

- The hosted owner can reach the existing governed review workflow without receiving database or
  bearer-token access.
- A compromised or different authenticated account cannot activate roles unless the deployment
  allowlist is also changed.
- Authorization history remains inspectable and revocation remains meaningful.
- This removes an operational blocker; it does not itself ratify evidence, create an assessment,
  generate a plan, or qualify the owner as an independent reviewer.
