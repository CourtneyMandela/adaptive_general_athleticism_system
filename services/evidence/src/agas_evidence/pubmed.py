from __future__ import annotations

import argparse
import json
import os
import re
from calendar import month_abbr
from datetime import UTC, date, datetime
from typing import Annotated
from xml.etree import ElementTree

import httpx
from agas_domain import EvidenceSource, EvidenceSourceIdentifier
from pydantic import BaseModel, ConfigDict, Field, field_validator

EUTILITIES_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PUBMED_METADATA_VERSION = "pubmed-efetch-xml@1.0.0"
DEFAULT_TOOL_NAME = "adaptive_general_athleticism_system"


class PubMedRetrievalError(RuntimeError):
    pass


class PubMedClientConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contact_email: Annotated[
        str,
        Field(min_length=3, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
    ]
    api_key: Annotated[str, Field(min_length=1)] | None = None
    tool_name: Annotated[str, Field(min_length=1, pattern=r"^[^\s]+$")] = DEFAULT_TOOL_NAME
    base_url: Annotated[str, Field(min_length=1)] = EUTILITIES_BASE_URL
    timeout_seconds: float = Field(default=15.0, gt=0, le=120)


class PubMedSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    query: Annotated[str, Field(min_length=1)]
    total_count: int = Field(ge=0)
    pmids: tuple[Annotated[str, Field(pattern=r"^\d+$")], ...]
    retrieved_at: datetime

    @field_validator("retrieved_at")
    @classmethod
    def require_aware_retrieved_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("retrieved_at must include a timezone")
        return value


class PubMedClient:
    """Small synchronous NCBI E-utilities adapter for operator-driven curation."""

    def __init__(
        self,
        configuration: PubMedClientConfiguration,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.configuration = configuration
        self._owns_client = client is None
        self.client = client or httpx.Client(
            base_url=f"{configuration.base_url.rstrip('/')}/",
            timeout=configuration.timeout_seconds,
            follow_redirects=True,
        )

    def __enter__(self) -> PubMedClient:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def search(
        self,
        query: str,
        *,
        max_results: int = 20,
        retrieved_at: datetime | None = None,
    ) -> PubMedSearchResult:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("PubMed query must not be empty")
        if max_results < 1 or max_results > 100:
            raise ValueError("PubMed max_results must be between 1 and 100")
        response = self._get(
            "esearch.fcgi",
            params={
                "db": "pubmed",
                "term": normalized_query,
                "retmode": "json",
                "retmax": str(max_results),
                "sort": "relevance",
            },
        )
        try:
            result = response.json()["esearchresult"]
            total_count = int(result["count"])
            pmids = tuple(str(value) for value in result["idlist"])
        except (KeyError, TypeError, ValueError) as error:
            raise PubMedRetrievalError("PubMed ESearch returned an invalid payload") from error
        if any(not pmid.isdigit() for pmid in pmids):
            raise PubMedRetrievalError("PubMed ESearch returned a non-numeric identifier")
        instant = retrieved_at or datetime.now(UTC)
        return PubMedSearchResult(
            query=normalized_query,
            total_count=total_count,
            pmids=pmids,
            retrieved_at=instant,
        )

    def fetch_source(
        self,
        pmid: str,
        *,
        retrieval_query: str | None = None,
        retrieved_at: datetime | None = None,
    ) -> EvidenceSource:
        normalized_pmid = pmid.strip()
        if not normalized_pmid.isdigit():
            raise ValueError("PMID must contain digits only")
        response = self._get(
            "efetch.fcgi",
            params={
                "db": "pubmed",
                "id": normalized_pmid,
                "retmode": "xml",
            },
        )
        instant = retrieved_at or datetime.now(UTC)
        return parse_pubmed_source(
            response.text,
            expected_pmid=normalized_pmid,
            retrieval_query=retrieval_query,
            retrieved_at=instant,
        )

    def _get(self, path: str, *, params: dict[str, str]) -> httpx.Response:
        request_params = {
            **params,
            "tool": self.configuration.tool_name,
            "email": self.configuration.contact_email,
        }
        if self.configuration.api_key:
            request_params["api_key"] = self.configuration.api_key
        try:
            response = self.client.get(path, params=request_params)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as error:
            raise PubMedRetrievalError(
                f"PubMed request returned HTTP {error.response.status_code}"
            ) from error
        except httpx.RequestError as error:
            raise PubMedRetrievalError(
                f"PubMed request could not be completed ({type(error).__name__})"
            ) from error


def parse_pubmed_source(
    xml_text: str,
    *,
    expected_pmid: str,
    retrieval_query: str | None,
    retrieved_at: datetime,
) -> EvidenceSource:
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
        raise ValueError("PubMed retrieval time must include a timezone")
    if "<!ENTITY" in xml_text.upper():
        raise PubMedRetrievalError("PubMed XML entity declarations are not accepted")
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as error:
        raise PubMedRetrievalError("PubMed EFetch returned invalid XML") from error
    articles = root.findall(".//PubmedArticle")
    if len(articles) != 1:
        raise PubMedRetrievalError(
            f"PubMed EFetch must return exactly one article; received {len(articles)}"
        )
    article = articles[0]
    actual_pmid = _required_text(article.find("./MedlineCitation/PMID"), "PMID")
    if actual_pmid != expected_pmid:
        raise PubMedRetrievalError(
            f"PubMed EFetch returned PMID {actual_pmid}, expected {expected_pmid}"
        )
    article_node = article.find("./MedlineCitation/Article")
    if article_node is None:
        raise PubMedRetrievalError("PubMed article metadata is missing")

    title = _required_text(article_node.find("./ArticleTitle"), "article title")
    authors = _authors(article_node)
    journal = _optional_text(article_node.find("./Journal/Title"))
    publication_year, publication_date = _publication_dates(article_node)
    abstract = _abstract(article_node)
    publication_types = tuple(
        text
        for node in article_node.findall("./PublicationTypeList/PublicationType")
        if (text := _optional_text(node)) is not None
    )
    identifiers = [EvidenceSourceIdentifier(scheme="pmid", value=actual_pmid)]
    doi = _doi(article)
    if doi is not None:
        identifiers.append(EvidenceSourceIdentifier(scheme="doi", value=doi))
    primary = identifiers[0]
    return EvidenceSource(
        title=title,
        authors=authors,
        journal=journal,
        publication_year=publication_year,
        publication_date=publication_date,
        abstract=abstract,
        publication_types=publication_types,
        primary_identifier=primary,
        source_identifiers=tuple(identifiers),
        metadata_provider="pubmed",
        retrieval_uri=f"https://pubmed.ncbi.nlm.nih.gov/{actual_pmid}/",
        retrieval_query=retrieval_query,
        retrieved_at=retrieved_at,
        metadata_version=PUBMED_METADATA_VERSION,
        provenance_notes=(
            "Metadata retrieved through NCBI E-utilities; no scientific interpretation or "
            "approval was performed.",
        ),
    )


def _required_text(node: ElementTree.Element | None, label: str) -> str:
    value = _optional_text(node)
    if value is None:
        raise PubMedRetrievalError(f"PubMed {label} is missing")
    return value


def _optional_text(node: ElementTree.Element | None) -> str | None:
    if node is None:
        return None
    value = "".join(node.itertext())
    normalized = " ".join(value.split())
    return normalized or None


def _authors(article_node: ElementTree.Element) -> tuple[str, ...]:
    values: list[str] = []
    for author in article_node.findall("./AuthorList/Author"):
        collective = _optional_text(author.find("./CollectiveName"))
        if collective:
            values.append(collective)
            continue
        last_name = _optional_text(author.find("./LastName"))
        fore_name = _optional_text(author.find("./ForeName"))
        initials = _optional_text(author.find("./Initials"))
        given = fore_name or initials
        name = ", ".join(part for part in (last_name, given) if part)
        if name:
            values.append(name)
    return tuple(values)


def _publication_dates(article_node: ElementTree.Element) -> tuple[int | None, date | None]:
    pub_date = article_node.find("./Journal/JournalIssue/PubDate")
    if pub_date is None:
        return None, None
    year_text = _optional_text(pub_date.find("./Year"))
    medline_date = _optional_text(pub_date.find("./MedlineDate"))
    if year_text is None and medline_date:
        match = re.search(r"\b(1[6-9]\d{2}|20\d{2}|21\d{2})\b", medline_date)
        year_text = match.group(1) if match else None
    if year_text is None or not year_text.isdigit():
        return None, None
    year = int(year_text)
    month = _month_number(_optional_text(pub_date.find("./Month")))
    day_text = _optional_text(pub_date.find("./Day"))
    if month is None or day_text is None or not day_text.isdigit():
        return year, None
    try:
        return year, date(year, month, int(day_text))
    except ValueError:
        return year, None


def _month_number(value: str | None) -> int | None:
    if value is None:
        return None
    if value.isdigit() and 1 <= int(value) <= 12:
        return int(value)
    normalized = value[:3].title()
    return next((index for index, name in enumerate(month_abbr) if name == normalized), None)


def _abstract(article_node: ElementTree.Element) -> str | None:
    sections: list[str] = []
    for node in article_node.findall("./Abstract/AbstractText"):
        text = _optional_text(node)
        if text is None:
            continue
        label = (node.attrib.get("Label") or "").strip()
        sections.append(f"{label}: {text}" if label else text)
    return "\n\n".join(sections) or None


def _doi(article: ElementTree.Element) -> str | None:
    for node in article.findall("./PubmedData/ArticleIdList/ArticleId"):
        if node.attrib.get("IdType", "").casefold() == "doi":
            return _optional_text(node)
    for node in article.findall("./MedlineCitation/Article/ELocationID"):
        if node.attrib.get("EIdType", "").casefold() == "doi":
            return _optional_text(node)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search PubMed or retrieve one metadata snapshot for external review."
    )
    parser.add_argument("--email", default=os.getenv("AGAS_NCBI_EMAIL"))
    parser.add_argument("--api-key", default=os.getenv("AGAS_NCBI_API_KEY"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--max-results", type=int, default=20)
    fetch_parser = subparsers.add_parser("fetch")
    fetch_parser.add_argument("--pmid", required=True)
    fetch_parser.add_argument("--query")
    arguments = parser.parse_args()
    if not arguments.email:
        parser.error("--email or AGAS_NCBI_EMAIL is required by the PubMed retrieval adapter")

    configuration = PubMedClientConfiguration(
        contact_email=arguments.email,
        api_key=arguments.api_key,
    )
    try:
        with PubMedClient(configuration) as client:
            if arguments.command == "search":
                result: BaseModel = client.search(
                    arguments.query,
                    max_results=arguments.max_results,
                )
            elif arguments.command == "fetch":
                result = client.fetch_source(
                    arguments.pmid,
                    retrieval_query=arguments.query,
                )
            else:
                parser.error("unsupported PubMed command")
    except (PubMedRetrievalError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result.model_dump(mode="json"), sort_keys=True))


if __name__ == "__main__":
    main()
