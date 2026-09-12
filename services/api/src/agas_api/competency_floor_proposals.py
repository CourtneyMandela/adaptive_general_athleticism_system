from __future__ import annotations

import hashlib
import json
import sysconfig
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID, uuid5

from agas_domain import CapabilityDomain, ComparisonDirection
from pydantic import BaseModel, ConfigDict, Field, model_validator

PROPOSAL_VERSION = "competency-floor-proposal@1.0.0"
PROPOSAL_BATCH_VERSION = "competency-floor-proposal-batch@1.0.0"
PROPOSAL_BATCH_NAMESPACE = UUID("98800000-0000-4000-8000-000000000100")
NonEmptyText = Annotated[str, Field(min_length=1)]
Sha256Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class CompetencyFloorProposalSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: NonEmptyText
    title: NonEmptyText
    authors: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    edition: NonEmptyText
    publisher: NonEmptyText
    publication_year: int = Field(ge=1600, le=3000)
    isbn13: Annotated[str, Field(pattern=r"^\d{13}$")]
    table_locator: NonEmptyText
    page_locator: NonEmptyText
    source_population: NonEmptyText
    reported_value: NonEmptyText
    source_role: Literal["direct_reference", "derived_reference", "context_only"]
    limitations: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]


class CompetencyFloorProposal(BaseModel):
    """A review draft that cannot become planning authority by itself."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_version: Literal["competency-floor-proposal@1.0.0"]
    proposal_id: UUID
    slug: NonEmptyText
    label: NonEmptyText
    prepared_at: str
    content_digest: Sha256Digest
    stage: Literal["proposal_only"] = "proposal_only"
    domain: CapabilityDomain
    estimate_scope: NonEmptyText
    measurement: NonEmptyText
    unit_or_scale: NonEmptyText
    threshold: float = Field(gt=0)
    comparison_direction: ComparisonDirection
    minimum_age_years: int = Field(ge=0, le=130)
    maximum_age_years: int = Field(ge=0, le=130)
    sex_scope: Literal["male_reference", "female_reference", "sex_neutral"]
    numeric_value_origin: Literal[
        "direct_textbook_reference",
        "derived_from_textbook_reference",
        "engineering_proposal_without_numeric_evidence",
    ]
    operational_use_origin: Literal[
        "evidence_informed_engineering_proposal",
        "professional_judgment_required",
    ]
    threshold_rationale: NonEmptyText
    population_match: Literal["high", "moderate", "low"]
    population_match_notes: NonEmptyText
    source_ids: tuple[NonEmptyText, ...] = ()
    evidence_gap: NonEmptyText
    prerequisites_before_release: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    does_not_establish: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    review_questions: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_proposal(self) -> CompetencyFloorProposal:
        if self.minimum_age_years > self.maximum_age_years:
            raise ValueError("minimum_age_years cannot exceed maximum_age_years")
        if (
            self.numeric_value_origin == "engineering_proposal_without_numeric_evidence"
            and self.operational_use_origin != "professional_judgment_required"
        ):
            raise ValueError("unsupported numeric proposals require professional judgment")
        if (
            self.numeric_value_origin != "engineering_proposal_without_numeric_evidence"
            and not self.source_ids
        ):
            raise ValueError("textbook-derived proposals require a source")
        return self


class CompetencyFloorProposalBatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    batch_version: Literal["competency-floor-proposal-batch@1.0.0"]
    batch_id: UUID
    label: NonEmptyText
    prepared_at: str
    content_digest: Sha256Digest
    source_catalog: tuple[CompetencyFloorProposalSource, ...]
    proposals: Annotated[tuple[CompetencyFloorProposal, ...], Field(min_length=1)]
    release_boundary: NonEmptyText


class CompetencyFloorProposalValidationError(RuntimeError):
    pass


@lru_cache
def competency_floor_proposal_batch(
    data_path: Path | None = None,
) -> CompetencyFloorProposalBatch:
    path = data_path or _default_proposal_data_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CompetencyFloorProposalValidationError(
            f"unable to read competency-floor proposal batch {path.name}: {error}"
        ) from error
    if not isinstance(raw, dict):
        raise CompetencyFloorProposalValidationError("proposal batch document must be an object")
    raw_proposals = raw.get("proposals")
    if not isinstance(raw_proposals, list):
        raise CompetencyFloorProposalValidationError("proposal batch requires a proposals array")

    proposals: list[CompetencyFloorProposal] = []
    for raw_proposal in raw_proposals:
        if not isinstance(raw_proposal, dict):
            raise CompetencyFloorProposalValidationError("each proposal must be an object")
        supplied_digest = raw_proposal.get("content_digest")
        canonical = json.dumps(
            {key: value for key, value in raw_proposal.items() if key != "content_digest"},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        actual_digest = f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
        if supplied_digest != actual_digest:
            raise CompetencyFloorProposalValidationError(
                f"proposal {raw_proposal.get('slug', '<unknown>')} has a stale content digest"
            )
        proposals.append(CompetencyFloorProposal.model_validate(raw_proposal))

    raw_sources = raw.get("source_catalog")
    if not isinstance(raw_sources, list):
        raise CompetencyFloorProposalValidationError("proposal batch requires a source catalog")
    sources = tuple(CompetencyFloorProposalSource.model_validate(item) for item in raw_sources)
    source_ids = [item.source_id for item in sources]
    if len(source_ids) != len(set(source_ids)):
        raise CompetencyFloorProposalValidationError("proposal source ids must be unique")
    available_sources = set(source_ids)
    for proposal in proposals:
        if not set(proposal.source_ids).issubset(available_sources):
            raise CompetencyFloorProposalValidationError(
                f"proposal {proposal.slug} cites an unknown source"
            )

    ids = [item.proposal_id for item in proposals]
    if len(ids) != len(set(ids)):
        raise CompetencyFloorProposalValidationError("proposal ids must be unique")
    slugs = [item.slug for item in proposals]
    if len(slugs) != len(set(slugs)):
        raise CompetencyFloorProposalValidationError("proposal slugs must be unique")

    canonical_batch = json.dumps(
        {
            "batch_version": raw.get("batch_version"),
            "label": raw.get("label"),
            "prepared_at": raw.get("prepared_at"),
            "source_catalog": raw_sources,
            "proposal_digests": [
                {"proposal_id": str(item.proposal_id), "content_digest": item.content_digest}
                for item in proposals
            ],
            "release_boundary": raw.get("release_boundary"),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    actual_batch_digest = f"sha256:{hashlib.sha256(canonical_batch.encode()).hexdigest()}"
    if raw.get("content_digest") != actual_batch_digest:
        raise CompetencyFloorProposalValidationError("proposal batch has a stale content digest")
    expected_batch_id = uuid5(PROPOSAL_BATCH_NAMESPACE, actual_batch_digest)
    if raw.get("batch_id") != str(expected_batch_id):
        raise CompetencyFloorProposalValidationError("proposal batch id does not match its digest")
    try:
        return CompetencyFloorProposalBatch.model_validate(raw)
    except ValueError as error:
        raise CompetencyFloorProposalValidationError(
            f"invalid competency-floor proposal batch: {error}"
        ) from error


def _default_proposal_data_path() -> Path:
    repository_data = (
        Path(__file__).resolve().parents[4]
        / "data"
        / "governance_proposals"
        / "competency_floors"
        / "owner_alpha_reference_batch.json"
    )
    if repository_data.is_file():
        return repository_data
    return (
        Path(sysconfig.get_path("data"))
        / "share"
        / "agas"
        / "data"
        / "governance_proposals"
        / "competency_floors"
        / "owner_alpha_reference_batch.json"
    )
