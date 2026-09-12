# 0107 — Empty-store athlete recovery

Date: 2026-09-12

Status: accepted

Decision version: `athlete-data-clean-restore@1.0.0`

## Decision

Add an operator-only recovery service and command that preflights a versioned athlete archive and
can restore it only when the target database contains no athletes. Preflight verifies the canonical
digest, manifest counts, current table and column shape, primary keys, value decoding, ownership
lineage, row reachability from the declared athlete, exact missing-parent references, target record
collisions, and the presence of every shared dependency. External references to athlete-owned
tables are always blockers.

The command is read-only unless `--apply` is supplied together with the archive's exact digest.
Application creates or reuses only the explicitly supplied owner identity with the archived account
ID, inserts records in foreign-key order, orders self-referencing history by its predecessors, and
re-exports the restored athlete inside the transaction. Any digest difference rolls back the whole
operation. Export versions 1.0 and 1.1 remain accepted; version 1.1 advertises the validated
clean-store procedure in its manifest.

Do not expose restoration as an HTTP or PWA upload endpoint. The supplied identity must be checked
against the identity provider by the recovery operator before application.

## Reason

A downloadable archive is useful only if corruption and missing dependencies are discovered before
recovery writes. Generic row insertion without an ownership-graph check could import unrelated
athlete data, while best-effort substitution of a missing policy, evidence record, exercise, or
equipment item would destroy the provenance chain. Empty-store-only recovery provides a narrow,
testable disaster path without becoming a general merge/import feature.

## Alternatives considered

- **Restore into an active athlete store.** Rejected because reconciling immutable histories,
  identities, and uniqueness conflicts needs a separate merge design.
- **Ignore missing shared references.** Rejected because plans and observations would point to
  absent or silently substituted authorities.
- **Trust the file extension or manifest digest without recomputation.** Rejected because neither
  proves that the supplied content is unchanged.
- **Provide a self-service upload screen.** Rejected because database recovery is a privileged,
  exceptional operation and malformed archives must not reach ordinary application writes.

## Assumptions and limitations

- The recovery operator obtains and verifies the exact identity-provider issuer and subject for the
  owner; the archive intentionally does not disclose identity-provider subject data.
- Repository seed imports or a separate operational backup must recreate all external shared
  authorities with their original identities before an athlete archive can pass preflight.
- The automated round trip currently runs on SQLite in CI. PostgreSQL disaster rehearsal remains a
  deployment operation before the archive is treated as the sole recovery mechanism.

## Consequences

- Tampered, cross-athlete, incomplete, colliding, or dependency-incomplete archives fail closed.
- A valid recovery is atomic and proves byte-independent semantic equality through a re-exported
  content digest.
- The feature protects one-athlete portability; it does not replace provider backups, shared
  authority backups, retention policy, or a PostgreSQL restore rehearsal.
