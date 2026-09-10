from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid5

from agas_domain import (
    InitialPlanningCandidateContext,
    InitialPlanningContextDraft,
    InitialPlanningContextReview,
)
from agas_domain.persistence.repository import DomainRepository
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from agas_api.identity import AuthorizedRole
from agas_api.initial_planning import CreateInitialStrategyCommand, PersistedInitialPlanningService
from agas_api.initial_planning_context import (
    InitialPlanningContextConflictError,
    OperatorInitialPlanningContextDraftRequest,
    PersistedInitialPlanningContextService,
)
from agas_api.initial_planning_preparation import InitialPlanningPreparationProjector

CANDIDATE_VERSION = "prepared-initial-planning-context@1.0.0"
POLICY_VERSION = "owner-alpha-deficit-only-priority@1.0.0"
ESTIMATE_SCOPE = "assessment_specific:thirty_second_chair_stand_repetitions"
FLOOR_VERSION = "chair-stand-age-30-39-lower-reference-floor@1.0.0"
ADAPTATION_ID = UUID("a0000000-0000-4000-8000-000000000004")
CANDIDATE_NAMESPACE = UUID("d85bc2d2-c821-4f0a-a126-a7a776f36d21")
NonEmptyText = Annotated[str, Field(min_length=1)]


class PreparedContextComponent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    field: NonEmptyText
    value: float | bool
    treatment: Literal["used", "unused", "hard_gate"]
    basis: NonEmptyText
    limitation: NonEmptyText


class PreparedInitialPlanningContextCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["prepared-initial-planning-context@1.0.0"]
    candidate_id: UUID
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    prepared_at: datetime
    athlete_id: UUID
    athlete_display_name: NonEmptyText
    status: Literal["available", "accepted"]
    summary: NonEmptyText
    priority_policy_id: UUID
    priority_policy_review_id: UUID
    policy_version: NonEmptyText
    floor_version: NonEmptyText
    estimate_scope: NonEmptyText
    candidate_context: InitialPlanningCandidateContext
    horizon_months: int
    review_after_days: int
    applicability_rationale: NonEmptyText
    uncertainty: NonEmptyText
    components: Annotated[tuple[PreparedContextComponent, ...], Field(min_length=1)]
    expected_priority_state: NonEmptyText
    expected_priority_score: float = Field(ge=0, le=1)
    safety_boundary: NonEmptyText
    accepted_draft_id: UUID | None = None
    accepted_draft: InitialPlanningContextDraft | None = None
    accepted_review: InitialPlanningContextReview | None = None


class PreparedInitialPlanningContextProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    athlete_id: UUID
    projected_at: datetime
    status: Literal["available", "blocked", "accepted"]
    message: NonEmptyText
    candidate: PreparedInitialPlanningContextCandidate | None
    blockers: tuple[str, ...]
    projection_version: str = "prepared-initial-planning-context-projection@1.0.0"


class RatifyPreparedInitialPlanningContextCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["prepared-initial-planning-context@1.0.0"]
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    approval_attestation: Literal[True]


class PreparedInitialPlanningContextRatificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: UUID
    candidate_content_digest: str
    created: bool
    draft: InitialPlanningContextDraft
    ratification_version: str = "prepared-initial-planning-context-ratification@1.0.0"


class PreparedInitialPlanningContextNotFoundError(LookupError):
    pass


class PreparedInitialPlanningContextConflictError(RuntimeError):
    pass


class PreparedInitialPlanningContextProjector:
    """Prepare one exact owner-alpha context without inventing weighted inputs."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def project(
        self,
        athlete_id: UUID,
        authority: AuthorizedRole,
        projected_at: datetime | None = None,
    ) -> PreparedInitialPlanningContextProjection:
        instant = projected_at or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("prepared context projection time must include a timezone")
        preparation = InitialPlanningPreparationProjector(self.session).project(athlete_id, instant)
        blockers: list[str] = []
        if preparation.status != "planning_context_review_required":
            blockers.append(preparation.message)

        policies = tuple(
            item
            for item in preparation.priority_policy_options
            if item.policy.policy_version == POLICY_VERSION
        )
        if len(policies) != 1:
            blockers.append(
                "The exact deficit-only owner-alpha policy must be approved before this "
                "context can be prepared."
            )

        pathways = []
        for option in preparation.estimate_options:
            if option.estimate.estimate_scope != ESTIMATE_SCOPE:
                continue
            floors = tuple(
                item for item in option.floor_options if item.floor.floor_version == FLOOR_VERSION
            )
            adaptations = tuple(
                item for item in option.adaptation_options if item.id == ADAPTATION_ID
            )
            if len(floors) == 1 and len(adaptations) == 1:
                pathways.append((option, floors[0], adaptations[0]))
        if len(pathways) != 1:
            blockers.append(
                "Exactly one current chair-stand estimate, approved age-applicable floor, "
                "and muscular-endurance adaptation path is required."
            )

        if blockers:
            return PreparedInitialPlanningContextProjection(
                athlete_id=athlete_id,
                projected_at=instant,
                status="blocked",
                message="The system-prepared context is not available yet.",
                candidate=None,
                blockers=tuple(dict.fromkeys(blockers)),
            )

        policy_option = policies[0]
        estimate_option, floor_option, adaptation = pathways[0]
        context = InitialPlanningCandidateContext(
            adaptation_id=adaptation.id,
            competency_floor_id=floor_option.floor.id,
            competency_floor_review_id=floor_option.review.id,
            capability_estimate_id=estimate_option.estimate.id,
            general_relevance=0,
            goal_relevance=0,
            prerequisite_value=0,
            expected_trainability=0,
            transfer_value=0,
            fatigue_cost=0,
            time_cost=0,
            interference_cost=0,
            safe_to_train=True,
            introductory_exposure_needed=False,
            prerequisites_met=True,
            prerequisite_adaptation_ids=(),
            cultivate_comparative_advantage=False,
            source_observation_ids=estimate_option.estimate.source_observation_ids,
            evidence_claim_ids=tuple(
                dict.fromkeys(
                    (
                        *floor_option.floor.evidence_claim_ids,
                        *adaptation.evidence_claim_ids,
                    )
                )
            ),
        )
        rationale = (
            "System-prepared owner-alpha context using one current assessment-specific "
            "chair-stand estimate, its exact approved age-applicable floor, the domain-matched "
            "muscular-endurance adaptation, and the deficit-only priority policy. Contextual "
            "scores are explicit zeros because this policy gives them zero weight, not because "
            "the system has evidence that they are unimportant."
        )
        uncertainty = (
            "The estimate is a low-confidence self-administered count and the floor is a narrow "
            "reference-distribution interpretation. The planning inclusion flag is not medical "
            "clearance or session readiness. Exercise, dose, feasibility, and a current session "
            "safety decision remain separate required gates."
        )
        summary = (
            "AGAS prepared the exact first planning context from governed state. No relevance, "
            "goal, transfer, trainability, or recovery-cost number was inferred."
        )
        safety_boundary = (
            "safe_to_train=true means only that this long-range candidate is not forcibly "
            "deferred by a known planning flag. It does not say that a workout is safe. Every "
            "performed session still requires the separate current safety gate, and this is "
            "not medical clearance."
        )
        components = _components()
        preview = PersistedInitialPlanningService(self.session).preview(
            athlete_id,
            CreateInitialStrategyCommand(
                priority_policy_id=policy_option.policy.id,
                priority_policy_review_id=policy_option.review.id,
                candidate_contexts=(context,),
                generated_at=instant,
                horizon_months=12,
                review_after_days=28,
                reviewed_by=f"account:{authority.account_id}",
                review_authority_assignment_id=authority.assignment_id,
                applicability_rationale=rationale,
                uncertainty=uncertainty,
            ),
        )
        priority = preview.strategy.priorities[0]
        stable_content = {
            "candidate_version": CANDIDATE_VERSION,
            "athlete_id": str(athlete_id),
            "authority_assignment_id": str(authority.assignment_id),
            "policy_id": str(policy_option.policy.id),
            "policy_review_id": str(policy_option.review.id),
            "policy_version": policy_option.policy.policy_version,
            "floor_version": floor_option.floor.floor_version,
            "estimate_scope": estimate_option.estimate.estimate_scope,
            "candidate_context": context.model_dump(mode="json"),
            "horizon_months": 12,
            "review_after_days": 28,
            "applicability_rationale": rationale,
            "uncertainty": uncertainty,
            "summary": summary,
            "components": [item.model_dump(mode="json") for item in components],
            "expected_priority_state": priority.state.value,
            "expected_priority_score": priority.score,
            "safety_boundary": safety_boundary,
        }
        canonical = json.dumps(stable_content, sort_keys=True, separators=(",", ":"))
        content_digest = f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
        candidate_id = uuid5(CANDIDATE_NAMESPACE, content_digest)
        existing = self.repository.get_initial_planning_context_draft(candidate_id)
        existing_review = (
            self.repository.get_initial_planning_context_review_by_draft(existing.id)
            if existing is not None
            else None
        )
        status: Literal["available", "accepted"] = "accepted" if existing else "available"
        candidate = PreparedInitialPlanningContextCandidate(
            candidate_version=CANDIDATE_VERSION,
            candidate_id=candidate_id,
            content_digest=content_digest,
            prepared_at=instant,
            athlete_id=athlete_id,
            athlete_display_name=preparation.athlete_display_name,
            status=status,
            summary=summary,
            priority_policy_id=policy_option.policy.id,
            priority_policy_review_id=policy_option.review.id,
            policy_version=policy_option.policy.policy_version,
            floor_version=floor_option.floor.floor_version,
            estimate_scope=estimate_option.estimate.estimate_scope,
            candidate_context=context,
            horizon_months=12,
            review_after_days=28,
            applicability_rationale=rationale,
            uncertainty=uncertainty,
            components=components,
            expected_priority_state=priority.state.value,
            expected_priority_score=priority.score,
            safety_boundary=safety_boundary,
            accepted_draft_id=existing.id if existing else None,
            accepted_draft=existing,
            accepted_review=existing_review,
        )
        return PreparedInitialPlanningContextProjection(
            athlete_id=athlete_id,
            projected_at=instant,
            status=status,
            message=(
                "The exact prepared context is already stored as an immutable draft."
                if existing
                else "One exact system-prepared context is ready for review and acceptance."
            ),
            candidate=candidate,
            blockers=(),
        )


def ratify_prepared_initial_planning_context(
    session: Session,
    athlete_id: UUID,
    candidate_id: UUID,
    command: RatifyPreparedInitialPlanningContextCommand,
    authority: AuthorizedRole,
) -> PreparedInitialPlanningContextRatificationResult:
    projection = PreparedInitialPlanningContextProjector(session).project(athlete_id, authority)
    candidate = projection.candidate
    if candidate is None or candidate.candidate_id != candidate_id:
        raise PreparedInitialPlanningContextNotFoundError(
            "the prepared context is unavailable or athlete state has changed"
        )
    if command.candidate_version != candidate.candidate_version:
        raise PreparedInitialPlanningContextConflictError(
            "candidate version does not match the current prepared context"
        )
    if command.content_digest != candidate.content_digest:
        raise PreparedInitialPlanningContextConflictError(
            "candidate content changed; refresh and inspect the exact current context"
        )
    repository = DomainRepository(session)
    existing = repository.get_initial_planning_context_draft(candidate.candidate_id)
    if existing is not None:
        _require_exact_existing(existing, candidate, authority)
        return PreparedInitialPlanningContextRatificationResult(
            candidate_id=candidate.candidate_id,
            candidate_content_digest=candidate.content_digest,
            created=False,
            draft=existing,
        )
    request = OperatorInitialPlanningContextDraftRequest(
        priority_policy_id=candidate.priority_policy_id,
        priority_policy_review_id=candidate.priority_policy_review_id,
        candidate_contexts=(candidate.candidate_context,),
        horizon_months=candidate.horizon_months,
        review_after_days=candidate.review_after_days,
        authored_at=datetime.now(UTC),
        applicability_rationale=(
            f"{candidate.applicability_rationale} Prepared candidate digest: "
            f"{candidate.content_digest}."
        ),
        uncertainty=candidate.uncertainty,
    )
    try:
        draft = PersistedInitialPlanningContextService(session).create_draft(
            athlete_id,
            request,
            authority,
            draft_id=candidate.candidate_id,
        )
    except InitialPlanningContextConflictError as error:
        raced = repository.get_initial_planning_context_draft(candidate.candidate_id)
        if raced is not None:
            _require_exact_existing(raced, candidate, authority)
            return PreparedInitialPlanningContextRatificationResult(
                candidate_id=candidate.candidate_id,
                candidate_content_digest=candidate.content_digest,
                created=False,
                draft=raced,
            )
        raise PreparedInitialPlanningContextConflictError(str(error)) from error
    return PreparedInitialPlanningContextRatificationResult(
        candidate_id=candidate.candidate_id,
        candidate_content_digest=candidate.content_digest,
        created=True,
        draft=draft,
    )


def _require_exact_existing(
    existing: InitialPlanningContextDraft,
    candidate: PreparedInitialPlanningContextCandidate,
    authority: AuthorizedRole,
) -> None:
    if (
        existing.athlete_id != candidate.athlete_id
        or existing.priority_policy_id != candidate.priority_policy_id
        or existing.priority_policy_review_id != candidate.priority_policy_review_id
        or existing.candidate_contexts != (candidate.candidate_context,)
        or existing.horizon_months != candidate.horizon_months
        or existing.review_after_days != candidate.review_after_days
        or existing.authored_by_account_id != authority.account_id
        or existing.author_authority_assignment_id != authority.assignment_id
        or candidate.content_digest not in existing.applicability_rationale
        or existing.uncertainty != candidate.uncertainty
    ):
        raise PreparedInitialPlanningContextConflictError(
            "prepared context identity is occupied by different immutable content"
        )


def _components() -> tuple[PreparedContextComponent, ...]:
    unused = (
        ("general_relevance", "No governed general-relevance magnitude exists."),
        (
            "goal_relevance",
            "Athlete goals are not yet mapped to this adaptation by a reviewed rule.",
        ),
        ("prerequisite_value", "No reviewed prerequisite-value magnitude exists."),
        (
            "expected_trainability",
            "Population-level evidence does not quantify this athlete's response.",
        ),
        ("transfer_value", "No reviewed transfer magnitude exists for this assessment path."),
        (
            "fatigue_cost",
            "Cost depends on the later selected stimulus, exercise, dose, and schedule.",
        ),
        ("time_cost", "Cost depends on the later selected stimulus, exercise, dose, and schedule."),
        ("interference_cost", "Cost depends on the later block composition and schedule."),
    )
    return (
        *(
            PreparedContextComponent(
                field=field,
                value=0,
                treatment="unused",
                basis="Explicit zero paired with zero weight in the exact selected policy.",
                limitation=limitation,
            )
            for field, limitation in unused
        ),
        PreparedContextComponent(
            field="safe_to_train",
            value=True,
            treatment="hard_gate",
            basis="No planning-level deferral is asserted for strategic inclusion.",
            limitation="This is not medical clearance or current session readiness.",
        ),
        PreparedContextComponent(
            field="prerequisites_met",
            value=True,
            treatment="hard_gate",
            basis=(
                "The current adaptation ontology contains no prerequisite relationship for "
                "this adaptation."
            ),
            limitation="Absence of a configured relationship is not a universal biological claim.",
        ),
        PreparedContextComponent(
            field="introductory_exposure_needed",
            value=False,
            treatment="hard_gate",
            basis="The candidate does not infer training inexperience from absent AGAS history.",
            limitation=(
                "Later exercise resolution may still choose a conservative introductory dose."
            ),
        ),
        PreparedContextComponent(
            field="cultivate_comparative_advantage",
            value=False,
            treatment="hard_gate",
            basis="No reviewed comparative-advantage decision exists.",
            limitation="False means not asserted, not that the athlete has no advantage.",
        ),
    )
