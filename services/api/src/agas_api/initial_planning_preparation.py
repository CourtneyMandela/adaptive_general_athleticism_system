from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from agas_domain import (
    Adaptation,
    AssessmentReviewDecision,
    CapabilityEstimate,
    CompetencyFloor,
    CompetencyFloorReview,
    EvidenceClaim,
    Observation,
    PriorityPolicy,
    PriorityPolicyReview,
)
from agas_domain.persistence.repository import DomainRepository
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

InitialPlanningPreparationStatus = Literal[
    "capability_estimate_required",
    "capability_estimate_stale",
    "planning_authorities_required",
    "planning_context_review_required",
    "initial_strategy_exists",
]


class InitialPlanningPreparationNotFoundError(LookupError):
    pass


class InitialPlanningPreparationProjectionError(RuntimeError):
    pass


class InitialPlanningFloorOption(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    floor: CompetencyFloor
    review: CompetencyFloorReview


class InitialPlanningEstimateOption(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    estimate: CapabilityEstimate
    source_observations: tuple[Observation, ...]
    floor_options: tuple[InitialPlanningFloorOption, ...]
    adaptation_options: tuple[Adaptation, ...]


class InitialPlanningPriorityPolicyOption(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy: PriorityPolicy
    review: PriorityPolicyReview


class InitialPlanningPreparationProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    athlete_id: UUID
    athlete_display_name: str
    projected_at: datetime
    status: InitialPlanningPreparationStatus
    message: str
    initial_strategy_id: UUID | None
    estimate_options: tuple[InitialPlanningEstimateOption, ...]
    stale_estimates: tuple[CapabilityEstimate, ...]
    priority_policy_options: tuple[InitialPlanningPriorityPolicyOption, ...]
    evidence_claims: tuple[EvidenceClaim, ...]
    projection_version: str = "initial-planning-preparation@1.0.0"


class InitialPlanningPreparationProjector:
    """Assemble eligible reviewed inputs without deriving candidate scores."""

    def __init__(self, session: Session) -> None:
        self.repository = DomainRepository(session)

    def project(
        self, athlete_id: UUID, projected_at: datetime | None = None
    ) -> InitialPlanningPreparationProjection:
        athlete = self.repository.get_athlete(athlete_id)
        if athlete is None:
            raise InitialPlanningPreparationNotFoundError("athlete does not exist")
        instant = projected_at or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("initial-planning preparation time must include a timezone")

        estimates = tuple(
            estimate
            for estimate in self.repository.list_capability_estimates(athlete.id)
            if estimate.estimated_at <= instant
        )
        current_estimates = tuple(
            estimate
            for estimate in estimates
            if estimate.valid_until is None or estimate.valid_until > instant
        )
        stale_estimates = tuple(
            estimate
            for estimate in estimates
            if estimate.valid_until is not None and estimate.valid_until <= instant
        )
        adaptations = self.repository.list_adaptations()
        floor_options = self._approved_floor_options(instant)
        policy_options = self._approved_policy_options(instant)
        estimate_options = tuple(
            self._estimate_option(estimate, adaptations, floor_options)
            for estimate in current_estimates
        )
        evidence_claims = self._evidence_claims(policy_options, estimate_options)
        strategy = self.repository.get_initial_long_range_strategy(athlete.id)
        status, message = self._status(
            strategy_exists=strategy is not None,
            current_estimates=current_estimates,
            stale_estimates=stale_estimates,
            policy_options=policy_options,
            estimate_options=estimate_options,
        )
        return InitialPlanningPreparationProjection(
            athlete_id=athlete.id,
            athlete_display_name=athlete.display_name,
            projected_at=instant,
            status=status,
            message=message,
            initial_strategy_id=strategy.id if strategy is not None else None,
            estimate_options=estimate_options,
            stale_estimates=stale_estimates,
            priority_policy_options=policy_options,
            evidence_claims=evidence_claims,
        )

    def _approved_floor_options(self, instant: datetime) -> tuple[InitialPlanningFloorOption, ...]:
        options = []
        for floor in self.repository.list_competency_floors():
            review = self.repository.get_current_competency_floor_review(floor.id)
            if (
                review is not None
                and review.decision is AssessmentReviewDecision.APPROVED
                and review.reviewed_at <= instant
            ):
                options.append(InitialPlanningFloorOption(floor=floor, review=review))
        return tuple(options)

    def _approved_policy_options(
        self, instant: datetime
    ) -> tuple[InitialPlanningPriorityPolicyOption, ...]:
        options = []
        for policy in self.repository.list_priority_policies():
            review = self.repository.get_current_priority_policy_review(policy.id)
            if (
                review is not None
                and review.decision is AssessmentReviewDecision.APPROVED
                and review.reviewed_at <= instant
            ):
                options.append(InitialPlanningPriorityPolicyOption(policy=policy, review=review))
        return tuple(options)

    def _estimate_option(
        self,
        estimate: CapabilityEstimate,
        adaptations: tuple[Adaptation, ...],
        floors: tuple[InitialPlanningFloorOption, ...],
    ) -> InitialPlanningEstimateOption:
        observations = []
        for observation_id in estimate.source_observation_ids:
            observation = self.repository.get_observation(observation_id)
            if observation is None:
                raise InitialPlanningPreparationProjectionError(
                    f"source observation {observation_id} does not exist"
                )
            if observation.athlete_id != estimate.athlete_id:
                raise InitialPlanningPreparationProjectionError(
                    "capability-estimate observation belongs to a different athlete"
                )
            observations.append(observation)
        return InitialPlanningEstimateOption(
            estimate=estimate,
            source_observations=tuple(observations),
            floor_options=tuple(
                item for item in floors if self._floor_matches_estimate(item.floor, estimate)
            ),
            adaptation_options=tuple(
                adaptation for adaptation in adaptations if adaptation.domain is estimate.domain
            ),
        )

    def _evidence_claims(
        self,
        policies: tuple[InitialPlanningPriorityPolicyOption, ...],
        estimates: tuple[InitialPlanningEstimateOption, ...],
    ) -> tuple[EvidenceClaim, ...]:
        evidence_ids: list[UUID] = []
        for policy_option in policies:
            evidence_ids.extend(policy_option.review.evidence_claim_ids)
        for estimate_option in estimates:
            for floor_option in estimate_option.floor_options:
                evidence_ids.extend(floor_option.floor.evidence_claim_ids)
                evidence_ids.extend(floor_option.review.evidence_claim_ids)
            for adaptation in estimate_option.adaptation_options:
                evidence_ids.extend(adaptation.evidence_claim_ids)
                for relationship in adaptation.relationships:
                    evidence_ids.extend(relationship.evidence_claim_ids)
        claims = []
        for claim_id in dict.fromkeys(evidence_ids):
            claim = self.repository.get_evidence_claim(claim_id)
            if claim is None:
                raise InitialPlanningPreparationProjectionError(
                    f"referenced evidence claim {claim_id} does not exist"
                )
            claims.append(claim)
        return tuple(claims)

    @staticmethod
    def _floor_matches_estimate(floor: CompetencyFloor, estimate: CapabilityEstimate) -> bool:
        return (
            floor.domain is estimate.domain
            and floor.estimate_scope == estimate.estimate_scope
            and floor.unit_or_scale == estimate.unit_or_scale
        )

    @staticmethod
    def _status(
        *,
        strategy_exists: bool,
        current_estimates: tuple[CapabilityEstimate, ...],
        stale_estimates: tuple[CapabilityEstimate, ...],
        policy_options: tuple[InitialPlanningPriorityPolicyOption, ...],
        estimate_options: tuple[InitialPlanningEstimateOption, ...],
    ) -> tuple[InitialPlanningPreparationStatus, str]:
        if strategy_exists:
            return (
                "initial_strategy_exists",
                "This athlete already has a root strategy. Later changes require review-linked "
                "replanning rather than another initial strategy.",
            )
        if not current_estimates and stale_estimates:
            return (
                "capability_estimate_stale",
                "Only stale capability estimates are available; reassessment or governed "
                "reinterpretation is required.",
            )
        if not current_estimates:
            return (
                "capability_estimate_required",
                "No current capability estimate is available for initial planning.",
            )
        eligible_estimate_count = sum(
            bool(option.floor_options and option.adaptation_options) for option in estimate_options
        )
        if not policy_options or eligible_estimate_count == 0:
            return (
                "planning_authorities_required",
                "Current estimates exist, but no complete approved policy, compatible floor, and "
                "adaptation path is available.",
            )
        return (
            "planning_context_review_required",
            "Reviewed authority and athlete-state options are available. Candidate relevance, "
            "cost, applicability, provenance, and uncertainty still require explicit review.",
        )
