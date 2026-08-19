# Seed data package

`agas_seed_data.load_seed_catalog()` reads the repository-owned JSON catalog and validates every
evidence, adaptation, equipment, exercise, relationship, and synthetic-scenario reference before
returning one immutable `SeedCatalog`.

Loading validates data but does not insert it into an athlete database. The manifest's
`secondary_ai_verified` state is intentionally below production approval. Exercise annotations
are ontology fixtures, not claims of dose equivalence or universally appropriate programming.
