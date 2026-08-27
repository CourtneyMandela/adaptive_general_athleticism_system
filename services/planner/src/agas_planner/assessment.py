from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import ClassVar
from uuid import UUID

from agas_domain import (
    AssessmentContext,
    AssessmentDecision,
    AssessmentDefinition,
    AssessmentDefinitionReview,
    AssessmentPerformance,
    AssessmentReason,
    AssessmentResultInput,
    AssessmentReviewDecision,
    AssessmentSelection,
    CapabilityEstimate,
    CapabilityEstimationPolicy,
    Confidence,
    Observation,
    ObservationSource,
)


class AssessmentError(ValueError):
    """Raised when an assessment operation would violate a domain invariant."""


@dataclass(frozen=True)
class AssessmentReassessmentTiming:
    assessment_definition_id: UUID
    current_review_id: UUID
    latest_performance_id: UUID | None
    interval_source_review_id: UUID
    next_reassessment_at: datetime | None
    due: bool


@dataclass(frozen=True)
class AssessmentReassessmentSchedule:
    timings: tuple[AssessmentReassessmentTiming, ...]
    evaluated_at: datetime
    rule_version: str

    @property
    def due_definition_ids(self) -> tuple[UUID, ...]:
        return tuple(item.assessment_definition_id for item in self.timings if item.due)

    @property
    def next_reassessment_at(self) -> datetime | None:
        future = tuple(
            item.next_reassessment_at
            for item in self.timings
            if not item.due and item.next_reassessment_at is not None
        )
        return min(future) if future else None


class AssessmentReassessmentScheduler:
    """Resolve protocol due dates without inventing an interval or rewriting history."""

    def __init__(self, rule_version: str = "assessment-reassessment-schedule@1.0.0") -> None:
        self.rule_version = rule_version

    def schedule(
        self,
        reviewed_definitions: Iterable[tuple[AssessmentDefinition, AssessmentDefinitionReview]],
        performances: Iterable[AssessmentPerformance],
        performance_reviews: Mapping[UUID, AssessmentDefinitionReview],
        evaluated_at: datetime,
    ) -> AssessmentReassessmentSchedule:
        if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
            raise AssessmentError("reassessment schedule time must include a timezone")

        latest_by_definition: dict[UUID, AssessmentPerformance] = {}
        for performance in sorted(
            performances,
            key=lambda item: (item.performed_at, item.created_at, str(item.id)),
            reverse=True,
        ):
            latest_by_definition.setdefault(performance.assessment_definition_id, performance)

        timings: list[AssessmentReassessmentTiming] = []
        for definition, current_review in reviewed_definitions:
            if current_review.assessment_definition_id != definition.id:
                raise AssessmentError("reassessment review does not match its definition")
            if (
                current_review.decision is not AssessmentReviewDecision.APPROVED
                or current_review.recommended_reassessment_days is None
            ):
                raise AssessmentError("reassessment requires a currently approved interval")

            latest = latest_by_definition.get(definition.id)
            if latest is None:
                timings.append(
                    AssessmentReassessmentTiming(
                        assessment_definition_id=definition.id,
                        current_review_id=current_review.id,
                        latest_performance_id=None,
                        interval_source_review_id=current_review.id,
                        next_reassessment_at=None,
                        due=True,
                    )
                )
                continue

            interval_review = performance_reviews.get(latest.assessment_definition_review_id)
            if (
                interval_review is None
                or interval_review.assessment_definition_id != definition.id
                or interval_review.decision is not AssessmentReviewDecision.APPROVED
                or interval_review.recommended_reassessment_days is None
            ):
                raise AssessmentError(
                    "latest assessment performance has no valid interval-source review"
                )
            next_at = latest.performed_at + timedelta(
                days=interval_review.recommended_reassessment_days
            )
            timings.append(
                AssessmentReassessmentTiming(
                    assessment_definition_id=definition.id,
                    current_review_id=current_review.id,
                    latest_performance_id=latest.id,
                    interval_source_review_id=interval_review.id,
                    next_reassessment_at=next_at,
                    due=evaluated_at >= next_at,
                )
            )

        return AssessmentReassessmentSchedule(
            timings=tuple(timings),
            evaluated_at=evaluated_at,
            rule_version=self.rule_version,
        )


class AdaptiveAssessmentSelector:
    """Select assessments using explicit, versioned, deterministic constraints."""

    def __init__(self, rule_version: str = "assessment-selection@1.0.0") -> None:
        self.rule_version = rule_version

    def select(
        self,
        context: AssessmentContext,
        definitions: Iterable[AssessmentDefinition],
    ) -> tuple[AssessmentSelection, ...]:
        return tuple(self._evaluate(context, definition, None) for definition in definitions)

    def select_reviewed(
        self,
        context: AssessmentContext,
        reviewed_definitions: Iterable[tuple[AssessmentDefinition, AssessmentDefinitionReview]],
        eligibility_review_id: UUID,
    ) -> tuple[AssessmentSelection, ...]:
        selections: list[AssessmentSelection] = []
        for definition, review in reviewed_definitions:
            if review.assessment_definition_id != definition.id:
                raise AssessmentError("assessment review does not match its definition")
            if review.decision is not AssessmentReviewDecision.APPROVED:
                raise AssessmentError("assessment review is not approved")
            if review.measurement_schema is None:
                raise AssessmentError("assessment review has no measurement schema")
            selections.append(self._evaluate(context, definition, review.id, eligibility_review_id))
        return tuple(selections)

    def _evaluate(
        self,
        context: AssessmentContext,
        definition: AssessmentDefinition,
        definition_review_id: UUID | None,
        eligibility_review_id: UUID | None = None,
    ) -> AssessmentSelection:
        exclusion_reasons: list[tuple[AssessmentReason, str]] = []
        deferral_reasons: list[tuple[AssessmentReason, str]] = []

        if not context.health_screening_completed:
            exclusion_reasons.append(
                (
                    AssessmentReason.HEALTH_SCREENING_CONSTRAINT,
                    "health screening has not been completed",
                )
            )

        health_flags = sorted(
            set(context.health_screening_flags) & set(definition.blocked_by_health_screening_flags)
        )
        if health_flags:
            exclusion_reasons.append(
                (
                    AssessmentReason.HEALTH_SCREENING_CONSTRAINT,
                    f"blocked by health-screening flags: {', '.join(health_flags)}",
                )
            )

        symptom_flags = sorted(
            set(context.current_symptom_flags) & set(definition.blocked_by_symptom_flags)
        )
        if symptom_flags:
            exclusion_reasons.append(
                (
                    AssessmentReason.SYMPTOM_CONSTRAINT,
                    f"blocked by current symptom flags: {', '.join(symptom_flags)}",
                )
            )

        injury_flags = sorted(
            set(context.current_injury_flags) & set(definition.blocked_by_injury_flags)
        )
        if injury_flags:
            exclusion_reasons.append(
                (
                    AssessmentReason.INJURY_CONSTRAINT,
                    f"blocked by current injury flags: {', '.join(injury_flags)}",
                )
            )

        if definition.requires_body_mass and context.body_mass_kg is None:
            deferral_reasons.append(
                (
                    AssessmentReason.MISSING_BODY_MASS,
                    "body mass is required by this protocol but was not observed",
                )
            )

        missing_equipment = sorted(
            set(definition.required_equipment_categories)
            - set(context.available_equipment_categories)
        )
        if missing_equipment:
            deferral_reasons.append(
                (
                    AssessmentReason.MISSING_EQUIPMENT,
                    f"missing equipment categories: {', '.join(missing_equipment)}",
                )
            )

        training_age = context.training_age_months_by_domain.get(definition.domain.value, 0)
        if training_age < definition.min_training_age_months:
            deferral_reasons.append(
                (
                    AssessmentReason.INSUFFICIENT_TRAINING_HISTORY,
                    "training history is "
                    f"{training_age} months; {definition.min_training_age_months} required",
                )
            )

        missing_skills = sorted(
            set(definition.required_skill_tags) - set(context.exercise_skill_tags)
        )
        if missing_skills:
            deferral_reasons.append(
                (
                    AssessmentReason.MISSING_SKILL,
                    f"missing skill tags: {', '.join(missing_skills)}",
                )
            )

        missing_exposures = sorted(
            set(definition.required_recent_exposure_tags) - set(context.recent_exposure_tags)
        )
        if missing_exposures:
            deferral_reasons.append(
                (
                    AssessmentReason.MISSING_RECENT_EXPOSURE,
                    f"missing recent exposure tags: {', '.join(missing_exposures)}",
                )
            )

        if exclusion_reasons:
            decision = AssessmentDecision.EXCLUDED
            reasons = exclusion_reasons + deferral_reasons
        elif deferral_reasons:
            decision = AssessmentDecision.DEFERRED
            reasons = deferral_reasons
        else:
            decision = AssessmentDecision.SELECTED
            reasons = [
                (
                    AssessmentReason.ELIGIBLE,
                    "all versioned assessment constraints were satisfied",
                )
            ]

        return AssessmentSelection(
            athlete_id=context.athlete_id,
            assessment_definition_id=definition.id,
            assessment_definition_review_id=definition_review_id,
            assessment_eligibility_review_id=eligibility_review_id,
            decision=decision,
            reason_codes=tuple(reason for reason, _ in reasons),
            rationale=tuple(rationale for _, rationale in reasons),
            source_observation_ids=context.source_observation_ids,
            evaluated_at=context.evaluated_at,
            rule_version=self.rule_version,
        )


class AssessmentResultRecorder:
    """Convert a performed assessment into an immutable direct observation."""

    def record(
        self,
        definition: AssessmentDefinition,
        result: AssessmentResultInput,
    ) -> Observation:
        if result.assessment_definition_id != definition.id:
            raise AssessmentError("result does not reference the supplied assessment definition")
        if result.unit != definition.unit_or_scale:
            raise AssessmentError(
                f"result unit {result.unit!r} does not match {definition.unit_or_scale!r}"
            )

        assessment_context = {
            **result.context,
            "assessment_definition_id": str(definition.id),
            "assessment_slug": definition.slug,
            "protocol_version": definition.protocol_version,
            "assessment_intensity": definition.intensity.value,
        }
        return Observation(
            athlete_id=result.athlete_id,
            observed_at=result.performed_at,
            observation_type=definition.observation_type,
            measurement=result.measurement,
            unit=result.unit,
            source=ObservationSource.TEST_RESULT,
            reliability=result.reliability,
            context=assessment_context,
            provenance=result.provenance,
        )


class ConservativeCapabilityEstimator:
    """Create bounded estimates without normative interpretation or invented cutoffs."""

    _confidence_rank: ClassVar[dict[Confidence, int]] = {
        Confidence.UNKNOWN: 0,
        Confidence.LOW: 1,
        Confidence.MODERATE: 2,
        Confidence.HIGH: 3,
    }

    def estimate(
        self,
        policy: CapabilityEstimationPolicy,
        observations: Iterable[Observation],
        estimated_at: datetime,
    ) -> CapabilityEstimate:
        if estimated_at.tzinfo is None or estimated_at.utcoffset() is None:
            raise AssessmentError("estimated_at must include a timezone")

        candidates = sorted(
            (
                observation
                for observation in observations
                if observation.observation_type == policy.observation_type
                and observation.observed_at <= estimated_at
                and estimated_at - observation.observed_at
                <= timedelta(days=policy.multi_observation_window_days)
            ),
            key=lambda item: (item.observed_at, item.created_at, str(item.id)),
        )
        if not candidates:
            raise AssessmentError("no matching observations are available inside the policy window")

        athlete_ids = {item.athlete_id for item in candidates}
        if len(athlete_ids) != 1:
            raise AssessmentError("all source observations must belong to one athlete")
        if any(item.unit != policy.unit_or_scale for item in candidates):
            raise AssessmentError("all source observation units must match the policy")

        latest = candidates[-1]
        valid_until = latest.observed_at + timedelta(days=policy.valid_for_days)
        if valid_until <= estimated_at:
            raise AssessmentError("the latest matching observation is stale under the policy")
        return CapabilityEstimate(
            athlete_id=latest.athlete_id,
            domain=policy.domain,
            estimate=latest.measurement,
            unit_or_scale=policy.unit_or_scale,
            estimate_scope=f"assessment_specific:{policy.observation_type}",
            confidence=self._confidence(candidates),
            calculation_method=policy.calculation_method,
            source_observation_ids=tuple(item.id for item in candidates),
            estimated_at=estimated_at,
            valid_until=valid_until,
            rule_version=policy.rule_version,
        )

    def _confidence(self, observations: list[Observation]) -> Confidence:
        lowest = min(observations, key=lambda item: self._confidence_rank[item.reliability])
        if lowest.reliability is Confidence.UNKNOWN:
            return Confidence.UNKNOWN
        if len(observations) == 1:
            return Confidence.LOW
        if self._confidence_rank[lowest.reliability] >= self._confidence_rank[Confidence.MODERATE]:
            return Confidence.MODERATE
        return Confidence.LOW
