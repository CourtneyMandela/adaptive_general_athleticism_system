from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from agas_domain import (
    AssessmentReviewDecision,
    CapabilityEstimate,
    CapabilityEstimationPolicy,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import AssessmentError, ConservativeCapabilityEstimator
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def _utc_now() -> datetime:
    return datetime.now(UTC)


class AssessmentCapabilityEstimateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    estimate: CapabilityEstimate
    policy: CapabilityEstimationPolicy
    created: bool


class AssessmentCapabilityEstimationError(RuntimeError):
    """Base error for governed assessment capability estimation."""


class AssessmentCapabilityEstimationNotFoundError(AssessmentCapabilityEstimationError):
    pass


class AssessmentCapabilityEstimationConflictError(AssessmentCapabilityEstimationError):
    pass


class AssessmentCapabilityEstimationValidationError(AssessmentCapabilityEstimationError):
    pass


class PersistedAssessmentCapabilityEstimationService:
    """Apply the current reviewed policy to governed performances of one protocol."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(self, athlete_id: UUID, performance_id: UUID) -> AssessmentCapabilityEstimateResult:
        try:
            result = self._build(athlete_id, performance_id)
            if result.created:
                self.repository.add_capability_estimate(result.estimate)
                self.session.commit()
            return result
        except AssessmentCapabilityEstimationError:
            self.session.rollback()
            raise
        except (AssessmentError, DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise AssessmentCapabilityEstimationValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            policy = self._current_policy_for_performance(athlete_id, performance_id)
            existing = self.repository.get_assessment_capability_estimate(performance_id, policy.id)
            if existing is not None:
                return AssessmentCapabilityEstimateResult(
                    estimate=existing, policy=policy, created=False
                )
            raise AssessmentCapabilityEstimationConflictError(
                "capability estimate conflicts with persisted interpretation history"
            ) from error

    def _build(self, athlete_id: UUID, performance_id: UUID) -> AssessmentCapabilityEstimateResult:
        policy = self._current_policy_for_performance(athlete_id, performance_id)
        existing = self.repository.get_assessment_capability_estimate(performance_id, policy.id)
        if existing is not None:
            return AssessmentCapabilityEstimateResult(
                estimate=existing, policy=policy, created=False
            )

        performance = self.repository.get_assessment_performance(performance_id)
        if performance is None:
            raise AssessmentCapabilityEstimationNotFoundError(
                "assessment performance does not exist"
            )
        performances = tuple(
            item
            for item in self.repository.list_assessment_performances(athlete_id)
            if item.assessment_definition_id == performance.assessment_definition_id
            and item.assessment_definition_review_id == policy.assessment_definition_review_id
        )
        latest = max(
            performances,
            key=lambda item: (item.performed_at, item.created_at, str(item.id)),
        )
        if latest.id != performance.id:
            raise AssessmentCapabilityEstimationConflictError(
                "only the latest performance for a protocol can trigger a new estimate"
            )
        observations = []
        for item in performances:
            observation = self.repository.get_observation(item.result_observation_id)
            if observation is None:
                raise AssessmentCapabilityEstimationValidationError(
                    "assessment performance references a missing result observation"
                )
            observations.append(observation)
        estimate = ConservativeCapabilityEstimator().estimate(
            policy,
            observations,
            _utc_now(),
            triggering_assessment_performance_id=performance.id,
        )
        return AssessmentCapabilityEstimateResult(
            estimate=estimate,
            policy=policy,
            created=True,
        )

    def _current_policy_for_performance(
        self, athlete_id: UUID, performance_id: UUID
    ) -> CapabilityEstimationPolicy:
        performance = self.repository.get_assessment_performance(performance_id)
        if performance is None or performance.athlete_id != athlete_id:
            raise AssessmentCapabilityEstimationNotFoundError(
                "assessment performance does not exist"
            )
        policy = self.repository.get_current_capability_estimation_policy(
            performance.assessment_definition_id
        )
        current_review = self.repository.get_current_assessment_definition_review(
            performance.assessment_definition_id
        )
        if (
            policy is None
            or policy.decision is not AssessmentReviewDecision.APPROVED
            or current_review is None
            or current_review.id != policy.assessment_definition_review_id
            or current_review.decision is not AssessmentReviewDecision.APPROVED
            or performance.assessment_definition_review_id != policy.assessment_definition_review_id
            or policy.reviewed_at > _utc_now()
        ):
            raise AssessmentCapabilityEstimationConflictError(
                "no current approved capability estimation policy governs this protocol"
            )
        return policy
