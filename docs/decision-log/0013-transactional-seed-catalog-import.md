# 0013: Transactional seed-catalog import

- Status: accepted provisionally
- Date: 2026-08-21
- Decision version: `seed-catalog-importer@1.0.0`

## Decision

Add an explicit importer between the validated repository catalog and domain persistence. Import
the evidence claims, adaptations, equipment, and exercises as immutable global reference data in
one nested transaction, then append a `CatalogImport` receipt containing the manifest review
metadata, a canonical SHA-256 digest, importer version, timestamp, and ordered relational links to
every imported record.

The catalog version is unique. Reimporting the exact version and digest is idempotent and verifies
that every persisted record still equals the catalog. Reusing a version for different content or
colliding with a different immutable record fails and rolls back records staged by that attempt.
The API composition layer owns the outer commit through `python -m agas_api.seed`.

The synthetic travel athlete and its scenario environments are validation fixtures, not global
reference data, and are not imported into the authoritative athlete store.

## Reason

The ontology milestone proved file loading and counterfactual behavior but left no safe way to
populate a fresh database. Direct one-off inserts would lose release provenance, allow partial
catalog state, and make reruns ambiguous. A digest-backed append-only receipt makes database state
auditable without treating seed review status as scientific approval.

## Alternatives considered

- Load JSON dynamically on every request: rejected because planning records must reference stable
  persisted identities.
- Upsert by overwriting matching IDs: rejected because catalog records and their consumers are
  append-only history.
- Import the synthetic athlete: rejected because test personas are not real athlete state.
- Mark the current catalog production-approved during import: rejected because persistence does
  not elevate its `secondary_ai_verified` review status.
- Store only counts in the receipt: rejected because exact imported identities are material
  provenance and are represented with ordered foreign-key links.

## Assumptions and limitations

The current `0.1.0` catalog contains no adaptation or exercise progression relationship edges, so
the existing repository's single-record insertion APIs are sufficient. A future catalog release
that introduces mutually referencing graph edges requires a reviewed batch graph-persistence
method before import; the importer must not reorder or strip those edges to force success.

The nested transaction makes each importer call atomic inside a caller-owned database transaction.
Durability still requires the composition root to commit, which the provided command does.

## Consequences

- A fresh migrated database can be populated with one repeatable command.
- Partial failed imports do not leak catalog records.
- Catalog review status, exact content digest, and identities remain queryable and immutable.
- Seed release history remains distinct from athlete observations and estimates.
