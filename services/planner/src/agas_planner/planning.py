from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from numbers import Real
from typing import Protocol, TypeVar
from uuid import UUID

from agas_domain import (
    Adaptation,
    AdaptationPlanningCandidate,
    AdaptationPriority,
    CapabilityEstimate,
    CapabilityNeed,
    ComparisonDirection,
    CompetencyFloor,
    CompetencyStatus,
    Confidence,
    LongRangeStrategy,
    PlanningReason,
    PriorityPolicy,
    RoadmapItem,
    TrainingPriorityState,
)


class _HasId(Protocol):
    @property
    def id(self) -> UUID: ...


_Record = TypeVar("_Record", bound=_HasId)


class PlanningError(ValueError):
    """Raised when planning inputs cannot produce an inspectable strategy."""


class CompetencyFloorDetector:
    """Compare one estimate with one evidence-linked floor without hiding uncertainty."""

    def __init__(self, rule_version: str = "competency-floor-detection@1.0.0") -> None:
        self.rule_version = rule_version

    def identify(
        self,
        athlete_id: UUID,
        floor: CompetencyFloor,
        estimate: CapabilityEstimate | None,
        identified_at: datetime,
    ) -> CapabilityNeed:
        self._require_aware(identified_at)
        if estimate is None:
            return self._need(
                athlete_id=athlete_id,
                floor=floor,
                estimate=None,
                status=CompetencyStatus.UNKNOWN,
                observed_value=None,
                confidence=Confidence.UNKNOWN,
                rationale="no capability estimate is available for this competency floor",
                identified_at=identified_at,
            )
        if estimate.athlete_id != athlete_id:
            raise PlanningError("capability estimate belongs to a different athlete")
        if estimate.estimated_at > identified_at:
            raise PlanningError("capability estimate cannot come from the future")
        if estimate.valid_until is not None and estimate.valid_until <= identified_at:
            return self._need(
                athlete_id=athlete_id,
                floor=floor,
                estimate=estimate,
                status=CompetencyStatus.STALE,
                observed_value=self._numeric_value(estimate.estimate),
                confidence=estimate.confidence,
                rationale="capability estimate is stale at the time of need identification",
                identified_at=identified_at,
            )
        if (
            estimate.domain is not floor.domain
            or estimate.estimate_scope != floor.estimate_scope
            or estimate.unit_or_scale != floor.unit_or_scale
        ):
            return self._need(
                athlete_id=athlete_id,
                floor=floor,
                estimate=estimate,
                status=CompetencyStatus.INCOMPARABLE,
                observed_value=self._numeric_value(estimate.estimate),
                confidence=estimate.confidence,
                rationale="estimate domain, scope, or unit does not match the competency floor",
                identified_at=identified_at,
            )

        observed_value = self._numeric_value(estimate.estimate)
        if observed_value is None:
            return self._need(
                athlete_id=athlete_id,
                floor=floor,
                estimate=estimate,
                status=CompetencyStatus.INCOMPARABLE,
                observed_value=None,
                confidence=estimate.confidence,
                rationale="capability estimate is not a numeric value comparable with the floor",
                identified_at=identified_at,
            )

        signed_gap = self._deficit_gap(floor, observed_value)
        if signed_gap > 0:
            status = CompetencyStatus.BELOW_FLOOR
            gap = signed_gap
            normalized = min(1.0, gap / floor.threshold)
            rationale = (
                f"observed value {observed_value:g} is below the configured competency floor "
                f"by {gap:g} {floor.unit_or_scale}"
            )
        elif observed_value == floor.threshold:
            status = CompetencyStatus.MEETS_FLOOR
            gap = 0.0
            normalized = 0.0
            rationale = "observed value exactly meets the configured competency floor"
        else:
            status = CompetencyStatus.ABOVE_FLOOR
            gap = 0.0
            normalized = 0.0
            rationale = "observed value exceeds the configured competency floor"

        return self._need(
            athlete_id=athlete_id,
            floor=floor,
            estimate=estimate,
            status=status,
            observed_value=observed_value,
            confidence=estimate.confidence,
            rationale=rationale,
            identified_at=identified_at,
            gap_from_floor=gap,
            normalized_deficit=normalized,
        )

    def _need(
        self,
        *,
        athlete_id: UUID,
        floor: CompetencyFloor,
        estimate: CapabilityEstimate | None,
        status: CompetencyStatus,
        observed_value: float | None,
        confidence: Confidence,
        rationale: str,
        identified_at: datetime,
        gap_from_floor: float | None = None,
        normalized_deficit: float | None = None,
    ) -> CapabilityNeed:
        return CapabilityNeed(
            athlete_id=athlete_id,
            domain=floor.domain,
            competency_floor_id=floor.id,
            capability_estimate_id=None if estimate is None else estimate.id,
            status=status,
            observed_value=observed_value,
            floor_value=floor.threshold,
            unit_or_scale=floor.unit_or_scale,
            gap_from_floor=gap_from_floor,
            normalized_deficit=normalized_deficit,
            confidence=confidence,
            rationale=rationale,
            evidence_claim_ids=floor.evidence_claim_ids,
            identified_at=identified_at,
            rule_version=self.rule_version,
        )

    @staticmethod
    def _numeric_value(value: object) -> float | None:
        if isinstance(value, bool) or not isinstance(value, Real):
            return None
        return float(value)

    @staticmethod
    def _deficit_gap(floor: CompetencyFloor, observed_value: float) -> float:
        if floor.comparison_direction is ComparisonDirection.HIGHER_IS_BETTER:
            return floor.threshold - observed_value
        return observed_value - floor.threshold

    @staticmethod
    def _require_aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise PlanningError("planning timestamps must include a timezone")


class LongRangeStrategyPlanner:
    """Rank adaptation needs and produce a revisionable, non-prescriptive roadmap."""

    def __init__(self, rule_version: str = "long-range-strategy@1.0.0") -> None:
        self.rule_version = rule_version

    def build(
        self,
        *,
        athlete_id: UUID,
        adaptations: Iterable[Adaptation],
        needs: Iterable[CapabilityNeed],
        candidates: Iterable[AdaptationPlanningCandidate],
        policy: PriorityPolicy,
        generated_at: datetime,
        horizon_months: int,
        review_after_days: int,
    ) -> LongRangeStrategy:
        CompetencyFloorDetector._require_aware(generated_at)
        if review_after_days < 1:
            raise PlanningError("review_after_days must be positive")

        adaptations_by_id = self._unique_by_id(adaptations, "adaptations")
        needs_by_id = self._unique_by_id(needs, "capability needs")
        candidate_list = tuple(candidates)
        candidate_ids = [item.adaptation_id for item in candidate_list]
        if not candidate_list:
            raise PlanningError("at least one adaptation candidate is required")
        if len(set(candidate_ids)) != len(candidate_ids):
            raise PlanningError("each adaptation may appear in planning candidates once")

        prepared = []
        for candidate in candidate_list:
            adaptation = adaptations_by_id.get(candidate.adaptation_id)
            need = needs_by_id.get(candidate.capability_need_id)
            if adaptation is None:
                raise PlanningError(f"unknown adaptation candidate: {candidate.adaptation_id}")
            if need is None:
                raise PlanningError(f"unknown capability need: {candidate.capability_need_id}")
            if need.athlete_id != athlete_id:
                raise PlanningError("all capability needs must belong to the strategy athlete")
            if adaptation.domain is not need.domain:
                raise PlanningError("adaptation and capability need domains must match")
            score, components = self._score(need, candidate, policy)
            prepared.append((candidate, adaptation, need, score, components))

        prepared.sort(key=lambda item: (-item[3], str(item[0].adaptation_id)))
        severe_deficit_exists = any(
            need.status is CompetencyStatus.BELOW_FLOOR
            and (need.normalized_deficit or 0) >= policy.severe_deficit_threshold
            for _, _, need, _, _ in prepared
        )

        state_drafts: list[tuple[TrainingPriorityState, PlanningReason, str]] = []
        development_slots = policy.max_develop_adaptations
        for candidate, adaptation, need, score, _ in prepared:
            state, reason, rationale, consumes_slot = self._assign_state(
                candidate=candidate,
                adaptation=adaptation,
                need=need,
                score=score,
                policy=policy,
                severe_deficit_exists=severe_deficit_exists,
                development_slot_available=development_slots > 0,
            )
            if consumes_slot:
                development_slots -= 1
            state_drafts.append((state, reason, rationale))

        develop_scores = [
            score
            for (_, _, _, score, _), (state, _, _) in zip(prepared, state_drafts, strict=True)
            if state is TrainingPriorityState.DEVELOP
        ]
        score_total = sum(develop_scores)
        develop_count = len(develop_scores)

        priorities = []
        roadmap = []
        for rank, ((candidate, adaptation, need, score, components), draft) in enumerate(
            zip(prepared, state_drafts, strict=True), start=1
        ):
            state, reason, rationale = draft
            if state is TrainingPriorityState.DEVELOP:
                allocation = score / score_total if score_total > 0 else 1 / develop_count
            else:
                allocation = 0.0
            priority = AdaptationPriority(
                adaptation_id=adaptation.id,
                capability_need_id=need.id,
                state=state,
                score=score,
                rank=rank,
                development_allocation=allocation,
                score_components=components,
                reason_codes=(reason,),
                rationale=(rationale,),
            )
            priorities.append(priority)
            roadmap.append(
                RoadmapItem(
                    adaptation_id=adaptation.id,
                    current_state=state,
                    sequence_group=1 if state is not TrainingPriorityState.DEFER else 2,
                    prerequisite_adaptation_ids=candidate.prerequisite_adaptation_ids,
                    rationale=rationale,
                    review_trigger=self._review_trigger(reason),
                )
            )

        source_observation_ids = self._ordered_unique(
            observation_id
            for candidate in candidate_list
            for observation_id in candidate.source_observation_ids
        )
        used_needs = tuple(needs_by_id[item.capability_need_id] for item in candidate_list)
        source_estimate_ids = self._ordered_unique(
            need.capability_estimate_id
            for need in used_needs
            if need.capability_estimate_id is not None
        )
        if not source_estimate_ids:
            raise PlanningError("a long-range strategy requires at least one capability estimate")
        floor_ids = self._ordered_unique(need.competency_floor_id for need in used_needs)
        evidence_ids = self._ordered_unique(
            evidence_id
            for candidate in candidate_list
            for evidence_id in candidate.evidence_claim_ids
        )
        evidence_ids = self._ordered_unique(
            (
                *evidence_ids,
                *(evidence_id for need in used_needs for evidence_id in need.evidence_claim_ids),
            )
        )

        return LongRangeStrategy(
            athlete_id=athlete_id,
            priority_policy_id=policy.id,
            horizon_months=horizon_months,
            priorities=tuple(priorities),
            roadmap=tuple(roadmap),
            block_hypothesis=self._hypothesis(priorities, adaptations_by_id),
            source_observation_ids=source_observation_ids,
            source_capability_estimate_ids=source_estimate_ids,
            competency_floor_ids=floor_ids,
            evidence_claim_ids=evidence_ids,
            generated_at=generated_at,
            next_review_at=generated_at + timedelta(days=review_after_days),
            rule_version=f"{self.rule_version};policy={policy.policy_version}",
        )

    @staticmethod
    def _unique_by_id(items: Iterable[_Record], label: str) -> dict[UUID, _Record]:
        result: dict[UUID, _Record] = {}
        for item in items:
            item_id = item.id
            if item_id in result:
                raise PlanningError(f"{label} contain duplicate ids")
            result[item_id] = item
        return result

    @staticmethod
    def _ordered_unique(values: Iterable[UUID]) -> tuple[UUID, ...]:
        return tuple(dict.fromkeys(values))

    @staticmethod
    def _score(
        need: CapabilityNeed,
        candidate: AdaptationPlanningCandidate,
        policy: PriorityPolicy,
    ) -> tuple[float, dict[str, float]]:
        deficit = need.normalized_deficit or 0.0
        benefits = (
            (deficit, policy.deficit_weight),
            (candidate.general_relevance, policy.general_relevance_weight),
            (candidate.goal_relevance, policy.goal_relevance_weight),
            (candidate.prerequisite_value, policy.prerequisite_value_weight),
            (candidate.expected_trainability, policy.expected_trainability_weight),
            (candidate.transfer_value, policy.transfer_value_weight),
        )
        benefit_weight = sum(weight for _, weight in benefits)
        raw_benefit = sum(value * weight for value, weight in benefits) / benefit_weight
        confidence_multiplier = policy.confidence_multipliers[need.confidence]
        adjusted_benefit = raw_benefit * confidence_multiplier

        costs = (
            (candidate.fatigue_cost, policy.fatigue_cost_weight),
            (candidate.time_cost, policy.time_cost_weight),
            (candidate.interference_cost, policy.interference_cost_weight),
        )
        cost_weight = sum(weight for _, weight in costs)
        cost = sum(value * weight for value, weight in costs) / cost_weight if cost_weight else 0.0
        score = min(1.0, max(0.0, adjusted_benefit - policy.cost_penalty * cost))
        return score, {
            "deficit": deficit,
            "general_relevance": candidate.general_relevance,
            "goal_relevance": candidate.goal_relevance,
            "prerequisite_value": candidate.prerequisite_value,
            "expected_trainability": candidate.expected_trainability,
            "transfer_value": candidate.transfer_value,
            "confidence_multiplier": confidence_multiplier,
            "raw_benefit": raw_benefit,
            "cost": cost,
            "final_score": score,
        }

    @staticmethod
    def _assign_state(
        *,
        candidate: AdaptationPlanningCandidate,
        adaptation: Adaptation,
        need: CapabilityNeed,
        score: float,
        policy: PriorityPolicy,
        severe_deficit_exists: bool,
        development_slot_available: bool,
    ) -> tuple[TrainingPriorityState, PlanningReason, str, bool]:
        if not candidate.safe_to_train:
            return (
                TrainingPriorityState.DEFER,
                PlanningReason.SAFETY_CONSTRAINT,
                f"defer {adaptation.name} because an explicit safety constraint is active",
                False,
            )
        if candidate.introductory_exposure_needed:
            return (
                TrainingPriorityState.EXPOSE,
                PlanningReason.INTRODUCTORY_EXPOSURE,
                f"introduce low-dose {adaptation.name} exposure before development emphasis",
                False,
            )
        if not candidate.prerequisites_met:
            return (
                TrainingPriorityState.DEFER,
                PlanningReason.PREREQUISITE_NOT_MET,
                f"defer {adaptation.name} until its configured prerequisites are met",
                False,
            )
        if need.status in {
            CompetencyStatus.UNKNOWN,
            CompetencyStatus.STALE,
            CompetencyStatus.INCOMPARABLE,
        }:
            return (
                TrainingPriorityState.DEFER,
                PlanningReason.INFORMATION_GAP,
                f"defer {adaptation.name} development until capability information is resolved",
                False,
            )
        if need.status is CompetencyStatus.BELOW_FLOOR:
            if score >= policy.develop_score_threshold and development_slot_available:
                return (
                    TrainingPriorityState.DEVELOP,
                    PlanningReason.COMPETENCY_DEFICIT,
                    f"develop {adaptation.name} because the capability is below its "
                    "configured floor",
                    True,
                )
            return (
                TrainingPriorityState.DEFER,
                PlanningReason.LOWER_PRIORITY,
                f"defer {adaptation.name}; its deficit ranks below the current development set",
                False,
            )
        if (
            candidate.cultivate_comparative_advantage
            and not severe_deficit_exists
            and score >= policy.comparative_advantage_threshold
            and development_slot_available
        ):
            return (
                TrainingPriorityState.DEVELOP,
                PlanningReason.COMPARATIVE_ADVANTAGE,
                f"develop athlete-valued comparative advantage in {adaptation.name}",
                True,
            )
        return (
            TrainingPriorityState.MAINTAIN,
            PlanningReason.COMPETENCY_MET,
            f"maintain {adaptation.name} because its configured competency floor is met",
            False,
        )

    @staticmethod
    def _review_trigger(reason: PlanningReason) -> str:
        if reason is PlanningReason.INFORMATION_GAP:
            return "a new valid compatible capability estimate becomes available"
        if reason is PlanningReason.SAFETY_CONSTRAINT:
            return "the safety workflow records that the constraint is resolved"
        if reason is PlanningReason.PREREQUISITE_NOT_MET:
            return "configured prerequisites are reassessed as met"
        return "the scheduled strategy review or a material athlete-state change occurs"

    @staticmethod
    def _hypothesis(
        priorities: list[AdaptationPriority],
        adaptations_by_id: dict[UUID, Adaptation],
    ) -> str:
        names_by_state: dict[TrainingPriorityState, list[str]] = {
            state: [] for state in TrainingPriorityState
        }
        for priority in priorities:
            adaptation = adaptations_by_id[priority.adaptation_id]
            names_by_state[priority.state].append(adaptation.name)

        clauses = []
        if names_by_state[TrainingPriorityState.DEVELOP]:
            clauses.append("develop " + ", ".join(names_by_state[TrainingPriorityState.DEVELOP]))
        if names_by_state[TrainingPriorityState.MAINTAIN]:
            clauses.append("maintain " + ", ".join(names_by_state[TrainingPriorityState.MAINTAIN]))
        if names_by_state[TrainingPriorityState.EXPOSE]:
            clauses.append(
                "introduce exposure to " + ", ".join(names_by_state[TrainingPriorityState.EXPOSE])
            )
        if names_by_state[TrainingPriorityState.DEFER]:
            clauses.append("defer " + ", ".join(names_by_state[TrainingPriorityState.DEFER]))
        return "; ".join(clauses) + "; reassess before changing the allocation strategy."
