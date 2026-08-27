from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from agas_domain import (
    AssessmentDecision,
    AssessmentEligibilityOutcome,
    AssessmentPerformance,
    AssessmentResultInput,
    Confidence,
    Observation,
    Provenance,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import AssessmentError, AssessmentResultRecorder
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

NonEmptyText = Annotated[str, Field(min_length=1)]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class RecordAssessmentPerformanceCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    performed_at: datetime
    measurement: JsonValue
    unit: NonEmptyText
    reliability: Confidence
    provenance: Provenance

    @field_validator("performed_at")
    @classmethod
    def require_aware_performed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("performed_at must include a timezone")
        return value

    @field_validator("measurement")
    @classmethod
    def require_measurement(cls, value: JsonValue) -> JsonValue:
        if value is None:
            raise ValueError("measurement must contain a reported result")
        return value


class AssessmentPerformanceResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    performance: AssessmentPerformance
    result_observation: Observation


class AssessmentPerformanceError(RuntimeError):
    """Base error for governed assessment performance recording."""


class AssessmentPerformanceNotFoundError(AssessmentPerformanceError):
    pass


class AssessmentPerformanceConflictError(AssessmentPerformanceError):
    pass


class AssessmentPerformanceValidationError(AssessmentPerformanceError):
    pass


class PersistedAssessmentPerformanceService:
    """Record one selected self-administered assessment as a direct observation."""

    rule_version = "assessment-performance-recording@1.0.0"

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(
        self,
        athlete_id: UUID,
        run_id: UUID,
        selection_id: UUID,
        command: RecordAssessmentPerformanceCommand,
    ) -> AssessmentPerformanceResult:
        try:
            result = self._build(athlete_id, run_id, selection_id, command)
            self.repository.add_observation(result.result_observation)
            self.session.flush()
            self.repository.add_assessment_performance(result.performance)
            self.session.commit()
            return result
        except AssessmentPerformanceError:
            self.session.rollback()
            raise
        except (AssessmentError, DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise AssessmentPerformanceValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise AssessmentPerformanceConflictError(
                "assessment selection already has a result or conflicts with persisted history"
            ) from error

    def _build(
        self,
        athlete_id: UUID,
        run_id: UUID,
        selection_id: UUID,
        command: RecordAssessmentPerformanceCommand,
    ) -> AssessmentPerformanceResult:
        run = self.repository.get_assessment_selection_run(run_id)
        if run is None or run.athlete_id != athlete_id:
            raise AssessmentPerformanceNotFoundError("assessment run does not exist")
        if selection_id not in run.selection_ids:
            raise AssessmentPerformanceNotFoundError("assessment selection does not exist in run")
        selection = self.repository.get_assessment_selection(selection_id)
        if selection is None or selection.athlete_id != athlete_id:
            raise AssessmentPerformanceNotFoundError("assessment selection does not exist")
        if selection.decision is not AssessmentDecision.SELECTED:
            raise AssessmentPerformanceConflictError(
                "only an assessment selected by the run can record a result"
            )
        if command.performed_at < selection.evaluated_at:
            raise AssessmentPerformanceValidationError(
                "performed_at cannot predate the assessment selection"
            )
        if command.performed_at > _utc_now():
            raise AssessmentPerformanceValidationError("performed_at cannot be in the future")

        definition = self.repository.get_assessment_definition(selection.assessment_definition_id)
        if definition is None:
            raise AssessmentPerformanceNotFoundError("assessment definition does not exist")
        review = self.repository.get_current_assessment_definition_review(definition.id)
        if (
            review is None
            or review.id != selection.assessment_definition_review_id
            or review.decision.value != "approved"
            or not review.self_administered
        ):
            raise AssessmentPerformanceConflictError(
                "selected protocol is no longer approved for self-administration"
            )
        eligibility = self.repository.get_current_assessment_eligibility_review(athlete_id)
        if (
            eligibility is None
            or eligibility.id != selection.assessment_eligibility_review_id
            or eligibility.outcome is not AssessmentEligibilityOutcome.SELECTION_ALLOWED
            or not eligibility.reviewed_at <= command.performed_at < eligibility.valid_until
        ):
            raise AssessmentPerformanceConflictError(
                "assessment eligibility is no longer active for this selection"
            )

        result_input = AssessmentResultInput(
            athlete_id=athlete_id,
            assessment_definition_id=definition.id,
            performed_at=command.performed_at,
            measurement=command.measurement,
            unit=command.unit,
            reliability=command.reliability,
            context={
                "assessment_selection_run_id": str(run.id),
                "assessment_selection_id": str(selection.id),
                "assessment_definition_review_id": str(review.id),
                "assessment_eligibility_review_id": str(eligibility.id),
                "recording_rule_version": self.rule_version,
            },
            provenance=command.provenance,
        )
        observation = AssessmentResultRecorder().record(definition, result_input)
        performance = AssessmentPerformance(
            athlete_id=athlete_id,
            assessment_selection_run_id=run.id,
            assessment_selection_id=selection.id,
            assessment_definition_id=definition.id,
            assessment_definition_review_id=review.id,
            assessment_eligibility_review_id=eligibility.id,
            result_observation_id=observation.id,
            performed_at=command.performed_at,
            rule_version=self.rule_version,
        )
        return AssessmentPerformanceResult(
            performance=performance,
            result_observation=observation,
        )
