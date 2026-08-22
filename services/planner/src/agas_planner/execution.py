from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from agas_domain import (
    Observation,
    ObservationSource,
    PlannedSession,
    SafetyGateOutcome,
    SafetyGateTiming,
    SessionAdherence,
    SessionExecution,
    SessionExecutionInput,
    SessionExecutionStatus,
    SessionItemExecution,
    SessionItemExecutionInput,
    SessionPrescription,
    SessionSafetyDecision,
    SessionTemplate,
    WeeklyPlan,
    WeeklyPlanStatus,
)


class ExecutionRecordingError(ValueError):
    """Raised when workout logging would violate the plan or safety decision."""


class SessionExecutionRecorder:
    """Record actual performance as an observation after deterministic safety authorization."""

    def __init__(self, rule_version: str = "session-execution-recorder@1.0.0") -> None:
        self.rule_version = rule_version

    def record(
        self,
        *,
        execution_input: SessionExecutionInput,
        weekly_plan: WeeklyPlan,
        planned_session: PlannedSession,
        session_template: SessionTemplate,
        prescriptions: Iterable[SessionPrescription],
        pre_session_decision: SessionSafetyDecision,
    ) -> tuple[Observation, SessionExecution]:
        if weekly_plan.status is not WeeklyPlanStatus.FEASIBLE:
            raise ExecutionRecordingError("an infeasible weekly plan cannot authorize execution")
        if execution_input.athlete_id != weekly_plan.athlete_id:
            raise ExecutionRecordingError("execution belongs to a different athlete")
        if execution_input.weekly_plan_id != weekly_plan.id:
            raise ExecutionRecordingError("execution belongs to a different weekly plan")
        stored_session = next(
            (
                item
                for item in weekly_plan.sessions
                if item.id == execution_input.planned_session_id
            ),
            None,
        )
        if stored_session is None or stored_session != planned_session:
            raise ExecutionRecordingError("execution does not reference this planned session")
        if planned_session.session_template_id != session_template.id:
            raise ExecutionRecordingError("planned session and template do not match")
        if (
            session_template.athlete_id != weekly_plan.athlete_id
            or session_template.block_plan_id != weekly_plan.block_plan_id
        ):
            raise ExecutionRecordingError("session template belongs to another athlete or block")
        if (
            pre_session_decision.id != execution_input.pre_session_safety_decision_id
            or pre_session_decision.athlete_id != execution_input.athlete_id
            or pre_session_decision.weekly_plan_id != weekly_plan.id
            or pre_session_decision.planned_session_id != planned_session.id
            or pre_session_decision.timing is not SafetyGateTiming.PRE_SESSION
        ):
            raise ExecutionRecordingError("pre-session safety decision does not match execution")
        if pre_session_decision.outcome in {
            SafetyGateOutcome.HOLD,
            SafetyGateOutcome.STOP_AND_ESCALATE,
        }:
            raise ExecutionRecordingError("the safety decision does not authorize execution")
        authorization_boundary = execution_input.started_at or execution_input.logged_at
        if pre_session_decision.decided_at > authorization_boundary:
            raise ExecutionRecordingError(
                "pre-session safety decision cannot postdate execution start or logging"
            )
        if set(execution_input.applied_modifications) != set(
            pre_session_decision.required_modifications
        ):
            raise ExecutionRecordingError(
                "applied modifications must exactly match the safety decision"
            )
        prescription_items = tuple(prescriptions)
        prescription_by_id = {item.id: item for item in prescription_items}
        if len(prescription_by_id) != len(prescription_items):
            raise ExecutionRecordingError("session prescriptions contain duplicate ids")
        expected_ids = tuple(item.prescription_id for item in session_template.items)
        actual_ids = tuple(item.prescription_id for item in execution_input.items)
        if actual_ids != expected_ids or set(prescription_by_id) != set(expected_ids):
            raise ExecutionRecordingError(
                "execution items must match the ordered session template prescriptions"
            )
        for item in execution_input.items:
            self._validate_item(item, prescription_by_id[item.prescription_id])

        observation = Observation(
            athlete_id=execution_input.athlete_id,
            observed_at=execution_input.logged_at,
            observation_type="session_execution",
            measurement={
                "status": execution_input.status.value,
                "started_at": (
                    execution_input.started_at.isoformat()
                    if execution_input.started_at is not None
                    else None
                ),
                "ended_at": (
                    execution_input.ended_at.isoformat()
                    if execution_input.ended_at is not None
                    else None
                ),
                "items": [item.model_dump(mode="json") for item in execution_input.items],
                "applied_modifications": [
                    item.value for item in execution_input.applied_modifications
                ],
                "session_rpe": execution_input.session_rpe,
                "note": execution_input.note,
            },
            source=ObservationSource.WORKOUT_RESULT,
            reliability=execution_input.reliability,
            context={
                "weekly_plan_id": str(weekly_plan.id),
                "planned_session_id": str(planned_session.id),
                "session_template_id": str(session_template.id),
                "pre_session_safety_decision_id": str(pre_session_decision.id),
            },
            provenance=execution_input.provenance,
        )
        execution = SessionExecution(
            athlete_id=execution_input.athlete_id,
            weekly_plan_id=execution_input.weekly_plan_id,
            planned_session_id=execution_input.planned_session_id,
            session_template_id=session_template.id,
            pre_session_safety_decision_id=pre_session_decision.id,
            status=execution_input.status,
            started_at=execution_input.started_at,
            ended_at=execution_input.ended_at,
            items=tuple(
                SessionItemExecution(
                    prescription_id=item.prescription_id,
                    status=item.status,
                    performances=item.performances,
                    item_rpe=item.item_rpe,
                    note=item.note,
                )
                for item in execution_input.items
            ),
            applied_modifications=execution_input.applied_modifications,
            session_rpe=execution_input.session_rpe,
            note=execution_input.note,
            performance_observation_id=observation.id,
            logged_at=execution_input.logged_at,
            rule_version=self.rule_version,
        )
        return observation, execution

    @staticmethod
    def _validate_item(item: SessionItemExecutionInput, prescription: SessionPrescription) -> None:
        if any(performance.set_index > prescription.sets for performance in item.performances):
            raise ExecutionRecordingError("set performance exceeds the prescribed set count")
        for performance in item.performances:
            if not performance.performed:
                continue
            if prescription.repetitions_per_set is not None:
                if performance.actual_repetitions is None:
                    raise ExecutionRecordingError(
                        "repetition prescription requires repetition performance"
                    )
            elif performance.actual_duration_seconds is None:
                raise ExecutionRecordingError("duration prescription requires duration performance")
        if item.status is SessionExecutionStatus.COMPLETED and (
            len(item.performances) != prescription.sets
            or not all(performance.target_completed for performance in item.performances)
        ):
            raise ExecutionRecordingError(
                "completed item status requires every prescribed set target to be completed"
            )
        if item.status is SessionExecutionStatus.PARTIAL and all(
            performance.target_completed for performance in item.performances
        ):
            raise ExecutionRecordingError("partial item status requires an incomplete target")


class SessionAdherenceCalculator:
    """Derive bounded descriptive adherence from prescription and actual performance."""

    def __init__(self, rule_version: str = "session-adherence@1.0.0") -> None:
        self.rule_version = rule_version

    def calculate(
        self,
        *,
        execution: SessionExecution,
        planned_session: PlannedSession,
        prescription: SessionPrescription,
        calculated_at: datetime,
    ) -> SessionAdherence:
        self._require_aware(calculated_at)
        if calculated_at < execution.logged_at:
            raise ExecutionRecordingError("adherence cannot predate execution logging")
        if execution.planned_session_id != planned_session.id:
            raise ExecutionRecordingError("adherence inputs do not describe the same session")

        item_execution = next(
            (item for item in execution.items if item.prescription_id == prescription.id), None
        )
        if item_execution is None:
            raise ExecutionRecordingError("execution does not contain the prescription item")

        performed_sets = sum(item.performed for item in item_execution.performances)
        target_completed_sets = sum(item.target_completed for item in item_execution.performances)
        if prescription.repetitions_per_set is not None:
            prescribed_per_set = prescription.repetitions_per_set
            actual = sum(item.actual_repetitions or 0 for item in item_execution.performances)
            unit = "repetitions"
        else:
            assert prescription.duration_seconds is not None
            prescribed_per_set = prescription.duration_seconds
            actual = sum(item.actual_duration_seconds or 0 for item in item_execution.performances)
            unit = "seconds"
        prescribed_total = prescription.sets * prescribed_per_set
        return SessionAdherence(
            athlete_id=execution.athlete_id,
            session_execution_id=execution.id,
            planned_session_id=planned_session.id,
            prescription_id=prescription.id,
            prescribed_sets=prescription.sets,
            performed_sets=performed_sets,
            target_completed_sets=target_completed_sets,
            prescribed_dose_total=prescribed_total,
            actual_dose_total=actual,
            dose_unit=unit,
            set_completion_ratio=min(1.0, performed_sets / prescription.sets),
            dose_completion_ratio=min(1.0, actual / prescribed_total),
            source_observation_ids=(execution.performance_observation_id,),
            calculated_at=calculated_at,
            calculation_method="prescribed-vs-performed-set-and-dose-ratio",
            rule_version=self.rule_version,
        )

    @staticmethod
    def _require_aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ExecutionRecordingError("execution timestamps must include a timezone")
