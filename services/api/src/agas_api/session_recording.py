from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from agas_domain import (
    Confidence,
    Observation,
    PlannedSession,
    PrescriptionModification,
    Provenance,
    ReadinessLevel,
    SafetyGateTiming,
    SafetySignal,
    SessionAdherence,
    SessionExecution,
    SessionExecutionInput,
    SessionExecutionStatus,
    SessionItemExecutionInput,
    SessionSafetyCheckInput,
    SessionSafetyDecision,
    WeeklyPlan,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import (
    ExecutionRecordingError,
    SessionAdherenceCalculator,
    SessionExecutionRecorder,
)
from agas_safety import SafetyGateError, SessionSafetyGate
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class CreateSessionSafetyDecisionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    timing: SafetyGateTiming
    related_session_execution_id: UUID | None = None
    readiness: ReadinessLevel | None = None
    unusual_soreness: bool = False
    major_sleep_disruption: bool = False
    major_schedule_limitation: bool = False
    signals: tuple[SafetySignal, ...] = ()
    note: str | None = None
    reported_at: datetime
    decided_at: datetime
    reliability: Confidence
    provenance: Provenance

    @field_validator("reported_at", "decided_at")
    @classmethod
    def require_aware_safety_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("safety timestamps must include a timezone")
        return value


class SessionSafetyCreationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observation: Observation
    decision: SessionSafetyDecision


class CreateSessionExecutionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pre_session_safety_decision_id: UUID
    status: SessionExecutionStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None
    items: Annotated[tuple[SessionItemExecutionInput, ...], Field(min_length=1)]
    applied_modifications: tuple[PrescriptionModification, ...] = ()
    session_rpe: float | None = Field(default=None, ge=0, le=10)
    note: str | None = None
    logged_at: datetime
    adherence_calculated_at: datetime
    reliability: Confidence
    provenance: Provenance

    @field_validator("started_at", "ended_at", "logged_at", "adherence_calculated_at")
    @classmethod
    def require_aware_execution_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("execution timestamps must include a timezone")
        return value


class SessionExecutionCreationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observation: Observation
    execution: SessionExecution
    adherence: Annotated[tuple[SessionAdherence, ...], Field(min_length=1)]


class SessionRecordingUseCaseError(RuntimeError):
    """Base error for persisted safety and execution use cases."""


class SessionRecordingNotFoundError(SessionRecordingUseCaseError):
    pass


class SessionRecordingConflictError(SessionRecordingUseCaseError):
    pass


class SessionRecordingValidationError(SessionRecordingUseCaseError):
    pass


class PersistedSessionSafetyService:
    """Evaluate and append one structured safety report and decision atomically."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(
        self,
        weekly_plan_id: UUID,
        planned_session_id: UUID,
        command: CreateSessionSafetyDecisionCommand,
    ) -> SessionSafetyCreationResult:
        try:
            result = self._build(weekly_plan_id, planned_session_id, command)
            self.repository.add_observation(result.observation)
            self.session.flush()
            self.repository.add_session_safety_decision(result.decision)
            self.session.commit()
            return result
        except SessionRecordingUseCaseError:
            self.session.rollback()
            raise
        except (SafetyGateError, DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise SessionRecordingValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise SessionRecordingConflictError(
                "the safety decision conflicts with persisted session state"
            ) from error

    def _build(
        self,
        weekly_plan_id: UUID,
        planned_session_id: UUID,
        command: CreateSessionSafetyDecisionCommand,
    ) -> SessionSafetyCreationResult:
        plan, planned_session = self._load_plan_session(weekly_plan_id, planned_session_id)
        assignment = self.repository.get_current_athlete_safety_policy_assignment(plan.athlete_id)
        if assignment is None:
            raise SessionRecordingNotFoundError(
                "athlete does not have a reviewed safety-policy assignment"
            )
        policy = self.repository.get_session_safety_policy(assignment.safety_policy_id)
        if policy is None:
            raise SessionRecordingConflictError(
                "the athlete safety-policy assignment references a missing policy"
            )
        related_execution = None
        if command.related_session_execution_id is not None:
            related_execution = self.repository.get_session_execution(
                command.related_session_execution_id
            )
            if related_execution is None:
                raise SessionRecordingNotFoundError("related session execution does not exist")

        check = SessionSafetyCheckInput(
            athlete_id=plan.athlete_id,
            weekly_plan_id=plan.id,
            planned_session_id=planned_session.id,
            related_session_execution_id=command.related_session_execution_id,
            timing=command.timing,
            readiness=command.readiness,
            unusual_soreness=command.unusual_soreness,
            major_sleep_disruption=command.major_sleep_disruption,
            major_schedule_limitation=command.major_schedule_limitation,
            signals=command.signals,
            note=command.note,
            reported_at=command.reported_at,
            reliability=command.reliability,
            provenance=command.provenance,
        )
        observation, decision = SessionSafetyGate().evaluate(
            check=check,
            weekly_plan=plan,
            planned_session=planned_session,
            policy=policy,
            decided_at=command.decided_at,
            related_execution=related_execution,
        )
        decision = decision.model_copy(
            update={"safety_policy_assignment_id": assignment.id},
        )
        return SessionSafetyCreationResult(observation=observation, decision=decision)

    def _load_plan_session(
        self, weekly_plan_id: UUID, planned_session_id: UUID
    ) -> tuple[WeeklyPlan, PlannedSession]:
        plan = self.repository.get_weekly_plan(weekly_plan_id)
        if plan is None:
            raise SessionRecordingNotFoundError("weekly plan does not exist")
        planned_session = next(
            (item for item in plan.sessions if item.id == planned_session_id), None
        )
        if planned_session is None:
            raise SessionRecordingNotFoundError("planned session does not belong to weekly plan")
        return plan, planned_session


class PersistedSessionExecutionService:
    """Append performed work, its direct observation, and derived adherence atomically."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(
        self,
        weekly_plan_id: UUID,
        planned_session_id: UUID,
        command: CreateSessionExecutionCommand,
    ) -> SessionExecutionCreationResult:
        try:
            result = self._build(weekly_plan_id, planned_session_id, command)
            self.repository.add_observation(result.observation)
            self.session.flush()
            self.repository.add_session_execution(result.execution)
            self.session.flush()
            for adherence in result.adherence:
                self.repository.add_session_adherence(adherence)
            self.session.commit()
            return result
        except SessionRecordingUseCaseError:
            self.session.rollback()
            raise
        except (ExecutionRecordingError, DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise SessionRecordingValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise SessionRecordingConflictError(
                "the planned session already has an execution"
            ) from error

    def _build(
        self,
        weekly_plan_id: UUID,
        planned_session_id: UUID,
        command: CreateSessionExecutionCommand,
    ) -> SessionExecutionCreationResult:
        plan, planned_session = self._load_plan_session(weekly_plan_id, planned_session_id)
        if self.repository.get_session_execution_by_planned_session(planned_session.id) is not None:
            raise SessionRecordingConflictError("the planned session already has an execution")

        template = self.repository.get_session_template(planned_session.session_template_id)
        if template is None:
            raise SessionRecordingNotFoundError("planned session template does not exist")
        prescriptions = []
        for item in template.items:
            prescription = self.repository.get_session_prescription(item.prescription_id)
            if prescription is None:
                raise SessionRecordingNotFoundError(
                    f"session prescription {item.prescription_id} does not exist"
                )
            prescriptions.append(prescription)

        decision = self.repository.get_session_safety_decision(
            command.pre_session_safety_decision_id
        )
        if decision is None:
            raise SessionRecordingNotFoundError("pre-session safety decision does not exist")
        latest_decision = self.repository.get_latest_session_safety_decision(
            planned_session.id, SafetyGateTiming.PRE_SESSION.value
        )
        if latest_decision is None or latest_decision.id != decision.id:
            raise SessionRecordingConflictError(
                "execution requires the latest pre-session safety decision"
            )

        execution_input = SessionExecutionInput(
            athlete_id=plan.athlete_id,
            weekly_plan_id=plan.id,
            planned_session_id=planned_session.id,
            pre_session_safety_decision_id=decision.id,
            status=command.status,
            started_at=command.started_at,
            ended_at=command.ended_at,
            items=command.items,
            applied_modifications=command.applied_modifications,
            session_rpe=command.session_rpe,
            note=command.note,
            logged_at=command.logged_at,
            reliability=command.reliability,
            provenance=command.provenance,
        )
        observation, execution = SessionExecutionRecorder().record(
            execution_input=execution_input,
            weekly_plan=plan,
            planned_session=planned_session,
            session_template=template,
            prescriptions=prescriptions,
            pre_session_decision=decision,
        )
        adherence = tuple(
            SessionAdherenceCalculator().calculate(
                execution=execution,
                planned_session=planned_session,
                prescription=prescription,
                calculated_at=command.adherence_calculated_at,
            )
            for prescription in prescriptions
        )
        return SessionExecutionCreationResult(
            observation=observation,
            execution=execution,
            adherence=adherence,
        )

    def _load_plan_session(
        self, weekly_plan_id: UUID, planned_session_id: UUID
    ) -> tuple[WeeklyPlan, PlannedSession]:
        plan = self.repository.get_weekly_plan(weekly_plan_id)
        if plan is None:
            raise SessionRecordingNotFoundError("weekly plan does not exist")
        planned_session = next(
            (item for item in plan.sessions if item.id == planned_session_id), None
        )
        if planned_session is None:
            raise SessionRecordingNotFoundError("planned session does not belong to weekly plan")
        return plan, planned_session
