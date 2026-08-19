from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from agas_domain import (
    Observation,
    ObservationSource,
    PlannedSession,
    PrescriptionModification,
    ReadinessLevel,
    SafetyGateOutcome,
    SafetyGateTiming,
    SafetySignalClass,
    SessionExecution,
    SessionSafetyCheckInput,
    SessionSafetyDecision,
    SessionSafetyPolicy,
    WeeklyPlan,
)


class SafetyGateError(ValueError):
    """Raised when a safety check cannot be evaluated without breaking provenance."""


class SessionSafetyGate:
    """Apply deterministic precedence to already classified safety input."""

    def __init__(self, rule_version: str = "session-safety-gate@1.0.0") -> None:
        self.rule_version = rule_version

    def evaluate(
        self,
        *,
        check: SessionSafetyCheckInput,
        weekly_plan: WeeklyPlan,
        planned_session: PlannedSession,
        policy: SessionSafetyPolicy,
        decided_at: datetime,
        related_execution: SessionExecution | None = None,
    ) -> tuple[Observation, SessionSafetyDecision]:
        self._require_aware(decided_at)
        if check.athlete_id != weekly_plan.athlete_id:
            raise SafetyGateError("safety check belongs to a different athlete")
        if check.weekly_plan_id != weekly_plan.id:
            raise SafetyGateError("safety check belongs to a different weekly plan")
        persisted_session = next(
            (item for item in weekly_plan.sessions if item.id == check.planned_session_id), None
        )
        if persisted_session is None or persisted_session != planned_session:
            raise SafetyGateError("safety check does not reference this immutable planned session")
        if decided_at < check.reported_at:
            raise SafetyGateError("safety decision cannot predate its report")
        if check.timing is SafetyGateTiming.POST_SESSION:
            if related_execution is None:
                raise SafetyGateError("post-session checks require the related execution")
            if (
                related_execution.id != check.related_session_execution_id
                or related_execution.athlete_id != check.athlete_id
                or related_execution.planned_session_id != planned_session.id
            ):
                raise SafetyGateError("post-session execution does not match the safety check")
            if decided_at < related_execution.logged_at:
                raise SafetyGateError("post-session decision cannot predate execution logging")
        elif related_execution is not None:
            raise SafetyGateError("pre-session checks cannot include an execution")

        signal_modifications = self._ordered_union(
            *(item.required_modifications for item in check.signals)
        )
        if not set(signal_modifications) <= set(policy.allowed_modifications):
            raise SafetyGateError("safety signal requests a modification not allowed by policy")

        rationale: tuple[str, ...]
        if any(item.classification is SafetySignalClass.ESCALATE for item in check.signals):
            outcome = SafetyGateOutcome.STOP_AND_ESCALATE
            modifications: tuple[PrescriptionModification, ...] = ()
            rationale = (
                "a preclassified escalation signal stops ordinary programming and requires "
                "the governed escalation guidance",
            )
        elif (
            check.timing is SafetyGateTiming.PRE_SESSION
            and check.readiness is ReadinessLevel.NOT_READY
        ):
            outcome = SafetyGateOutcome.HOLD
            modifications = ()
            rationale = ("the athlete reported not-ready status; hold the planned session",)
        else:
            modification_groups: list[Iterable[PrescriptionModification]] = [signal_modifications]
            reasons = []
            if check.readiness is ReadinessLevel.LIMITED:
                modification_groups.append(policy.limited_readiness_modifications)
                reasons.append("limited readiness requires the configured modifications")
            if check.unusual_soreness:
                modification_groups.append(policy.unusual_soreness_modifications)
                reasons.append("unusual soreness requires the configured modifications")
            if check.major_sleep_disruption:
                modification_groups.append(policy.sleep_disruption_modifications)
                reasons.append("major sleep disruption requires the configured modifications")
            if check.major_schedule_limitation:
                modification_groups.append(policy.schedule_limitation_modifications)
                reasons.append("major schedule limitation requires the configured modifications")
            if signal_modifications:
                reasons.append("preclassified safety signals require explicit modifications")
            modifications = self._ordered_union(*modification_groups)
            if modifications:
                outcome = SafetyGateOutcome.MODIFY
                rationale = tuple(reasons)
            else:
                outcome = SafetyGateOutcome.PROCEED
                rationale = ("no configured hold, escalation, or modification condition is active",)

        observation = Observation(
            athlete_id=check.athlete_id,
            observed_at=check.reported_at,
            observation_type=f"session_safety_{check.timing.value}",
            measurement={
                "readiness": check.readiness.value if check.readiness is not None else None,
                "unusual_soreness": check.unusual_soreness,
                "major_sleep_disruption": check.major_sleep_disruption,
                "major_schedule_limitation": check.major_schedule_limitation,
                "signals": [item.model_dump(mode="json") for item in check.signals],
                "note": check.note,
            },
            source=ObservationSource.USER_REPORT,
            reliability=check.reliability,
            context={
                "weekly_plan_id": str(check.weekly_plan_id),
                "planned_session_id": str(check.planned_session_id),
                "related_session_execution_id": (
                    str(check.related_session_execution_id)
                    if check.related_session_execution_id is not None
                    else None
                ),
                "timing": check.timing.value,
            },
            provenance=check.provenance,
        )
        decision = SessionSafetyDecision(
            athlete_id=check.athlete_id,
            weekly_plan_id=check.weekly_plan_id,
            planned_session_id=check.planned_session_id,
            related_session_execution_id=check.related_session_execution_id,
            safety_policy_id=policy.id,
            timing=check.timing,
            outcome=outcome,
            required_modifications=modifications,
            source_observation_ids=(observation.id,),
            rationale=rationale,
            decided_at=decided_at,
            rule_version=f"{self.rule_version};policy={policy.policy_version}",
        )
        return observation, decision

    @staticmethod
    def _ordered_union(
        *groups: Iterable[PrescriptionModification],
    ) -> tuple[PrescriptionModification, ...]:
        result = []
        seen = set()
        for group in groups:
            for item in group:
                if item not in seen:
                    seen.add(item)
                    result.append(item)
        return tuple(result)

    @staticmethod
    def _require_aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise SafetyGateError("safety timestamps must include a timezone")
