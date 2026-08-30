from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from agas_domain import (
    Adaptation,
    AdaptationPriority,
    BlockPlan,
    BlockReview,
    BlockReviewPolicy,
    CapabilityEstimate,
    CompetencyFloor,
    EvidenceClaim,
    LongRangeStrategy,
    Observation,
    PlannedSession,
    PriorityPolicy,
    SessionAdherence,
    SessionExecution,
    SessionPrescription,
    SessionSafetyDecision,
    SessionTemplate,
    TrainingResponse,
    WeeklyPlan,
    WeeklyPlanStatus,
)
from agas_domain.persistence.repository import DomainRepository
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session


class PostBlockPreparationNotFoundError(LookupError):
    pass


class PostBlockPreparationProjectionError(RuntimeError):
    pass


class BlockReviewSessionHistory(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    weekly_plan_id: UUID
    planned_session: PlannedSession
    session_template: SessionTemplate
    prescriptions: tuple[SessionPrescription, ...]
    execution: SessionExecution | None = None
    adherences: tuple[SessionAdherence, ...] = ()
    post_session_safety_decisions: tuple[SessionSafetyDecision, ...] = ()


class BlockReviewPreparationProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    block: BlockPlan
    strategy: LongRangeStrategy
    projected_at: datetime
    status: Literal["incomplete_history", "ready_for_explicit_review", "already_reviewed"]
    issues: tuple[str, ...]
    weekly_plans: tuple[WeeklyPlan, ...]
    session_history: tuple[BlockReviewSessionHistory, ...]
    prescriptions: tuple[SessionPrescription, ...]
    baseline_estimates: tuple[CapabilityEstimate, ...]
    followup_estimates: tuple[CapabilityEstimate, ...]
    block_review_policies: tuple[BlockReviewPolicy, ...]
    existing_review: BlockReview | None = None
    source_observations: tuple[Observation, ...] = ()
    evidence_claims: tuple[EvidenceClaim, ...] = ()
    projection_version: str = "block-review-preparation@1.0.0"


class ReplanningAdaptationOption(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    previous_priority: AdaptationPriority
    adaptation: Adaptation
    training_response: TrainingResponse | None = None
    requires_reviewed_followup: bool
    estimate_options: tuple[CapabilityEstimate, ...]
    compatible_competency_floors: tuple[CompetencyFloor, ...]


class ReplanningPreparationProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    block_review: BlockReview
    completed_block: BlockPlan
    previous_strategy: LongRangeStrategy
    priority_policy: PriorityPolicy
    projected_at: datetime
    status: Literal["blocked", "ready_for_explicit_replanning", "already_replanned"]
    issues: tuple[str, ...]
    training_responses: tuple[TrainingResponse, ...]
    adaptation_options: tuple[ReplanningAdaptationOption, ...]
    existing_successor_strategy: LongRangeStrategy | None = None
    source_observations: tuple[Observation, ...] = ()
    evidence_claims: tuple[EvidenceClaim, ...] = ()
    projection_version: str = "replanning-preparation@1.0.0"


def _load_observations(
    repository: DomainRepository, athlete_id: UUID, observation_ids: list[UUID]
) -> tuple[Observation, ...]:
    observations = []
    for observation_id in dict.fromkeys(observation_ids):
        observation = repository.get_observation(observation_id)
        if observation is None:
            raise PostBlockPreparationProjectionError(
                f"source observation {observation_id} does not exist"
            )
        if observation.athlete_id != athlete_id:
            raise PostBlockPreparationProjectionError(
                "source observation belongs to a different athlete"
            )
        observations.append(observation)
    return tuple(observations)


def _load_evidence_claims(
    repository: DomainRepository, evidence_ids: list[UUID]
) -> tuple[EvidenceClaim, ...]:
    claims = []
    for evidence_id in dict.fromkeys(evidence_ids):
        claim = repository.get_evidence_claim(evidence_id)
        if claim is None:
            raise PostBlockPreparationProjectionError(
                f"evidence claim {evidence_id} does not exist"
            )
        claims.append(claim)
    return tuple(claims)


class BlockReviewPreparationProjector:
    """Compose completed-block history without choosing response groupings or thresholds."""

    def __init__(self, session: Session) -> None:
        self.repository = DomainRepository(session)

    def project(
        self, block_id: UUID, projected_at: datetime | None = None
    ) -> BlockReviewPreparationProjection:
        block = self.repository.get_block_plan(block_id)
        if block is None:
            raise PostBlockPreparationNotFoundError("block plan does not exist")
        strategy = self.repository.get_long_range_strategy(block.long_range_strategy_id)
        if strategy is None:
            raise PostBlockPreparationProjectionError("block strategy does not exist")
        instant = self._instant(projected_at)
        if instant < block.generated_at:
            raise ValueError("post-block preparation cannot predate block generation")
        existing_review = self.repository.get_block_review_by_block(block.id)
        plans = self.repository.list_weekly_plans_for_block(block.id)
        expected_weeks = {
            (week, block.starts_on + timedelta(weeks=week - 1))
            for week in range(1, block.duration_weeks + 1)
        }
        actual_weeks = {(plan.block_week, plan.week_start) for plan in plans}
        issues: list[str] = []
        if len(plans) != block.duration_weeks or actual_weeks != expected_weeks:
            issues.append("exactly one persisted weekly plan is required for every block week")
        if any(plan.status is not WeeklyPlanStatus.FEASIBLE for plan in plans):
            issues.append("every persisted block week must be feasible")

        histories: list[BlockReviewSessionHistory] = []
        prescriptions_by_id: dict[UUID, SessionPrescription] = {}
        observation_ids = list(block.source_observation_ids)
        evidence_ids = list(block.evidence_claim_ids)
        for plan in plans:
            for planned_session in plan.sessions:
                template = self.repository.get_session_template(planned_session.session_template_id)
                if template is None:
                    raise PostBlockPreparationProjectionError(
                        f"session template {planned_session.session_template_id} does not exist"
                    )
                prescriptions = tuple(
                    self._require_prescription(item.prescription_id) for item in template.items
                )
                for prescription in prescriptions:
                    prescriptions_by_id[prescription.id] = prescription
                    observation_ids.extend(prescription.source_observation_ids)
                    evidence_ids.extend(prescription.evidence_claim_ids)
                execution = self.repository.get_session_execution_by_planned_session(
                    planned_session.id
                )
                adherences: tuple[SessionAdherence, ...] = ()
                post_decisions: tuple[SessionSafetyDecision, ...] = ()
                if execution is None:
                    issues.append(f"planned session {planned_session.id} has no execution outcome")
                else:
                    observation_ids.append(execution.performance_observation_id)
                    adherence_items = []
                    for item in execution.items:
                        adherence = (
                            self.repository.get_session_adherence_by_execution_and_prescription(
                                execution.id, item.prescription_id
                            )
                        )
                        if adherence is None:
                            issues.append(
                                f"execution {execution.id} prescription "
                                f"{item.prescription_id} has no adherence"
                            )
                        else:
                            adherence_items.append(adherence)
                            observation_ids.extend(adherence.source_observation_ids)
                    adherences = tuple(adherence_items)
                    post_decisions = self.repository.list_post_session_safety_decisions(
                        execution.id
                    )
                    if not post_decisions:
                        issues.append(
                            f"session execution {execution.id} has no post-session safety decision"
                        )
                    for decision in post_decisions:
                        observation_ids.extend(decision.source_observation_ids)
                histories.append(
                    BlockReviewSessionHistory(
                        weekly_plan_id=plan.id,
                        planned_session=planned_session,
                        session_template=template,
                        prescriptions=prescriptions,
                        execution=execution,
                        adherences=adherences,
                        post_session_safety_decisions=post_decisions,
                    )
                )

        estimates = self.repository.list_capability_estimates(block.athlete_id)
        block_end = block.starts_on + timedelta(weeks=block.duration_weeks)
        baselines = tuple(item for item in estimates if item.estimated_at.date() <= block.starts_on)
        followups = tuple(
            item
            for item in estimates
            if item.estimated_at.date() >= block_end and item.estimated_at <= instant
        )
        for estimate in (*baselines, *followups):
            observation_ids.extend(estimate.source_observation_ids)
        policies = self.repository.list_block_review_policies()
        for policy in policies:
            evidence_ids.extend(policy.evidence_claim_ids)
        if instant.date() < block_end:
            issues.append("the block has not reached its planned end")
        if not baselines:
            issues.append("no pre-block capability estimate is available")
        if not followups:
            issues.append("no post-block capability estimate is available")
        if not policies:
            issues.append("no block-review policy is available")

        if existing_review is not None:
            status = "already_reviewed"
        elif issues:
            status = "incomplete_history"
        else:
            status = "ready_for_explicit_review"
        return BlockReviewPreparationProjection(
            block=block,
            strategy=strategy,
            projected_at=instant,
            status=status,
            issues=tuple(dict.fromkeys(issues)),
            weekly_plans=plans,
            session_history=tuple(histories),
            prescriptions=tuple(prescriptions_by_id.values()),
            baseline_estimates=baselines,
            followup_estimates=followups,
            block_review_policies=policies,
            existing_review=existing_review,
            source_observations=_load_observations(
                self.repository, block.athlete_id, observation_ids
            ),
            evidence_claims=_load_evidence_claims(self.repository, evidence_ids),
        )

    def _require_prescription(self, prescription_id: UUID) -> SessionPrescription:
        prescription = self.repository.get_session_prescription(prescription_id)
        if prescription is None:
            raise PostBlockPreparationProjectionError(
                f"session prescription {prescription_id} does not exist"
            )
        return prescription

    @staticmethod
    def _instant(value: datetime | None) -> datetime:
        instant = value or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("post-block preparation time must include a timezone")
        return instant


class ReplanningPreparationProjector:
    """Expose reviewed response inputs without choosing successor-strategy scores."""

    def __init__(self, session: Session) -> None:
        self.repository = DomainRepository(session)

    def project(
        self, block_review_id: UUID, projected_at: datetime | None = None
    ) -> ReplanningPreparationProjection:
        review = self.repository.get_block_review(block_review_id)
        if review is None:
            raise PostBlockPreparationNotFoundError("block review does not exist")
        block = self.repository.get_block_plan(review.block_plan_id)
        if block is None:
            raise PostBlockPreparationProjectionError("reviewed block does not exist")
        strategy = self.repository.get_long_range_strategy(block.long_range_strategy_id)
        if strategy is None:
            raise PostBlockPreparationProjectionError("prior strategy does not exist")
        policy = self.repository.get_priority_policy(strategy.priority_policy_id)
        if policy is None:
            raise PostBlockPreparationProjectionError("priority policy does not exist")
        instant = BlockReviewPreparationProjector._instant(projected_at)
        if instant < review.reviewed_at:
            raise ValueError("replanning preparation cannot predate the block review")
        responses = tuple(
            self._require_response(response_id) for response_id in review.training_response_ids
        )
        responses_by_adaptation: dict[UUID, list[TrainingResponse]] = {}
        for response in responses:
            responses_by_adaptation.setdefault(response.adaptation_id, []).append(response)
        active_adaptation_ids = {
            item.adaptation_id for item in block.allocations if item.allocated_weekly_minutes > 0
        }
        allowed_estimate_ids = tuple(
            dict.fromkeys(
                (
                    *strategy.source_capability_estimate_ids,
                    *(item.followup_capability_estimate_id for item in responses),
                )
            )
        )
        allowed_estimates = tuple(
            estimate
            for estimate_id in allowed_estimate_ids
            if (estimate := self._require_estimate(estimate_id)).estimated_at <= instant
            and (estimate.valid_until is None or estimate.valid_until >= instant)
        )
        floors = self.repository.list_competency_floors()
        issues: list[str] = []
        options = []
        for priority in strategy.priorities:
            adaptation = self.repository.get_adaptation(priority.adaptation_id)
            if adaptation is None:
                raise PostBlockPreparationProjectionError(
                    f"adaptation {priority.adaptation_id} does not exist"
                )
            matching_responses = responses_by_adaptation.get(adaptation.id, [])
            active = adaptation.id in active_adaptation_ids
            reviewed_response = matching_responses[0] if len(matching_responses) == 1 else None
            if active and len(matching_responses) != 1:
                issues.append(
                    f"active adaptation {adaptation.id} requires exactly one training response"
                )
            if not active and len(matching_responses) > 1:
                issues.append(f"adaptation {adaptation.id} has ambiguous training-response history")
            if active and reviewed_response is not None:
                estimate_options = tuple(
                    item
                    for item in allowed_estimates
                    if item.id == reviewed_response.followup_capability_estimate_id
                )
            else:
                estimate_options = tuple(
                    item for item in allowed_estimates if item.domain is adaptation.domain
                )
            compatible_floors = tuple(
                floor
                for floor in floors
                if floor.domain is adaptation.domain
                and any(
                    estimate.estimate_scope == floor.estimate_scope
                    and estimate.unit_or_scale == floor.unit_or_scale
                    for estimate in estimate_options
                )
            )
            if not estimate_options:
                issues.append(f"adaptation {adaptation.id} has no eligible estimate")
            if not compatible_floors:
                issues.append(f"adaptation {adaptation.id} has no compatible competency floor")
            options.append(
                ReplanningAdaptationOption(
                    previous_priority=priority,
                    adaptation=adaptation,
                    training_response=reviewed_response,
                    requires_reviewed_followup=active,
                    estimate_options=estimate_options,
                    compatible_competency_floors=compatible_floors,
                )
            )

        successor = self.repository.get_long_range_strategy_by_triggering_review(review.id)
        if successor is not None:
            status = "already_replanned"
        elif issues:
            status = "blocked"
        else:
            status = "ready_for_explicit_replanning"
        exposed_floors = tuple(
            {
                floor.id: floor
                for option in options
                for floor in option.compatible_competency_floors
            }.values()
        )
        observation_ids = [
            *strategy.source_observation_ids,
            *review.source_observation_ids,
            *(item for estimate in allowed_estimates for item in estimate.source_observation_ids),
        ]
        evidence_ids = [
            *strategy.evidence_claim_ids,
            *review.evidence_claim_ids,
            *(item for floor in exposed_floors for item in floor.evidence_claim_ids),
        ]
        return ReplanningPreparationProjection(
            block_review=review,
            completed_block=block,
            previous_strategy=strategy,
            priority_policy=policy,
            projected_at=instant,
            status=status,
            issues=tuple(dict.fromkeys(issues)),
            training_responses=responses,
            adaptation_options=tuple(options),
            existing_successor_strategy=successor,
            source_observations=_load_observations(
                self.repository, block.athlete_id, observation_ids
            ),
            evidence_claims=_load_evidence_claims(self.repository, evidence_ids),
        )

    def _require_response(self, response_id: UUID) -> TrainingResponse:
        response = self.repository.get_training_response(response_id)
        if response is None:
            raise PostBlockPreparationProjectionError(
                f"training response {response_id} does not exist"
            )
        return response

    def _require_estimate(self, estimate_id: UUID) -> CapabilityEstimate:
        estimate = self.repository.get_capability_estimate(estimate_id)
        if estimate is None:
            raise PostBlockPreparationProjectionError(
                f"capability estimate {estimate_id} does not exist"
            )
        return estimate
