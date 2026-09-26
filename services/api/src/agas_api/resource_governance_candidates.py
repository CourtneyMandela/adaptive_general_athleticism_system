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
    EvidenceSource,
    EvidenceSourceIdentifier,
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
    TrainingPriorityState,
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
PUSHUP_CANDIDATE_ID = UUID("98600000-0000-4000-8000-000000000002")
EVIDENCE_CLAIM_ID = UUID("91000000-0000-4000-8000-000000000005")
EVIDENCE_REVIEW_ID = UUID("91100000-0000-4000-8000-000000000005")
PUSHUP_EVIDENCE_CLAIM_ID = UUID("91000000-0000-4000-8000-000000000007")
PUSHUP_EVIDENCE_REVIEW_ID = UUID("91100000-0000-4000-8000-000000000007")
JUMP_CANDIDATE_ID = UUID("98600000-0000-4000-8000-000000000003")
JUMP_MAINTENANCE_CANDIDATE_ID = UUID("98600000-0000-4000-8000-000000000004")
JUMP_SOURCE_ID = UUID("91400000-0000-4000-8000-000000000001")
JUMP_EVIDENCE_CLAIM_ID = UUID("91410000-0000-4000-8000-000000000001")
JUMP_EVIDENCE_REVIEW_ID = UUID("91420000-0000-4000-8000-000000000001")
JUMP_MAINTENANCE_EVIDENCE_CLAIM_ID = UUID("91410000-0000-4000-8000-000000000002")
JUMP_MAINTENANCE_EVIDENCE_REVIEW_ID = UUID("91420000-0000-4000-8000-000000000002")
AEROBIC_CANDIDATE_ID = UUID("91900000-0000-4000-8000-000000000001")
AEROBIC_SOURCE_ID = UUID("91910000-0000-4000-8000-000000000001")
AEROBIC_EVIDENCE_CLAIM_ID = UUID("91920000-0000-4000-8000-000000000001")
AEROBIC_EVIDENCE_REVIEW_ID = UUID("91930000-0000-4000-8000-000000000001")
EQUIPMENT_ID = UUID("e1000000-0000-4000-8000-000000000001")
EXERCISE_ID = UUID("b1000000-0000-4000-8000-000000000001")
PUSHUP_EXERCISE_ID = UUID("b1000000-0000-4000-8000-000000000002")
RESOLVER_POLICY_ID = UUID("98700000-0000-4000-8000-000000000001")
PUSHUP_RESOLVER_POLICY_ID = UUID("98700000-0000-4000-8000-000000000002")
ALLOCATION_POLICY_ID = UUID("98800000-0000-4000-8000-000000000001")
PUSHUP_ALLOCATION_POLICY_ID = UUID("98800000-0000-4000-8000-000000000002")
ADAPTATION_ID = UUID("a0000000-0000-4000-8000-000000000004")
EXPLOSIVE_POWER_ADAPTATION_ID = UUID("a0000000-0000-4000-8000-000000000003")
JUMP_EXERCISE_ID = UUID("b0000000-0000-4000-8000-000000000012")
JUMP_RESOLVER_POLICY_ID = UUID("91430000-0000-4000-8000-000000000001")
JUMP_ALLOCATION_POLICY_ID = UUID("91440000-0000-4000-8000-000000000001")
JUMP_MAINTENANCE_ALLOCATION_POLICY_ID = UUID("91440000-0000-4000-8000-000000000002")
AEROBIC_ADAPTATION_ID = UUID("a0000000-0000-4000-8000-000000000002")
AEROBIC_EXERCISE_ID = UUID("b0000000-0000-4000-8000-000000000009")
AEROBIC_RESOLVER_POLICY_ID = UUID("91940000-0000-4000-8000-000000000001")
AEROBIC_ALLOCATION_POLICY_ID = UUID("91950000-0000-4000-8000-000000000001")
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
    created_source: bool
    created_claim: bool
    created_evidence_review: bool
    created_equipment: bool
    created_exercise: bool
    created_resolver_policy: bool
    created_allocation_policy: bool
    decision_record_created: bool
    equipment: Equipment | None
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
    source: EvidenceSource | None = None
    claim: EvidenceClaim
    evidence_review_content: dict[str, str]
    equipment: Equipment | None
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


def prepared_resource_governance_candidates() -> tuple[PreparedResourceGovernanceCandidate, ...]:
    """Return every immutable resource release, preserving the historical chair release."""

    return (
        _prepared_candidate(),
        _prepared_pushup_candidate(),
        _prepared_jump_candidate(),
        _prepared_jump_maintenance_candidate(),
        _prepared_aerobic_candidate(),
    )


def prepared_resource_governance_candidate_for_scope(
    estimate_scope: str,
    priority_state: TrainingPriorityState | None = None,
) -> PreparedResourceGovernanceCandidate:
    if estimate_scope == "assessment_specific:maximum_consecutive_standard_pushup_repetitions":
        return _prepared_pushup_candidate()
    if estimate_scope == "assessment_specific:thirty_second_chair_stand_repetitions":
        return _prepared_candidate()
    if estimate_scope == "assessment_specific:countermovement_vertical_jump_height_cm":
        if priority_state is TrainingPriorityState.MAINTAIN:
            return _prepared_jump_maintenance_candidate()
        return _prepared_jump_candidate()
    if estimate_scope == "assessment_specific:twelve_minute_walk_run_distance_m":
        return _prepared_aerobic_candidate()
    raise KeyError(f"no resource-governance candidate is registered for {estimate_scope}")


def list_resource_governance_candidates(
    session: Session, *, projected_at: datetime | None = None
) -> ResourceGovernanceCandidateProjection:
    instant = projected_at or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("resource-governance projection time must include a timezone")
    repository = DomainRepository(session)
    items: list[ResourceGovernanceCandidateItem] = []
    for prepared in prepared_resource_governance_candidates():
        decision = repository.get_decision_record(prepared.presentation.candidate_id)
        source = repository.get_evidence_source(prepared.release.claim.source_record_ids[0])
        source_is_required_prerequisite = prepared.release.source is None
        issues: tuple[str, ...]
        prerequisite_issues = tuple(
            issue
            for missing, issue in (
                (
                    source_is_required_prerequisite and source is None,
                    "Approve the prepared deficit-only planning policy first so its exact ACSM source snapshot exists.",
                ),
                (
                    any(
                        repository.get_adaptation(adaptation_id) is None
                        for adaptation_id in prepared.release.exercise.primary_adaptation_ids
                    ),
                    "Import the controlled seed catalog so the exact primary adaptation exists.",
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
        elif (
            f"candidate_content_digest:{prepared.presentation.content_digest}" in decision.evidence
        ):
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
        items.append(
            ResourceGovernanceCandidateItem(
                candidate=prepared.presentation,
                status=status,
                ratified_at=ratified_at,
                issues=issues,
            )
        )
    return ResourceGovernanceCandidateProjection(
        projected_at=instant,
        items=tuple(items),
    )


def ratify_resource_governance_candidate(
    session: Session,
    candidate_id: UUID,
    command: RatifyResourceGovernanceCandidateCommand,
    authority: AuthorizedRole,
    *,
    ratified_at: datetime | None = None,
) -> ResourceGovernanceRatificationResult:
    prepared = next(
        (
            item
            for item in prepared_resource_governance_candidates()
            if item.presentation.candidate_id == candidate_id
        ),
        None,
    )
    if prepared is None:
        raise KeyError("resource-governance candidate does not exist")
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
    existing_decision = repository.get_decision_record(candidate_id)
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
    expected_source = _expected_source(prepared)
    if (
        prepared.release.source is None
        and repository.get_evidence_source(source_id) != expected_source
    ):
        raise ResourceGovernanceCandidateValidationError(
            "the exact prerequisite evidence source is unavailable"
        )
    if any(
        repository.get_adaptation(adaptation_id) is None
        for adaptation_id in prepared.release.exercise.primary_adaptation_ids
    ):
        raise ResourceGovernanceCandidateValidationError(
            "the exact primary adaptation is unavailable; import the controlled catalog first"
        )
    reviewer = f"account:{authority.account_id}"
    review = EvidenceClaimReview(
        id=_evidence_review_id(prepared),
        created_at=instant,
        evidence_claim_id=prepared.release.claim.id,
        decision=EvidenceReviewDecision.APPROVED,
        sequence_number=1,
        reviewed_at=instant,
        reviewer=reviewer,
        **prepared.release.evidence_review_content,
    )
    decision = DecisionRecord(
        id=candidate_id,
        created_at=instant,
        decision=f"Ratified owner-alpha resource-governance bundle {prepared.presentation.release_label}.",
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
            f"evidence_source_id:{source_id}",
            f"evidence_claim_id:{prepared.release.claim.id}",
            f"evidence_review_id:{review.id}",
            *(
                (f"equipment_id:{prepared.release.equipment.id}",)
                if prepared.release.equipment is not None
                else ()
            ),
            f"exercise_id:{prepared.release.exercise.id}",
            f"exercise_resolver_policy_id:{prepared.release.resolver_policy.id}",
            f"resource_allocation_policy_id:{prepared.release.allocation_policy.id}",
        ),
        uncertainty=prepared.release.release_uncertainty,
        decision_version="resource-governance-ratification@1.0.0",
        decided_on=instant.date(),
    )
    try:
        if prepared.release.source is None:
            created_source = False
        else:
            created_source = _ensure_exact(
                "evidence source",
                prepared.release.source,
                repository.get_evidence_source,
                repository.add_evidence_source,
            )
            session.flush()
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
        if prepared.release.equipment is None:
            created_equipment = False
        else:
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
        candidate_id=candidate_id,
        candidate_content_digest=prepared.presentation.content_digest,
        created_source=created_source,
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
        {"presentation": fields, "release": _release_digest_payload(release)},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    presentation = ResourceGovernanceCandidate(
        **fields,
        content_digest=f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}",
    )
    return PreparedResourceGovernanceCandidate(presentation=presentation, release=release)


@lru_cache
def _prepared_pushup_candidate() -> PreparedResourceGovernanceCandidate:
    source = prepared_acsm_resistance_training_source()
    prepared_at = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
    claim = EvidenceClaim(
        id=PUSHUP_EVIDENCE_CLAIM_ID,
        created_at=prepared_at - timedelta(minutes=10),
        claim="Progressive resistance training performed at least twice weekly can improve muscular endurance in healthy adults; this broad evidence does not establish standard push-ups as a superior exercise or validate an exact starting dose.",
        domain="resistance_training_frequency",
        population="Healthy adults aged 18 years or older, with much of the synthesized evidence from inexperienced trainees.",
        intervention="Progressive resistance training lasting at least six weeks and at least twelve exposures in the review eligibility criteria.",
        comparator="No exercise or distinct resistance-training prescriptions, depending on the underlying review.",
        outcome="Muscle function and physical performance, including muscular endurance.",
        study_design="ACSM position stand using an overview of systematic reviews of randomized trials",
        duration="Eligible resistance-training programs lasted at least six weeks.",
        effect_direction="Resistance training improved multiple muscle-function and physical-performance outcomes.",
        uncertainty="The recommendation supports resistance-training direction and at-least-twice-weekly frequency. It does not validate standard push-ups, exact sets or repetitions, weekly minutes, resolver weights, or allocation weights.",
        limitations=(
            "The overview combines heterogeneous populations, outcomes, exercises, and prescriptions.",
            "Its overview method does not estimate comparative effectiveness of complete programs.",
            "Broad muscular-endurance improvement does not prove that standard push-ups are optimal or guarantee individual response.",
        ),
        evidence_strength=EvidenceStrength.HIGH,
        athlete_applicability=Applicability.MODERATE,
        applicability_notes="Directionally relevant to a healthy-adult owner alpha; current session safety, exact movement feasibility, dose review, and observed response remain controlling.",
        source_identifiers=source.source_identifiers,
        source_record_ids=(source.id,),
        reviewer="Codex evidence synthesis candidate; authority pending",
        claim_version="acsm-resistance-training-muscular-endurance@1.0.0",
    )
    exercise = Exercise(
        id=PUSHUP_EXERCISE_ID,
        created_at=prepared_at,
        name="Standard push-up",
        movement_patterns=(MovementPattern.HORIZONTAL_PUSH,),
        primary_adaptation_ids=(ADAPTATION_ID,),
        joint_demands=(JointRegion.WRIST, JointRegion.ELBOW, JointRegion.SHOULDER),
        equipment_requirement_ids=(),
        loading_type=LoadingType.BODYWEIGHT,
        laterality=Laterality.BILATERAL,
        loadability=Loadability.LIMITED,
        skill_complexity=CostLevel.LOW,
        impact_level=ImpactLevel.NONE,
        velocity_characteristics=(VelocityCharacteristic.CONTROLLED,),
        stability_demand=CostLevel.MODERATE,
        fatigue_cost=CostLevel.MODERATE,
        soreness_cost=CostLevel.MODERATE,
        minimum_floor_area_m2=2,
        noise_level=CostLevel.LOW,
        measurement_methods=("valid consecutive repetitions",),
    )
    resolver = ExerciseResolverPolicy(
        id=PUSHUP_RESOLVER_POLICY_ID,
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
        policy_version="owner-alpha-pushup-exact-primary-match@1.0.0",
    )
    allocation = ResourceAllocationPolicy(
        id=PUSHUP_ALLOCATION_POLICY_ID,
        created_at=prepared_at,
        develop_weight=1,
        maintain_weight=1,
        expose_weight=0,
        allow_partial_exercise_resolution=False,
        policy_version="owner-alpha-single-active-pushup-allocation@1.0.0",
    )
    release = PreparedResourceGovernanceRelease(
        prepared_at=prepared_at,
        claim=claim,
        evidence_review_content={
            "source_verification_rationale": "The full PMC text and PubMed metadata for PMID 41843416 were checked for population, review eligibility, muscular-endurance outcomes, and the authors' primary frequency recommendation.",
            "extraction_rationale": "The claim retains broad resistance-training direction and at-least-twice-weekly frequency while excluding unsupported exercise, minute, set, repetition, and policy conclusions.",
            "evidence_strength_rationale": "A current professional position stand synthesizing 137 systematic reviews strongly supports the broad claim; heterogeneity limits program-specific inference.",
            "applicability_rationale": "The healthy-adult evidence is directionally applicable to the owner alpha, subject to current safety, exact push-up feasibility, and individualized response.",
            "uncertainty": "This review does not approve a complete workout, medical clearance, the push-up exercise choice, or the engineering policy constants.",
            "conflict_disclosure": "No conflict was identified by the reviewing agent; source-author disclosures require dedicated review before broader production use.",
            "review_version": "evidence-review-acsm-muscular-endurance@1.0.0",
        },
        equipment=None,
        exercise=exercise,
        resolver_policy=resolver,
        allocation_policy=allocation,
        release_rationale="Provide exact, inspectable no-equipment push-up resource artifacts for the owner-alpha pathway without asking the owner to author ontology, resolver, or allocation constants.",
        release_uncertainty="Standard push-up is assessment-proximal and may produce test-specific learning. The ontology and policies are engineering choices, not proof of exercise superiority. No dose, block, week, or session is created.",
    )
    fields = {
        "candidate_version": CANDIDATE_VERSION,
        "candidate_id": PUSHUP_CANDIDATE_ID,
        "prepared_at": prepared_at,
        "release_label": "Owner-alpha push-up resource authorities",
        "summary": "A narrow no-equipment bundle for resolving the governed push-up muscular-endurance priority while preserving both DEVELOP and MAINTAIN paths.",
        "exact_artifacts": (
            f"Exercise: {exercise.name} ({exercise.id})",
            f"Resolver: {resolver.policy_version} ({resolver.id})",
            f"Allocator: {allocation.policy_version} ({allocation.id})",
        ),
        "governs": (
            "The exact standard push-up ontology record with no equipment requirement.",
            "A resolver that requires an exact primary-adaptation and full constraint match.",
            "A single-active-priority allocator that can resource either DEVELOP or MAINTAIN without treating maintenance as no training.",
        ),
        "does_not_establish": (
            "That the athlete can currently perform a standard push-up safely or with valid technique.",
            "Medical clearance, current session readiness, pain tolerance, or exercise safety.",
            "Sets, repetitions, effort target, rest, weekly minutes, progression, or a workout.",
        ),
        "operational_choices": (
            "Standard push-up is modeled as bilateral, bodyweight, controlled, horizontal-push, low-skill, no-impact, and moderate stability/fatigue cost.",
            "Only a primary adaptation match contributes resolver score; every constraint must still match for FULL status.",
            "Partial exercise resolutions are not allocatable in the owner-alpha path.",
            "The sole active priority receives equal allocation weight whether its state is DEVELOP or MAINTAIN.",
        ),
        "unresolved_limitations": (
            "Exercise metadata is a reviewed engineering ontology assertion, not proof of superiority.",
            "Assessment-proximal training may improve test familiarity as well as underlying capacity.",
            "Wrist, elbow, shoulder, trunk-control, and floor-access constraints still require current review.",
            "A separate dose authority is required before a session can be built.",
        ),
        "evidence": (
            ResourceGovernanceEvidenceSummary(
                title="ACSM resistance-training position stand (2026)",
                source_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC12965823/",
                population="Healthy adults across 137 systematic reviews; much evidence involved novice participants.",
                finding="Resistance training improved muscular endurance; the primary recommendation includes high-effort resistance training at least twice weekly.",
                limitations=(
                    "The source does not identify standard push-up as an optimal exercise.",
                    "The source does not validate the resolver or allocator constants.",
                    "A complete dose and current safety decision remain separate.",
                ),
            ),
        ),
    }
    canonical = json.dumps(
        {"presentation": fields, "release": _release_digest_payload(release)},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    presentation = ResourceGovernanceCandidate(
        **fields,
        content_digest=f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}",
    )
    return PreparedResourceGovernanceCandidate(presentation=presentation, release=release)


@lru_cache
def _prepared_jump_candidate() -> PreparedResourceGovernanceCandidate:
    source_created_at = datetime(2026, 9, 23, 15, 0, tzinfo=UTC)
    prepared_at = datetime(2026, 9, 23, 15, 30, tzinfo=UTC)
    pmid = EvidenceSourceIdentifier(scheme="pmid", value="31136014")
    doi = EvidenceSourceIdentifier(scheme="doi", value="10.1111/sms.13487")
    source = EvidenceSource(
        id=JUMP_SOURCE_ID,
        created_at=source_created_at,
        title=(
            "Effects of plyometric training on jumping, sprint performance, and lower body "
            "muscle strength in healthy adults: A systematic review and meta-analyses"
        ),
        authors=("Mikkel Oxfeldt", "Kristian Overgaard", "Lars G Hvid", "Ulrik Dalgas"),
        journal="Scandinavian Journal of Medicine & Science in Sports",
        publication_year=2019,
        publication_types=("Systematic Review", "Meta-Analysis"),
        primary_identifier=pmid,
        source_identifiers=(pmid, doi),
        metadata_provider="pubmed",
        retrieval_uri="https://pubmed.ncbi.nlm.nih.gov/31136014/",
        retrieval_query="PMID 31136014",
        retrieved_at=source_created_at,
        metadata_version="pubmed-record-snapshot@2026-09-23",
        provenance_notes=(
            "Title, authors, journal, publication year, DOI, eligibility criteria, study count, intervention duration, and abstract conclusions were checked against the PubMed record.",
            "The abstract is intentionally not copied into the stored snapshot.",
            "This release uses the review for broad intervention-to-outcome direction, not for an exact exercise dose or safety threshold.",
        ),
    )
    claim = EvidenceClaim(
        id=JUMP_EVIDENCE_CLAIM_ID,
        created_at=source_created_at + timedelta(minutes=10),
        claim=(
            "Lower-body plyometric training lasting 4 to 12 weeks produced a small-to-moderate "
            "positive effect on jump performance in healthy recreationally active adults or athletes."
        ),
        domain="explosive_power_training",
        population="Healthy adults aged 18 years or older who were recreationally active or athletes.",
        intervention="Lower-body plyometric training lasting at least four weeks.",
        comparator="Training or non-training control groups in the included studies.",
        outcome="Jump performance, with separate meta-analyses also covering sprint time and lower-body muscle strength.",
        study_design="Systematic review and meta-analyses of controlled interventions",
        duration="Included interventions lasted 4 to 12 weeks.",
        effect_direction="Plyometric training had a small-to-moderate positive effect on jump performance across included studies.",
        uncertainty=(
            "The pooled result supports the broad intervention direction, not one exercise, starting "
            "contact count, weekly frequency, progression cap, or individual response."
        ),
        limitations=(
            "Participants and plyometric programs were heterogeneous.",
            "The abstract does not establish a minimum safe starting volume or readiness threshold.",
            "A pooled performance effect cannot establish that countermovement jumps are optimal for this athlete.",
        ),
        evidence_strength=EvidenceStrength.MODERATE,
        athlete_applicability=Applicability.MODERATE,
        applicability_notes=(
            "The healthy-adult and recreationally active populations are directionally relevant, but "
            "current impact exposure, symptoms, environment, technique, and observed response remain controlling."
        ),
        source_identifiers=source.source_identifiers,
        source_record_ids=(source.id,),
        reviewer="Codex evidence synthesis candidate; authority pending",
        claim_version="oxfeldt-plyometric-jump-performance@1.0.0",
    )
    exercise = Exercise(
        id=JUMP_EXERCISE_ID,
        created_at=datetime(2026, 8, 19, 14, 0, tzinfo=UTC),
        name="Countermovement jump",
        movement_patterns=(MovementPattern.JUMP,),
        primary_adaptation_ids=(EXPLOSIVE_POWER_ADAPTATION_ID,),
        joint_demands=(JointRegion.ANKLE, JointRegion.KNEE, JointRegion.HIP),
        equipment_requirement_ids=(UUID("e0000000-0000-4000-8000-000000000008"),),
        loading_type=LoadingType.BALLISTIC,
        laterality=Laterality.BILATERAL,
        loadability=Loadability.LIMITED,
        skill_complexity=CostLevel.MODERATE,
        impact_level=ImpactLevel.MODERATE,
        velocity_characteristics=(VelocityCharacteristic.EXPLOSIVE,),
        stability_demand=CostLevel.MODERATE,
        fatigue_cost=CostLevel.MODERATE,
        soreness_cost=CostLevel.LOW,
        minimum_floor_area_m2=5,
        noise_level=CostLevel.MODERATE,
        measurement_methods=("jump height",),
    )
    resolver = ExerciseResolverPolicy(
        id=JUMP_RESOLVER_POLICY_ID,
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
        policy_version="owner-alpha-jump-exact-primary-match@1.0.0",
    )
    allocation = ResourceAllocationPolicy(
        id=JUMP_ALLOCATION_POLICY_ID,
        created_at=prepared_at,
        develop_weight=1,
        maintain_weight=0,
        expose_weight=0,
        allow_partial_exercise_resolution=False,
        policy_version="owner-alpha-single-develop-jump-allocation@1.0.0",
    )
    release = PreparedResourceGovernanceRelease(
        prepared_at=prepared_at,
        source=source,
        claim=claim,
        evidence_review_content={
            "source_verification_rationale": "The PubMed record for PMID 31136014 was checked for source identity, adult population, controlled-intervention eligibility, study count, intervention duration, outcomes, and abstract conclusion.",
            "extraction_rationale": "The claim retains only the broad direction that multiweek lower-body plyometric training can improve jump performance and excludes exact exercise, dose, readiness, and progression conclusions.",
            "evidence_strength_rationale": "Moderate reflects a systematic review and meta-analyses of 25 controlled studies, reduced from high because intervention and population heterogeneity limit program-specific inference.",
            "applicability_rationale": "Moderate reflects healthy adult recreational and athletic samples that are directionally relevant but not established as equivalent to the owner-alpha athlete.",
            "uncertainty": "The source cannot determine the athlete's safe starting contact count, optimal modality, or likely individual response.",
            "conflict_disclosure": "No conflict disclosure was evaluated beyond the accessible PubMed record; this requires dedicated source review before broader production use.",
            "review_version": "oxfeldt-plyometric-jump-performance-review@1.0.0",
        },
        equipment=None,
        exercise=exercise,
        resolver_policy=resolver,
        allocation_policy=allocation,
        release_rationale=(
            "Provide exact, inspectable explosive-power resource artifacts so a governed jump-height "
            "deficit can resolve to the existing countermovement-jump ontology record without hidden defaults."
        ),
        release_uncertainty=(
            "The broad intervention direction is evidence-linked, while exercise selection and policy "
            "weights remain reviewable engineering choices. No dose, block, week, or session is created."
        ),
    )
    fields = {
        "candidate_version": CANDIDATE_VERSION,
        "candidate_id": JUMP_CANDIDATE_ID,
        "prepared_at": prepared_at,
        "release_label": "Owner-alpha explosive-power resource authorities",
        "summary": (
            "A narrow bundle that links a reviewed explosive-power development need to the existing "
            "countermovement-jump exercise while refusing partial substitution or hidden dose defaults."
        ),
        "exact_artifacts": (
            f"Evidence source: PMID 31136014 ({source.id})",
            f"Exercise: {exercise.name} ({exercise.id})",
            f"Resolver: {resolver.policy_version} ({resolver.id})",
            f"Allocator: {allocation.policy_version} ({allocation.id})",
        ),
        "governs": (
            "A reviewed scientific claim that multiweek lower-body plyometric training can improve jump performance in healthy adults.",
            "Reuse of the controlled-catalog countermovement-jump ontology record for an explosive-power DEVELOP priority.",
            "A resolver requiring an exact primary-adaptation match and an allocator refusing partial exercise resolution.",
            "A downstream prepared-demand envelope of 24 weekly minutes across two 12-minute sessions for this exact first fixed-dose path.",
        ),
        "does_not_establish": (
            "Medical clearance, tissue readiness, injury prediction, or permission to ignore concerning symptoms.",
            "That countermovement jumps are superior to other feasible explosive-power modalities.",
            "Sets, contacts, effort target, rest, an athlete-specific schedule, or a workout.",
        ),
        "operational_choices": (
            "The existing countermovement jump remains bilateral, bodyweight-ballistic, explosive, moderate-impact, moderate-skill, and moderate-fatigue.",
            "Only a primary explosive-power adaptation match contributes resolver score; all environment constraints still apply.",
            "Only a DEVELOP priority receives allocation weight in this first fixed-dose path.",
            "The 24-minute, two-session weekly resource envelope is an explicit engineering choice sized to two 12-minute candidate sessions, not a scientific optimum.",
        ),
        "unresolved_limitations": (
            "The source supports a broad plyometric-training direction, not this exact exercise choice.",
            "The athlete's recent jumping exposure and current readiness remain separate controlling gates.",
            "The controlled-catalog exercise requires appropriate floor space and its exact equipment availability must be current.",
            "A separate fixed-dose construction authority is required before a session can be built.",
        ),
        "evidence": (
            ResourceGovernanceEvidenceSummary(
                title="Oxfeldt et al. (2019), lower-body plyometric training in healthy adults",
                source_url="https://pubmed.ncbi.nlm.nih.gov/31136014/",
                population="Healthy adults aged 18 years or older who were recreationally active or athletes.",
                finding="Across 25 included studies, 4-to-12-week lower-body plyometric training showed a small-to-moderate positive effect on jump performance.",
                limitations=(
                    "The source does not identify countermovement jumps as universally optimal.",
                    "The source does not validate a starting contact count or the resolver and allocator constants.",
                    "Current readiness, exposure history, environment feasibility, and individual response remain separate.",
                ),
            ),
        ),
    }
    canonical = json.dumps(
        {"presentation": fields, "release": _release_digest_payload(release)},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    presentation = ResourceGovernanceCandidate(
        **fields,
        content_digest=f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}",
    )
    return PreparedResourceGovernanceCandidate(presentation=presentation, release=release)


@lru_cache(maxsize=1)
def _prepared_jump_maintenance_candidate() -> PreparedResourceGovernanceCandidate:
    """Add a separately reviewable maintenance path without rewriting the DEVELOP authority."""

    develop = _prepared_jump_candidate()
    claim = develop.release.claim.model_copy(
        update={
            "id": JUMP_MAINTENANCE_EVIDENCE_CLAIM_ID,
            "claim_version": "oxfeldt-plyometric-jump-maintenance@1.0.0",
        }
    )
    allocation = ResourceAllocationPolicy(
        id=JUMP_MAINTENANCE_ALLOCATION_POLICY_ID,
        created_at=develop.release.prepared_at,
        develop_weight=1,
        maintain_weight=1,
        expose_weight=0,
        allow_partial_exercise_resolution=False,
        policy_version="owner-alpha-single-maintain-jump-allocation@1.0.0",
    )
    release = develop.release.model_copy(
        update={
            "claim": claim,
            "allocation_policy": allocation,
            "release_rationale": (
                "Provide a distinct, inspectable explosive-power maintenance resource authority "
                "for a reviewed successor strategy that has crossed the provisional jump floor."
            ),
            "release_uncertainty": (
                "The 12-minute maintenance envelope and allocation weight are reviewable engineering "
                "choices, not scientific optima. No dose, block, week, or session is created."
            ),
        }
    )
    fields = develop.presentation.model_dump(exclude={"content_digest"})
    fields.update(
        {
            "candidate_id": JUMP_MAINTENANCE_CANDIDATE_ID,
            "release_label": "Owner-alpha explosive-power maintenance resource authorities",
            "summary": (
                "A narrow successor-cycle bundle that preserves feasible countermovement-jump "
                "exposure after the reviewed jump-height need changes from DEVELOP to MAINTAIN."
            ),
            "exact_artifacts": (
                *develop.presentation.exact_artifacts[:-1],
                f"Allocator: {allocation.policy_version} ({allocation.id})",
            ),
            "governs": (
                "The same reviewed plyometric-training direction and exact countermovement-jump ontology used by the DEVELOP authority.",
                "A resolver requiring the same exact primary-adaptation and full environment match.",
                "A policy with explicit MAINTAIN allocation weight and a downstream 12-minute weekly envelope across two 6-minute scheduling slots.",
            ),
            "operational_choices": (
                "The exercise ontology and environmental feasibility constraints remain unchanged from the reviewed DEVELOP authority.",
                "A MAINTAIN priority receives nonzero allocation weight in this successor path.",
                "The 12-minute, two-session weekly envelope is an explicit engineering maintenance allowance, not a literature-derived dose.",
            ),
            "unresolved_limitations": (
                *develop.presentation.unresolved_limitations,
                "A separate maintenance-dose construction authority is required before a successor week can be built.",
            ),
        }
    )
    canonical = json.dumps(
        {"presentation": fields, "release": _release_digest_payload(release)},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    presentation = ResourceGovernanceCandidate(
        **fields,
        content_digest=f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}",
    )
    return PreparedResourceGovernanceCandidate(presentation=presentation, release=release)


@lru_cache(maxsize=1)
def _prepared_aerobic_candidate() -> PreparedResourceGovernanceCandidate:
    source_created_at = datetime(2026, 9, 25, 15, 10, tzinfo=UTC)
    prepared_at = datetime(2026, 9, 25, 15, 30, tzinfo=UTC)
    pmid = EvidenceSourceIdentifier(scheme="pmid", value="21694556")
    doi = EvidenceSourceIdentifier(scheme="doi", value="10.1249/MSS.0b013e318213fefb")
    source = EvidenceSource(
        id=AEROBIC_SOURCE_ID,
        created_at=source_created_at,
        title=(
            "Quantity and Quality of Exercise for Developing and Maintaining "
            "Cardiorespiratory, Musculoskeletal, and Neuromotor Fitness in Apparently "
            "Healthy Adults: Guidance for Prescribing Exercise"
        ),
        authors=(
            "Carol Ewing Garber",
            "Bryan Blissmer",
            "Michael R Deschenes",
            "Barry A Franklin",
            "Michael J Lamonte",
            "I-Min Lee",
            "David C Nieman",
            "David P Swain",
        ),
        journal="Medicine & Science in Sports & Exercise",
        publication_year=2011,
        publication_types=("Practice Guideline", "Position Stand"),
        primary_identifier=pmid,
        source_identifiers=(pmid, doi),
        metadata_provider="pubmed",
        retrieval_uri="https://pubmed.ncbi.nlm.nih.gov/21694556/",
        retrieval_query="PMID 21694556",
        retrieved_at=source_created_at,
        metadata_version="pubmed-record-snapshot@2026-09-25",
        provenance_notes=(
            "Title, authors, journal, identifiers, population scope, aerobic-exercise direction, individualization language, and abstract conclusions were checked against PubMed.",
            "The abstract is intentionally not copied into the stored snapshot.",
            "This release uses the position stand only for broad aerobic-training direction and individualization, not for its exact owner-alpha duration envelope.",
        ),
    )
    claim = EvidenceClaim(
        id=AEROBIC_EVIDENCE_CLAIM_ID,
        created_at=source_created_at + timedelta(minutes=10),
        claim=(
            "Regular aerobic exercise improves cardiorespiratory fitness in apparently healthy "
            "adults, and exercise prescriptions should be modified according to habitual activity, "
            "physical function, health status, response, and goals; volumes below public-health "
            "targets may still be beneficial."
        ),
        domain="aerobic_training_direction",
        population="Apparently healthy adults.",
        intervention="Regular aerobic exercise prescribed with individualized frequency, intensity, time, and type.",
        comparator="Lower activity or alternative exercise prescriptions across the evidence synthesized by the position stand.",
        outcome="Cardiorespiratory fitness and related health outcomes.",
        study_design="Professional position stand synthesizing available exercise-prescription evidence",
        effect_direction="Regular aerobic exercise improves cardiorespiratory fitness, with benefit possible below the full public-health target.",
        uncertainty=(
            "The source supports broad aerobic-training direction and individualization, not "
            "treadmill superiority, a 24-minute weekly envelope, a 10-minute starting dose, or a one-minute progression."
        ),
        limitations=(
            "The position stand addresses broad apparently healthy adult populations and multiple aerobic modalities.",
            "Population guidance cannot determine this athlete's best modality, safe current intensity, or individual response.",
            "The source does not validate the resolver, allocator, exact duration dose, progression ceiling, or response threshold in this release chain.",
        ),
        evidence_strength=EvidenceStrength.HIGH,
        athlete_applicability=Applicability.MODERATE,
        applicability_notes=(
            "Directionally relevant to an apparently healthy owner-alpha adult, subject to current "
            "readiness, environmental feasibility, lower-body symptoms, modality familiarity, and observed response."
        ),
        source_identifiers=source.source_identifiers,
        source_record_ids=(source.id,),
        reviewer="Codex evidence synthesis candidate; authority pending",
        claim_version="acsm-aerobic-training-direction-individualization@1.0.0",
    )
    exercise = Exercise(
        id=AEROBIC_EXERCISE_ID,
        created_at=datetime(2026, 8, 19, 14, 0, tzinfo=UTC),
        name="Treadmill walk or run",
        movement_patterns=(MovementPattern.CYCLIC, MovementPattern.LOCOMOTION),
        primary_adaptation_ids=(AEROBIC_ADAPTATION_ID,),
        joint_demands=(JointRegion.ANKLE, JointRegion.KNEE, JointRegion.HIP),
        equipment_requirement_ids=(UUID("e0000000-0000-4000-8000-000000000005"),),
        loading_type=LoadingType.CYCLIC,
        laterality=Laterality.ALTERNATING,
        loadability=Loadability.LIMITED,
        skill_complexity=CostLevel.LOW,
        impact_level=ImpactLevel.LOW,
        velocity_characteristics=(VelocityCharacteristic.CONTINUOUS,),
        stability_demand=CostLevel.LOW,
        fatigue_cost=CostLevel.MODERATE,
        soreness_cost=CostLevel.LOW,
        minimum_floor_area_m2=4,
        noise_level=CostLevel.MODERATE,
        measurement_methods=("duration", "distance", "speed"),
    )
    resolver = ExerciseResolverPolicy(
        id=AEROBIC_RESOLVER_POLICY_ID,
        created_at=prepared_at,
        adaptation_role_weight=1,
        movement_pattern_weight=1,
        loading_type_weight=1,
        loadability_weight=0,
        velocity_weight=1,
        laterality_weight=0,
        secondary_adaptation_credit=0,
        partial_match_threshold=0.75,
        full_match_threshold=1,
        max_ranked_candidates=3,
        policy_version="owner-alpha-aerobic-cyclic-resolution@1.0.0",
    )
    allocation = ResourceAllocationPolicy(
        id=AEROBIC_ALLOCATION_POLICY_ID,
        created_at=prepared_at,
        develop_weight=1,
        maintain_weight=0,
        expose_weight=0,
        allow_partial_exercise_resolution=False,
        policy_version="owner-alpha-single-develop-aerobic-allocation@1.0.0",
    )
    release = PreparedResourceGovernanceRelease(
        prepared_at=prepared_at,
        source=source,
        claim=claim,
        evidence_review_content={
            "source_verification_rationale": "The PubMed record for PMID 21694556 was checked for source identity, apparently healthy adult population, aerobic-exercise direction, individualization factors, and the statement that activity below the full recommendation may still be beneficial.",
            "extraction_rationale": "The claim retains only broad aerobic-training direction and the need to individualize while excluding exact modality, duration, intensity, frequency, progression, and response conclusions.",
            "evidence_strength_rationale": "High reflects a professional position stand synthesizing exercise-prescription evidence for apparently healthy adults; exact candidate constants remain outside the claim.",
            "applicability_rationale": "Moderate reflects an adult owner-alpha use case while current readiness, constraints, modality familiarity, and response remain athlete-specific.",
            "uncertainty": "The source cannot determine this athlete's safe starting intensity, preferred modality, adherence, or likely response.",
            "conflict_disclosure": "No conflict disclosure was evaluated beyond the accessible PubMed record; dedicated full-source review is required before broader production use.",
            "review_version": "acsm-aerobic-training-direction-review@1.0.0",
        },
        equipment=None,
        exercise=exercise,
        resolver_policy=resolver,
        allocation_policy=allocation,
        release_rationale=(
            "Provide an exact, inspectable aerobic resource path so a governed 12-minute distance "
            "deficit can resolve to the existing treadmill walk/run ontology record without hidden defaults."
        ),
        release_uncertainty=(
            "The broad aerobic-training direction is evidence-linked, while exercise selection, "
            "resolver weights, and the weekly resource envelope remain reviewable engineering choices. "
            "No duration dose, intensity target, block, week, or session is created."
        ),
    )
    fields = {
        "candidate_version": CANDIDATE_VERSION,
        "candidate_id": AEROBIC_CANDIDATE_ID,
        "prepared_at": prepared_at,
        "release_label": "Owner-alpha aerobic-base resource authorities",
        "summary": (
            "A narrow bundle linking a reviewed aerobic-capacity development need to the existing "
            "treadmill walk/run exercise while refusing partial resolution and hidden dose defaults."
        ),
        "exact_artifacts": (
            f"Evidence source: PMID 21694556 ({source.id})",
            f"Exercise: {exercise.name} ({exercise.id})",
            f"Resolver: {resolver.policy_version} ({resolver.id})",
            f"Allocator: {allocation.policy_version} ({allocation.id})",
        ),
        "governs": (
            "A reviewed scientific claim supporting regular individualized aerobic exercise for apparently healthy adults.",
            "Reuse of the controlled-catalog treadmill walk/run ontology record for an aerobic-base DEVELOP priority.",
            "A resolver requiring a full cyclic locomotion, loading, velocity, adaptation, equipment, and environment match.",
            "A downstream prepared-demand envelope of 24 weekly minutes across two 12-minute scheduling slots for this exact first duration path.",
        ),
        "does_not_establish": (
            "Medical clearance, running readiness, injury prediction, or permission to ignore concerning symptoms.",
            "That treadmill work is superior to other feasible aerobic modalities or equivalent when their stimulus constraints differ.",
            "A speed, grade, heart rate, pace, exact effort, progression, athlete-specific schedule, or workout.",
        ),
        "operational_choices": (
            "The existing treadmill exercise remains cyclic locomotion, alternating, low-impact, continuous, low-skill, and moderate-fatigue.",
            "A full resolution requires the exact treadmill and current floor-space constraints; partial substitution is not silently accepted.",
            "Only an aerobic DEVELOP priority receives allocation weight in this first owner-alpha path.",
            "The 24-minute, two-session weekly envelope is an explicit engineering allowance sized to two 12-minute candidate sessions, not a scientific optimum.",
        ),
        "unresolved_limitations": (
            "The source supports broad aerobic training rather than treadmill superiority or this resource envelope.",
            "The athlete's current readiness, symptoms, and walking or running familiarity remain separate controlling gates.",
            "The controlled-catalog exercise requires a treadmill; infeasibility must remain visible when it is absent.",
            "A separate fixed-duration construction authority is required before a session can be built.",
        ),
        "evidence": (
            ResourceGovernanceEvidenceSummary(
                title="ACSM position stand on exercise quantity and quality (2011)",
                source_url="https://pubmed.ncbi.nlm.nih.gov/21694556/",
                population="Apparently healthy adults.",
                finding="Regular aerobic exercise improves cardiorespiratory fitness, should be individualized, and may provide benefit below the full public-health target.",
                limitations=(
                    "The source does not identify treadmill exercise as universally optimal.",
                    "The source does not validate the 24-minute envelope or resolver and allocator constants.",
                    "Current readiness, environment feasibility, modality familiarity, and individual response remain separate.",
                ),
            ),
        ),
    }
    canonical = json.dumps(
        {"presentation": fields, "release": _release_digest_payload(release)},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    presentation = ResourceGovernanceCandidate(
        **fields,
        content_digest=f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}",
    )
    return PreparedResourceGovernanceCandidate(presentation=presentation, release=release)


def _evidence_review_id(prepared: PreparedResourceGovernanceCandidate) -> UUID:
    if prepared.presentation.candidate_id == CANDIDATE_ID:
        return EVIDENCE_REVIEW_ID
    if prepared.presentation.candidate_id == PUSHUP_CANDIDATE_ID:
        return PUSHUP_EVIDENCE_REVIEW_ID
    if prepared.presentation.candidate_id == JUMP_CANDIDATE_ID:
        return JUMP_EVIDENCE_REVIEW_ID
    if prepared.presentation.candidate_id == JUMP_MAINTENANCE_CANDIDATE_ID:
        return JUMP_MAINTENANCE_EVIDENCE_REVIEW_ID
    if prepared.presentation.candidate_id == AEROBIC_CANDIDATE_ID:
        return AEROBIC_EVIDENCE_REVIEW_ID
    raise ResourceGovernanceCandidateValidationError(
        "resource candidate review identity is unknown"
    )


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
    if repository.get_evidence_source(release.claim.source_record_ids[0]) != _expected_source(
        prepared
    ) or any(
        repository.get_adaptation(adaptation_id) is None
        for adaptation_id in release.exercise.primary_adaptation_ids
    ):
        raise ResourceGovernanceCandidateConflictError(
            "persisted resource-governance release has incomplete prerequisites"
        )
    records = (
        repository.get_evidence_claim(release.claim.id),
        repository.get_evidence_claim_review(_evidence_review_id(prepared)),
        (repository.get_equipment(release.equipment.id) if release.equipment is not None else None),
        repository.get_exercise(release.exercise.id),
        repository.get_exercise_resolver_policy(release.resolver_policy.id),
        repository.get_resource_allocation_policy(release.allocation_policy.id),
    )
    required_records = (records[1], *records[3:])
    if records[0] != release.claim or any(item is None for item in required_records):
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
        candidate_id=prepared.presentation.candidate_id,
        candidate_content_digest=prepared.presentation.content_digest,
        created_source=False,
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


def _expected_source(prepared: PreparedResourceGovernanceCandidate) -> EvidenceSource:
    return prepared.release.source or prepared_acsm_resistance_training_source()


def _release_digest_payload(release: PreparedResourceGovernanceRelease) -> dict[str, object]:
    """Keep historical candidate digests stable while binding an optional bundled source."""

    payload = release.model_dump(mode="json", exclude={"source"})
    if release.source is not None:
        payload["source"] = release.source.model_dump(mode="json")
    return payload
