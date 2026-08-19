from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from agas_domain import (
    BlockPlan,
    BlockReview,
    BlockReviewOutcome,
    BlockReviewPolicy,
    CapabilityEstimate,
    ComparisonDirection,
    Confidence,
    ResponseEvaluation,
    ResponseEvaluationTarget,
    SafetyGateTiming,
    SessionAdherence,
    SessionExecution,
    SessionExecutionStatus,
    SessionPrescription,
    SessionSafetyDecision,
    TrainingResponse,
)

_CONFIDENCE_RANK = {
    Confidence.UNKNOWN: 0,
    Confidence.LOW: 1,
    Confidence.MODERATE: 2,
    Confidence.HIGH: 3,
}


class BlockReviewError(ValueError):
    """Raised when review inputs do not describe one auditable block."""


class TrainingResponseCalculator:
    def __init__(self, rule_version: str = "training-response@1.0.0") -> None:
        self.rule_version = rule_version

    def calculate(
        self,
        *,
        block: BlockPlan,
        adaptation_id: UUID,
        prescriptions: Iterable[SessionPrescription],
        executions: Iterable[SessionExecution],
        adherences: Iterable[SessionAdherence],
        baseline: CapabilityEstimate,
        followup: CapabilityEstimate,
        intervention_summary: str,
        measurement_uncertainty: str,
        contextual_factors: tuple[str, ...],
        calculated_at: datetime,
    ) -> TrainingResponse:
        self._aware(calculated_at)
        prescription_items = tuple(prescriptions)
        execution_items = tuple(executions)
        adherence_items = tuple(adherences)
        if not prescription_items or not execution_items or not adherence_items:
            raise BlockReviewError("training response requires prescribed and performed work")
        for items, label in (
            (prescription_items, "prescriptions"),
            (execution_items, "executions"),
            (adherence_items, "adherence records"),
        ):
            if len({item.id for item in items}) != len(items):
                raise BlockReviewError(f"training response contains duplicate {label}")
        if baseline.athlete_id != block.athlete_id or followup.athlete_id != block.athlete_id:
            raise BlockReviewError("capability estimates belong to another athlete")
        if (
            baseline.domain is not followup.domain
            or baseline.estimate_scope != followup.estimate_scope
            or baseline.unit_or_scale != followup.unit_or_scale
            or followup.estimated_at <= baseline.estimated_at
        ):
            raise BlockReviewError("baseline and follow-up estimates are not comparable")
        if calculated_at < followup.estimated_at:
            raise BlockReviewError("training response cannot predate its follow-up estimate")
        if isinstance(baseline.estimate, bool) or not isinstance(baseline.estimate, (int, float)):
            raise BlockReviewError("baseline estimate must be numeric")
        if isinstance(followup.estimate, bool) or not isinstance(followup.estimate, (int, float)):
            raise BlockReviewError("follow-up estimate must be numeric")
        adaptation_ids = {item.adaptation_id for item in block.allocations}
        if adaptation_id not in adaptation_ids or any(
            item.block_plan_id != block.id
            or item.athlete_id != block.athlete_id
            or item.adaptation_id != adaptation_id
            for item in prescription_items
        ):
            raise BlockReviewError("prescriptions do not match the block adaptation")
        prescription_ids = {item.id for item in prescription_items}
        if any(
            item.athlete_id != block.athlete_id or item.prescription_id not in prescription_ids
            for item in execution_items
        ):
            raise BlockReviewError("executions do not match the response prescriptions")
        if {item.prescription_id for item in execution_items} != prescription_ids:
            raise BlockReviewError("each response prescription must have a recorded execution")
        execution_ids = {item.id for item in execution_items}
        if any(
            item.athlete_id != block.athlete_id
            or item.session_execution_id not in execution_ids
            or item.prescription_id not in prescription_ids
            for item in adherence_items
        ):
            raise BlockReviewError("adherence does not match the response executions")
        if {item.session_execution_id for item in adherence_items} != execution_ids:
            raise BlockReviewError("each response execution requires one adherence record")

        prescription_by_id = {item.id: item for item in prescription_items}
        prescribed_total = sum(
            prescription_by_id[item.prescription_id].sets
            * (
                prescription_by_id[item.prescription_id].repetitions_per_set
                or prescription_by_id[item.prescription_id].duration_seconds
                or 0
            )
            for item in execution_items
        )
        dose_units = {
            "repetitions" if item.repetitions_per_set is not None else "seconds"
            for item in prescription_items
        }
        if len(dose_units) != 1:
            raise BlockReviewError("one training response cannot mix dose units")
        actual_total = sum(item.actual_dose_total for item in adherence_items)
        confidence = min(
            (baseline.confidence, followup.confidence), key=lambda item: _CONFIDENCE_RANK[item]
        )
        sources = tuple(
            dict.fromkeys(
                (
                    *baseline.source_observation_ids,
                    *followup.source_observation_ids,
                    *(source for item in adherence_items for source in item.source_observation_ids),
                )
            )
        )
        return TrainingResponse(
            athlete_id=block.athlete_id,
            block_plan_id=block.id,
            adaptation_id=adaptation_id,
            intervention_summary=intervention_summary,
            prescription_ids=tuple(item.id for item in prescription_items),
            session_execution_ids=tuple(item.id for item in execution_items),
            session_adherence_ids=tuple(item.id for item in adherence_items),
            prescribed_sessions=len(execution_items),
            completed_sessions=sum(
                item.status is SessionExecutionStatus.COMPLETED for item in execution_items
            ),
            prescribed_dose_total=prescribed_total,
            actual_dose_total=actual_total,
            dose_unit=dose_units.pop(),
            adherence_ratio=min(1.0, actual_total / prescribed_total),
            baseline_capability_estimate_id=baseline.id,
            followup_capability_estimate_id=followup.id,
            baseline_value=float(baseline.estimate),
            followup_value=float(followup.estimate),
            observed_change=float(followup.estimate) - float(baseline.estimate),
            measurement_uncertainty=measurement_uncertainty,
            contextual_factors=contextual_factors,
            confidence=confidence,
            source_observation_ids=sources,
            calculated_at=calculated_at,
            calculation_method="compatible-estimate-change-with-delivered-dose",
            rule_version=self.rule_version,
        )

    @staticmethod
    def _aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise BlockReviewError("review timestamps must include a timezone")


class BlockReviewEngine:
    def __init__(self, rule_version: str = "block-review@1.0.0") -> None:
        self.rule_version = rule_version

    def review(
        self,
        *,
        block: BlockPlan,
        responses: Iterable[TrainingResponse],
        targets: Iterable[ResponseEvaluationTarget],
        safety_decisions: Iterable[SessionSafetyDecision],
        policy: BlockReviewPolicy,
        reviewed_at: datetime,
    ) -> BlockReview:
        TrainingResponseCalculator._aware(reviewed_at)
        response_items = tuple(responses)
        target_items = tuple(targets)
        safety_items = tuple(safety_decisions)
        if not response_items or tuple(item.id for item in response_items) != tuple(
            item.training_response_id for item in target_items
        ):
            raise BlockReviewError("each ordered response requires one evaluation target")
        if any(
            item.athlete_id != block.athlete_id or item.block_plan_id != block.id
            for item in response_items
        ) or any(item.athlete_id != block.athlete_id for item in safety_items):
            raise BlockReviewError("review inputs belong to another athlete or block")
        if any(item.calculated_at > reviewed_at for item in response_items) or any(
            item.decided_at > reviewed_at for item in safety_items
        ):
            raise BlockReviewError("block review cannot predate its inputs")
        if any(item.timing is not SafetyGateTiming.POST_SESSION for item in safety_items):
            raise BlockReviewError("block reviews accept only post-session safety decisions")
        execution_ids = [
            execution_id
            for response in response_items
            for execution_id in response.session_execution_ids
        ]
        if len(set(execution_ids)) != len(execution_ids):
            raise BlockReviewError("training responses cannot count one execution twice")

        evaluations = []
        for response, target in zip(response_items, target_items, strict=True):
            if response.adherence_ratio < policy.minimum_adherence_ratio:
                met = None
                rationale = "delivery was below the configured interpretation threshold"
            elif (
                _CONFIDENCE_RANK[response.confidence]
                < _CONFIDENCE_RANK[policy.minimum_response_confidence]
            ):
                met = None
                rationale = "response confidence was below the configured threshold"
            else:
                signed_change = (
                    response.observed_change
                    if target.comparison_direction is ComparisonDirection.HIGHER_IS_BETTER
                    else -response.observed_change
                )
                met = signed_change >= target.minimum_meaningful_change
                rationale = (
                    "observed change met the explicit meaningful-change threshold"
                    if met
                    else "observed change did not meet the explicit meaningful-change threshold"
                )
            evaluations.append(
                ResponseEvaluation(
                    training_response_id=response.id,
                    comparison_direction=target.comparison_direction,
                    minimum_meaningful_change=target.minimum_meaningful_change,
                    threshold_met=met,
                    rationale=rationale,
                )
            )
        results = [item.threshold_met for item in evaluations]
        if any(item is None for item in results):
            outcome = BlockReviewOutcome.INCONCLUSIVE
        elif all(results):
            outcome = BlockReviewOutcome.SUPPORTED
        elif any(results):
            outcome = BlockReviewOutcome.PARTIALLY_SUPPORTED
        else:
            outcome = BlockReviewOutcome.NOT_SUPPORTED
        prescribed = sum(item.prescribed_sessions for item in response_items)
        actual = sum(item.actual_dose_total for item in response_items)
        planned = sum(item.prescribed_dose_total for item in response_items)
        observations = tuple(
            dict.fromkeys(
                source for item in response_items for source in item.source_observation_ids
            )
        )
        evidence = tuple(dict.fromkeys((*block.evidence_claim_ids, *policy.evidence_claim_ids)))
        return BlockReview(
            athlete_id=block.athlete_id,
            block_plan_id=block.id,
            block_hypothesis=block.hypothesis,
            block_review_policy_id=policy.id,
            training_response_ids=tuple(item.id for item in response_items),
            response_evaluations=tuple(evaluations),
            post_session_safety_decision_ids=tuple(item.id for item in safety_items),
            prescribed_sessions=prescribed,
            completed_sessions=sum(item.completed_sessions for item in response_items),
            aggregate_adherence_ratio=min(1.0, actual / planned),
            outcome=outcome,
            source_observation_ids=observations,
            evidence_claim_ids=evidence,
            rationale=(
                f"block hypothesis review outcome: {outcome.value}",
                "no capability estimate or future plan was changed by this review",
            ),
            reviewed_at=reviewed_at,
            rule_version=f"{self.rule_version};policy={policy.policy_version}",
        )
