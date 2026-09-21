from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID, uuid5

from agas_domain import (
    AssessmentEligibilityOutcome,
    Confidence,
    Environment,
    Exercise,
    ExposureNeed,
    ExposureNeedStatus,
    IntroductoryExposureExecution,
    Observation,
    ObservationSource,
    Provenance,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import EnvironmentSnapshotBuilder, IntroductoryExposureDosePlanner
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agas_api.assessment_readiness import JUMP_EXPOSURE_TARGET_SCOPE
from agas_api.training_construction_candidates import (
    prepared_training_construction_candidate_for_scope,
)

INTRODUCTORY_EXPOSURE_DOSE_NAMESPACE = UUID("b94379d6-2f41-43b2-aa05-58e7e9441f8c")
INTRODUCTORY_EXPOSURE_OBSERVATION_NAMESPACE = UUID("7eb7baa1-32d7-4c1d-9a0f-3e1aa373bfa6")
INTRODUCTORY_EXPOSURE_NEED_NAMESPACE = UUID("c43bd7b9-3394-4f14-a58a-85c18bbdba35")
INTRODUCTORY_EXPOSURE_RULE_VERSION = "introductory-exposure-execution@1.0.0"


class RecordIntroductoryExposureCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: UUID
    exposure_need_id: UUID
    environment_id: UUID
    started_at: datetime
    ended_at: datetime
    actual_sets: int = Field(ge=0)
    actual_contacts: int = Field(ge=0)
    session_rpe: float | None = Field(default=None, ge=0, le=10)
    pre_session_ready: bool
    controlled_landings: bool
    stop_condition_occurred: bool
    answers_confirmed: Literal[True]
    reliability: Confidence
    provenance: Provenance

    @field_validator("started_at", "ended_at")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("execution timestamps must include a timezone")
        return value


class IntroductoryExposureExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution: IntroductoryExposureExecution
    observation: Observation
    current_exposure_need: ExposureNeed
    qualifying_exposure_days: int
    required_exposure_days: int
    created: bool
    next_action: str


class IntroductoryExposureError(RuntimeError):
    pass


class IntroductoryExposureNotFoundError(IntroductoryExposureError):
    pass


class IntroductoryExposureConflictError(IntroductoryExposureError):
    pass


class IntroductoryExposureValidationError(IntroductoryExposureError):
    pass


class PersistedIntroductoryExposureService:
    """Record one bounded assessment-preparation exposure and append its derived state."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(
        self, athlete_id: UUID, command: RecordIntroductoryExposureCommand
    ) -> IntroductoryExposureExecutionResult:
        try:
            existing = self.repository.get_introductory_exposure_execution(command.execution_id)
            if existing is not None:
                if existing.athlete_id != athlete_id:
                    raise IntroductoryExposureConflictError(
                        "execution identity already belongs to another athlete"
                    )
                if not self._execution_matches_command(existing, command):
                    raise IntroductoryExposureConflictError(
                        "execution identity was already used with different content"
                    )
                observation = self.repository.get_observation(existing.performance_observation_id)
                if observation is None:
                    raise IntroductoryExposureConflictError(
                        "existing execution is missing its observation"
                    )
                current_need = self._latest_need(athlete_id)
                days = self._qualifying_days(
                    athlete_id,
                    current_need,
                    max(command.ended_at, current_need.identified_at),
                )
                return self._result(existing, observation, current_need, days, created=False)

            execution, observation, next_need = self._build(athlete_id, command)
            dose = self.repository.get_introductory_exposure_dose(
                execution.introductory_exposure_dose_id
            )
            if dose is None:
                raise IntroductoryExposureConflictError("derived dose was not persisted")
            self.repository.add_observation(observation)
            self.session.flush()
            self.repository.add_introductory_exposure_execution(execution)
            self.session.flush()
            if next_need.id != execution.exposure_need_id:
                self.repository.add_exposure_need(next_need)
            self.session.commit()
            days = self._qualifying_days(athlete_id, next_need, command.ended_at)
            return self._result(execution, observation, next_need, days, created=True)
        except IntroductoryExposureError:
            self.session.rollback()
            raise
        except (DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise IntroductoryExposureValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise IntroductoryExposureConflictError(
                "introductory exposure conflicts with persisted history"
            ) from error

    def _build(
        self, athlete_id: UUID, command: RecordIntroductoryExposureCommand
    ) -> tuple[IntroductoryExposureExecution, Observation, ExposureNeed]:
        if self.repository.get_athlete(athlete_id) is None:
            raise IntroductoryExposureNotFoundError("athlete does not exist")
        need = self._latest_need(athlete_id)
        if need.id != command.exposure_need_id:
            raise IntroductoryExposureConflictError(
                "exposure need is no longer current; refresh before recording"
            )
        if (
            need.status is not ExposureNeedStatus.INTRODUCTORY_EXPOSURE_NEEDED
            or need.identified_at > command.started_at
            or (need.valid_until is not None and need.valid_until <= command.started_at)
            or (need.valid_until is not None and need.valid_until <= command.ended_at)
        ):
            raise IntroductoryExposureConflictError(
                "current exposure need does not authorize an introductory session"
            )
        if command.ended_at < command.started_at:
            raise IntroductoryExposureValidationError("ended_at cannot precede started_at")
        if command.ended_at - command.started_at > timedelta(hours=2):
            raise IntroductoryExposureValidationError(
                "introductory exposure duration cannot exceed two hours"
            )
        self._require_current_readiness(athlete_id, need, command.started_at)
        if not command.pre_session_ready:
            raise IntroductoryExposureValidationError(
                "do not start this exposure when the pre-session readiness check is not clear"
            )

        prepared = prepared_training_construction_candidate_for_scope(need.target_scope)
        release = prepared.release
        policy = release.introductory_exposure_dose_policy
        definition = release.exposure_definition
        if policy is None or definition is None:
            raise IntroductoryExposureNotFoundError(
                "governed introductory exposure authorities are unavailable"
            )
        decision = self.repository.get_decision_record(prepared.presentation.candidate_id)
        if (
            decision is None
            or f"candidate_content_digest:{prepared.presentation.content_digest}"
            not in decision.evidence
            or self.repository.get_introductory_exposure_dose_policy(policy.id) != policy
            or self.repository.get_exposure_definition(definition.id) != definition
        ):
            raise IntroductoryExposureConflictError(
                "governed introductory exposure authorities are not ratified exactly"
            )
        adaptation = self.repository.get_adaptation(policy.adaptation_id)
        exercise = self.repository.get_exercise(definition.exercise_id)
        environment = self.repository.get_environment(command.environment_id)
        if adaptation is None or exercise is None:
            raise IntroductoryExposureNotFoundError(
                "introductory exposure exercise or adaptation is unavailable"
            )
        if environment is None or environment.athlete_id != athlete_id:
            raise IntroductoryExposureNotFoundError(
                "selected environment does not belong to this athlete"
            )
        self._require_compatible_environment(environment, exercise, command.started_at)
        if any(
            item.started_at.date() == command.started_at.date()
            for item in self.repository.list_introductory_exposure_executions(athlete_id)
        ):
            raise IntroductoryExposureConflictError(
                "only one introductory jump-exposure session may be recorded per day"
            )

        dose = self.repository.get_introductory_exposure_dose_for_need_policy(need.id, policy.id)
        if dose is None:
            dose = IntroductoryExposureDosePlanner().derive(
                dose_id=uuid5(INTRODUCTORY_EXPOSURE_DOSE_NAMESPACE, f"{need.id}:{policy.id}"),
                need=need,
                adaptation=adaptation,
                policy=policy,
                derived_at=command.started_at,
            )
            self.repository.add_introductory_exposure_dose(dose)
            self.session.flush()

        if not command.controlled_landings and not command.stop_condition_occurred:
            raise IntroductoryExposureValidationError(
                "loss of controlled landing must be recorded as a stop condition"
            )
        completed_exactly = (
            command.pre_session_ready
            and not command.stop_condition_occurred
            and command.controlled_landings
            and command.actual_sets == dose.sets
            and command.actual_contacts == dose.total_dose
            and command.session_rpe is not None
            and command.session_rpe <= dose.effort_rpe_maximum
        )
        status: Literal["completed", "partial", "stopped_safety"]
        if command.stop_condition_occurred:
            status = "stopped_safety"
        elif completed_exactly:
            status = "completed"
        else:
            status = "partial"

        observation_id = uuid5(
            INTRODUCTORY_EXPOSURE_OBSERVATION_NAMESPACE, str(command.execution_id)
        )
        observation = Observation(
            id=observation_id,
            created_at=command.ended_at,
            athlete_id=athlete_id,
            observed_at=command.ended_at,
            observation_type="introductory_jump_exposure_execution",
            measurement={
                "actual_sets": command.actual_sets,
                "actual_contacts": command.actual_contacts,
                "session_rpe": command.session_rpe,
                "pre_session_ready": command.pre_session_ready,
                "controlled_landings": command.controlled_landings,
                "stop_condition_occurred": command.stop_condition_occurred,
                "status": status,
                "qualifies_as_exposure_day": completed_exactly,
            },
            unit="jump_contacts",
            source=ObservationSource.USER_REPORT,
            reliability=command.reliability,
            context={
                "exposure_need_id": str(need.id),
                "introductory_exposure_dose_id": str(dose.id),
                "exposure_definition_id": str(definition.id),
                "exercise_id": str(exercise.id),
                "environment_id": str(environment.id),
            },
            provenance=command.provenance,
        )
        execution = IntroductoryExposureExecution(
            id=command.execution_id,
            created_at=command.ended_at,
            athlete_id=athlete_id,
            exposure_need_id=need.id,
            introductory_exposure_dose_id=dose.id,
            exposure_definition_id=definition.id,
            exercise_id=exercise.id,
            environment_id=environment.id,
            performance_observation_id=observation.id,
            status=status,
            actual_sets=command.actual_sets,
            actual_dose=command.actual_contacts,
            dose_unit=dose.dose_unit,
            session_rpe=command.session_rpe,
            pre_session_ready=command.pre_session_ready,
            controlled_technique=command.controlled_landings,
            stop_condition_occurred=command.stop_condition_occurred,
            qualifies_as_exposure_day=completed_exactly,
            started_at=command.started_at,
            ended_at=command.ended_at,
            rule_version=INTRODUCTORY_EXPOSURE_RULE_VERSION,
        )
        next_need = self._derive_next_need(need, execution, observation)
        return execution, observation, next_need

    def _latest_need(self, athlete_id: UUID) -> ExposureNeed:
        needs = self.repository.list_exposure_needs(
            athlete_id,
            exposure_type="jumping",
            target_scope=JUMP_EXPOSURE_TARGET_SCOPE,
        )
        if not needs:
            raise IntroductoryExposureNotFoundError(
                "no jump-exposure need exists; complete readiness first"
            )
        return needs[0]

    def _require_current_readiness(
        self, athlete_id: UUID, need: ExposureNeed, at: datetime
    ) -> None:
        eligibility = self.repository.get_current_assessment_eligibility_review(athlete_id)
        if (
            eligibility is None
            or eligibility.outcome is not AssessmentEligibilityOutcome.SELECTION_ALLOWED
            or not eligibility.reviewed_at <= at < eligibility.valid_until
        ):
            raise IntroductoryExposureConflictError(
                "a current allowed readiness review is required"
            )
        report = self.repository.get_observation(eligibility.source_observation_ids[0])
        if report is None or not isinstance(report.measurement, dict):
            raise IntroductoryExposureConflictError("current readiness report is unavailable")
        required = {
            "known_cardiovascular_metabolic_or_renal_disease": "no",
            "concerning_signs_or_symptoms": "no",
            "clinician_exercise_restriction": "no",
            "current_lower_body_or_balance_concern": "no",
            "controlled_two_foot_jump_and_landing": "yes",
        }
        if any(report.measurement.get(key) != value for key, value in required.items()):
            raise IntroductoryExposureConflictError(
                "current readiness answers do not authorize introductory jumping"
            )
        if report.id not in need.source_observation_ids:
            raise IntroductoryExposureConflictError(
                "exposure need does not descend from the current readiness report"
            )

    def _require_compatible_environment(
        self, environment: Environment, exercise: Exercise, at: datetime
    ) -> None:
        snapshot = EnvironmentSnapshotBuilder().build(
            environment,
            self.repository.list_equipment(),
            self.repository.list_equipment_availability(environment.id),
            at,
        )
        available_ids = {item.equipment_id for item in snapshot.available_equipment}
        missing = set(exercise.equipment_requirement_ids) - available_ids
        if missing:
            raise IntroductoryExposureConflictError(
                "selected environment does not currently confirm the required open floor area"
            )
        if exercise.minimum_floor_area_m2 is not None and (
            snapshot.floor_area_m2 is None
            or snapshot.floor_area_m2 < exercise.minimum_floor_area_m2
        ):
            raise IntroductoryExposureConflictError(
                "selected environment does not confirm enough clear floor area"
            )

    def _derive_next_need(
        self,
        need: ExposureNeed,
        execution: IntroductoryExposureExecution,
        observation: Observation,
    ) -> ExposureNeed:
        if not execution.qualifies_as_exposure_day:
            return need
        prior = [
            item
            for item in self.repository.list_introductory_exposure_executions(execution.athlete_id)
            if item.qualifies_as_exposure_day
            and item.ended_at >= execution.ended_at - timedelta(days=need.lookback_days)
            and self._execution_matches_need(item, need)
        ]
        qualifying = (*prior, execution)
        distinct_days = {item.ended_at.date() for item in qualifying}
        status = (
            ExposureNeedStatus.RECENT_EXPOSURE_CONFIRMED
            if len(distinct_days) >= need.minimum_exposure_days
            else ExposureNeedStatus.INTRODUCTORY_EXPOSURE_NEEDED
        )
        source_ids = tuple(
            dict.fromkeys(
                (
                    *need.source_observation_ids,
                    *(item.performance_observation_id for item in prior),
                    observation.id,
                )
            )
        )
        return ExposureNeed(
            id=uuid5(
                INTRODUCTORY_EXPOSURE_NEED_NAMESPACE,
                f"{need.id}:{execution.id}:{status.value}",
            ),
            created_at=execution.ended_at,
            athlete_id=execution.athlete_id,
            exposure_type=need.exposure_type,
            target_scope=need.target_scope,
            status=status,
            lookback_days=need.lookback_days,
            minimum_exposure_days=need.minimum_exposure_days,
            source_observation_ids=source_ids,
            confidence=self._lower_confidence(need.confidence, observation.reliability),
            rationale=(
                f"AGAS has logged {len(distinct_days)} distinct qualifying introductory "
                f"{need.exposure_type.value} exposure day(s) in the configured "
                f"{need.lookback_days}-day window; {need.minimum_exposure_days} are required."
            ),
            uncertainty=(
                "Exposure-day status comes from athlete-entered completion, RPE, and controlled-"
                "landing reports. It is not a tissue-capacity test, medical clearance, or proof "
                "that maximal jumping is risk-free."
            ),
            authority_reference=(
                f"{need.authority_reference};{INTRODUCTORY_EXPOSURE_RULE_VERSION}"
            ),
            identified_at=execution.ended_at,
            valid_until=need.valid_until,
            rule_version=INTRODUCTORY_EXPOSURE_RULE_VERSION,
        )

    def _qualifying_days(self, athlete_id: UUID, need: ExposureNeed, at: datetime) -> int:
        return len(
            {
                item.ended_at.date()
                for item in self.repository.list_introductory_exposure_executions(athlete_id)
                if item.qualifies_as_exposure_day
                and item.ended_at >= at - timedelta(days=need.lookback_days)
                and item.ended_at <= at
                and self._execution_matches_need(item, need)
            }
        )

    def _execution_matches_need(
        self, execution: IntroductoryExposureExecution, need: ExposureNeed
    ) -> bool:
        source_need = self.repository.get_exposure_need(execution.exposure_need_id)
        return bool(
            source_need
            and source_need.exposure_type is need.exposure_type
            and source_need.target_scope == need.target_scope
        )

    @staticmethod
    def _lower_confidence(left: Confidence, right: Confidence) -> Confidence:
        rank = {
            Confidence.UNKNOWN: 0,
            Confidence.LOW: 1,
            Confidence.MODERATE: 2,
            Confidence.HIGH: 3,
        }
        return left if rank[left] <= rank[right] else right

    @staticmethod
    def _execution_matches_command(
        execution: IntroductoryExposureExecution,
        command: RecordIntroductoryExposureCommand,
    ) -> bool:
        return (
            execution.exposure_need_id == command.exposure_need_id
            and execution.environment_id == command.environment_id
            and execution.started_at == command.started_at
            and execution.ended_at == command.ended_at
            and execution.actual_sets == command.actual_sets
            and execution.actual_dose == command.actual_contacts
            and execution.session_rpe == command.session_rpe
            and execution.pre_session_ready == command.pre_session_ready
            and execution.controlled_technique == command.controlled_landings
            and execution.stop_condition_occurred == command.stop_condition_occurred
        )

    def _result(
        self,
        execution: IntroductoryExposureExecution,
        observation: Observation,
        need: ExposureNeed,
        days: int,
        *,
        created: bool,
    ) -> IntroductoryExposureExecutionResult:
        if need.status is ExposureNeedStatus.RECENT_EXPOSURE_CONFIRMED:
            next_action = (
                "The two-day exposure prerequisite is now satisfied. Refresh assessment "
                "selection; all other readiness gates still apply."
            )
        elif execution.qualifies_as_exposure_day:
            next_action = (
                "This exposure day counts. Wait until another calendar day before completing "
                "the same governed exposure again."
            )
        else:
            next_action = (
                "This record was preserved but does not count as a qualifying exposure day. "
                "Do not repeat today; refresh readiness before a later attempt."
            )
        return IntroductoryExposureExecutionResult(
            execution=execution,
            observation=observation,
            current_exposure_need=need,
            qualifying_exposure_days=days,
            required_exposure_days=need.minimum_exposure_days,
            created=created,
            next_action=next_action,
        )
