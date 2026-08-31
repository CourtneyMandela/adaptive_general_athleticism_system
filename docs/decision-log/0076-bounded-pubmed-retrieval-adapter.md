# 0076: Bounded PubMed retrieval adapter

- Status: accepted provisionally
- Date: 2026-08-31
- Extends: Decision 0075
- Decision version: `pubmed-retrieval@1.0.0`

## Decision

Create `services/evidence` as an importable Python package and add a synchronous operator-facing
PubMed adapter using NCBI E-utilities. Support bounded ESearch queries and single-PMID EFetch XML.
Map EFetch metadata to an unpersisted `EvidenceSource` snapshot, preserving title markup as text,
ordered authors, journal and publication date, optional abstract sections, publication types,
PMID/DOI identifiers, exact retrieval query and time, and adapter version.

Require a developer contact email, send a stable tool name, accept an optional API key, cap one
search command at 100 results, and make only one provider request per command. Reject non-numeric
PMIDs, malformed provider responses, ambiguous fetches, and returned-PMID mismatches. Do not expose
the API key in errors. Keep retrieval separate from persistence and claim review.

## Reason

The blueprint calls for structured PubMed search and local publication metadata. The versioned
source storage from Decision 0075 needs a provider adapter that produces the exact record shape
without coupling network behavior to database transactions or scientific approval. A narrow CLI
is inspectable, scriptable, and appropriate before a production curation workbench exists.

NCBI documents ESearch as the text-query-to-UID boundary and EFetch as the record-retrieval
boundary. Its usage guidance requests tool/contact identification, limits request frequency, and
notes that abstracts may be copyrighted. The adapter therefore avoids bulk loops, requires contact
configuration, and records metadata without treating retrieval as permission or scientific review.

## Alternatives considered

- Scrape PubMed web pages. Rejected because NCBI provides a structured official API.
- Fetch and persist in one command. Rejected because an operator must inspect metadata and assemble
  a reviewed bundle before authoritative persistence.
- Extract claims automatically during retrieval. Rejected because source text, interpretation,
  evidence strength, and athlete applicability are different review responsibilities.
- Add PubMed, Crossref, and OpenAlex simultaneously. Deferred to prove one reliable provider path
  before adding reconciliation and conflict rules.
- Build an asynchronous batch worker. Deferred because current curation volume is small and the
  product has no background-job infrastructure.

## Assumptions and unresolved questions

- The initial operator flow performs isolated search or single-record retrieval; it does not need a
  rate-limited batch scheduler.
- `httpx` becomes a runtime dependency because provider retrieval is product behavior.
- Provider contact registration, production secrets, organization policy, and acceptable abstract
  retention still need deployment decisions.
- PubMed metadata may be incomplete; missing authors, dates, DOI, or abstract remain explicit rather
  than being inferred from another source.
- Crossref reconciliation and raw-response digest retention remain future work.

## Consequences

- An operator can obtain a structured source snapshot from a real PMID without copying metadata by
  hand.
- Provider errors cannot silently become empty scientific records.
- The resulting JSON still requires external claim extraction and review before bundle import.
- Milestone 7 now includes bounded PubMed search, metadata retrieval, storage, and governed local
  ingestion foundations; applicability review and plan-facing citation remain incomplete.

## Evidence boundary

Official interface behavior and usage constraints were checked against NCBI's E-utilities Help:
https://www.ncbi.nlm.nih.gov/books/NBK25501/ and
https://www.ncbi.nlm.nih.gov/books/NBK25497/. This adapter establishes provenance mechanics only;
it validates no scientific conclusion and authorizes no training behavior.
