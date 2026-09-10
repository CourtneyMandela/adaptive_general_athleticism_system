# ruff: noqa: E501 -- reviewed evidence and policy prose remains exact and readable.
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
    Confidence,
    DecisionRecord,
    EvidenceClaim,
    EvidenceClaimReview,
    EvidenceReviewDecision,
    EvidenceSource,
    EvidenceSourceIdentifier,
    EvidenceStrength,
    PriorityPolicy,
    PriorityPolicyReview,
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

CANDIDATE_VERSION = "planning-governance-candidate@1.0.0"
NonEmptyText = Annotated[str, Field(min_length=1)]


class PlanningPolicyEvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: NonEmptyText
    source_url: NonEmptyText
    population: NonEmptyText
    finding: NonEmptyText
    limitations: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    conflict_disclosure: NonEmptyText


class PlanningGovernanceCandidate(BaseModel):
    """Immutable owner-readable presentation of a prepared planning policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["planning-governance-candidate@1.0.0"]
    candidate_id: UUID
    slug: NonEmptyText
    release_label: NonEmptyText
    prepared_at: datetime
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    summary: NonEmptyText
    governs: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    does_not_establish: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    operational_choices: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    unresolved_limitations: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    evidence: Annotated[tuple[PlanningPolicyEvidenceSummary, ...], Field(min_length=1)]


class PlanningGovernanceCandidateItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate: PlanningGovernanceCandidate
    status: Literal["available", "ratified", "conflict"]
    ratified_at: datetime | None = None
    issues: tuple[str, ...] = ()


class PlanningGovernanceCandidateProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    projected_at: datetime
    items: tuple[PlanningGovernanceCandidateItem, ...]
    projection_version: str = "planning-governance-candidates@1.0.0"


class RatifyPlanningGovernanceCandidateCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["planning-governance-candidate@1.0.0"]
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    approval_attestation: Literal[True]


class PreparedPlanningPolicyRelease(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    release_id: UUID
    release_label: NonEmptyText
    prepared_at: datetime
    source: EvidenceSource
    claim: EvidenceClaim
    evidence_review_id: UUID
    evidence_review_content: dict[str, str]
    policy: PriorityPolicy
    policy_review_id: UUID
    policy_review_content: dict[str, str]
    release_rationale: NonEmptyText
    release_uncertainty: NonEmptyText


class PreparedPlanningGovernanceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    presentation: PlanningGovernanceCandidate
    release: PreparedPlanningPolicyRelease


class PlanningGovernanceRatificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    release_id: UUID
    release_version: str = "planning-governance-ratification@1.0.0"
    candidate_content_digest: str
    authority_account_id: UUID
    authority_assignment_id: UUID
    created_source: bool
    created_claim: bool
    created_evidence_review: bool
    created_policy: bool
    created_policy_review: bool
    decision_record_created: bool
    policy: PriorityPolicy
    policy_review: PriorityPolicyReview


class PlanningGovernanceCandidateConflictError(RuntimeError):
    pass


class PlanningGovernanceCandidateValidationError(RuntimeError):
    pass


def list_planning_governance_candidates(
    session: Session,
    *,
    projected_at: datetime | None = None,
) -> PlanningGovernanceCandidateProjection:
    instant = projected_at or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("candidate projection time must include a timezone")
    repository = DomainRepository(session)
    items: list[PlanningGovernanceCandidateItem] = []
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
            issues = (
                "The candidate release identity is already occupied by different immutable content.",
            )
        items.append(
            PlanningGovernanceCandidateItem(
                candidate=prepared.presentation,
                status=status,
                ratified_at=ratified_at,
                issues=issues,
            )
        )
    return PlanningGovernanceCandidateProjection(
        projected_at=instant,
        items=tuple(sorted(items, key=lambda item: item.candidate.slug)),
    )


def ratify_planning_governance_candidate(
    session: Session,
    candidate_id: UUID,
    command: RatifyPlanningGovernanceCandidateCommand,
    authority: AuthorizedRole,
    *,
    ratified_at: datetime | None = None,
) -> PlanningGovernanceRatificationResult:
    try:
        prepared = _candidate_registry()[candidate_id]
    except KeyError as error:
        raise KeyError("planning-governance candidate does not exist") from error
    if authority.role is not AccountRole.PLANNING_REVIEWER:
        raise PlanningGovernanceCandidateValidationError(
            "planning-governance ratification requires planning_reviewer authority"
        )
    if command.candidate_version != prepared.presentation.candidate_version:
        raise PlanningGovernanceCandidateValidationError(
            "candidate version does not match the prepared release"
        )
    if command.content_digest != prepared.presentation.content_digest:
        raise PlanningGovernanceCandidateConflictError(
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
        raise PlanningGovernanceCandidateValidationError(
            "ratification cannot predate prepared content"
        )
    if instant < authority.assigned_at:
        raise PlanningGovernanceCandidateValidationError(
            "ratification cannot predate the reviewer role assignment"
        )
    if instant > datetime.now(UTC) + timedelta(minutes=5):
        raise PlanningGovernanceCandidateValidationError("ratification cannot be in the future")

    reviewer = f"account:{authority.account_id}"
    release = prepared.release
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
    policy_review = PriorityPolicyReview(
        id=release.policy_review_id,
        created_at=instant,
        priority_policy_id=release.policy.id,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=1,
        evidence_claim_ids=(release.claim.id,),
        reviewed_at=instant,
        reviewed_by=reviewer,
        **release.policy_review_content,
    )
    decision = DecisionRecord(
        id=release.release_id,
        created_at=instant,
        decision=f"Ratified planning-governance candidate: {release.release_label}",
        reason=release.release_rationale,
        alternatives_considered=(
            "Leave initial planning blocked until a later reviewed policy is available.",
            "Ask the owner to invent policy weights in an administrative form.",
            "Allow the runtime or an LLM to choose unversioned policy values silently.",
        ),
        evidence=(
            f"candidate_content_digest:{prepared.presentation.content_digest}",
            f"authority_account_id:{authority.account_id}",
            f"authority_assignment_id:{authority.assignment_id}",
            f"evidence_claim_id:{release.claim.id}",
            f"priority_policy_id:{release.policy.id}",
            f"priority_policy_review_id:{policy_review.id}",
        ),
        uncertainty=release.release_uncertainty,
        decision_version="planning-governance-ratification@1.0.0",
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
        created_policy = _ensure_exact(
            label="priority policy",
            expected=release.policy,
            existing=repository.get_priority_policy(release.policy.id),
            add=repository.add_priority_policy,
        )
        session.flush()
        created_policy_review = _ensure_exact(
            label="priority policy review",
            expected=policy_review,
            existing=repository.get_priority_policy_review(policy_review.id),
            add=repository.add_priority_policy_review,
        )
        session.flush()
        decision_record_created = _ensure_exact(
            label="decision record",
            expected=decision,
            existing=repository.get_decision_record(decision.id),
            add=repository.add_decision_record,
        )
        session.commit()
    except PlanningGovernanceCandidateConflictError:
        session.rollback()
        raise
    except (
        DomainIntegrityError,
        EvidenceAuthorityEvaluationError,
        EvidenceAuthorityNotReadyError,
        IntegrityError,
    ) as error:
        session.rollback()
        raise PlanningGovernanceCandidateConflictError(str(error)) from error
    except Exception:
        session.rollback()
        raise

    return PlanningGovernanceRatificationResult(
        release_id=release.release_id,
        candidate_content_digest=prepared.presentation.content_digest,
        authority_account_id=authority.account_id,
        authority_assignment_id=authority.assignment_id,
        created_source=created_source,
        created_claim=created_claim,
        created_evidence_review=created_evidence_review,
        created_policy=created_policy,
        created_policy_review=created_policy_review,
        decision_record_created=decision_record_created,
        policy=release.policy,
        policy_review=policy_review,
    )


def _existing_result(
    repository: DomainRepository,
    prepared: PreparedPlanningGovernanceCandidate,
    decision: DecisionRecord,
) -> PlanningGovernanceRatificationResult:
    values = {
        key: value
        for item in decision.evidence
        if ":" in item
        for key, value in (item.split(":", 1),)
    }
    if values.get("candidate_content_digest") != prepared.presentation.content_digest:
        raise PlanningGovernanceCandidateConflictError(
            "candidate release identity is occupied by different immutable content"
        )
    try:
        account_id = UUID(values["authority_account_id"])
        assignment_id = UUID(values["authority_assignment_id"])
    except (KeyError, ValueError) as error:
        raise PlanningGovernanceCandidateConflictError(
            "persisted candidate decision has incomplete authority provenance"
        ) from error
    policy = repository.get_priority_policy(prepared.release.policy.id)
    review = repository.get_priority_policy_review(prepared.release.policy_review_id)
    if policy != prepared.release.policy or review is None:
        raise PlanningGovernanceCandidateConflictError(
            "persisted candidate decision has incomplete policy lineage"
        )
    return PlanningGovernanceRatificationResult(
        release_id=prepared.release.release_id,
        candidate_content_digest=prepared.presentation.content_digest,
        authority_account_id=account_id,
        authority_assignment_id=assignment_id,
        created_source=False,
        created_claim=False,
        created_evidence_review=False,
        created_policy=False,
        created_policy_review=False,
        decision_record_created=False,
        policy=policy,
        policy_review=review,
    )


@lru_cache
def _candidate_registry() -> dict[UUID, PreparedPlanningGovernanceCandidate]:
    candidates = []
    for release, presentation_fields in (
        (
            _conservative_priority_policy_release(),
            _conservative_priority_policy_presentation_fields(),
        ),
        (
            _deficit_only_priority_policy_release(),
            _deficit_only_priority_policy_presentation_fields(),
        ),
    ):
        content_digest = _candidate_digest(release, presentation_fields)
        presentation = PlanningGovernanceCandidate(
            candidate_version=CANDIDATE_VERSION,
            content_digest=content_digest,
            **presentation_fields,
        )
        candidates.append(
            PreparedPlanningGovernanceCandidate(
                presentation=presentation,
                release=release,
            )
        )
    return {candidate.presentation.candidate_id: candidate for candidate in candidates}


def _candidate_digest(
    release: PreparedPlanningPolicyRelease,
    presentation_fields: dict[str, object],
) -> str:
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
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def _conservative_priority_policy_release() -> PreparedPlanningPolicyRelease:
    source_time = datetime(2026, 9, 9, 10, 0, tzinfo=UTC)
    claim_time = datetime(2026, 9, 9, 10, 10, tzinfo=UTC)
    prepared_at = datetime(2026, 9, 9, 10, 30, tzinfo=UTC)
    pmid = EvidenceSourceIdentifier(scheme="pmid", value="41843416")
    doi = EvidenceSourceIdentifier(scheme="doi", value="10.1249/MSS.0000000000003897")
    pmcid = EvidenceSourceIdentifier(scheme="other", value="pmcid:PMC12965823")
    source = EvidenceSource(
        id=UUID("90000000-0000-4000-8000-000000000003"),
        created_at=source_time,
        title="American College of Sports Medicine Position Stand. Resistance Training Prescription for Muscle Function, Hypertrophy, and Physical Performance in Healthy Adults: An Overview of Reviews",
        authors=(
            "Brad S Currier",
            "Alysha C D'Souza",
            "Maria A Fiatarone Singh",
            "Caroline V Lowisz",
            "Eric S Rawson",
            "Brad J Schoenfeld",
            "Abbie E Smith-Ryan",
            "Jeremy P Steen",
            "Gwendolyn A Thomas",
            "N Travis Triplett",
            "Tyrone A Washington",
            "Timothy J Werner",
            "Stuart M Phillips",
        ),
        journal="Medicine & Science in Sports & Exercise",
        publication_year=2026,
        publication_date=date(2026, 4, 1),
        publication_types=("Review",),
        primary_identifier=pmid,
        source_identifiers=(pmid, doi, pmcid),
        metadata_provider="pubmed",
        retrieval_uri="https://pubmed.ncbi.nlm.nih.gov/41843416/",
        retrieval_query="PMID 41843416",
        retrieved_at=source_time,
        metadata_version="pubmed-record-snapshot@2026-09-09",
        provenance_notes=(
            "Publication metadata and abstract-level results were checked against PubMed.",
            "The abstract is intentionally not copied into this metadata snapshot.",
        ),
    )
    claim = EvidenceClaim(
        id=UUID("91000000-0000-4000-8000-000000000003"),
        created_at=claim_time,
        claim=(
            "Across 137 systematic reviews representing more than 30,000 healthy adults, progressive resistance training improved strength, hypertrophy, power, endurance, contraction velocity, gait speed, balance, and multiple physical-function outcomes compared with no exercise."
        ),
        domain="resistance_training",
        population="Healthy adults aged 18 years or older represented across 137 systematic reviews.",
        intervention="Progressive resistance training lasting at least six weeks.",
        comparator="No exercise or alternative resistance-training prescriptions, depending on the underlying review.",
        outcome="Muscle function, hypertrophy, power, endurance, gait speed, balance, and physical performance.",
        study_design="American College of Sports Medicine position stand using an overview of systematic reviews",
        duration="Underlying randomized trials ranged from 6 to 52 weeks.",
        effect_direction="Resistance training was beneficial across multiple muscle-function and physical-performance outcomes.",
        uncertainty=(
            "The overview supports resistance training as a useful adaptation method; it does not validate AGAS priority weights, score thresholds, athlete-specific priority rankings, or a workout dose."
        ),
        limitations=(
            "The overview combines heterogeneous systematic reviews, populations, outcomes, and prescriptions.",
            "Abstract-level extraction does not establish subgroup-specific effects.",
            "The source does not define the numeric values in the AGAS operational priority policy.",
        ),
        evidence_strength=EvidenceStrength.HIGH,
        athlete_applicability=Applicability.MODERATE,
        applicability_notes=(
            "Applicable as broad support for resistance-training adaptation in healthy adults; current safety, goals, capability state, environment, and later dose governance still control use."
        ),
        source_identifiers=(pmid, doi, pmcid),
        source_record_ids=(source.id,),
        reviewer="Codex evidence synthesis candidate; authority pending",
        claim_version="acsm-resistance-training-multiple-outcomes@1.0.0",
    )
    policy = PriorityPolicy(
        id=UUID("98000000-0000-4000-8000-000000000001"),
        created_at=prepared_at,
        deficit_weight=4.0,
        general_relevance_weight=1.0,
        goal_relevance_weight=1.0,
        prerequisite_value_weight=1.0,
        expected_trainability_weight=1.0,
        transfer_value_weight=1.0,
        fatigue_cost_weight=1.0,
        time_cost_weight=1.0,
        interference_cost_weight=1.0,
        cost_penalty=0.25,
        confidence_multipliers={
            Confidence.UNKNOWN: 0.0,
            Confidence.LOW: 0.5,
            Confidence.MODERATE: 0.75,
            Confidence.HIGH: 1.0,
        },
        develop_score_threshold=0.35,
        comparative_advantage_threshold=0.75,
        severe_deficit_threshold=0.5,
        max_develop_adaptations=2,
        policy_version="owner-alpha-conservative-priority@1.0.0",
    )
    return PreparedPlanningPolicyRelease(
        release_id=UUID("98400000-0000-4000-8000-000000000001"),
        release_label="Conservative owner-alpha priority policy",
        prepared_at=prepared_at,
        source=source,
        claim=claim,
        evidence_review_id=UUID("91100000-0000-4000-8000-000000000003"),
        evidence_review_content={
            "source_verification_rationale": "PubMed identifiers, authorship, publication timing, review scope, participant scale, and abstract-level outcomes were checked against PMID 41843416.",
            "extraction_rationale": "The claim retains only the broad comparison and outcomes reported by the abstract and does not import dose rules into the priority algorithm.",
            "evidence_strength_rationale": "A current professional position stand synthesizing 137 systematic reviews provides strong broad evidence, while heterogeneous review quality limits finer claims.",
            "applicability_rationale": "The healthy-adult population is directionally relevant to an owner alpha, but individual applicability still depends on readiness, observed capability, goals, and environment.",
            "uncertainty": "This review approves the extracted resistance-training claim, not AGAS numeric priority weights or any athlete-specific prescription.",
            "conflict_disclosure": "No conflict was identified by the reviewing agent; source-author disclosures require full-text review before broader production use.",
            "review_version": "evidence-review-acsm-resistance-training@1.0.0",
        },
        policy=policy,
        policy_review_id=UUID("98300000-0000-4000-8000-000000000001"),
        policy_review_content={
            "applicability_rationale": "Use as a conservative, replaceable owner-alpha ranking policy only after athlete observations, compatible floors, and explicit candidate context are present.",
            "uncertainty": "The numeric weights and thresholds are operational product choices rather than estimates from PMID 41843416. They must be evaluated with counterfactual tests and replaced if observed decisions are poorly calibrated.",
            "review_version": "owner-alpha-priority-policy-review@1.0.0",
        },
        release_rationale="Provide one inspectable, fail-closed priority policy so the owner is not required to invent planning weights and the runtime never chooses hidden defaults.",
        release_uncertainty="This release intentionally creates no competency floor, athlete-specific candidate scores, strategy, block, session, exercise, or dose. Those remain separate governed decisions.",
    )


def prepared_acsm_resistance_training_source() -> EvidenceSource:
    """Return the exact source snapshot shared by prepared training authorities."""

    return _conservative_priority_policy_release().source


def _conservative_priority_policy_presentation_fields() -> dict[str, object]:
    return {
        "candidate_id": UUID("98400000-0000-4000-8000-000000000001"),
        "slug": "owner_alpha_conservative_priority_policy",
        "release_label": "Conservative owner-alpha priority policy",
        "prepared_at": datetime(2026, 9, 9, 10, 30, tzinfo=UTC),
        "summary": (
            "A transparent first ranking policy that makes measured deficits the strongest benefit signal, reduces low-confidence priorities, limits simultaneous development targets, and charges explicit fatigue, time, and interference costs."
        ),
        "governs": (
            "How already-reviewed benefit and cost inputs are combined into a bounded priority score.",
            "How estimate confidence reduces the influence of uncertain capability state.",
            "The score threshold and maximum of two simultaneous DEVELOP assignments.",
        ),
        "does_not_establish": (
            "Whether Courtney is below a useful competency floor.",
            "Which adaptation Courtney should develop, maintain, expose, or defer.",
            "Any exercise, workout dose, progression, medical clearance, or diagnosis.",
            "That these numeric weights were measured in the cited research.",
        ),
        "operational_choices": (
            "Deficit receives four times the weight of each other benefit component.",
            "Unknown confidence contributes no adjusted benefit; low and moderate confidence are discounted.",
            "Fatigue, time, and interference are weighted equally and apply a 0.25 cost penalty.",
            "At most two adaptations may receive DEVELOP status in one strategy.",
            "Every value is versioned and replaceable; changing one requires a new candidate and review.",
        ),
        "unresolved_limitations": (
            "The numerical policy is an inspectable engineering prior, not a scientifically estimated optimum.",
            "One resistance-training source does not substantiate priorities across every athletic domain.",
            "Counterfactual and personal-response calibration are required before broader use.",
            "A compatible reviewed competency floor and reviewed athlete-specific context are still required before a strategy can be created.",
        ),
        "evidence": (
            PlanningPolicyEvidenceSummary(
                title="ACSM resistance-training position stand (2026)",
                source_url="https://pubmed.ncbi.nlm.nih.gov/41843416/",
                population="Healthy adults represented across 137 systematic reviews and more than 30,000 participants.",
                finding="Progressive resistance training improved multiple muscle-function and physical-performance outcomes compared with no exercise.",
                limitations=(
                    "The source supports training effects, not the candidate's numeric ranking weights.",
                    "It does not identify Courtney's current priority or prescribe a first workout.",
                ),
                conflict_disclosure="No conflict was identified by the reviewing agent; full source-author disclosure review remains required before broader production use.",
            ),
        ),
    }


def _deficit_only_priority_policy_release() -> PreparedPlanningPolicyRelease:
    """Prepare the narrow policy used while contextual planning signals remain unavailable."""

    source = _conservative_priority_policy_release().source
    claim_time = datetime(2026, 9, 9, 14, 10, tzinfo=UTC)
    prepared_at = datetime(2026, 9, 9, 14, 30, tzinfo=UTC)
    claim = EvidenceClaim(
        id=UUID("91000000-0000-4000-8000-000000000004"),
        created_at=claim_time,
        claim=(
            "The reviewed resistance-training overview reports improvement in muscular endurance "
            "among the multiple muscle-function and physical-performance outcomes that improved "
            "with progressive resistance training compared with no exercise."
        ),
        domain="muscular_endurance",
        population="Healthy adults aged 18 years or older represented across 137 systematic reviews.",
        intervention="Progressive resistance training lasting at least six weeks.",
        comparator="No exercise or alternative resistance-training prescriptions, depending on the underlying review.",
        outcome="Muscular endurance as one outcome within a broad overview of resistance-training effects.",
        study_design="American College of Sports Medicine position stand using an overview of systematic reviews",
        duration="Underlying randomized trials ranged from 6 to 52 weeks.",
        effect_direction="Progressive resistance training improved muscular endurance in the reviewed evidence base.",
        uncertainty=(
            "The overview supports trainability at a population level. It does not establish that "
            "one individual will respond, validate a chair-stand threshold, quantify a priority "
            "score, or prescribe an exercise or dose."
        ),
        limitations=(
            "The overview combines heterogeneous reviews, populations, endurance measures, and prescriptions.",
            "The abstract does not provide a chair-stand-specific effect estimate.",
            "The source does not determine AGAS policy thresholds or an athlete-specific decision.",
        ),
        evidence_strength=EvidenceStrength.HIGH,
        athlete_applicability=Applicability.MODERATE,
        applicability_notes=(
            "Directionally applicable to a healthy-adult owner alpha only as support that muscular "
            "endurance is trainable; current readiness and later exercise-dose governance remain required."
        ),
        source_identifiers=source.source_identifiers,
        source_record_ids=(source.id,),
        reviewer="Codex evidence synthesis candidate; authority pending",
        claim_version="acsm-resistance-training-muscular-endurance@1.0.0",
    )
    policy = PriorityPolicy(
        id=UUID("98000000-0000-4000-8000-000000000002"),
        created_at=prepared_at,
        deficit_weight=1.0,
        general_relevance_weight=0.0,
        goal_relevance_weight=0.0,
        prerequisite_value_weight=0.0,
        expected_trainability_weight=0.0,
        transfer_value_weight=0.0,
        fatigue_cost_weight=0.0,
        time_cost_weight=0.0,
        interference_cost_weight=0.0,
        cost_penalty=0.0,
        confidence_multipliers={
            Confidence.UNKNOWN: 0.0,
            Confidence.LOW: 0.5,
            Confidence.MODERATE: 0.75,
            Confidence.HIGH: 1.0,
        },
        develop_score_threshold=0.01,
        comparative_advantage_threshold=1.0,
        severe_deficit_threshold=0.5,
        max_develop_adaptations=1,
        policy_version="owner-alpha-deficit-only-priority@1.0.0",
    )
    return PreparedPlanningPolicyRelease(
        release_id=UUID("98400000-0000-4000-8000-000000000002"),
        release_label="Deficit-only owner-alpha initial policy",
        prepared_at=prepared_at,
        source=source,
        claim=claim,
        evidence_review_id=UUID("91100000-0000-4000-8000-000000000004"),
        evidence_review_content={
            "source_verification_rationale": "PubMed identifiers, overview scale, population, and the reported muscular-endurance outcome were checked against PMID 41843416.",
            "extraction_rationale": "The narrower claim retains only the reported direction for muscular endurance and excludes athlete-specific response, threshold, and dose conclusions.",
            "evidence_strength_rationale": "A current professional position stand synthesizing 137 systematic reviews provides strong broad evidence while heterogeneous underlying methods limit specificity.",
            "applicability_rationale": "The healthy-adult evidence supports trainability directionally; it does not replace current readiness, individual response, or exercise feasibility checks.",
            "uncertainty": "This review approves the extracted trainability claim, not the policy's 0.01 operational threshold or any workout.",
            "conflict_disclosure": "No conflict was identified by the reviewing agent; source-author disclosures require full-text review before broader production use.",
            "review_version": "evidence-review-acsm-muscular-endurance@1.0.0",
        },
        policy=policy,
        policy_review_id=UUID("98300000-0000-4000-8000-000000000002"),
        policy_review_content={
            "applicability_rationale": "Use only for the owner-alpha initial strategy when a current estimate is exactly comparable with a reviewed competency floor and richer contextual signals have not yet been established.",
            "uncertainty": "The nonzero threshold is a versioned numerical guard against floating-point noise, not a clinically or scientifically established minimum meaningful difference. Reassessment and later response data must challenge the decision.",
            "review_version": "owner-alpha-deficit-only-priority-review@1.0.0",
        },
        release_rationale="Let the first strategy use the exact governed deficit and estimate confidence that AGAS can substantiate without forcing the owner to invent relevance, transfer, trainability, or recovery-cost scores.",
        release_uncertainty="This policy is intentionally narrow. It creates no athlete context, safety clearance, strategy, block, exercise, dose, session, or workout.",
    )


def _deficit_only_priority_policy_presentation_fields() -> dict[str, object]:
    return {
        "candidate_id": UUID("98400000-0000-4000-8000-000000000002"),
        "slug": "owner_alpha_deficit_only_initial_policy",
        "release_label": "Deficit-only owner-alpha initial policy",
        "prepared_at": datetime(2026, 9, 9, 14, 30, tzinfo=UTC),
        "summary": (
            "A deliberately narrow initial policy that ranks only an exact measured deficit, "
            "discounted by estimate confidence. Inputs AGAS cannot yet substantiate receive zero "
            "weight rather than becoming hidden guesses."
        ),
        "governs": (
            "Whether an exact current estimate below its reviewed compatible floor may receive DEVELOP status.",
            "How estimate confidence reduces the measured deficit's ranking influence.",
            "A maximum of one development priority in the first owner-alpha strategy.",
        ),
        "does_not_establish": (
            "Medical clearance or current readiness to perform a session.",
            "Goal relevance, transfer value, prerequisites, fatigue cost, time cost, or interference cost.",
            "An exercise, training dose, weekly schedule, or guaranteed response.",
            "That a small deficit is clinically important or harmful.",
        ),
        "operational_choices": (
            "Only normalized deficit has nonzero benefit weight; every unavailable contextual score has zero weight.",
            "Unknown confidence contributes no adjusted benefit; low and moderate confidence remain discounted.",
            "The 0.01 DEVELOP threshold distinguishes a real normalized deficit from zero or numerical noise; it is not a scientific cutoff.",
            "Cost terms receive zero weight because cost depends on the later selected stimulus, exercise, dose, and schedule.",
            "At most one adaptation may receive DEVELOP status in this initial narrow policy.",
        ),
        "unresolved_limitations": (
            "The policy is suitable only while the owner alpha has one narrowly governed capability path.",
            "It cannot compare rich multi-domain tradeoffs until structured goal, relationship, and resource evidence exists.",
            "Any below-floor nonzero deficit with known confidence can qualify; personal response and repeat measurement must test whether that is useful.",
            "A separately reviewed athlete-specific context and current session safety gate remain required.",
        ),
        "evidence": (
            PlanningPolicyEvidenceSummary(
                title="ACSM resistance-training position stand (2026)",
                source_url="https://pubmed.ncbi.nlm.nih.gov/41843416/",
                population="Healthy adults represented across 137 systematic reviews and more than 30,000 participants.",
                finding="Progressive resistance training improved muscular endurance among multiple reported outcomes.",
                limitations=(
                    "The source supports population-level trainability, not the policy's numeric threshold.",
                    "It does not establish an individual priority, chair-stand cutoff, exercise, or dose.",
                ),
                conflict_disclosure="No conflict was identified by the reviewing agent; full source-author disclosure review remains required before broader production use.",
            ),
        ),
    }


def _ensure_exact[Record: VersionedRecord](
    *,
    label: str,
    expected: Record,
    existing: Record | None,
    add: Callable[[Record], None],
) -> bool:
    if existing is None:
        add(expected)
        return True
    if existing != expected:
        raise PlanningGovernanceCandidateConflictError(
            f"persisted {label} {expected.id} differs from candidate content"
        )
    return False
