# ruff: noqa: E501 -- reviewed evidence and authority prose remains exact.
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated, Literal
from uuid import UUID

from agas_domain import (
    AccountRole,
    Applicability,
    CostLevel,
    DecisionRecord,
    Equipment,
    EvidenceClaim,
    EvidenceClaimReview,
    EvidenceReviewDecision,
    EvidenceStrength,
    Exercise,
    ExerciseResolverPolicy,
    ImpactLevel,
    JointRegion,
    Laterality,
    Loadability,
    LoadingType,
    MovementPattern,
    ResourceAllocationPolicy,
    VelocityCharacteristic,
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
from agas_api.planning_governance_candidates import prepared_acsm_resistance_training_source

CANDIDATE_VERSION = "resource-governance-candidate@1.0.0"
CANDIDATE_ID = UUID("98600000-0000-4000-8000-000000000001")
EVIDENCE_CLAIM_ID = UUID("91000000-0000-4000-8000-000000000005")
EVIDENCE_REVIEW_ID = UUID("91100000-0000-4000-8000-000000000005")
EQUIPMENT_ID = UUID("e1000000-0000-4000-8000-000000000001")
EXERCISE_ID = UUID("b1000000-0000-4000-8000-000000000001")
RESOLVER_POLICY_ID = UUID("98700000-0000-4000-8000-000000000001")
ALLOCATION_POLICY_ID = UUID("98800000-0000-4000-8000-000000000001")
ADAPTATION_ID = UUID("a0000000-0000-4000-8000-000000000004")
NonEmptyText = Annotated[str, Field(min_length=1)]


class ResourceGovernanceEvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: NonEmptyText
    source_url: NonEmptyText
    population: NonEmptyText
    finding: NonEmptyText
    limitations: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]


class ResourceGovernanceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["resource-governance-candidate@1.0.0"]
    candidate_id: UUID
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    prepared_at: datetime
    release_label: NonEmptyText
    summary: NonEmptyText
    exact_artifacts: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    governs: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    does_not_establish: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    operational_choices: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    unresolved_limitations: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    evidence: Annotated[tuple[ResourceGovernanceEvidenceSummary, ...], Field(min_length=1)]


class ResourceGovernanceCandidateItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate: ResourceGovernanceCandidate
    status: Literal["available", "blocked", "ratified", "conflict"]
    ratified_at: datetime | None = None
    issues: tuple[str, ...] = ()


class ResourceGovernanceCandidateProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    projected_at: datetime
    items: tuple[ResourceGovernanceCandidateItem, ...]
    projection_version: str = "resource-governance-candidates@1.0.0"


class RatifyResourceGovernanceCandidateCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["resource-governance-candidate@1.0.0"]
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    approval_attestation: Literal[True]


class ResourceGovernanceRatificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: UUID
    candidate_content_digest: str
    created_claim: bool
    created_evidence_review: bool
    created_equipment: bool
    created_exercise: bool
    created_resolver_policy: bool
    created_allocation_policy: bool
    decision_record_created: bool
    equipment: Equipment
    exercise: Exercise
    resolver_policy: ExerciseResolverPolicy
    allocation_policy: ResourceAllocationPolicy
    ratification_version: str = "resource-governance-ratification@1.0.0"


class ResourceGovernanceCandidateConflictError(RuntimeError):
    pass


class ResourceGovernanceCandidateValidationError(RuntimeError):
    pass


class PreparedResourceGovernanceRelease(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prepared_at: datetime
    claim: EvidenceClaim
    evidence_review_content: dict[str, str]
    equipment: Equipment
    exercise: Exercise
    resolver_policy: ExerciseResolverPolicy
    allocation_policy: ResourceAllocationPolicy
    release_rationale: NonEmptyText
    release_uncertainty: NonEmptyText


class PreparedResourceGovernanceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    presentation: ResourceGovernanceCandidate
    release: PreparedResourceGovernanceRelease


def prepared_resource_governance_candidate() -> PreparedResourceGovernanceCandidate:
    """Return the exact immutable release used by downstream prepared workflows."""

    return _prepared_candidate()


def list_resource_governance_candidates(
    session: Session, *, projected_at: datetime | None = None
) -> ResourceGovernanceCandidateProjection:
    instant = projected_at or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("resource-governance projection time must include a timezone")
    prepared = _prepared_candidate()
    repository = DomainRepository(session)
    decision = repository.get_decision_record(CANDIDATE_ID)
    source = repository.get_evidence_source(prepared.release.claim.source_record_ids[0])
    adaptation = repository.get_adaptation(ADAPTATION_ID)
    issues: tuple[str, ...]
    prerequisite_issues = tuple(
        issue
        for missing, issue in (
            (
                source is None,
                "Approve the prepared deficit-only planning policy first so its exact ACSM source snapshot exists.",
            ),
            (
                adaptation is None,
                "Import the controlled seed catalog so the exact muscular-endurance adaptation exists.",
            ),
        )
        if missing
    )
    if decision is None and prerequisite_issues:
        status: Literal["available", "blocked", "ratified", "conflict"] = "blocked"
        ratified_at = None
        issues = prerequisite_issues
    elif decision is None:
        status = "available"
        ratified_at = None
        issues = ()
    elif f"candidate_content_digest:{prepared.presentation.content_digest}" in decision.evidence:
        try:
            _existing_result(repository, prepared, decision)
        except ResourceGovernanceCandidateConflictError as error:
            status = "conflict"
            ratified_at = decision.created_at
            issues = (str(error),)
        else:
            status = "ratified"
            ratified_at = decision.created_at
            issues = ()
    else:
        status = "conflict"
        ratified_at = decision.created_at
        issues = ("The release identity is occupied by different immutable content.",)
    return ResourceGovernanceCandidateProjection(
        projected_at=instant,
        items=(
            ResourceGovernanceCandidateItem(
                candidate=prepared.presentation,
                status=status,
                ratified_at=ratified_at,
                issues=issues,
            ),
        ),
    )


def ratify_resource_governance_candidate(
    session: Session,
    candidate_id: UUID,
    command: RatifyResourceGovernanceCandidateCommand,
    authority: AuthorizedRole,
    *,
    ratified_at: datetime | None = None,
) -> ResourceGovernanceRatificationResult:
    if candidate_id != CANDIDATE_ID:
        raise KeyError("resource-governance candidate does not exist")
    prepared = _prepared_candidate()
    if authority.role is not AccountRole.PLANNING_REVIEWER:
        raise ResourceGovernanceCandidateValidationError(
            "resource-governance ratification requires planning_reviewer authority"
        )
    if command.candidate_version != prepared.presentation.candidate_version:
        raise ResourceGovernanceCandidateValidationError(
            "candidate version does not match the prepared release"
        )
    if command.content_digest != prepared.presentation.content_digest:
        raise ResourceGovernanceCandidateConflictError(
            "candidate content changed; refresh and review the exact current release"
        )
    repository = DomainRepository(session)
    existing_decision = repository.get_decision_record(CANDIDATE_ID)
    if existing_decision is not None:
        return _existing_result(repository, prepared, existing_decision)
    instant = ratified_at or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("ratification time must include a timezone")
    if instant < prepared.release.prepared_at or instant < authority.assigned_at:
        raise ResourceGovernanceCandidateValidationError(
            "ratification cannot predate the prepared release or reviewer assignment"
        )
    if instant > datetime.now(UTC) + timedelta(minutes=5):
        raise ResourceGovernanceCandidateValidationError("ratification cannot be in the future")
    source_id = prepared.release.claim.source_record_ids[0]
    if repository.get_evidence_source(source_id) != prepared_acsm_resistance_training_source():
        raise ResourceGovernanceCandidateValidationError(
            "the exact prerequisite ACSM source is unavailable; approve the planning authority first"
        )
    if repository.get_adaptation(ADAPTATION_ID) is None:
        raise ResourceGovernanceCandidateValidationError(
            "the exact muscular-endurance adaptation is unavailable; import the controlled catalog first"
        )
    reviewer = f"account:{authority.account_id}"
    review = EvidenceClaimReview(
        id=EVIDENCE_REVIEW_ID,
        created_at=instant,
        evidence_claim_id=prepared.release.claim.id,
        decision=EvidenceReviewDecision.APPROVED,
        sequence_number=1,
        reviewed_at=instant,
        reviewer=reviewer,
        **prepared.release.evidence_review_content,
    )
    decision = DecisionRecord(
        id=CANDIDATE_ID,
        created_at=instant,
        decision="Ratified the first owner-alpha resource-governance bundle.",
        reason=prepared.release.release_rationale,
        alternatives_considered=(
            "Ask the owner to invent resolver, allocation, equipment, and exercise records.",
            "Allow the runtime to select unversioned defaults.",
            "Wait until a larger exercise catalog and multi-user review system exist.",
        ),
        evidence=(
            f"candidate_content_digest:{prepared.presentation.content_digest}",
            f"authority_account_id:{authority.account_id}",
            f"authority_assignment_id:{authority.assignment_id}",
            f"evidence_claim_id:{prepared.release.claim.id}",
            f"evidence_review_id:{review.id}",
            f"equipment_id:{prepared.release.equipment.id}",
            f"exercise_id:{prepared.release.exercise.id}",
            f"exercise_resolver_policy_id:{prepared.release.resolver_policy.id}",
            f"resource_allocation_policy_id:{prepared.release.allocation_policy.id}",
        ),
        uncertainty=prepared.release.release_uncertainty,
        decision_version="resource-governance-ratification@1.0.0",
        decided_on=instant.date(),
    )
    try:
        created_claim = _ensure_exact(
            "evidence claim",
            prepared.release.claim,
            repository.get_evidence_claim,
            repository.add_evidence_claim,
        )
        session.flush()
        created_review = _ensure_exact(
            "evidence review",
            review,
            repository.get_evidence_claim_review,
            repository.add_evidence_claim_review,
        )
        session.flush()
        EvidenceAuthorityEvaluator(session).require_ready((prepared.release.claim.id,), instant)
        created_equipment = _ensure_exact(
            "equipment",
            prepared.release.equipment,
            repository.get_equipment,
            repository.add_equipment,
        )
        session.flush()
        created_exercise = _ensure_exact(
            "exercise", prepared.release.exercise, repository.get_exercise, repository.add_exercise
        )
        session.flush()
        created_resolver = _ensure_exact(
            "resolver policy",
            prepared.release.resolver_policy,
            repository.get_exercise_resolver_policy,
            repository.add_exercise_resolver_policy,
        )
        created_allocation = _ensure_exact(
            "allocation policy",
            prepared.release.allocation_policy,
            repository.get_resource_allocation_policy,
            repository.add_resource_allocation_policy,
        )
        created_decision = _ensure_exact(
            "decision record",
            decision,
            repository.get_decision_record,
            repository.add_decision_record,
        )
        session.commit()
    except ResourceGovernanceCandidateConflictError:
        session.rollback()
        raise
    except (
        DomainIntegrityError,
        EvidenceAuthorityEvaluationError,
        EvidenceAuthorityNotReadyError,
        IntegrityError,
    ) as error:
        session.rollback()
        raise ResourceGovernanceCandidateConflictError(str(error)) from error
    except Exception:
        session.rollback()
        raise
    return ResourceGovernanceRatificationResult(
        candidate_id=CANDIDATE_ID,
        candidate_content_digest=prepared.presentation.content_digest,
        created_claim=created_claim,
        created_evidence_review=created_review,
        created_equipment=created_equipment,
        created_exercise=created_exercise,
        created_resolver_policy=created_resolver,
        created_allocation_policy=created_allocation,
        decision_record_created=created_decision,
        equipment=prepared.release.equipment,
        exercise=prepared.release.exercise,
        resolver_policy=prepared.release.resolver_policy,
        allocation_policy=prepared.release.allocation_policy,
    )


@lru_cache
def _prepared_candidate() -> PreparedResourceGovernanceCandidate:
    source = prepared_acsm_resistance_training_source()
    prepared_at = datetime(2026, 9, 10, 17, 0, tzinfo=UTC)
    claim = EvidenceClaim(
        id=EVIDENCE_CLAIM_ID,
        created_at=prepared_at - timedelta(minutes=10),
        claim="The ACSM overview's primary recommendation is high-effort resistance training at least twice weekly, engaging all major muscle groups; many resistance-training forms can improve function.",
        domain="resistance_training_frequency",
        population="Healthy adults aged 18 years or older, with much of the synthesized evidence from inexperienced trainees.",
        intervention="Progressive resistance training lasting at least six weeks and at least twelve exposures in the review eligibility criteria.",
        comparator="No exercise or distinct resistance-training prescriptions, depending on the underlying review.",
        outcome="Muscle function and physical performance, including muscular endurance and chair-stand performance.",
        study_design="ACSM position stand using an overview of systematic reviews of randomized trials",
        duration="Eligible resistance-training programs lasted at least six weeks.",
        effect_direction="Resistance training improved multiple muscle-function and physical-performance outcomes.",
        uncertainty="The recommendation supports resistance-training type and at-least-twice-weekly frequency. It does not validate one exercise, exact sets or repetitions, weekly minutes, resolver weights, or allocation weights.",
        limitations=(
            "The overview combines heterogeneous populations, outcomes, and prescriptions.",
            "Its overview method does not estimate comparative effectiveness of complete programs.",
            "Chair-stand improvement does not prove that one selected exercise is optimal or guarantee individual response.",
        ),
        evidence_strength=EvidenceStrength.HIGH,
        athlete_applicability=Applicability.MODERATE,
        applicability_notes="Directionally relevant to a healthy-adult owner alpha; current session safety, environment feasibility, dose review, and observed response remain controlling.",
        source_identifiers=source.source_identifiers,
        source_record_ids=(source.id,),
        reviewer="Codex evidence synthesis candidate; authority pending",
        claim_version="acsm-resistance-training-frequency-function@1.0.0",
    )
    equipment = Equipment(
        id=EQUIPMENT_ID,
        created_at=prepared_at,
        name="Stable chair",
        category="support",
        capabilities={"stable_seat": True, "sit_to_stand_support": True},
    )
    exercise = Exercise(
        id=EXERCISE_ID,
        created_at=prepared_at,
        name="Chair sit-to-stand",
        movement_patterns=(MovementPattern.KNEE_DOMINANT,),
        primary_adaptation_ids=(ADAPTATION_ID,),
        joint_demands=(JointRegion.ANKLE, JointRegion.KNEE, JointRegion.HIP),
        equipment_requirement_ids=(EQUIPMENT_ID,),
        loading_type=LoadingType.BODYWEIGHT,
        laterality=Laterality.BILATERAL,
        loadability=Loadability.LIMITED,
        skill_complexity=CostLevel.LOW,
        impact_level=ImpactLevel.NONE,
        velocity_characteristics=(VelocityCharacteristic.CONTROLLED,),
        stability_demand=CostLevel.LOW,
        fatigue_cost=CostLevel.LOW,
        soreness_cost=CostLevel.LOW,
        minimum_floor_area_m2=2,
        noise_level=CostLevel.LOW,
        measurement_methods=("controlled repetitions",),
    )
    resolver = ExerciseResolverPolicy(
        id=RESOLVER_POLICY_ID,
        created_at=prepared_at,
        adaptation_role_weight=1,
        movement_pattern_weight=0,
        loading_type_weight=0,
        loadability_weight=0,
        velocity_weight=0,
        laterality_weight=0,
        secondary_adaptation_credit=0,
        partial_match_threshold=1,
        full_match_threshold=1,
        max_ranked_candidates=1,
        policy_version="owner-alpha-exact-primary-match@1.0.0",
    )
    allocation = ResourceAllocationPolicy(
        id=ALLOCATION_POLICY_ID,
        created_at=prepared_at,
        develop_weight=1,
        maintain_weight=0,
        expose_weight=0,
        allow_partial_exercise_resolution=False,
        policy_version="owner-alpha-single-develop-allocation@1.0.0",
    )
    release = PreparedResourceGovernanceRelease(
        prepared_at=prepared_at,
        claim=claim,
        evidence_review_content={
            "source_verification_rationale": "The full PMC text and PubMed metadata for PMID 41843416 were checked for population, review eligibility, chair-stand outcome, and the authors' primary frequency recommendation.",
            "extraction_rationale": "The claim retains broad resistance-training direction and at-least-twice-weekly frequency while excluding unsupported exercise, minute, set, repetition, and policy conclusions.",
            "evidence_strength_rationale": "A current professional position stand synthesizing 137 systematic reviews strongly supports the broad claim; heterogeneity limits program-specific inference.",
            "applicability_rationale": "The healthy-adult evidence is directionally applicable to the owner alpha, subject to current safety and individualized feasibility.",
            "uncertainty": "This review does not approve a complete workout, medical clearance, or the engineering policy constants.",
            "conflict_disclosure": "No conflict was identified by the reviewing agent; source-author disclosures require dedicated review before broader production use.",
            "review_version": "evidence-review-acsm-frequency-function@1.0.0",
        },
        equipment=equipment,
        exercise=exercise,
        resolver_policy=resolver,
        allocation_policy=allocation,
        release_rationale="Provide exact, inspectable first-block support artifacts so the owner is not asked to invent equipment ontology, exercise metadata, resolver weights, or allocation weights.",
        release_uncertainty="The chair sit-to-stand is one conservative, assessment-proximal candidate and may produce test-specific learning. The policies are engineering constraints, not scientific optima. No dose, block, week, or session is created.",
    )
    fields = {
        "candidate_version": CANDIDATE_VERSION,
        "candidate_id": CANDIDATE_ID,
        "prepared_at": prepared_at,
        "release_label": "First owner-alpha resource authorities",
        "summary": "A narrow bundle for resolving one muscular-endurance priority to a stable-chair exercise without allowing a partial substitute or asking the owner to author policy numbers.",
        "exact_artifacts": (
            f"Equipment: {equipment.name} ({equipment.id})",
            f"Exercise: {exercise.name} ({exercise.id})",
            f"Resolver: {resolver.policy_version} ({resolver.id})",
            f"Allocator: {allocation.policy_version} ({allocation.id})",
        ),
        "governs": (
            "The exact stable-chair equipment and chair sit-to-stand ontology records.",
            "A resolver that requires an exact primary-adaptation and full constraint match.",
            "A one-DEVELOP-priority allocator that refuses partial exercise resolution.",
        ),
        "does_not_establish": (
            "That a stable chair is currently available in Courtney's selected environment.",
            "Medical clearance, current session readiness, technique quality, pain tolerance, or exercise safety.",
            "Sets, repetitions, effort target, rest, weekly minutes, progression, or a workout.",
        ),
        "operational_choices": (
            "Chair sit-to-stand is modeled as bilateral, bodyweight, controlled, knee-dominant, low-skill, no-impact, and low cost.",
            "Only a primary adaptation match contributes resolver score; every constraint must still match for FULL status.",
            "Partial exercise resolutions are not allocatable in the first owner-alpha block.",
            "The single DEVELOP priority receives all available allocation weight.",
        ),
        "unresolved_limitations": (
            "Exercise metadata is a reviewed engineering ontology assertion, not proof of superiority.",
            "Assessment-proximal training may improve test familiarity as well as underlying capacity.",
            "The athlete must separately report stable-chair availability before resolution.",
            "A later prepared resource demand and dose authority are still required.",
        ),
        "evidence": (
            ResourceGovernanceEvidenceSummary(
                title="ACSM resistance-training position stand (2026)",
                source_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC12965823/",
                population="Healthy adults across 137 systematic reviews; much evidence involved novice participants.",
                finding="Resistance training improved muscular endurance and chair-stand performance; the primary recommendation is high-effort resistance training at least twice weekly.",
                limitations=(
                    "The source does not identify chair sit-to-stand as an optimal exercise.",
                    "The source does not validate the resolver or allocator constants.",
                    "A complete dose and current safety decision remain separate.",
                ),
            ),
        ),
    }
    canonical = json.dumps(
        {"presentation": fields, "release": release.model_dump(mode="json")},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    presentation = ResourceGovernanceCandidate(
        **fields,
        content_digest=f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}",
    )
    return PreparedResourceGovernanceCandidate(presentation=presentation, release=release)


def _ensure_exact[Record: VersionedRecord](
    label: str,
    expected: Record,
    getter: Callable[[UUID], Record | None],
    adder: Callable[[Record], None],
) -> bool:
    existing = getter(expected.id)
    if existing is None:
        adder(expected)
        return True
    if existing != expected:
        raise ResourceGovernanceCandidateConflictError(
            f"persisted {label} {expected.id} differs from the prepared release"
        )
    return False


def _existing_result(
    repository: DomainRepository,
    prepared: PreparedResourceGovernanceCandidate,
    decision: DecisionRecord,
) -> ResourceGovernanceRatificationResult:
    if f"candidate_content_digest:{prepared.presentation.content_digest}" not in decision.evidence:
        raise ResourceGovernanceCandidateConflictError(
            "candidate release identity is occupied by different immutable content"
        )
    release = prepared.release
    if (
        repository.get_evidence_source(release.claim.source_record_ids[0])
        != prepared_acsm_resistance_training_source()
        or repository.get_adaptation(ADAPTATION_ID) is None
    ):
        raise ResourceGovernanceCandidateConflictError(
            "persisted resource-governance release has incomplete prerequisites"
        )
    records = (
        repository.get_evidence_claim(release.claim.id),
        repository.get_evidence_claim_review(EVIDENCE_REVIEW_ID),
        repository.get_equipment(release.equipment.id),
        repository.get_exercise(release.exercise.id),
        repository.get_exercise_resolver_policy(release.resolver_policy.id),
        repository.get_resource_allocation_policy(release.allocation_policy.id),
    )
    if records[0] != release.claim or any(item is None for item in records[1:]):
        raise ResourceGovernanceCandidateConflictError(
            "persisted resource-governance release has incomplete lineage"
        )
    if records[2:] != (
        release.equipment,
        release.exercise,
        release.resolver_policy,
        release.allocation_policy,
    ):
        raise ResourceGovernanceCandidateConflictError(
            "persisted resource-governance artifacts differ from the prepared release"
        )
    return ResourceGovernanceRatificationResult(
        candidate_id=CANDIDATE_ID,
        candidate_content_digest=prepared.presentation.content_digest,
        created_claim=False,
        created_evidence_review=False,
        created_equipment=False,
        created_exercise=False,
        created_resolver_policy=False,
        created_allocation_policy=False,
        decision_record_created=False,
        equipment=release.equipment,
        exercise=release.exercise,
        resolver_policy=release.resolver_policy,
        allocation_policy=release.allocation_policy,
    )
