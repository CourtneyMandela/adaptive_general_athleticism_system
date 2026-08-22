from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Literal
from uuid import UUID

from agas_domain import (
    AbsoluteLoadTarget,
    BodyweightTarget,
    EffortRpeTarget,
    HeartRateZoneTarget,
    PaceTarget,
    PlannedSession,
    ProgressionDecision,
    ProgressionDimension,
    RelativeLoadTarget,
    RepetitionsInReserveTarget,
    SafetyGateOutcome,
    SessionExecutionStatus,
    SessionPrescription,
    TechniqueTarget,
    WeeklyPlan,
    WeeklyPlanStatus,
)
from agas_domain.models import IntensityTarget
from agas_domain.persistence.repository import DomainRepository
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

SessionDisplayStatus = Literal[
    "scheduled",
    "cleared",
    "modified",
    "held",
    "needs_attention",
    "completed",
    "partial",
    "not_started",
    "stopped_safety",
]
ProgressionActionStatus = Literal[
    "awaiting_execution",
    "awaiting_post_session_safety",
    "ready",
    "manual_configuration_required",
    "policy_unavailable",
    "completed",
]


class SafetyStatusProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: UUID
    outcome: SafetyGateOutcome
    required_modifications: tuple[str, ...]
    decided_at: datetime


class AdherenceProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    adherence_id: UUID
    performed_sets: int
    prescribed_sets: int
    actual_dose_total: int
    prescribed_dose_total: int
    dose_unit: str
    set_completion_ratio: float
    dose_completion_ratio: float


class ProgressionProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: UUID
    outcome: str
    adjustment_description: str | None
    decided_at: datetime


class ProgressionActionProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: ProgressionActionStatus
    rule_reference: str
    progression_policy_id: UUID | None = None
    adjustment_dimension: str | None = None
    adjustment_description: str | None = None
    reason: str


class PrescriptionProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    order_index: int
    section: str
    prescription_id: UUID
    exercise_id: UUID
    exercise_name: str
    adaptation_id: UUID
    adaptation_name: str
    reason_for_inclusion: str
    sets: int
    repetitions_per_set: int | None
    duration_seconds: int | None
    intensity_targets: tuple[str, ...]
    rest_seconds: int
    adherence: AdherenceProjection | None
    progression: ProgressionProjection | None
    progression_action: ProgressionActionProjection


class ExecutionProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: UUID
    status: SessionExecutionStatus
    session_rpe: float | None
    logged_at: datetime
    post_session_safety_outcomes: tuple[SafetyGateOutcome, ...]


class PlannedSessionProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    planned_session_id: UUID
    session_template_id: UUID
    session_name: str
    starts_at: datetime
    ends_at: datetime
    planned_duration_minutes: int
    environment_id: UUID
    environment_name: str
    status: SessionDisplayStatus
    pre_session_safety: SafetyStatusProjection | None
    execution: ExecutionProjection | None
    prescriptions: tuple[PrescriptionProjection, ...]


class WeekProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    weekly_plan_id: UUID
    block_plan_id: UUID
    week_start: date
    week_end: date
    block_week: int
    status: WeeklyPlanStatus
    sessions: tuple[PlannedSessionProjection, ...]


class CurrentWeekProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    athlete_id: UUID
    athlete_display_name: str
    as_of: date
    week: WeekProjection | None


class CurrentWeekProjectionError(RuntimeError):
    """Base error for current-week read projection failures."""


class CurrentWeekNotFoundError(CurrentWeekProjectionError):
    pass


class CurrentWeekConflictError(CurrentWeekProjectionError):
    pass


class CurrentWeekProjector:
    """Build a read-only daily-use projection from immutable persisted records."""

    def __init__(self, session: Session) -> None:
        self.repository = DomainRepository(session)

    def project(self, athlete_id: UUID, as_of: date) -> CurrentWeekProjection:
        athlete = self.repository.get_athlete(athlete_id)
        if athlete is None:
            raise CurrentWeekNotFoundError("athlete does not exist")
        matching_plans = tuple(
            plan
            for plan in self.repository.list_weekly_plans_for_athlete(athlete_id)
            if plan.week_start <= as_of < plan.week_start + timedelta(days=7)
        )
        if len(matching_plans) > 1:
            raise CurrentWeekConflictError(
                "multiple weekly plans cover the requested date; supersession is unresolved"
            )
        week = self._project_week(matching_plans[0]) if matching_plans else None
        return CurrentWeekProjection(
            athlete_id=athlete.id,
            athlete_display_name=athlete.display_name,
            as_of=as_of,
            week=week,
        )

    def _project_week(self, plan: WeeklyPlan) -> WeekProjection:
        sessions = tuple(self._project_session(plan, item) for item in plan.sessions)
        return WeekProjection(
            weekly_plan_id=plan.id,
            block_plan_id=plan.block_plan_id,
            week_start=plan.week_start,
            week_end=plan.week_start + timedelta(days=6),
            block_week=plan.block_week,
            status=plan.status,
            sessions=sessions,
        )

    def _project_session(
        self, plan: WeeklyPlan, planned_session: PlannedSession
    ) -> PlannedSessionProjection:
        template = self.repository.get_session_template(planned_session.session_template_id)
        environment = self.repository.get_environment(planned_session.environment_id)
        if template is None or environment is None:
            raise CurrentWeekConflictError("weekly plan references incomplete session metadata")
        if template.athlete_id != plan.athlete_id or environment.athlete_id != plan.athlete_id:
            raise CurrentWeekConflictError(
                "weekly plan session metadata belongs to another athlete"
            )

        safety = self.repository.get_latest_session_safety_decision(
            planned_session.id, "pre_session"
        )
        execution = self.repository.get_session_execution_by_planned_session(planned_session.id)
        post_safety = (
            self.repository.list_post_session_safety_decisions(execution.id)
            if execution is not None
            else ()
        )
        if safety is not None and (
            safety.athlete_id != plan.athlete_id or safety.weekly_plan_id != plan.id
        ):
            raise CurrentWeekConflictError("safety decision belongs to another weekly plan")
        if execution is not None and (
            execution.athlete_id != plan.athlete_id or execution.weekly_plan_id != plan.id
        ):
            raise CurrentWeekConflictError("execution belongs to another weekly plan")
        prescriptions = []
        for template_item in template.items:
            prescription = self.repository.get_session_prescription(template_item.prescription_id)
            if prescription is None:
                raise CurrentWeekConflictError("session template references a missing prescription")
            if (
                prescription.athlete_id != plan.athlete_id
                or prescription.block_plan_id != plan.block_plan_id
            ):
                raise CurrentWeekConflictError("prescription belongs to another athlete or block")
            exercise = self.repository.get_exercise(prescription.exercise_id)
            adaptation = self.repository.get_adaptation(prescription.adaptation_id)
            if exercise is None or adaptation is None:
                raise CurrentWeekConflictError(
                    "prescription references incomplete catalog metadata"
                )
            adherence = (
                self.repository.get_session_adherence_by_execution_and_prescription(
                    execution.id, prescription.id
                )
                if execution is not None
                else None
            )
            progression = (
                self.repository.get_progression_decision_by_execution_and_prescription(
                    execution.id, prescription.id
                )
                if execution is not None
                else None
            )
            prescriptions.append(
                PrescriptionProjection(
                    order_index=template_item.order_index,
                    section=template_item.section.value,
                    prescription_id=prescription.id,
                    exercise_id=exercise.id,
                    exercise_name=exercise.name,
                    adaptation_id=adaptation.id,
                    adaptation_name=adaptation.name,
                    reason_for_inclusion=prescription.reason_for_inclusion,
                    sets=prescription.sets,
                    repetitions_per_set=prescription.repetitions_per_set,
                    duration_seconds=prescription.duration_seconds,
                    intensity_targets=tuple(
                        self._intensity_label(target) for target in prescription.intensity_targets
                    ),
                    rest_seconds=prescription.rest_seconds,
                    adherence=(
                        AdherenceProjection(
                            adherence_id=adherence.id,
                            performed_sets=adherence.performed_sets,
                            prescribed_sets=adherence.prescribed_sets,
                            actual_dose_total=adherence.actual_dose_total,
                            prescribed_dose_total=adherence.prescribed_dose_total,
                            dose_unit=adherence.dose_unit,
                            set_completion_ratio=adherence.set_completion_ratio,
                            dose_completion_ratio=adherence.dose_completion_ratio,
                        )
                        if adherence is not None
                        else None
                    ),
                    progression=(
                        ProgressionProjection(
                            decision_id=progression.id,
                            outcome=progression.outcome.value,
                            adjustment_description=(
                                progression.adjustment.description
                                if progression.adjustment is not None
                                else None
                            ),
                            decided_at=progression.decided_at,
                        )
                        if progression is not None
                        else None
                    ),
                    progression_action=self._progression_action(
                        prescription=prescription,
                        execution_exists=execution is not None,
                        post_session_safety_exists=bool(post_safety),
                        progression=progression,
                    ),
                )
            )

        safety_projection = (
            SafetyStatusProjection(
                decision_id=safety.id,
                outcome=safety.outcome,
                required_modifications=tuple(item.value for item in safety.required_modifications),
                decided_at=safety.decided_at,
            )
            if safety is not None
            else None
        )
        execution_projection = None
        if execution is not None:
            execution_projection = ExecutionProjection(
                execution_id=execution.id,
                status=execution.status,
                session_rpe=execution.session_rpe,
                logged_at=execution.logged_at,
                post_session_safety_outcomes=tuple(item.outcome for item in post_safety),
            )
        return PlannedSessionProjection(
            planned_session_id=planned_session.id,
            session_template_id=template.id,
            session_name=template.name,
            starts_at=planned_session.starts_at,
            ends_at=planned_session.ends_at,
            planned_duration_minutes=planned_session.planned_duration_minutes,
            environment_id=environment.id,
            environment_name=environment.name,
            status=self._display_status(
                execution.status if execution else None,
                safety.outcome if safety else None,
            ),
            pre_session_safety=safety_projection,
            execution=execution_projection,
            prescriptions=tuple(prescriptions),
        )

    def _progression_action(
        self,
        *,
        prescription: SessionPrescription,
        execution_exists: bool,
        post_session_safety_exists: bool,
        progression: ProgressionDecision | None,
    ) -> ProgressionActionProjection:
        reference = prescription.progression_rule_reference
        if progression is not None:
            return ProgressionActionProjection(
                status="completed",
                rule_reference=reference,
                adjustment_dimension=(
                    progression.adjustment.dimension.value
                    if progression.adjustment is not None
                    else None
                ),
                adjustment_description=(
                    progression.adjustment.description
                    if progression.adjustment is not None
                    else None
                ),
                reason="an immutable progression decision already exists",
            )
        if not execution_exists:
            return ProgressionActionProjection(
                status="awaiting_execution",
                rule_reference=reference,
                reason="progression requires a recorded session execution",
            )
        if not post_session_safety_exists:
            return ProgressionActionProjection(
                status="awaiting_post_session_safety",
                rule_reference=reference,
                reason="progression requires a post-session safety decision",
            )

        policies = self.repository.list_progression_policies_by_reference(reference)
        if len(policies) != 1:
            reason = (
                "no persisted progression policy matches the prescription rule reference"
                if not policies
                else "multiple progression policies match the prescription rule reference"
            )
            return ProgressionActionProjection(
                status="policy_unavailable",
                rule_reference=reference,
                reason=reason,
            )

        policy = policies[0]
        dimension = policy.adjustment.dimension
        common = {
            "rule_reference": reference,
            "adjustment_dimension": dimension.value,
            "adjustment_description": policy.adjustment.description,
        }
        if policy.exposure_type is not None:
            return ProgressionActionProjection(
                status="manual_configuration_required",
                reason=(
                    f"{policy.exposure_type.value} progression requires an explicit reviewed "
                    "exposure target and policy"
                ),
                **common,
            )
        if dimension not in {ProgressionDimension.LOAD, ProgressionDimension.REPETITIONS}:
            return ProgressionActionProjection(
                status="manual_configuration_required",
                reason=(
                    f"{dimension.value} progression requires a governed prescription-revision "
                    "workflow"
                ),
                **common,
            )
        return ProgressionActionProjection(
            status="ready",
            progression_policy_id=policy.id,
            reason="the exact assigned policy can be evaluated by the deterministic engine",
            **common,
        )

    @staticmethod
    def _display_status(
        execution_status: SessionExecutionStatus | None,
        safety_outcome: SafetyGateOutcome | None,
    ) -> SessionDisplayStatus:
        execution_statuses: dict[SessionExecutionStatus, SessionDisplayStatus] = {
            SessionExecutionStatus.COMPLETED: "completed",
            SessionExecutionStatus.PARTIAL: "partial",
            SessionExecutionStatus.NOT_STARTED: "not_started",
            SessionExecutionStatus.STOPPED_SAFETY: "stopped_safety",
        }
        if execution_status is not None:
            return execution_statuses[execution_status]
        if safety_outcome is SafetyGateOutcome.PROCEED:
            return "cleared"
        if safety_outcome is SafetyGateOutcome.MODIFY:
            return "modified"
        if safety_outcome is SafetyGateOutcome.HOLD:
            return "held"
        if safety_outcome is SafetyGateOutcome.STOP_AND_ESCALATE:
            return "needs_attention"
        return "scheduled"

    @staticmethod
    def _intensity_label(target: IntensityTarget) -> str:
        if isinstance(target, AbsoluteLoadTarget):
            return f"{target.value:g} {target.unit}"
        if isinstance(target, RelativeLoadTarget):
            return f"{target.percentage:g}% {target.reference}"
        if isinstance(target, BodyweightTarget):
            return "Bodyweight"
        if isinstance(target, EffortRpeTarget):
            return f"RPE {target.minimum:g}-{target.maximum:g}"
        if isinstance(target, RepetitionsInReserveTarget):
            return f"RIR {target.minimum:g}-{target.maximum:g}"
        if isinstance(target, HeartRateZoneTarget):
            return f"Heart-rate zone {target.zone}"
        if isinstance(target, PaceTarget):
            return f"{target.value:g} {target.unit}"
        if isinstance(target, TechniqueTarget):
            return "; ".join(target.constraints)
        raise CurrentWeekConflictError("prescription contains an unsupported intensity target")
