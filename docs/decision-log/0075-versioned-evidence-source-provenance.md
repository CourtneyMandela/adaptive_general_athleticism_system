# 0075: Versioned evidence-source provenance

- Status: accepted provisionally
- Date: 2026-08-31
- Extends: Decisions 0001, 0011, and 0074
- Decision version: `evidence-source-provenance@1.0.0`

## Decision

Add an immutable `EvidenceSource` domain record for one exact retrieval snapshot of scientific
publication metadata. Store title, authors, journal and publication dates, optional abstract,
publication types, stable identifiers, one primary identifier, provider, retrieval URI and query,
retrieval time, metadata version, provenance notes, and explicit linear supersession. Persist claim
to source-snapshot links relationally while retaining portable PMID/DOI-style identifiers on the
claim.

Add a development-only `evidence-governance-bundle@1.0.0` command that atomically and idempotently
imports one or more exact source snapshots and their externally reviewed claims. Every imported
claim must reference bundled source snapshots, and claim identifiers must agree with the linked
metadata. Existing IDs must match immutable content exactly. Source updates must preserve primary
identity, advance the sequence by one, and cannot fork a predecessor.

Do not backfill the existing secondary-AI seed with invented snapshots. Do not add network
retrieval, automatic claim extraction, evidence scoring, or production approval in this increment.

## Reason

An identifier string says which publication was intended, but not which metadata was actually
inspected, when it was retrieved, or whether later metadata changes rewrote history. Exact source
snapshots close that provenance gap and create the storage contract needed for PubMed/Crossref
retrieval without letting a provider response or LLM output become an approved training rule.

A local typed import boundary enables deliberate curation now while keeping scientific authoring
out of the athlete PWA and public API. Atomicity prevents a claim from surviving without its source;
idempotence makes reviewed bundles safely repeatable.

## Alternatives considered

- Keep only PMID/DOI strings on claims. Rejected because retrieval metadata and historical review
  basis remain unverifiable.
- Store mutable metadata keyed directly by PMID. Rejected because corrections would silently alter
  the basis of historical claims.
- Store raw provider JSON only. Rejected because core publication fields would remain opaque and
  provider-specific; a later retrieval adapter may retain a hashed raw artifact separately.
- Automatically approve claims that pass schema validation. Rejected because structure and source
  identity do not establish scientific validity or athlete applicability.
- Backfill snapshots from model memory. Rejected as a direct evidence-policy violation.
- Expose browser claim-approval forms now. Deferred until verified reviewer identity,
  qualifications, conflict controls, and separation of duties are specified.

## Assumptions and unresolved questions

- The primary identifier is stable within one source lineage. A change in preferred identity is a
  new lineage until an explicit identity-merge policy exists.
- Abstract storage is supported by the model, but provider terms, copyright, retention, and raw
  response handling must be resolved in the retrieval adapter.
- The current `EvidenceClaim` reviewer field records supplied provenance, not a verified credential
  or an independent append-only approval chain.
- A future production boundary must distinguish retrieval, extraction, scientific review,
  applicability review, and authorization to use a claim in operational policies.
- Existing seed claims remain readable and provisional with empty source-record links.

## Consequences

- New claims can answer exactly which retrieved metadata snapshot was interpreted.
- Source metadata corrections preserve earlier claims and reject branching history.
- Import failures roll back all newly staged sources and claims.
- Milestone 7 now has its authoritative storage and local ingestion contract, but not yet provider
  search/retrieval or qualified scientific review.

## Evidence boundary

This is provenance infrastructure. It creates no scientific claim, validates no study result,
authorizes no assessment or training rule, and does not make the existing app safe for production
training use.
