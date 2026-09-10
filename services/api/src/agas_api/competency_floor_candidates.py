# ruff: noqa: E501 -- reviewed evidence and governance prose remains exact and readable.
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from typing import Annotated, Literal
from uuid import UUID

from agas_domain import (
    AccountRole,
    Applicability,
    AssessmentReviewDecision,
    CapabilityDomain,
    ComparisonDirection,
    CompetencyFloor,
    CompetencyFloorReview,
    DecisionRecord,
    EvidenceClaim,
    EvidenceClaimReview,
    EvidenceReviewDecision,
    EvidenceSource,
    EvidenceSourceIdentifier,
    EvidenceStrength,
)
from agas_domain.models import VersionedRecord
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agas_api.evidence_governance import (
    EvidenceAuthorityEvaluationError,
    EvidenceAuthorityEvaluator,
    EvidenceAuthorityNotReadyError,
)
from agas_api.identity import AuthorizedRole

CANDIDATE_VERSION = "competency-floor-candidate@1.0.0"
NonEmptyText = Annotated[str, Field(min_length=1)]


class CompetencyFloorEvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: NonEmptyText
    source_url: NonEmptyText
    population: NonEmptyText
    finding: NonEmptyText
    limitations: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    conflict_disclosure: NonEmptyText


class CompetencyFloorCandidate(BaseModel):
    """Immutable owner-readable presentation of a prepared competency floor."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["competency-floor-candidate@1.0.0"]
    candidate_id: UUID
    slug: NonEmptyText
    release_label: NonEmptyText
    prepared_at: datetime
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    summary: NonEmptyText
    domain: CapabilityDomain
    estimate_scope: NonEmptyText
    unit_or_scale: NonEmptyText
    threshold: float
    comparison_direction: ComparisonDirection
    minimum_age_years: int
    maximum_age_years: int
    governs: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    does_not_establish: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    unresolved_limitations: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    evidence: Annotated[tuple[CompetencyFloorEvidenceSummary, ...], Field(min_length=1)]


class CompetencyFloorCandidateItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate: CompetencyFloorCandidate
    status: Literal["available", "ratified", "conflict"]
    ratified_at: datetime | None = None
    issues: tuple[str, ...] = ()


class CompetencyFloorCandidateProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    projected_at: datetime
    items: tuple[CompetencyFloorCandidateItem, ...]
    projection_version: str = "competency-floor-candidates@1.0.0"


class RatifyCompetencyFloorCandidateCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["competency-floor-candidate@1.0.0"]
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    approval_attestation: Literal[True]


class PreparedCompetencyFloorRelease(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    release_id: UUID
    release_label: NonEmptyText
    prepared_at: datetime
    source: EvidenceSource
    claim: EvidenceClaim
    evidence_review_id: UUID
    evidence_review_content: dict[str, str]
    floor: CompetencyFloor
    floor_review_id: UUID
    floor_review_content: dict[str, str]
    release_rationale: NonEmptyText
    release_uncertainty: NonEmptyText


class PreparedCompetencyFloorCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    presentation: CompetencyFloorCandidate
    release: PreparedCompetencyFloorRelease


class CompetencyFloorRatificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    release_id: UUID
    release_version: str = "competency-floor-ratification@1.0.0"
    candidate_content_digest: str
    authority_account_id: UUID
    authority_assignment_id: UUID
    created_source: bool
    created_claim: bool
    created_evidence_review: bool
    created_floor: bool
    created_floor_review: bool
    decision_record_created: bool
    floor: CompetencyFloor
    floor_review: CompetencyFloorReview


class CompetencyFloorCandidateConflictError(RuntimeError):
    pass


class CompetencyFloorCandidateValidationError(RuntimeError):
    pass


def list_competency_floor_candidates(
    session: Session, *, projected_at: datetime | None = None
) -> CompetencyFloorCandidateProjection:
    instant = projected_at or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("candidate projection time must include a timezone")
    repository = DomainRepository(session)
    items: list[CompetencyFloorCandidateItem] = []
    for prepared in _candidate_registry().values():
        decision = repository.get_decision_record(prepared.release.release_id)
        if decision is None:
            status: Literal["available", "ratified", "conflict"] = "available"
            ratified_at = None
            issues: tuple[str, ...] = ()
        elif (
            f"candidate_content_digest:{prepared.presentation.content_digest}" in decision.evidence
        ):
            status = "ratified"
            ratified_at = decision.created_at
            issues = ()
        else:
            status = "conflict"
            ratified_at = decision.created_at
            issues = ("The candidate release identity is occupied by different immutable content.",)
        items.append(
            CompetencyFloorCandidateItem(
                candidate=prepared.presentation,
                status=status,
                ratified_at=ratified_at,
                issues=issues,
            )
        )
    return CompetencyFloorCandidateProjection(projected_at=instant, items=tuple(items))


def ratify_competency_floor_candidate(
    session: Session,
    candidate_id: UUID,
    command: RatifyCompetencyFloorCandidateCommand,
    authority: AuthorizedRole,
    *,
    ratified_at: datetime | None = None,
) -> CompetencyFloorRatificationResult:
    try:
        prepared = _candidate_registry()[candidate_id]
    except KeyError as error:
        raise KeyError("competency-floor candidate does not exist") from error
    if authority.role is not AccountRole.PLANNING_REVIEWER:
        raise CompetencyFloorCandidateValidationError(
            "competency-floor ratification requires planning_reviewer authority"
        )
    if command.candidate_version != prepared.presentation.candidate_version:
        raise CompetencyFloorCandidateValidationError(
            "candidate version does not match the prepared release"
        )
    if command.content_digest != prepared.presentation.content_digest:
        raise CompetencyFloorCandidateConflictError(
            "candidate content changed; refresh and review the exact current release"
        )

    repository = DomainRepository(session)
    existing_decision = repository.get_decision_record(prepared.release.release_id)
    if existing_decision is not None:
        return _existing_result(repository, prepared, existing_decision)

    instant = ratified_at or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("ratification time must include a timezone")
    if instant < prepared.release.prepared_at:
        raise CompetencyFloorCandidateValidationError(
            "ratification cannot predate prepared content"
        )
    if instant < authority.assigned_at:
        raise CompetencyFloorCandidateValidationError(
            "ratification cannot predate the reviewer role assignment"
        )
    if instant > datetime.now(UTC) + timedelta(minutes=5):
        raise CompetencyFloorCandidateValidationError("ratification cannot be in the future")

    release = prepared.release
    reviewer = f"account:{authority.account_id}"
    evidence_review = EvidenceClaimReview(
        id=release.evidence_review_id,
        created_at=instant,
        evidence_claim_id=release.claim.id,
        decision=EvidenceReviewDecision.APPROVED,
        sequence_number=1,
        reviewed_at=instant,
        reviewer=reviewer,
        **release.evidence_review_content,
    )
    floor_review = CompetencyFloorReview(
        id=release.floor_review_id,
        created_at=instant,
        competency_floor_id=release.floor.id,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=1,
        evidence_claim_ids=(release.claim.id,),
        reviewed_at=instant,
        reviewed_by=reviewer,
        **release.floor_review_content,
    )
    decision = DecisionRecord(
        id=release.release_id,
        created_at=instant,
        decision=f"Ratified competency-floor candidate: {release.release_label}",
        reason=release.release_rationale,
        alternatives_considered=(
            "Leave initial planning blocked until a broader reference source is reviewed.",
            "Ask the owner to invent a threshold without traceable evidence.",
            "Misrepresent the cohort median as a minimum competency floor.",
        ),
        evidence=(
            f"candidate_content_digest:{prepared.presentation.content_digest}",
            f"authority_account_id:{authority.account_id}",
            f"authority_assignment_id:{authority.assignment_id}",
            f"evidence_claim_id:{release.claim.id}",
            f"competency_floor_id:{release.floor.id}",
            f"competency_floor_review_id:{floor_review.id}",
        ),
        uncertainty=release.release_uncertainty,
        decision_version="competency-floor-ratification@1.0.0",
        decided_on=instant.date(),
    )

    try:
        created_source = _ensure_exact(
            label="evidence source",
            expected=release.source,
            existing=repository.get_evidence_source(release.source.id),
            add=repository.add_evidence_source,
        )
        session.flush()
        created_claim = _ensure_exact(
            label="evidence claim",
            expected=release.claim,
            existing=repository.get_evidence_claim(release.claim.id),
            add=repository.add_evidence_claim,
        )
        session.flush()
        created_evidence_review = _ensure_exact(
            label="evidence review",
            expected=evidence_review,
            existing=repository.get_evidence_claim_review(evidence_review.id),
            add=repository.add_evidence_claim_review,
        )
        session.flush()
        EvidenceAuthorityEvaluator(session).require_ready((release.claim.id,), instant)
        created_floor = _ensure_exact(
            label="competency floor",
            expected=release.floor,
            existing=repository.get_competency_floor(release.floor.id),
            add=repository.add_competency_floor,
        )
        session.flush()
        created_floor_review = _ensure_exact(
            label="competency floor review",
            expected=floor_review,
            existing=repository.get_competency_floor_review(floor_review.id),
            add=repository.add_competency_floor_review,
        )
        session.flush()
        decision_record_created = _ensure_exact(
            label="decision record",
            expected=decision,
            existing=repository.get_decision_record(decision.id),
            add=repository.add_decision_record,
        )
        session.commit()
    except CompetencyFloorCandidateConflictError:
        session.rollback()
        raise
    except (
        DomainIntegrityError,
        EvidenceAuthorityEvaluationError,
        EvidenceAuthorityNotReadyError,
        IntegrityError,
    ) as error:
        session.rollback()
        raise CompetencyFloorCandidateConflictError(str(error)) from error
    except Exception:
        session.rollback()
        raise

    return CompetencyFloorRatificationResult(
        release_id=release.release_id,
        candidate_content_digest=prepared.presentation.content_digest,
        authority_account_id=authority.account_id,
        authority_assignment_id=authority.assignment_id,
        created_source=created_source,
        created_claim=created_claim,
        created_evidence_review=created_evidence_review,
        created_floor=created_floor,
        created_floor_review=created_floor_review,
        decision_record_created=decision_record_created,
        floor=release.floor,
        floor_review=floor_review,
    )


def _existing_result(
    repository: DomainRepository,
    prepared: PreparedCompetencyFloorCandidate,
    decision: DecisionRecord,
) -> CompetencyFloorRatificationResult:
    values = {
        key: value
        for item in decision.evidence
        if ":" in item
        for key, value in (item.split(":", 1),)
    }
    if values.get("candidate_content_digest") != prepared.presentation.content_digest:
        raise CompetencyFloorCandidateConflictError(
            "candidate release identity is occupied by different immutable content"
        )
    try:
        account_id = UUID(values["authority_account_id"])
        assignment_id = UUID(values["authority_assignment_id"])
    except (KeyError, ValueError) as error:
        raise CompetencyFloorCandidateConflictError(
            "persisted candidate decision has incomplete authority provenance"
        ) from error
    floor = repository.get_competency_floor(prepared.release.floor.id)
    review = repository.get_competency_floor_review(prepared.release.floor_review_id)
    if floor != prepared.release.floor or review is None:
        raise CompetencyFloorCandidateConflictError(
            "persisted candidate decision has incomplete competency-floor lineage"
        )
    return CompetencyFloorRatificationResult(
        release_id=prepared.release.release_id,
        candidate_content_digest=prepared.presentation.content_digest,
        authority_account_id=account_id,
        authority_assignment_id=assignment_id,
        created_source=False,
        created_claim=False,
        created_evidence_review=False,
        created_floor=False,
        created_floor_review=False,
        decision_record_created=False,
        floor=floor,
        floor_review=review,
    )


@lru_cache
def _candidate_registry() -> dict[UUID, PreparedCompetencyFloorCandidate]:
    release = _chair_stand_floor_release()
    presentation_fields = _chair_stand_floor_presentation_fields()
    canonical = json.dumps(
        {
            "candidate_version": CANDIDATE_VERSION,
            "presentation": presentation_fields,
            "release": release.model_dump(mode="json"),
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    presentation = CompetencyFloorCandidate(
        candidate_version=CANDIDATE_VERSION,
        content_digest=f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}",
        **presentation_fields,
    )
    prepared = PreparedCompetencyFloorCandidate(presentation=presentation, release=release)
    return {presentation.candidate_id: prepared}


def _chair_stand_floor_release() -> PreparedCompetencyFloorRelease:
    source_time = datetime(2026, 9, 9, 0, 0, tzinfo=UTC)
    claim_time = datetime(2026, 9, 9, 0, 5, tzinfo=UTC)
    prepared_at = datetime(2026, 9, 9, 0, 10, tzinfo=UTC)
    pmid = EvidenceSourceIdentifier(scheme="pmid", value="42183074")
    doi = EvidenceSourceIdentifier(scheme="doi", value="10.25100/cm.v56i4.6874")
    pmcid = EvidenceSourceIdentifier(scheme="other", value="pmcid:PMC13193711")
    source = EvidenceSource(
        id=UUID("90000000-0000-4000-8000-000000000004"),
        created_at=source_time,
        title="Reference values for sit-to-stand tests in Colombian adults: a multicenter cross-sectional study",
        authors=(
            "Jenifer Rodríguez-Castro",
            "Vicente Benavides-Cordoba",
            "Rodrigo Torres-Castro",
            "Matías Otto-Yáñez",
            "Jhonatan Betancourt-Peña",
            "Juan Carlos Ávila-Valencia",
        ),
        journal="Colombia Médica",
        publication_year=2025,
        publication_date=date(2025, 12, 30),
        publication_types=("Journal Article", "Multicenter Study"),
        primary_identifier=pmid,
        source_identifiers=(pmid, doi, pmcid),
        metadata_provider="pubmed",
        retrieval_uri="https://pmc.ncbi.nlm.nih.gov/articles/PMC13193711/",
        retrieval_query="PMID 42183074; PMCID PMC13193711",
        retrieved_at=source_time,
        metadata_version="pubmed-pmc-record-snapshot@2026-09-09",
        provenance_notes=(
            "Bibliographic metadata, participant criteria, protocol, subgroup sizes, percentile method, Table 2 values, and conflict statement were checked against the PubMed and PMC records.",
            "The source is retained as a snapshot reference; the article text is not copied into AGAS.",
        ),
    )
    claim = EvidenceClaim(
        id=UUID("91000000-0000-4000-8000-000000000004"),
        created_at=claim_time,
        claim=(
            "In the study's Colombian 30-to-39-year age group, the empirical 2.5th percentile for completed 30-second sit-to-stand repetitions was 11 for women (n=29) and 11 for men (n=31)."
        ),
        domain="muscular_endurance",
        population=(
            "Community-dwelling Colombian adults aged 30 to 39 who self-reported good health and could perform sit-to-stand movements; BMI above 35 and recent conditions interfering with performance were excluded."
        ),
        intervention="One investigator-instructed 30-second sit-to-stand trial using a standard 43-to-46 cm chair.",
        comparator="Empirical sex- and age-stratified reference distribution; no intervention comparator.",
        outcome="Completed sit-to-stand repetitions in 30 seconds.",
        study_design="Multicenter cross-sectional reference-value study",
        duration="Single testing session; data collected March 2023 through June 2024.",
        effect_direction="Higher repetition count represented higher test performance.",
        uncertainty=(
            "The 2.5th percentile is a descriptive lower reference boundary in this sample, not a validated causal threshold for health, safety, athletic performance, or training response."
        ),
        limitations=(
            "Only 29 women and 31 men contributed to the 30-to-39-year subgroup.",
            "Population-specific Colombian values may not transfer to an individual from another geography or background.",
            "The investigator-administered source protocol is not identical to AGAS digital self-administration.",
            "The cross-sectional design does not establish a minimum useful athletic competency or training dose.",
        ),
        evidence_strength=EvidenceStrength.MODERATE,
        athlete_applicability=Applicability.LOW,
        applicability_notes=(
            "The exact age-stratified test value is usable only as a conservative, provisional owner-alpha reference when the athlete is 30 to 39 and completes the matching AGAS assessment; geography, administration, and individual differences limit transfer."
        ),
        source_identifiers=(pmid, doi, pmcid),
        source_record_ids=(source.id,),
        reviewer="Codex evidence synthesis candidate; authority pending",
        claim_version="colombian-chair-stand-age-30-39-p025@1.0.0",
    )
    floor = CompetencyFloor(
        id=UUID("98500000-0000-4000-8000-000000000001"),
        created_at=prepared_at,
        domain=CapabilityDomain.MUSCULAR_ENDURANCE,
        estimate_scope="assessment_specific:thirty_second_chair_stand_repetitions",
        unit_or_scale="repetitions",
        threshold=11,
        comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
        population=(
            "Provisional owner-alpha reference for adults aged 30 to 39, derived from the shared female and male 2.5th-percentile value in one Colombian community sample."
        ),
        minimum_age_years=30,
        maximum_age_years=39,
        applicability_notes=(
            "Apply only to a current estimate produced from the matching governed AGAS 30-second chair-stand protocol. Use solely to prioritize further development or maintenance review; never to clear exercise or diagnose impairment."
        ),
        uncertainty=(
            "This is an engineering interpretation of a population lower reference boundary as a deliberately low, replaceable screening floor. It is not a validated universal minimum useful competency, and it should be superseded when more applicable evidence or personal longitudinal calibration is available."
        ),
        evidence_claim_ids=(claim.id,),
        floor_version="owner-alpha-chair-stand-age-30-39-lower-reference@1.0.0",
    )
    return PreparedCompetencyFloorRelease(
        release_id=UUID("98400000-0000-4000-8000-000000000002"),
        release_label="Age 30-39 chair-stand lower-reference floor",
        prepared_at=prepared_at,
        source=source,
        claim=claim,
        evidence_review_id=UUID("91100000-0000-4000-8000-000000000004"),
        evidence_review_content={
            "source_verification_rationale": "PubMed identifiers and the open full text were checked; Table 2 reports 11 repetitions at p2.5 for both 30-to-39-year sex strata.",
            "extraction_rationale": "The claim preserves the subgroup sizes, empirical percentile, test duration, and observed value without converting it into a health or causal claim.",
            "evidence_strength_rationale": "The multicenter sample and directly reported empirical percentiles support the descriptive claim, while the small age-sex subgroups and single-country design limit certainty.",
            "applicability_rationale": "Applicability to an owner outside the sampled population is low; age matching and an assessment-specific estimate are mandatory but do not resolve geography or self-administration differences.",
            "uncertainty": "Approval covers exact extraction of the reference value, not the product decision to treat it as a competency floor.",
            "conflict_disclosure": "The authors reported no relevant financial affiliations or involvement; no independent conflict audit was performed by AGAS.",
            "review_version": "colombian-chair-stand-reference-evidence-review@1.0.0",
        },
        floor=floor,
        floor_review_id=UUID("98600000-0000-4000-8000-000000000001"),
        floor_review_content={
            "applicability_rationale": "Approve only as a provisional owner-alpha lower-reference screening floor for a 30-to-39-year-old athlete with a current matching estimate. Below-floor status prioritizes review; it does not make a medical or safety determination.",
            "uncertainty": "The study labels p2.5 as a lower limit of normality in its population, but it does not validate AGAS's minimum-useful-competency construct. The floor is intentionally narrow, age-bounded, versioned, and replaceable.",
            "review_version": "owner-alpha-chair-stand-floor-review@1.0.0",
        },
        release_rationale="Provide one inspectable, age-bounded floor so a matching first assessment can enter planning without requiring the owner or runtime to invent a hidden threshold.",
        release_uncertainty="Ratification authorizes only this low, population-limited comparison. It creates no diagnosis, medical clearance, adaptation priority, strategy, block, exercise, session, or dose.",
    )


def _chair_stand_floor_presentation_fields() -> dict[str, object]:
    return {
        "candidate_id": UUID("98400000-0000-4000-8000-000000000002"),
        "slug": "chair_stand_age_30_39_lower_reference_floor",
        "release_label": "Age 30-39 chair-stand lower-reference floor",
        "prepared_at": datetime(2026, 9, 9, 0, 10, tzinfo=UTC),
        "summary": "A deliberately low, provisional comparison point: 11 completed repetitions in the governed 30-second chair-stand assessment for athletes aged 30-39.",
        "domain": CapabilityDomain.MUSCULAR_ENDURANCE,
        "estimate_scope": "assessment_specific:thirty_second_chair_stand_repetitions",
        "unit_or_scale": "repetitions",
        "threshold": 11,
        "comparison_direction": ComparisonDirection.HIGHER_IS_BETTER,
        "minimum_age_years": 30,
        "maximum_age_years": 39,
        "governs": (
            "Whether a current, matching chair-stand estimate is below or at least meets this provisional lower-reference floor.",
            "Whether that comparison may become one reviewed input to initial planning.",
        ),
        "does_not_establish": (
            "Medical safety, diagnosis, injury risk, or clearance to train.",
            "A universal normal value, ideal performance target, or definition of athleticism.",
            "Any adaptation priority, workout, exercise, dose, or progression.",
            "Applicability outside ages 30-39 or to a nonmatching assessment protocol.",
        ),
        "unresolved_limitations": (
            "The source is Colombian and the 30-to-39 subgroup contained 29 women and 31 men.",
            "The source test was investigator-administered; AGAS uses governed digital self-administration.",
            "The study reports a population reference, not a validated minimum useful training competency.",
            "Personal longitudinal response should eventually replace broad population assumptions where possible.",
        ),
        "evidence": (
            CompetencyFloorEvidenceSummary(
                title="Colombian adult sit-to-stand reference values (2025)",
                source_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC13193711/",
                population="Community-dwelling Colombian adults; the relevant age subgroup included 29 women and 31 men aged 30-39.",
                finding="The empirical 2.5th percentile for the 30-second test was 11 repetitions in both sex strata aged 30-39.",
                limitations=(
                    "A descriptive percentile does not prove a health, safety, or athletic threshold.",
                    "Population and administration differences limit individual transfer.",
                ),
                conflict_disclosure="The authors reported no relevant financial affiliations or involvement; AGAS did not conduct an independent audit.",
            ),
        ),
    }


def _ensure_exact[Record: VersionedRecord](
    *, label: str, expected: Record, existing: Record | None, add: Callable[[Record], None]
) -> bool:
    if existing is None:
        add(expected)
        return True
    if existing != expected:
        raise CompetencyFloorCandidateConflictError(
            f"persisted {label} {expected.id} differs from candidate content"
        )
    return False
