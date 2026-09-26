from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from agas_domain import (
    AssessmentAttempt,
    AssessmentAttemptReason,
    AssessmentAttemptStatus,
    AssessmentDecision,
    AssessmentEligibilityOutcome,
    AssessmentReviewDecision,
    Confidence,
    Observation,
    ObservationSource,
    Provenance,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def _utc_now() -> datetime:
    return datetime.now(UTC)


class RecordAssessmentAttemptCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    attempted_at: datetime
    status: AssessmentAttemptStatus
    reason: AssessmentAttemptReason
    protocol_completed: Literal[False]
    stop_condition_occurred: bool
    reliability: Confidence
    provenance: Provenance

    @field_validator("attempted_at")
    @classmethod
    def require_aware_attempted_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("attempted_at must include a timezone")
        return value

    @model_validator(mode="after")
    def require_status_consistency(self) -> RecordAssessmentAttemptCommand:
        expected_stop = self.status is AssessmentAttemptStatus.SAFETY_STOPPED
        if self.stop_condition_occurred is not expected_stop:
            raise ValueError("attempt status must match whether a stop condition occurred")
        if self.reason is AssessmentAttemptReason.LEGACY_UNSPECIFIED:
            raise ValueError("legacy_unspecified is reserved for migrated historical attempts")
        listed_stop = self.reason is AssessmentAttemptReason.LISTED_STOP_CONDITION
        if listed_stop is not expected_stop:
            raise ValueError("attempt reason must match whether a listed stop condition occurred")
        return self


class AssessmentAttemptResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt: AssessmentAttempt
    attempt_observation: Observation
    eligible_for_capability_estimation: Literal[False] = False


class AssessmentAttemptError(RuntimeError):
    """Base error for incomplete assessment-attempt recording."""


class AssessmentAttemptNotFoundError(AssessmentAttemptError):
    pass


class AssessmentAttemptConflictError(AssessmentAttemptError):
    pass


class AssessmentAttemptValidationError(AssessmentAttemptError):
    pass


class PersistedAssessmentAttemptService:
    """Append an incomplete or safety-stopped attempt without creating a result."""

    rule_version = "assessment-attempt-recording@1.1.0"

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(
        self,
        athlete_id: UUID,
        run_id: UUID,
        selection_id: UUID,
        command: RecordAssessmentAttemptCommand,
    ) -> AssessmentAttemptResult:
        try:
            result = self._build(athlete_id, run_id, selection_id, command)
            self.repository.add_observation(result.attempt_observation)
            self.session.flush()
            self.repository.add_assessment_attempt(result.attempt)
            self.session.commit()
            return result
        except AssessmentAttemptError:
            self.session.rollback()
            raise
        except (DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise AssessmentAttemptValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise AssessmentAttemptConflictError(
                "assessment attempt conflicts with persisted history"
            ) from error

    def _build(
        self,
        athlete_id: UUID,
        run_id: UUID,
        selection_id: UUID,
        command: RecordAssessmentAttemptCommand,
    ) -> AssessmentAttemptResult:
        run = self.repository.get_assessment_selection_run(run_id)
        if run is None or run.athlete_id != athlete_id:
            raise AssessmentAttemptNotFoundError("assessment run does not exist")
        if selection_id not in run.selection_ids:
            raise AssessmentAttemptNotFoundError("assessment selection does not exist in run")
        selection = self.repository.get_assessment_selection(selection_id)
        if selection is None or selection.athlete_id != athlete_id:
            raise AssessmentAttemptNotFoundError("assessment selection does not exist")
        if selection.decision is not AssessmentDecision.SELECTED:
            raise AssessmentAttemptConflictError(
                "only an assessment selected by the run can record an attempt"
            )
        if any(
            attempt.status is AssessmentAttemptStatus.SAFETY_STOPPED
            for attempt in self.repository.list_assessment_attempts_for_selection(selection.id)
        ):
            raise AssessmentAttemptConflictError(
                "a safety-stopped attempt requires a new readiness review and assessment selection"
            )
        if self.repository.get_assessment_performance_for_selection(selection.id) is not None:
            raise AssessmentAttemptConflictError(
                "a completed assessment cannot record another attempt"
            )
        if command.attempted_at < selection.evaluated_at:
            raise AssessmentAttemptValidationError(
                "attempted_at cannot predate the assessment selection"
            )
        if command.attempted_at > _utc_now():
            raise AssessmentAttemptValidationError("attempted_at cannot be in the future")

        definition = self.repository.get_assessment_definition(selection.assessment_definition_id)
        if definition is None:
            raise AssessmentAttemptNotFoundError("assessment definition does not exist")
        review = self.repository.get_current_assessment_definition_review(definition.id)
        if (
            review is None
            or review.id != selection.assessment_definition_review_id
            or review.decision is not AssessmentReviewDecision.APPROVED
            or not review.self_administered
        ):
            raise AssessmentAttemptConflictError(
                "selected protocol is no longer approved for self-administration"
            )
        if not self.repository.evidence_authority_is_ready(
            review.evidence_claim_ids,
            review.reviewed_at,
        ):
            raise AssessmentAttemptConflictError(
                "selected protocol evidence was not ready at its review time"
            )
        eligibility = self.repository.get_current_assessment_eligibility_review(athlete_id)
        if (
            eligibility is None
            or eligibility.id != selection.assessment_eligibility_review_id
            or eligibility.outcome is not AssessmentEligibilityOutcome.SELECTION_ALLOWED
            or not eligibility.reviewed_at <= command.attempted_at < eligibility.valid_until
        ):
            raise AssessmentAttemptConflictError(
                "assessment eligibility is no longer active for this selection"
            )

        observation = Observation(
            created_at=command.attempted_at,
            athlete_id=athlete_id,
            observed_at=command.attempted_at,
            observation_type="assessment_attempt",
            measurement={
                "status": command.status.value,
                "reason": command.reason.value,
                "protocol_completed": command.protocol_completed,
                "stop_condition_occurred": command.stop_condition_occurred,
                "eligible_for_capability_estimation": False,
            },
            unit="attempt_status",
            source=ObservationSource.USER_REPORT,
            reliability=command.reliability,
            context={
                "assessment_selection_run_id": str(run.id),
                "assessment_selection_id": str(selection.id),
                "assessment_definition_id": str(definition.id),
                "assessment_definition_review_id": str(review.id),
                "assessment_eligibility_review_id": str(eligibility.id),
                "recording_rule_version": self.rule_version,
            },
            provenance=command.provenance,
        )
        attempt = AssessmentAttempt(
            created_at=command.attempted_at,
            athlete_id=athlete_id,
            assessment_selection_run_id=run.id,
            assessment_selection_id=selection.id,
            assessment_definition_id=definition.id,
            assessment_definition_review_id=review.id,
            assessment_eligibility_review_id=eligibility.id,
            attempt_observation_id=observation.id,
            status=command.status,
            reason=command.reason,
            attempted_at=command.attempted_at,
            rule_version=self.rule_version,
        )
        return AssessmentAttemptResult(
            attempt=attempt,
            attempt_observation=observation,
        )
