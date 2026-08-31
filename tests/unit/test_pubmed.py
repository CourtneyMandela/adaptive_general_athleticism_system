from datetime import UTC, datetime

import httpx
import pytest
from agas_evidence import PubMedClient, PubMedClientConfiguration, PubMedRetrievalError

NOW = datetime(2026, 8, 31, 15, 0, tzinfo=UTC)
PUBMED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID Version="1">12345678</PMID>
      <Article>
        <Journal>
          <JournalIssue>
            <PubDate><Year>2026</Year><Month>Aug</Month><Day>31</Day></PubDate>
          </JournalIssue>
          <Title>Software Test Journal</Title>
        </Journal>
        <ArticleTitle>Resistance <i>training</i> software fixture</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">Synthetic background.</AbstractText>
          <AbstractText Label="RESULTS">Synthetic results.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author><LastName>Doe</LastName><ForeName>Jane Q</ForeName></Author>
          <Author><CollectiveName>AGAS Test Group</CollectiveName></Author>
        </AuthorList>
        <PublicationTypeList>
          <PublicationType UI="D016428">Journal Article</PublicationType>
          <PublicationType UI="D000078182">Systematic Review</PublicationType>
        </PublicationTypeList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">12345678</ArticleId>
        <ArticleId IdType="doi">10.0000/software-fixture</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""


def _configuration() -> PubMedClientConfiguration:
    return PubMedClientConfiguration(
        contact_email="agas-test@example.invalid",
        api_key="test-api-key",
        base_url="https://eutils.test/entrez/eutils",
    )


def test_pubmed_search_preserves_query_result_ids_and_contact_parameters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/esearch.fcgi")
        assert request.url.params["db"] == "pubmed"
        assert request.url.params["term"] == "resistance training[Title]"
        assert request.url.params["retmax"] == "2"
        assert request.url.params["tool"] == "adaptive_general_athleticism_system"
        assert request.url.params["email"] == "agas-test@example.invalid"
        assert request.url.params["api_key"] == "test-api-key"
        return httpx.Response(
            200,
            json={
                "esearchresult": {
                    "count": "42",
                    "idlist": ["12345678", "87654321"],
                }
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://eutils.test/entrez/eutils/",
    )

    result = PubMedClient(_configuration(), client=client).search(
        "  resistance training[Title]  ",
        max_results=2,
        retrieved_at=NOW,
    )

    assert result.query == "resistance training[Title]"
    assert result.total_count == 42
    assert result.pmids == ("12345678", "87654321")
    assert result.retrieved_at == NOW


def test_pubmed_fetch_maps_xml_to_an_uninterpreted_source_snapshot() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/efetch.fcgi")
        assert request.url.params["id"] == "12345678"
        assert request.url.params["retmode"] == "xml"
        return httpx.Response(200, text=PUBMED_XML)

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://eutils.test/entrez/eutils/",
    )

    source = PubMedClient(_configuration(), client=client).fetch_source(
        "12345678",
        retrieval_query="resistance training[Title]",
        retrieved_at=NOW,
    )

    assert source.title == "Resistance training software fixture"
    assert source.authors == ("Doe, Jane Q", "AGAS Test Group")
    assert source.journal == "Software Test Journal"
    assert source.publication_year == 2026
    assert source.publication_date is not None
    assert source.publication_date.isoformat() == "2026-08-31"
    assert source.publication_types == ("Journal Article", "Systematic Review")
    assert source.abstract == "BACKGROUND: Synthetic background.\n\nRESULTS: Synthetic results."
    assert [(item.scheme, item.value) for item in source.source_identifiers] == [
        ("pmid", "12345678"),
        ("doi", "10.0000/software-fixture"),
    ]
    assert source.retrieval_query == "resistance training[Title]"
    assert source.retrieved_at == NOW
    assert "no scientific interpretation" in source.provenance_notes[0]


def test_pubmed_fetch_rejects_wrong_or_ambiguous_records() -> None:
    wrong_pmid_xml = PUBMED_XML.replace(">12345678</PMID>", ">99999999</PMID>")
    responses = iter(
        (
            httpx.Response(200, text=wrong_pmid_xml),
            httpx.Response(200, text="<PubmedArticleSet />"),
        )
    )
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _request: next(responses)),
        base_url="https://eutils.test/entrez/eutils/",
    )
    adapter = PubMedClient(_configuration(), client=client)

    with pytest.raises(PubMedRetrievalError, match="expected 12345678"):
        adapter.fetch_source("12345678", retrieved_at=NOW)
    with pytest.raises(PubMedRetrievalError, match="exactly one article"):
        adapter.fetch_source("12345678", retrieved_at=NOW)


def test_pubmed_search_rejects_invalid_provider_payload() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json={"error": "bad"})),
        base_url="https://eutils.test/entrez/eutils/",
    )

    with pytest.raises(PubMedRetrievalError, match="invalid payload"):
        PubMedClient(_configuration(), client=client).search("fixture", retrieved_at=NOW)


def test_pubmed_http_error_does_not_expose_api_key() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(503)),
        base_url="https://eutils.test/entrez/eutils/",
    )

    with pytest.raises(PubMedRetrievalError) as error:
        PubMedClient(_configuration(), client=client).search("fixture", retrieved_at=NOW)

    assert "503" in str(error.value)
    assert "test-api-key" not in str(error.value)
