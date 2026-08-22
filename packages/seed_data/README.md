# Seed data package

`agas_seed_data.load_seed_catalog()` reads the repository-owned JSON catalog and validates every
evidence, adaptation, equipment, exercise, relationship, and synthetic-scenario reference before
returning one immutable `SeedCatalog`.

Loading alone validates data but does not insert it into a database. `SeedCatalogImporter` stages
the global evidence, adaptation, equipment, and exercise records atomically and writes an
append-only, digest-backed import receipt; its caller owns the outer commit. The synthetic travel
athlete remains a test fixture and is never imported by this boundary. The manifest's
`secondary_ai_verified` state is intentionally below production approval. Exercise annotations
are ontology fixtures, not claims of dose equivalence or universally appropriate programming.
