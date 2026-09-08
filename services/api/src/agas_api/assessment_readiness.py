from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from agas_domain import (
    AssessmentEligibilityOutcome,
    AssessmentEligibilityReview,
    AssessmentIntensity,
    Confidence,
    Observation,
    ObservationSource,
    Provenance,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agas_api.identity import AuthenticatedPrincipal

READINESS_RULE_VERSION = "assessment-readiness-screen@1.0.0"
SCREENING_PROCESS_REFERENCE = (
    "agas-readiness@1.0.0;ACSM-factors:PMID26473759;application:PMID28557860"
)
READINESS_VALID_FOR = timedelta(hours=24)
Answer = Literal["no", "yes", "unsure"]


class SubmitAssessmentReadinessReportCommand(BaseModel):
    """Factual self-report inputs; the caller cannot choose the eligibility outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    report_id: UUID
    reported_at: datetime
    adult_confirmed: bool
    regular_moderate_activity_last_three_months: Answer
    known_cardiovascular_metabolic_or_renal_disease: Answer
    concerning_signs_or_symptoms: Answer
    clinician_exercise_restriction: Answer
    current_lower_body_or_balance_concern: Answer
    controlled_chair_stand_without_arms: Answer
    answers_confirmed: Literal[True]

    @field_validator("reported_at")
    @classmethod
    def require_aware_reported_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reported_at must include a timezone")
        return value


class AssessmentReadinessReportResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: UUID
    eligibility_review_id: UUID
    outcome: AssessmentEligibilityOutcome
    maximum_assessment_intensity: AssessmentIntensity
    valid_until: datetime
    next_action: str
    created: bool
    rule_version: str = READINESS_RULE_VERSION


class AssessmentReadinessNotFoundError(LookupError):
    pass


class AssessmentReadinessConflictError(RuntimeError):
    pass


class AssessmentReadinessValidationError(ValueError):
    pass


class PersistedAssessmentReadinessService:
    """Persist a minimal report and deterministic, time-bounded eligibility decision atomically."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(
        self,
        athlete_id: UUID,
        command: SubmitAssessmentReadinessReportCommand,
        principal: AuthenticatedPrincipal,
        *,
        recorded_at: datetime | None = None,
    ) -> AssessmentReadinessReportResult:
        instant = recorded_at or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise AssessmentReadinessValidationError("recording time must include a timezone")
        if self.repository.get_athlete(athlete_id) is None:
            raise AssessmentReadinessNotFoundError("athlete does not exist")

        observation = self._observation(athlete_id, command, principal)
        existing = self.repository.get_observation(command.report_id)
        current = self.repository.get_current_assessment_eligibility_review(athlete_id)
        if existing is not None:
            if existing != observation:
                raise AssessmentReadinessConflictError(
                    "readiness report identity is already occupied by different content"
                )
            if (
                current is None
                or current.source_observation_ids != (observation.id,)
                or current.rule_version != READINESS_RULE_VERSION
            ):
                raise AssessmentReadinessConflictError(
                    "readiness report was already processed but is no longer the current decision"
                )
            return self._result(current, created=False)

        if command.reported_at > instant + timedelta(minutes=5):
            raise AssessmentReadinessValidationError("reported_at cannot be in the future")
        if command.reported_at < instant - timedelta(minutes=15):
            raise AssessmentReadinessValidationError(
                "a new readiness report must describe the athlete's current state"
            )
        if current is not None and command.reported_at < current.reviewed_at:
            raise AssessmentReadinessConflictError(
                "readiness report cannot predate the current eligibility decision"
            )

        outcome, rationale, next_action = self._evaluate(command)
        review = AssessmentEligibilityReview(
            created_at=command.reported_at,
            athlete_id=athlete_id,
            outcome=outcome,
            sequence_number=1 if current is None else current.sequence_number + 1,
            supersedes_review_id=None if current is None else current.id,
            source_observation_ids=(observation.id,),
            reviewed_at=command.reported_at,
            valid_until=command.reported_at + READINESS_VALID_FOR,
            maximum_assessment_intensity=AssessmentIntensity.MODERATE,
            reviewed_by=f"deterministic-rule:{READINESS_RULE_VERSION}",
            screening_process_reference=SCREENING_PROCESS_REFERENCE,
            rationale=rationale,
            uncertainty=(
                "This decision uses a current self-report, not a physical examination or medical "
                "clearance. It is limited to evidence-ready low/moderate self-administered "
                "assessment selection and expires after 24 hours."
            ),
            rule_version=READINESS_RULE_VERSION,
        )
        try:
            self.repository.add_observation(observation)
            self.session.flush()
            self.repository.add_assessment_eligibility_review(review)
            self.session.commit()
        except DomainIntegrityError as error:
            self.session.rollback()
            raise AssessmentReadinessValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise AssessmentReadinessConflictError(
                "readiness report conflicts with persisted athlete history"
            ) from error
        except Exception:
            self.session.rollback()
            raise
        return self._result(review, created=True).model_copy(update={"next_action": next_action})

    @staticmethod
    def _observation(
        athlete_id: UUID,
        command: SubmitAssessmentReadinessReportCommand,
        principal: AuthenticatedPrincipal,
    ) -> Observation:
        return Observation(
            id=command.report_id,
            created_at=command.reported_at,
            athlete_id=athlete_id,
            observed_at=command.reported_at,
            observation_type="assessment_readiness_self_report",
            measurement={
                "adult_confirmed": command.adult_confirmed,
                "regular_moderate_activity_last_three_months": (
                    command.regular_moderate_activity_last_three_months
                ),
                "known_cardiovascular_metabolic_or_renal_disease": (
                    command.known_cardiovascular_metabolic_or_renal_disease
                ),
                "concerning_signs_or_symptoms": command.concerning_signs_or_symptoms,
                "clinician_exercise_restriction": command.clinician_exercise_restriction,
                "current_lower_body_or_balance_concern": (
                    command.current_lower_body_or_balance_concern
                ),
                "controlled_chair_stand_without_arms": (
                    command.controlled_chair_stand_without_arms
                ),
            },
            source=ObservationSource.USER_REPORT,
            reliability=Confidence.MODERATE,
            context={
                "readiness_rule_version": READINESS_RULE_VERSION,
                "intended_assessment_intensity": AssessmentIntensity.MODERATE.value,
                "evidence_source_identifiers": ["PMID:26473759", "PMID:28557860"],
                "data_minimization": "grouped readiness factors; no diagnosis inferred",
            },
            provenance=Provenance(
                recorded_by=f"{principal.issuer}:{principal.subject}",
                source_system="agas-web",
                ingestion_method="authenticated-assessment-readiness-report",
            ),
        )

    @staticmethod
    def _evaluate(
        command: SubmitAssessmentReadinessReportCommand,
    ) -> tuple[AssessmentEligibilityOutcome, str, str]:
        if not command.adult_confirmed:
            return (
                AssessmentEligibilityOutcome.SELECTION_BLOCKED,
                "The owner-alpha assessment workflow is limited to adults.",
                "Do not perform the assessment through AGAS.",
            )
        concern_answers = (
            command.known_cardiovascular_metabolic_or_renal_disease,
            command.concerning_signs_or_symptoms,
            command.clinician_exercise_restriction,
            command.current_lower_body_or_balance_concern,
        )
        if "yes" in concern_answers or "unsure" in concern_answers:
            return (
                AssessmentEligibilityOutcome.REVIEW_REQUIRED,
                "At least one safety-relevant factor was present or uncertain; AGAS does not "
                "interpret its medical significance.",
                "Do not perform the assessment. Seek appropriate qualified guidance before "
                "submitting a new current-state report.",
            )
        if command.controlled_chair_stand_without_arms != "yes":
            return (
                AssessmentEligibilityOutcome.REVIEW_REQUIRED,
                "A controlled unassisted repetition was not confirmed, so the full timed test is "
                "not authorized.",
                "Do not perform the timed assessment. Seek appropriate qualified guidance if the "
                "movement is difficult, painful, or uncertain.",
            )
        return (
            AssessmentEligibilityOutcome.SELECTION_ALLOWED,
            "The adult athlete reported no listed safety concern or restriction and confirmed one "
            "controlled unassisted chair stand. Current activity was recorded as context and was "
            "not converted into a fitness judgment.",
            "Continue to governed low/moderate assessment selection. Stop if current state "
            "changes.",
        )

    @staticmethod
    def _result(
        review: AssessmentEligibilityReview,
        *,
        created: bool,
    ) -> AssessmentReadinessReportResult:
        if review.outcome is AssessmentEligibilityOutcome.SELECTION_ALLOWED:
            next_action = "Continue to governed low/moderate assessment selection."
        elif review.outcome is AssessmentEligibilityOutcome.SELECTION_BLOCKED:
            next_action = "Do not perform the assessment through AGAS."
        else:
            next_action = "Do not perform the assessment; seek appropriate qualified guidance."
        return AssessmentReadinessReportResult(
            observation_id=review.source_observation_ids[0],
            eligibility_review_id=review.id,
            outcome=review.outcome,
            maximum_assessment_intensity=review.maximum_assessment_intensity,
            valid_until=review.valid_until,
            next_action=next_action,
            created=created,
        )
