# 0106 — Verifiable owner data export

Date: 2026-09-12

Status: accepted

Decision version: `athlete-data-export@1.0.0`

## Decision

Provide an authenticated, athlete-owner-scoped JSON export before real training history
accumulates on the free hosted database. The archive contains the selected athlete row, every row
with that athlete's ID, and the transitive child records that depend on those rows. It never walks
from an athlete record into a referenced shared parent, so global equipment, exercise, adaptation,
policy, and evidence catalogs are not copied as though the owner authored them.

List excluded parent identities as external references. Sort tables and rows deterministically and
calculate a canonical SHA-256 digest over the export version, athlete ID, records, and external
references. Exclude generation time from the digest so two exports of unchanged state can be
compared. Expose the archive through the normal ownership boundary and a PWA download action.

Mark the archive explicitly as not yet restorable. Do not add an upload endpoint until a separate
validator can preflight schema version, digest, shared references, identity ownership, uniqueness,
and append-only conflicts in a disposable database.

## Reason

The owner-only alpha uses a no-card PostgreSQL tier with limited provider recovery. A portable,
scoped record makes current state inspectable and allows changes to be detected without dumping
unrelated accounts or confusing global governed authorities with athlete-owned history. Honest
restore status prevents a downloadable file from creating false confidence that recovery has been
proved.

## Alternatives considered

- **Rely only on provider backups.** Rejected as the sole path because free-tier recovery windows
  and service availability can change, and the owner needs a portable copy outside the provider.
- **Expose a whole-database dump.** Rejected because it crosses ownership boundaries and couples a
  personal export to operational accounts, migrations, and global catalogs.
- **Duplicate all referenced catalog and authority rows.** Rejected because those are governed
  system inputs, not athlete-owned observations, and recursively copying them would blur
  provenance and substantially widen the archive.
- **Add import alongside export.** Deferred because restoring append-only, identity-bound records
  without validation can corrupt lineage or attach data to the wrong account.

## Consequences

- The owner can download one deterministic JSON archive from the phone PWA.
- An unchanged archive retains the same digest even when downloaded at a later time.
- Shared dependencies remain explicit and must exist or be reconciled during a future restore.
- This reduces data-portability risk but is not a database backup or proven disaster-recovery
  procedure. A round-trip restore drill remains required before irreplaceable history accumulates.
