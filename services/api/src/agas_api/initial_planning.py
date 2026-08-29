from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from agas_domain import (
    AdaptationPlanningCandidate,
    AssessmentReviewDecision,
    CapabilityNeed,
    DecisionRecord,
    LongRangeStrategy,
    ReplanningCandidateContext,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import CompetencyFloorDetector, LongRangeStrategyPlanner, PlanningError
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class InitialPlanningCandidateContext(ReplanningCandidateContext):
    """Candidate inputs pinned to an exact competency-floor governance review."""

    competency_floor_review_id: UUID


class CreateInitialStrategyCommand(BaseModel):
    """Governed inputs for the first strategy; scores are explicit, not inferred."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    priority_policy_id: UUID
    priority_policy_review_id: UUID
    candidate_contexts: Annotated[tuple[InitialPlanningCandidateContext, ...], Field(min_length=1)]
    generated_at: datetime
    horizon_months: int = Field(ge=6, le=24)
    review_after_days: int = Field(ge=1)
    reviewed_by: Annotated[str, Field(min_length=1)]
    applicability_rationale: Annotated[str, Field(min_length=1)]
    uncertainty: Annotated[str, Field(min_length=1)]

    @field_validator("generated_at")
    @classmethod
    def require_aware_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at must include a timezone")
        return value

    @field_validator("reviewed_by", "applicability_rationale", "uncertainty")
    @classmethod
    def require_meaningful_review_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("operator review metadata must not be blank")
        return normalized

    @model_validator(mode="after")
    def require_one_context_per_adaptation(self) -> CreateInitialStrategyCommand:
        adaptation_ids = tuple(item.adaptation_id for item in self.candidate_contexts)
        if len(set(adaptation_ids)) != len(adaptation_ids):
            raise ValueError("candidate_contexts must contain each adaptation once")
        return self


class InitialStrategyCreationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    capability_needs: Annotated[tuple[CapabilityNeed, ...], Field(min_length=1)]
    strategy: LongRangeStrategy
    decision_record: DecisionRecord

    @model_validator(mode="after")
    def validate_result(self) -> InitialStrategyCreationResult:
        need_ids = tuple(item.id for item in self.capability_needs)
        if len(set(need_ids)) != len(need_ids):
            raise ValueError("initial strategy needs must have unique ids")
        if {item.capability_need_id for item in self.strategy.priorities} != set(need_ids):
            raise ValueError("initial strategy priorities must use the returned capability needs")
        return self


class InitialPlanningUseCaseError(RuntimeError):
    """Base error for persisted initial-strategy creation."""


class InitialPlanningNotFoundError(InitialPlanningUseCaseError):
    pass


class InitialPlanningConflictError(InitialPlanningUseCaseError):
    pass


class InitialPlanningValidationError(InitialPlanningUseCaseError):
    pass


class PersistedInitialPlanningService:
    """Identify needs and append an athlete's first strategy atomically."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(
        self, athlete_id: UUID, command: CreateInitialStrategyCommand
    ) -> InitialStrategyCreationResult:
        try:
            result = self._build_result(athlete_id, command)
            for need in result.capability_needs:
                self.repository.add_capability_need(need)
            self.session.flush()
            self.repository.add_long_range_strategy(result.strategy)
            self.repository.add_decision_record(result.decision_record)
            self.session.commit()
            return result
        except InitialPlanningUseCaseError:
            self.session.rollback()
            raise
        except (PlanningError, DomainIntegrityError) as error:
            self.session.rollback()
            raise InitialPlanningValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise InitialPlanningConflictError(
                "the athlete already has an initial long-range strategy"
            ) from error

    def _build_result(
        self, athlete_id: UUID, command: CreateInitialStrategyCommand
    ) -> InitialStrategyCreationResult:
        if self.repository.get_athlete(athlete_id) is None:
            raise InitialPlanningNotFoundError("athlete does not exist")
        if self.repository.get_initial_long_range_strategy(athlete_id) is not None:
            raise InitialPlanningConflictError(
                "the athlete already has an initial long-range strategy"
            )
        policy = self.repository.get_priority_policy(command.priority_policy_id)
        if policy is None:
            raise InitialPlanningNotFoundError("priority policy does not exist")
        policy_review = self.repository.get_priority_policy_review(
            command.priority_policy_review_id
        )
        if policy_review is None:
            raise InitialPlanningNotFoundError("priority policy review does not exist")
        current_policy_review = self.repository.get_current_priority_policy_review(policy.id)
        if (
            policy_review.priority_policy_id != policy.id
            or current_policy_review is None
            or current_policy_review.id != policy_review.id
        ):
            raise InitialPlanningValidationError(
                "initial planning requires the policy's exact current review"
            )
        if policy_review.decision is not AssessmentReviewDecision.APPROVED:
            raise InitialPlanningValidationError(
                "initial planning requires an approved priority policy review"
            )
        if policy_review.reviewed_at > command.generated_at:
            raise InitialPlanningValidationError(
                "priority policy review cannot come from the future"
            )

        detector = CompetencyFloorDetector()
        needs_by_pair: dict[tuple[UUID, UUID], CapabilityNeed] = {}
        adaptations_by_id = {}
        candidates = []

        for context in command.candidate_contexts:
            adaptation = self.repository.get_adaptation(context.adaptation_id)
            if adaptation is None:
                raise InitialPlanningNotFoundError(
                    f"adaptation {context.adaptation_id} does not exist"
                )
            floor = self.repository.get_competency_floor(context.competency_floor_id)
            if floor is None:
                raise InitialPlanningNotFoundError(
                    f"competency floor {context.competency_floor_id} does not exist"
                )
            floor_review = self.repository.get_competency_floor_review(
                context.competency_floor_review_id
            )
            if floor_review is None:
                raise InitialPlanningNotFoundError(
                    f"competency floor review {context.competency_floor_review_id} does not exist"
                )
            current_floor_review = self.repository.get_current_competency_floor_review(floor.id)
            if (
                floor_review.competency_floor_id != floor.id
                or current_floor_review is None
                or current_floor_review.id != floor_review.id
            ):
                raise InitialPlanningValidationError(
                    "initial planning requires each floor's exact current review"
                )
            if floor_review.decision is not AssessmentReviewDecision.APPROVED:
                raise InitialPlanningValidationError(
                    "initial planning requires approved competency floor reviews"
                )
            if floor_review.reviewed_at > command.generated_at:
                raise InitialPlanningValidationError(
                    "competency floor review cannot come from the future"
                )
            estimate = self.repository.get_capability_estimate(context.capability_estimate_id)
            if estimate is None:
                raise InitialPlanningNotFoundError(
                    f"capability estimate {context.capability_estimate_id} does not exist"
                )
            if estimate.athlete_id != athlete_id:
                raise InitialPlanningValidationError(
                    "capability estimate belongs to a different athlete"
                )
            if estimate.estimated_at > command.generated_at:
                raise InitialPlanningValidationError(
                    "capability estimate cannot come from the future"
                )

            for prerequisite_id in context.prerequisite_adaptation_ids:
                if self.repository.get_adaptation(prerequisite_id) is None:
                    raise InitialPlanningNotFoundError(
                        f"prerequisite adaptation {prerequisite_id} does not exist"
                    )
            for observation_id in context.source_observation_ids:
                observation = self.repository.get_observation(observation_id)
                if observation is None:
                    raise InitialPlanningNotFoundError(
                        f"source observation {observation_id} does not exist"
                    )
                if observation.athlete_id != athlete_id:
                    raise InitialPlanningValidationError(
                        "source observation belongs to a different athlete"
                    )
            for evidence_id in context.evidence_claim_ids:
                if self.repository.get_evidence_claim(evidence_id) is None:
                    raise InitialPlanningNotFoundError(
                        f"evidence claim {evidence_id} does not exist"
                    )

            pair = (floor.id, estimate.id)
            need = needs_by_pair.get(pair)
            if need is None:
                need = detector.identify(
                    athlete_id=athlete_id,
                    floor=floor,
                    estimate=estimate,
                    identified_at=command.generated_at,
                )
                needs_by_pair[pair] = need

            source_ids = tuple(
                dict.fromkeys((*context.source_observation_ids, *estimate.source_observation_ids))
            )
            evidence_ids = tuple(
                dict.fromkeys((*context.evidence_claim_ids, *floor.evidence_claim_ids))
            )
            candidates.append(
                AdaptationPlanningCandidate(
                    adaptation_id=context.adaptation_id,
                    capability_need_id=need.id,
                    general_relevance=context.general_relevance,
                    goal_relevance=context.goal_relevance,
                    prerequisite_value=context.prerequisite_value,
                    expected_trainability=context.expected_trainability,
                    transfer_value=context.transfer_value,
                    fatigue_cost=context.fatigue_cost,
                    time_cost=context.time_cost,
                    interference_cost=context.interference_cost,
                    safe_to_train=context.safe_to_train,
                    introductory_exposure_needed=context.introductory_exposure_needed,
                    prerequisites_met=context.prerequisites_met,
                    prerequisite_adaptation_ids=context.prerequisite_adaptation_ids,
                    cultivate_comparative_advantage=context.cultivate_comparative_advantage,
                    source_observation_ids=source_ids,
                    evidence_claim_ids=evidence_ids,
                )
            )
            adaptations_by_id[adaptation.id] = adaptation

        needs = tuple(needs_by_pair.values())
        strategy = LongRangeStrategyPlanner().build(
            athlete_id=athlete_id,
            adaptations=adaptations_by_id.values(),
            needs=needs,
            candidates=candidates,
            policy=policy,
            generated_at=command.generated_at,
            horizon_months=command.horizon_months,
            review_after_days=command.review_after_days,
        )
        decision_record = DecisionRecord(
            decision=(
                f"Create initial long-range strategy {strategy.id} for athlete {athlete_id}."
            ),
            reason=(f"Reviewed by {command.reviewed_by}. {command.applicability_rationale}"),
            alternatives_considered=(
                "Defer initial strategy until different governed inputs are available.",
            ),
            evidence=self._decision_evidence(command, strategy),
            uncertainty=command.uncertainty,
            decision_version=(
                f"initial-strategy-operator-review@1.0.0;planner={strategy.rule_version}"
            ),
            decided_on=command.generated_at.date(),
        )
        return InitialStrategyCreationResult(
            capability_needs=needs,
            strategy=strategy,
            decision_record=decision_record,
        )

    @staticmethod
    def _decision_evidence(
        command: CreateInitialStrategyCommand, strategy: LongRangeStrategy
    ) -> tuple[str, ...]:
        values = [
            f"priority_policy:{command.priority_policy_id}",
            f"priority_policy_review:{command.priority_policy_review_id}",
            *(f"adaptation:{item.adaptation_id}" for item in command.candidate_contexts),
            *(f"capability_estimate:{item}" for item in strategy.source_capability_estimate_ids),
            *(f"competency_floor:{item}" for item in strategy.competency_floor_ids),
            *(
                f"competency_floor_review:{item.competency_floor_review_id}"
                for item in command.candidate_contexts
            ),
            *(f"observation:{item}" for item in strategy.source_observation_ids),
            *(f"evidence_claim:{item}" for item in strategy.evidence_claim_ids),
        ]
        return tuple(dict.fromkeys(values))
