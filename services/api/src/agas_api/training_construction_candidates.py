# ruff: noqa: E501 -- reviewed governance prose remains exact.
from __future__ import annotations

import hashlib
import json
import sysconfig
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID

from agas_domain import (
    AccountRole,
    AssessmentReviewDecision,
    DecisionRecord,
    ExposureDefinition,
    ExposureProgressionPolicy,
    IntroductoryExposureDosePolicy,
    ProgressionPolicy,
    RepetitionDosePolicy,
    SessionSafetyPolicy,
    WeeklySchedulingPolicy,
    WeeklySchedulingPolicyReview,
)
from agas_domain.models import VersionedRecord
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agas_api.evidence_governance import (
    EvidenceAuthorityEvaluationError,
    EvidenceAuthorityEvaluator,
    EvidenceAuthorityNotReadyError,
)
from agas_api.identity import AuthorizedRole
from agas_api.resource_governance_candidates import (
    prepared_resource_governance_candidate_for_scope,
)

CANDIDATE_VERSION = "training-construction-candidate@1.0.0"
CANDIDATE_ID = UUID("98900000-0000-4000-8000-000000000001")
PUSHUP_CANDIDATE_ID = UUID("98900000-0000-4000-8000-000000000002")
JUMP_EXPOSURE_CANDIDATE_ID = UUID("98900000-0000-4000-8000-000000000003")
EVIDENCE_CLAIM_ID = UUID("91000000-0000-4000-8000-000000000005")
PUSHUP_EVIDENCE_CLAIM_ID = UUID("91000000-0000-4000-8000-000000000007")
JUMP_EVIDENCE_CLAIM_ID = UUID("91200000-0000-4000-8000-000000000004")
MUSCULAR_ENDURANCE_ADAPTATION_ID = UUID("a0000000-0000-4000-8000-000000000004")
LANDING_ADAPTATION_ID = UUID("a0000000-0000-4000-8000-000000000006")
NonEmptyText = Annotated[str, Field(min_length=1)]


class TrainingConstructionAuthorityBasis(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scientific_support: NonEmptyText
    engineering_prior: NonEmptyText


class TrainingConstructionEvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: UUID
    title: NonEmptyText
    source_url: NonEmptyText
    supported_use: NonEmptyText
    unsupported_specifics: NonEmptyText


class TrainingConstructionCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["training-construction-candidate@1.0.0"]
    candidate_id: UUID
    slug: NonEmptyText
    release_label: NonEmptyText
    prepared_at: datetime
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    summary: NonEmptyText
    authority_basis: TrainingConstructionAuthorityBasis
    exact_artifacts: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    governs: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    does_not_establish: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    unresolved_limitations: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    evidence: Annotated[tuple[TrainingConstructionEvidenceSummary, ...], Field(min_length=1)]


class PreparedTrainingConstructionRelease(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prepared_at: datetime
    weekly_scheduling_policy: WeeklySchedulingPolicy
    weekly_scheduling_policy_review_id: UUID
    weekly_scheduling_policy_review_content: dict[str, str]
    progression_policy: ProgressionPolicy
    repetition_dose_policy: RepetitionDosePolicy | None = None
    introductory_exposure_dose_policy: IntroductoryExposureDosePolicy | None = None
    exposure_definition: ExposureDefinition | None = None
    exposure_progression_policy: ExposureProgressionPolicy | None = None
    session_safety_policy: SessionSafetyPolicy
    release_rationale: NonEmptyText
    release_uncertainty: NonEmptyText


class TrainingConstructionCandidateDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    document_schema_version: Literal["training-construction-candidate-document@1.0.0"]
    candidate_version: Literal["training-construction-candidate@1.0.0"]
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    presentation: dict[str, Any]
    release: PreparedTrainingConstructionRelease

    @model_validator(mode="after")
    def validate_release_alignment(self) -> TrainingConstructionCandidateDocument:
        presentation = TrainingConstructionCandidate(
            candidate_version=self.candidate_version,
            content_digest=self.content_digest,
            **self.presentation,
        )
        release = self.release
        if presentation.prepared_at != release.prepared_at:
            raise ValueError("candidate and release preparation times must match")
        dose_policies = tuple(
            policy
            for policy in (
                release.repetition_dose_policy,
                release.introductory_exposure_dose_policy,
            )
            if policy is not None
        )
        if len(dose_policies) != 1:
            raise ValueError("release must contain exactly one dose policy")
        dose_policy = dose_policies[0]
        if dose_policy.progression_policy_id != release.progression_policy.id:
            raise ValueError("dose policy must reference the bundled progression policy")
        authority_evidence = (
            *release.progression_policy.evidence_claim_ids,
            *dose_policy.evidence_claim_ids,
            *release.session_safety_policy.evidence_claim_ids,
            *(
                release.exposure_definition.evidence_claim_ids
                if release.exposure_definition is not None
                else ()
            ),
            *(
                release.exposure_progression_policy.evidence_claim_ids
                if release.exposure_progression_policy is not None
                else ()
            ),
        )
        presentation_claim_ids = tuple(item.claim_id for item in presentation.evidence)
        if len(presentation_claim_ids) != 1 or set(authority_evidence) != set(
            presentation_claim_ids
        ):
            raise ValueError("every evidence-linked authority must cite the exact summarized claim")
        required_review_keys = {
            "applicability_rationale",
            "uncertainty",
            "review_version",
        }
        if set(release.weekly_scheduling_policy_review_content) != required_review_keys:
            raise ValueError("weekly scheduling review content has an unexpected shape")
        return self


class PreparedTrainingConstructionCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    presentation: TrainingConstructionCandidate
    release: PreparedTrainingConstructionRelease


class TrainingConstructionCandidateItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate: TrainingConstructionCandidate
    status: Literal["available", "blocked", "ratified", "conflict"]
    ratified_at: datetime | None = None
    issues: tuple[str, ...] = ()


class TrainingConstructionCandidateProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    projected_at: datetime
    items: tuple[TrainingConstructionCandidateItem, ...]
    projection_version: str = "training-construction-candidates@1.0.0"


class RatifyTrainingConstructionCandidateCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["training-construction-candidate@1.0.0"]
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    approval_attestation: Literal[True]


class TrainingConstructionRatificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: UUID
    candidate_content_digest: str
    created_weekly_scheduling_policy: bool
    created_weekly_scheduling_policy_review: bool
    created_progression_policy: bool
    created_repetition_dose_policy: bool
    created_introductory_exposure_dose_policy: bool
    created_exposure_definition: bool
    created_exposure_progression_policy: bool
    created_session_safety_policy: bool
    decision_record_created: bool
    weekly_scheduling_policy: WeeklySchedulingPolicy
    weekly_scheduling_policy_review: WeeklySchedulingPolicyReview
    progression_policy: ProgressionPolicy
    repetition_dose_policy: RepetitionDosePolicy | None
    introductory_exposure_dose_policy: IntroductoryExposureDosePolicy | None
    exposure_definition: ExposureDefinition | None
    exposure_progression_policy: ExposureProgressionPolicy | None
    session_safety_policy: SessionSafetyPolicy
    ratification_version: str = "training-construction-ratification@1.0.0"


class TrainingConstructionCandidateConflictError(RuntimeError):
    pass


class TrainingConstructionCandidateValidationError(RuntimeError):
    pass


def prepared_training_construction_candidate() -> PreparedTrainingConstructionCandidate:
    return _prepared_candidate()


def prepared_training_construction_candidates() -> tuple[
    PreparedTrainingConstructionCandidate, ...
]:
    return (
        _prepared_candidate(),
        _prepared_pushup_candidate(),
        _prepared_jump_exposure_candidate(),
    )


def prepared_training_construction_candidate_for_scope(
    estimate_scope: str,
) -> PreparedTrainingConstructionCandidate:
    for prepared in prepared_training_construction_candidates():
        if _release_scope(prepared.release) == estimate_scope:
            return prepared
    raise KeyError(f"no training-construction candidate is registered for {estimate_scope}")


def list_training_construction_candidates(
    session: Session, *, projected_at: datetime | None = None
) -> TrainingConstructionCandidateProjection:
    instant = projected_at or datetime.now(UTC)
    _require_aware(instant, "candidate projection")
    repository = DomainRepository(session)
    items: list[TrainingConstructionCandidateItem] = []
    for prepared in prepared_training_construction_candidates():
        decision = repository.get_decision_record(prepared.presentation.candidate_id)
        if decision is None:
            issues = _prerequisite_issues(session, instant, prepared)
            status: Literal["available", "blocked", "ratified", "conflict"] = (
                "blocked" if issues else "available"
            )
            ratified_at = None
        elif (
            f"candidate_content_digest:{prepared.presentation.content_digest}" in decision.evidence
        ):
            try:
                _existing_result(repository, prepared, decision)
            except TrainingConstructionCandidateConflictError as error:
                status = "conflict"
                issues = (str(error),)
            else:
                status = "ratified"
                issues = ()
            ratified_at = decision.created_at
        else:
            status = "conflict"
            ratified_at = decision.created_at
            issues = ("The release identity is occupied by different immutable content.",)
        items.append(
            TrainingConstructionCandidateItem(
                candidate=prepared.presentation,
                status=status,
                ratified_at=ratified_at,
                issues=issues,
            )
        )
    return TrainingConstructionCandidateProjection(
        projected_at=instant,
        items=tuple(items),
    )


def ratify_training_construction_candidate(
    session: Session,
    candidate_id: UUID,
    command: RatifyTrainingConstructionCandidateCommand,
    authority: AuthorizedRole,
    *,
    ratified_at: datetime | None = None,
) -> TrainingConstructionRatificationResult:
    prepared = next(
        (
            item
            for item in prepared_training_construction_candidates()
            if item.presentation.candidate_id == candidate_id
        ),
        None,
    )
    if prepared is None:
        raise KeyError("training-construction candidate does not exist")
    if authority.role is not AccountRole.PLANNING_REVIEWER:
        raise TrainingConstructionCandidateValidationError(
            "training-construction ratification requires planning_reviewer authority"
        )
    if command.candidate_version != prepared.presentation.candidate_version:
        raise TrainingConstructionCandidateValidationError(
            "candidate version does not match the prepared release"
        )
    if command.content_digest != prepared.presentation.content_digest:
        raise TrainingConstructionCandidateConflictError(
            "candidate content changed; refresh and review the exact current release"
        )
    repository = DomainRepository(session)
    existing_decision = repository.get_decision_record(candidate_id)
    if existing_decision is not None:
        return _existing_result(repository, prepared, existing_decision)
    instant = ratified_at or datetime.now(UTC)
    _require_aware(instant, "ratification")
    if instant < prepared.release.prepared_at or instant < authority.assigned_at:
        raise TrainingConstructionCandidateValidationError(
            "ratification cannot predate the prepared release or reviewer assignment"
        )
    if instant > datetime.now(UTC) + timedelta(minutes=5):
        raise TrainingConstructionCandidateValidationError("ratification cannot be in the future")
    prerequisite_issues = _prerequisite_issues(session, instant, prepared)
    if prerequisite_issues:
        raise TrainingConstructionCandidateValidationError("; ".join(prerequisite_issues))

    release = prepared.release
    reviewer = f"account:{authority.account_id}"
    scheduling_review = WeeklySchedulingPolicyReview(
        id=release.weekly_scheduling_policy_review_id,
        created_at=instant,
        weekly_scheduling_policy_id=release.weekly_scheduling_policy.id,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=1,
        evidence_claim_ids=release.progression_policy.evidence_claim_ids,
        reviewed_at=instant,
        reviewed_by=reviewer,
        **release.weekly_scheduling_policy_review_content,
    )
    decision = DecisionRecord(
        id=candidate_id,
        created_at=instant,
        decision="Ratified the owner-alpha first-session construction authority batch.",
        reason=release.release_rationale,
        alternatives_considered=(
            "Ask the owner to author dose, scheduling, progression, and safety values manually.",
            "Hide convenient defaults in the runtime or web form.",
            "Misrepresent the exact engineering constants as findings from the broad evidence claim.",
            "Delay all end-to-end training until every future capability domain is governed.",
        ),
        evidence=(
            f"candidate_content_digest:{prepared.presentation.content_digest}",
            f"authority_account_id:{authority.account_id}",
            f"authority_assignment_id:{authority.assignment_id}",
            *(
                f"evidence_claim_id:{claim_id}"
                for claim_id in release.progression_policy.evidence_claim_ids
            ),
            f"weekly_scheduling_policy_id:{release.weekly_scheduling_policy.id}",
            f"weekly_scheduling_policy_review_id:{scheduling_review.id}",
            f"progression_policy_id:{release.progression_policy.id}",
            *(
                (f"repetition_dose_policy_id:{release.repetition_dose_policy.id}",)
                if release.repetition_dose_policy is not None
                else ()
            ),
            *(
                (
                    "introductory_exposure_dose_policy_id:"
                    f"{release.introductory_exposure_dose_policy.id}",
                )
                if release.introductory_exposure_dose_policy is not None
                else ()
            ),
            *(
                (f"exposure_definition_id:{release.exposure_definition.id}",)
                if release.exposure_definition is not None
                else ()
            ),
            *(
                (f"exposure_progression_policy_id:{release.exposure_progression_policy.id}",)
                if release.exposure_progression_policy is not None
                else ()
            ),
            f"session_safety_policy_id:{release.session_safety_policy.id}",
        ),
        uncertainty=release.release_uncertainty,
        decision_version="training-construction-ratification@1.0.0",
        decided_on=instant.date(),
    )
    try:
        created_progression = _ensure_exact(
            label="progression policy",
            expected=release.progression_policy,
            getter=repository.get_progression_policy,
            adder=repository.add_progression_policy,
        )
        session.flush()
        created_repetition_dose = _ensure_optional_exact(
            label="repetition dose policy",
            expected=release.repetition_dose_policy,
            getter=repository.get_repetition_dose_policy,
            adder=repository.add_repetition_dose_policy,
        )
        created_introductory_dose = _ensure_optional_exact(
            label="introductory exposure dose policy",
            expected=release.introductory_exposure_dose_policy,
            getter=repository.get_introductory_exposure_dose_policy,
            adder=repository.add_introductory_exposure_dose_policy,
        )
        created_exposure_definition = _ensure_optional_exact(
            label="exposure definition",
            expected=release.exposure_definition,
            getter=repository.get_exposure_definition,
            adder=repository.add_exposure_definition,
        )
        created_exposure_progression = _ensure_optional_exact(
            label="exposure progression policy",
            expected=release.exposure_progression_policy,
            getter=repository.get_exposure_progression_policy,
            adder=repository.add_exposure_progression_policy,
        )
        created_scheduling = _ensure_exact(
            label="weekly scheduling policy",
            expected=release.weekly_scheduling_policy,
            getter=repository.get_weekly_scheduling_policy,
            adder=repository.add_weekly_scheduling_policy,
        )
        session.flush()
        created_scheduling_review = _ensure_exact(
            label="weekly scheduling policy review",
            expected=scheduling_review,
            getter=repository.get_weekly_scheduling_policy_review,
            adder=repository.add_weekly_scheduling_policy_review,
        )
        created_safety = _ensure_exact(
            label="session safety policy",
            expected=release.session_safety_policy,
            getter=repository.get_session_safety_policy,
            adder=repository.add_session_safety_policy,
        )
        created_decision = _ensure_exact(
            label="decision record",
            expected=decision,
            getter=repository.get_decision_record,
            adder=repository.add_decision_record,
        )
        session.commit()
    except TrainingConstructionCandidateConflictError:
        session.rollback()
        raise
    except (
        DomainIntegrityError,
        EvidenceAuthorityEvaluationError,
        EvidenceAuthorityNotReadyError,
        IntegrityError,
    ) as error:
        session.rollback()
        raise TrainingConstructionCandidateConflictError(str(error)) from error
    except Exception:
        session.rollback()
        raise
    return TrainingConstructionRatificationResult(
        candidate_id=candidate_id,
        candidate_content_digest=prepared.presentation.content_digest,
        created_weekly_scheduling_policy=created_scheduling,
        created_weekly_scheduling_policy_review=created_scheduling_review,
        created_progression_policy=created_progression,
        created_repetition_dose_policy=created_repetition_dose,
        created_introductory_exposure_dose_policy=created_introductory_dose,
        created_exposure_definition=created_exposure_definition,
        created_exposure_progression_policy=created_exposure_progression,
        created_session_safety_policy=created_safety,
        decision_record_created=created_decision,
        weekly_scheduling_policy=release.weekly_scheduling_policy,
        weekly_scheduling_policy_review=scheduling_review,
        progression_policy=release.progression_policy,
        repetition_dose_policy=release.repetition_dose_policy,
        introductory_exposure_dose_policy=release.introductory_exposure_dose_policy,
        exposure_definition=release.exposure_definition,
        exposure_progression_policy=release.exposure_progression_policy,
        session_safety_policy=release.session_safety_policy,
    )


def _prerequisite_issues(
    session: Session,
    instant: datetime,
    prepared: PreparedTrainingConstructionCandidate,
) -> tuple[str, ...]:
    repository = DomainRepository(session)
    release = prepared.release
    evidence_claim_ids = _release_evidence_claim_ids(release)
    issues: list[str] = []
    if release.repetition_dose_policy is not None:
        scope = release.repetition_dose_policy.estimate_scope
        resource = prepared_resource_governance_candidate_for_scope(scope)
        resource_decision = repository.get_decision_record(resource.presentation.candidate_id)
        if resource_decision is None or (
            f"candidate_content_digest:{resource.presentation.content_digest}"
            not in resource_decision.evidence
        ):
            issues.append(
                "Ratify the matching owner-alpha resource-governance bundle first so the exact claim, exercise, resolver, and allocator exist."
            )
    elif release.exposure_definition is not None and (
        repository.get_exercise(release.exposure_definition.exercise_id) is None
    ):
        issues.append("Import the controlled seed catalog so the exact exposure exercise exists.")
    if repository.get_adaptation(_release_dose_policy(release).adaptation_id) is None:
        issues.append("Import the controlled seed catalog so the exact adaptation exists.")
    missing_claim_ids = tuple(
        claim_id
        for claim_id in evidence_claim_ids
        if repository.get_evidence_claim(claim_id) is None
    )
    if missing_claim_ids:
        issues.append("The exact reviewed evidence claim is unavailable.")
    elif not issues:
        try:
            EvidenceAuthorityEvaluator(session).require_ready(evidence_claim_ids, instant)
        except (EvidenceAuthorityEvaluationError, EvidenceAuthorityNotReadyError) as error:
            issues.append(f"The exact evidence claim is not ready: {error}")
    return tuple(issues)


@lru_cache
def _prepared_candidate() -> PreparedTrainingConstructionCandidate:
    return _load_candidate(
        "owner_alpha_chair_stand.json",
        expected_candidate_id=CANDIDATE_ID,
        expected_evidence_claim_id=EVIDENCE_CLAIM_ID,
        expected_adaptation_id=MUSCULAR_ENDURANCE_ADAPTATION_ID,
    )


@lru_cache
def _prepared_pushup_candidate() -> PreparedTrainingConstructionCandidate:
    return _load_candidate(
        "owner_alpha_pushup.json",
        expected_candidate_id=PUSHUP_CANDIDATE_ID,
        expected_evidence_claim_id=PUSHUP_EVIDENCE_CLAIM_ID,
        expected_adaptation_id=MUSCULAR_ENDURANCE_ADAPTATION_ID,
    )


@lru_cache
def _prepared_jump_exposure_candidate() -> PreparedTrainingConstructionCandidate:
    return _load_candidate(
        "owner_alpha_jump_exposure.json",
        expected_candidate_id=JUMP_EXPOSURE_CANDIDATE_ID,
        expected_evidence_claim_id=JUMP_EVIDENCE_CLAIM_ID,
        expected_adaptation_id=LANDING_ADAPTATION_ID,
    )


def _load_candidate(
    filename: str,
    *,
    expected_candidate_id: UUID,
    expected_evidence_claim_id: UUID,
    expected_adaptation_id: UUID,
) -> PreparedTrainingConstructionCandidate:
    path = _default_candidate_data_root() / filename
    try:
        with path.open(encoding="utf-8") as file:
            raw = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise TrainingConstructionCandidateValidationError(
            f"unable to read training-construction candidate document: {error}"
        ) from error
    if not isinstance(raw, dict):
        raise TrainingConstructionCandidateValidationError(
            "training-construction candidate document must be an object"
        )
    try:
        document = TrainingConstructionCandidateDocument.model_validate(raw)
    except ValueError as error:
        raise TrainingConstructionCandidateValidationError(
            f"invalid training-construction candidate document: {error}"
        ) from error
    canonical = json.dumps(
        {
            "candidate_version": raw["candidate_version"],
            "presentation": raw["presentation"],
            "release": raw["release"],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    actual_digest = f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
    if actual_digest != document.content_digest:
        raise TrainingConstructionCandidateValidationError(
            "training-construction candidate document has a stale content digest"
        )
    presentation = TrainingConstructionCandidate(
        candidate_version=document.candidate_version,
        content_digest=document.content_digest,
        **document.presentation,
    )
    if presentation.candidate_id != expected_candidate_id:
        raise TrainingConstructionCandidateValidationError(
            "training-construction candidate identity is not recognized"
        )
    if tuple(item.claim_id for item in presentation.evidence) != (expected_evidence_claim_id,):
        raise TrainingConstructionCandidateValidationError(
            "training-construction candidate cites an unexpected evidence claim"
        )
    if _release_dose_policy(document.release).adaptation_id != expected_adaptation_id:
        raise TrainingConstructionCandidateValidationError(
            "training-construction candidate references an unexpected adaptation"
        )
    return PreparedTrainingConstructionCandidate(
        presentation=presentation,
        release=document.release,
    )


def _default_candidate_data_root() -> Path:
    repository_data = (
        Path(__file__).resolve().parents[4]
        / "data"
        / "governance_candidates"
        / "training_construction"
    )
    if repository_data.is_dir():
        return repository_data
    return (
        Path(sysconfig.get_path("data"))
        / "share"
        / "agas"
        / "data"
        / "governance_candidates"
        / "training_construction"
    )


def _ensure_exact[Record: VersionedRecord](
    *,
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
        raise TrainingConstructionCandidateConflictError(
            f"persisted {label} {expected.id} differs from candidate content"
        )
    return False


def _ensure_optional_exact[Record: VersionedRecord](
    *,
    label: str,
    expected: Record | None,
    getter: Callable[[UUID], Record | None],
    adder: Callable[[Record], None],
) -> bool:
    if expected is None:
        return False
    return _ensure_exact(label=label, expected=expected, getter=getter, adder=adder)


def _release_dose_policy(
    release: PreparedTrainingConstructionRelease,
) -> RepetitionDosePolicy | IntroductoryExposureDosePolicy:
    if release.repetition_dose_policy is not None:
        return release.repetition_dose_policy
    if release.introductory_exposure_dose_policy is not None:
        return release.introductory_exposure_dose_policy
    raise TrainingConstructionCandidateValidationError("release has no dose policy")


def _release_scope(release: PreparedTrainingConstructionRelease) -> str:
    dose_policy = _release_dose_policy(release)
    if isinstance(dose_policy, RepetitionDosePolicy):
        return dose_policy.estimate_scope
    return dose_policy.target_scope


def _release_evidence_claim_ids(
    release: PreparedTrainingConstructionRelease,
) -> tuple[UUID, ...]:
    values = (
        *release.progression_policy.evidence_claim_ids,
        *_release_dose_policy(release).evidence_claim_ids,
        *release.session_safety_policy.evidence_claim_ids,
        *(
            release.exposure_definition.evidence_claim_ids
            if release.exposure_definition is not None
            else ()
        ),
        *(
            release.exposure_progression_policy.evidence_claim_ids
            if release.exposure_progression_policy is not None
            else ()
        ),
    )
    return tuple(dict.fromkeys(values))


def _existing_result(
    repository: DomainRepository,
    prepared: PreparedTrainingConstructionCandidate,
    decision: DecisionRecord,
) -> TrainingConstructionRatificationResult:
    if f"candidate_content_digest:{prepared.presentation.content_digest}" not in decision.evidence:
        raise TrainingConstructionCandidateConflictError(
            "candidate release identity is occupied by different immutable content"
        )
    release = prepared.release
    scheduling_review = repository.get_weekly_scheduling_policy_review(
        release.weekly_scheduling_policy_review_id
    )
    if scheduling_review is None:
        raise TrainingConstructionCandidateConflictError(
            "persisted training-construction release has no scheduling review"
        )
    account_evidence = next(
        (value for value in decision.evidence if value.startswith("authority_account_id:")),
        None,
    )
    expected_reviewer = (
        None if account_evidence is None else f"account:{account_evidence.split(':', 1)[1]}"
    )
    review_content = release.weekly_scheduling_policy_review_content
    if (
        scheduling_review.weekly_scheduling_policy_id != release.weekly_scheduling_policy.id
        or scheduling_review.decision is not AssessmentReviewDecision.APPROVED
        or scheduling_review.sequence_number != 1
        or scheduling_review.supersedes_review_id is not None
        or scheduling_review.evidence_claim_ids != release.progression_policy.evidence_claim_ids
        or scheduling_review.reviewed_by != expected_reviewer
        or scheduling_review.applicability_rationale != review_content["applicability_rationale"]
        or scheduling_review.uncertainty != review_content["uncertainty"]
        or scheduling_review.review_version != review_content["review_version"]
    ):
        raise TrainingConstructionCandidateConflictError(
            "persisted scheduling review differs from the ratified release"
        )
    records = (
        repository.get_weekly_scheduling_policy(release.weekly_scheduling_policy.id),
        repository.get_progression_policy(release.progression_policy.id),
        (
            repository.get_repetition_dose_policy(release.repetition_dose_policy.id)
            if release.repetition_dose_policy is not None
            else None
        ),
        (
            repository.get_introductory_exposure_dose_policy(
                release.introductory_exposure_dose_policy.id
            )
            if release.introductory_exposure_dose_policy is not None
            else None
        ),
        (
            repository.get_exposure_definition(release.exposure_definition.id)
            if release.exposure_definition is not None
            else None
        ),
        (
            repository.get_exposure_progression_policy(release.exposure_progression_policy.id)
            if release.exposure_progression_policy is not None
            else None
        ),
        repository.get_session_safety_policy(release.session_safety_policy.id),
    )
    expected = (
        release.weekly_scheduling_policy,
        release.progression_policy,
        release.repetition_dose_policy,
        release.introductory_exposure_dose_policy,
        release.exposure_definition,
        release.exposure_progression_policy,
        release.session_safety_policy,
    )
    if records != expected:
        raise TrainingConstructionCandidateConflictError(
            "persisted training-construction authorities differ from the ratified release"
        )
    return TrainingConstructionRatificationResult(
        candidate_id=prepared.presentation.candidate_id,
        candidate_content_digest=prepared.presentation.content_digest,
        created_weekly_scheduling_policy=False,
        created_weekly_scheduling_policy_review=False,
        created_progression_policy=False,
        created_repetition_dose_policy=False,
        created_introductory_exposure_dose_policy=False,
        created_exposure_definition=False,
        created_exposure_progression_policy=False,
        created_session_safety_policy=False,
        decision_record_created=False,
        weekly_scheduling_policy=release.weekly_scheduling_policy,
        weekly_scheduling_policy_review=scheduling_review,
        progression_policy=release.progression_policy,
        repetition_dose_policy=release.repetition_dose_policy,
        introductory_exposure_dose_policy=release.introductory_exposure_dose_policy,
        exposure_definition=release.exposure_definition,
        exposure_progression_policy=release.exposure_progression_policy,
        session_safety_policy=release.session_safety_policy,
    )


def _require_aware(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} time must include a timezone")
