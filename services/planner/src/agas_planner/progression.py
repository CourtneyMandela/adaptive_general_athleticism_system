from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta

from agas_domain import (
    AbsoluteLoadTarget,
    ExposureDefinition,
    ExposureEntry,
    ExposureProgressionPolicy,
    ExposureTarget,
    ExposureValidationDecision,
    ExposureValidationOutcome,
    ProgressionDecision,
    ProgressionDimension,
    ProgressionOutcome,
    ProgressionPolicy,
    RelativeLoadTarget,
    SafetyGateOutcome,
    SafetyGateTiming,
    SessionAdherence,
    SessionExecution,
    SessionExecutionStatus,
    SessionPrescription,
    SessionSafetyDecision,
)


class ProgressionError(ValueError):
    """Raised when progression inputs do not form one traceable execution chain."""


class ExposureEntryCalculator:
    def __init__(self, rule_version: str = "exposure-entry@1.0.0") -> None:
        self.rule_version = rule_version

    def calculate(
        self,
        *,
        execution: SessionExecution,
        prescription: SessionPrescription,
        definition: ExposureDefinition,
    ) -> ExposureEntry:
        item_execution = next(
            (item for item in execution.items if item.prescription_id == prescription.id), None
        )
        if item_execution is None:
            raise ProgressionError("execution and prescription do not match")
        if definition.exercise_id != prescription.exercise_id:
            raise ProgressionError("exposure definition does not classify this exercise")
        if definition.dose_unit == "repetitions":
            dose = sum(item.actual_repetitions or 0 for item in item_execution.performances)
        else:
            dose = sum(item.actual_duration_seconds or 0 for item in item_execution.performances)
        if execution.ended_at is None:
            raise ProgressionError("an exposure entry requires a started execution")
        return ExposureEntry(
            athlete_id=execution.athlete_id,
            session_execution_id=execution.id,
            planned_session_id=execution.planned_session_id,
            prescription_id=prescription.id,
            exposure_definition_id=definition.id,
            exposure_type=definition.exposure_type,
            dose_value=dose,
            dose_unit=definition.dose_unit,
            source_observation_ids=(execution.performance_observation_id,),
            occurred_at=execution.ended_at,
            calculation_method="sum-actual-set-dose",
            rule_version=f"{self.rule_version};definition={definition.definition_version}",
        )


class ExposureProgressionValidator:
    def __init__(self, rule_version: str = "exposure-progression@1.0.0") -> None:
        self.rule_version = rule_version

    def validate(
        self,
        *,
        target: ExposureTarget,
        policy: ExposureProgressionPolicy,
        entries: Iterable[ExposureEntry],
        decided_at: datetime,
    ) -> ExposureValidationDecision:
        self._require_aware(decided_at)
        if decided_at < target.proposed_for:
            raise ProgressionError("exposure validation cannot predate its target")
        if target.exposure_type is not policy.exposure_type or target.dose_unit != policy.dose_unit:
            raise ProgressionError("exposure target and policy are incompatible")
        cutoff = target.proposed_for - timedelta(days=policy.lookback_days)
        recent = tuple(
            sorted(
                (
                    item
                    for item in entries
                    if item.athlete_id == target.athlete_id
                    and item.exposure_type is target.exposure_type
                    and item.dose_unit == target.dose_unit
                    and cutoff <= item.occurred_at < target.proposed_for
                ),
                key=lambda item: item.occurred_at,
            )
        )
        if len(recent) < policy.minimum_recent_entries:
            baseline = None
            maximum = policy.maximum_initial_dose
            basis = "insufficient recent exposure; the configured initial cap applies"
        else:
            baseline = max(item.dose_value for item in recent)
            maximum = min(
                baseline * (1 + policy.maximum_relative_increase),
                baseline + policy.maximum_absolute_increase,
            )
            basis = "the configured relative and absolute caps apply to maximum recent exposure"
        approved = target.proposed_dose <= maximum
        return ExposureValidationDecision(
            athlete_id=target.athlete_id,
            prescription_id=target.prescription_id,
            exposure_policy_id=policy.id,
            exposure_type=target.exposure_type,
            proposed_dose=target.proposed_dose,
            dose_unit=target.dose_unit,
            baseline_dose=baseline,
            maximum_allowed_dose=maximum,
            source_exposure_entry_ids=tuple(item.id for item in recent),
            outcome=(
                ExposureValidationOutcome.APPROVED
                if approved
                else ExposureValidationOutcome.REJECTED
            ),
            rationale=(
                basis,
                "proposed exposure is within the configured cap"
                if approved
                else "proposed exposure exceeds the configured cap",
            ),
            decided_at=decided_at,
            rule_version=f"{self.rule_version};policy={policy.policy_version}",
        )

    @staticmethod
    def _require_aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ProgressionError("progression timestamps must include a timezone")


class ProgressionEngine:
    def __init__(self, rule_version: str = "progression-engine@1.0.0") -> None:
        self.rule_version = rule_version

    def decide(
        self,
        *,
        prescription: SessionPrescription,
        execution: SessionExecution,
        adherence: SessionAdherence,
        policy: ProgressionPolicy,
        decided_at: datetime,
        post_session_decisions: Iterable[SessionSafetyDecision] = (),
        exposure_validation: ExposureValidationDecision | None = None,
    ) -> ProgressionDecision:
        ExposureProgressionValidator._require_aware(decided_at)
        if policy.reference != prescription.progression_rule_reference:
            raise ProgressionError("progression policy does not match the prescription reference")
        item_execution = next(
            (item for item in execution.items if item.prescription_id == prescription.id), None
        )
        if item_execution is None or adherence.prescription_id != prescription.id:
            raise ProgressionError("progression inputs do not share a prescription")
        if (
            adherence.session_execution_id != execution.id
            or adherence.athlete_id != execution.athlete_id
        ):
            raise ProgressionError("adherence does not describe this execution")
        safety = tuple(post_session_decisions)
        if any(
            item.timing is not SafetyGateTiming.POST_SESSION
            or item.related_session_execution_id != execution.id
            or item.athlete_id != execution.athlete_id
            for item in safety
        ):
            raise ProgressionError("post-session safety decision does not match execution")

        outcome = ProgressionOutcome.PROGRESS
        reasons: list[str] = []
        if any(item.outcome is SafetyGateOutcome.STOP_AND_ESCALATE for item in safety):
            outcome = ProgressionOutcome.REVIEW_REQUIRED
            reasons.append("post-session escalation requires review before progression")
        elif any(item.outcome is not SafetyGateOutcome.PROCEED for item in safety):
            outcome = ProgressionOutcome.HOLD
            reasons.append("post-session safety modification holds progression")
        elif item_execution.status is not SessionExecutionStatus.COMPLETED:
            outcome = ProgressionOutcome.REPEAT
            reasons.append("the prescribed session item was not completed")
        elif adherence.set_completion_ratio < policy.minimum_set_completion_ratio:
            outcome = ProgressionOutcome.REPEAT
            reasons.append("set completion is below the configured threshold")
        elif adherence.dose_completion_ratio < policy.minimum_dose_completion_ratio:
            outcome = ProgressionOutcome.REPEAT
            reasons.append("dose completion is below the configured threshold")
        elif item_execution.item_rpe is None or (
            item_execution.item_rpe > policy.maximum_session_rpe
        ):
            outcome = ProgressionOutcome.REPEAT
            reasons.append("item effort is missing or above the configured threshold")
        elif policy.require_technique_constraint and any(
            item.technique_constraint_met is not True for item in item_execution.performances
        ):
            outcome = ProgressionOutcome.REPEAT
            reasons.append("required technique constraints were not confirmed")
        elif policy.exposure_type is not None:
            if exposure_validation is None:
                outcome = ProgressionOutcome.REVIEW_REQUIRED
                reasons.append("the configured exposure validation is missing")
            elif (
                exposure_validation.athlete_id != execution.athlete_id
                or exposure_validation.prescription_id != prescription.id
                or exposure_validation.exposure_type is not policy.exposure_type
            ):
                raise ProgressionError("exposure validation does not match progression inputs")
            elif exposure_validation.outcome is ExposureValidationOutcome.REJECTED:
                outcome = ProgressionOutcome.HOLD
                reasons.append("the proposed exposure increase exceeds its configured cap")
        if outcome is ProgressionOutcome.PROGRESS:
            reasons.append("all configured progression criteria are satisfied")

        source_ids = tuple(
            dict.fromkeys(
                (
                    *adherence.source_observation_ids,
                    *(source for item in safety for source in item.source_observation_ids),
                )
            )
        )
        return ProgressionDecision(
            athlete_id=execution.athlete_id,
            weekly_plan_id=execution.weekly_plan_id,
            planned_session_id=execution.planned_session_id,
            prescription_id=prescription.id,
            session_execution_id=execution.id,
            session_adherence_id=adherence.id,
            progression_policy_id=policy.id,
            post_session_safety_decision_ids=tuple(item.id for item in safety),
            exposure_validation_decision_id=(
                exposure_validation.id if exposure_validation is not None else None
            ),
            outcome=outcome,
            adjustment=policy.adjustment if outcome is ProgressionOutcome.PROGRESS else None,
            source_observation_ids=source_ids,
            rationale=tuple(reasons),
            decided_at=decided_at,
            rule_version=f"{self.rule_version};policy={policy.policy_version}",
        )


class PrescriptionProgressionApplicator:
    """Create a new typed prescription without mutating its historical predecessor."""

    def __init__(self, rule_version: str = "prescription-progression@1.0.0") -> None:
        self.rule_version = rule_version

    def apply(
        self,
        *,
        prescription: SessionPrescription,
        decision: ProgressionDecision,
        policy: ProgressionPolicy,
        prescribed_at: datetime,
        planned_duration_minutes: int | None = None,
    ) -> SessionPrescription:
        ExposureProgressionValidator._require_aware(prescribed_at)
        if (
            decision.outcome is not ProgressionOutcome.PROGRESS
            or decision.adjustment is None
            or decision.prescription_id != prescription.id
            or decision.progression_policy_id != policy.id
            or decision.adjustment != policy.adjustment
        ):
            raise ProgressionError("decision does not authorize a prescription revision")
        amount = decision.adjustment.amount
        updates: dict[str, object] = {}
        dimension = decision.adjustment.dimension
        if dimension is ProgressionDimension.REPETITIONS:
            if not amount.is_integer():
                raise ProgressionError("repetition adjustments require an integer amount")
            if prescription.repetitions_per_set is None:
                raise ProgressionError("repetition progression requires a repetition prescription")
            updates["repetitions_per_set"] = prescription.repetitions_per_set + int(amount)
        elif dimension is ProgressionDimension.SETS:
            if not amount.is_integer():
                raise ProgressionError("set adjustments require an integer amount")
            if planned_duration_minutes is None:
                raise ProgressionError("set progression requires an explicit revised duration")
            updates["sets"] = prescription.sets + int(amount)
        elif dimension is ProgressionDimension.DURATION:
            if not amount.is_integer():
                raise ProgressionError("duration adjustments require an integer amount")
            if prescription.duration_seconds is None or planned_duration_minutes is None:
                raise ProgressionError(
                    "duration progression requires a duration prescription and revised duration"
                )
            updates["duration_seconds"] = prescription.duration_seconds + int(amount)
        elif dimension is ProgressionDimension.LOAD:
            revised_target: AbsoluteLoadTarget | RelativeLoadTarget
            load_target = next(
                (
                    item
                    for item in prescription.intensity_targets
                    if isinstance(item, (AbsoluteLoadTarget, RelativeLoadTarget))
                ),
                None,
            )
            if isinstance(load_target, AbsoluteLoadTarget):
                if decision.adjustment.unit != load_target.unit:
                    raise ProgressionError("load adjustment unit does not match absolute load")
                revised_target = load_target.model_copy(
                    update={"value": load_target.value + amount}
                )
            elif isinstance(load_target, RelativeLoadTarget):
                if decision.adjustment.unit != "percentage_points":
                    raise ProgressionError("relative-load adjustments require percentage_points")
                revised_target = load_target.model_copy(
                    update={"percentage": load_target.percentage + amount}
                )
            else:
                raise ProgressionError(
                    "load progression requires an absolute or relative typed load target"
                )
            updates["intensity_targets"] = tuple(
                revised_target if item is load_target else item
                for item in prescription.intensity_targets
            )
        else:
            raise ProgressionError(
                f"{dimension.value} progression lacks a typed prescription field in V1"
            )
        if planned_duration_minutes is not None:
            if planned_duration_minutes <= 0:
                raise ProgressionError("planned duration must be positive")
            updates["planned_duration_minutes"] = planned_duration_minutes

        values = prescription.model_dump()
        values.pop("id")
        values.pop("created_at")
        values.update(updates)
        values.update(
            prescribed_at=prescribed_at,
            source_observation_ids=tuple(
                dict.fromkeys(
                    (*prescription.source_observation_ids, *decision.source_observation_ids)
                )
            ),
            evidence_claim_ids=tuple(
                dict.fromkeys((*prescription.evidence_claim_ids, *policy.evidence_claim_ids))
            ),
            rule_version=f"{self.rule_version};decision={decision.rule_version}",
            supersedes_prescription_id=prescription.id,
            progression_decision_id=decision.id,
        )
        return SessionPrescription.model_validate(values)
