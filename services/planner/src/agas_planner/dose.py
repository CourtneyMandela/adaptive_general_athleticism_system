from __future__ import annotations

from datetime import datetime
from math import floor, isfinite
from numbers import Real
from uuid import UUID

from agas_domain import (
    Adaptation,
    AdaptationPriority,
    CapabilityEstimate,
    CapabilityNeed,
    CompetencyStatus,
    ExposureNeed,
    ExposureNeedStatus,
    FixedDurationDosePolicy,
    FixedRepetitionDosePolicy,
    IntroductoryExposureDose,
    IntroductoryExposureDosePolicy,
    RepetitionDosePolicy,
    TrainingPriorityState,
)
from pydantic import BaseModel, ConfigDict, Field


class RepetitionDoseError(ValueError):
    """Raised when a governed repetition dose cannot be derived safely."""


class IntroductoryExposureDoseError(ValueError):
    """Raised when an exposure need and fixed starting-dose policy are incompatible."""


class FixedRepetitionDoseError(ValueError):
    """Raised when governed capability lineage cannot authorize a fixed starting dose."""


class FixedDurationDoseError(ValueError):
    """Raised when governed capability lineage cannot authorize fixed duration work."""


class IntroductoryExposureDosePlanner:
    """Derive one inspectable starting dose without using a capability estimate."""

    def __init__(self, rule_version: str = "introductory-exposure-dose@1.0.0") -> None:
        self.rule_version = rule_version

    def derive(
        self,
        *,
        dose_id: UUID,
        need: ExposureNeed,
        adaptation: Adaptation,
        policy: IntroductoryExposureDosePolicy,
        derived_at: datetime,
    ) -> IntroductoryExposureDose:
        if derived_at.tzinfo is None or derived_at.utcoffset() is None:
            raise IntroductoryExposureDoseError(
                "dose derivation timestamps must include a timezone"
            )
        if need.status is not ExposureNeedStatus.INTRODUCTORY_EXPOSURE_NEEDED:
            raise IntroductoryExposureDoseError(
                "exposure need does not authorize an introductory dose"
            )
        if need.identified_at > derived_at:
            raise IntroductoryExposureDoseError("exposure need cannot come from the future")
        if need.valid_until is not None and need.valid_until <= derived_at:
            raise IntroductoryExposureDoseError("exposure need is stale")
        if adaptation.id != policy.adaptation_id:
            raise IntroductoryExposureDoseError("dose policy belongs to a different adaptation")
        if (
            need.exposure_type is not policy.exposure_type
            or need.target_scope != policy.target_scope
        ):
            raise IntroductoryExposureDoseError(
                "exposure need scope does not match the dose policy"
            )
        total_dose = policy.sets * policy.dose_per_set
        if total_dose > policy.maximum_total_dose:
            raise IntroductoryExposureDoseError("derived dose exceeds the policy maximum")
        return IntroductoryExposureDose(
            id=dose_id,
            created_at=derived_at,
            athlete_id=need.athlete_id,
            exposure_need_id=need.id,
            policy_id=policy.id,
            adaptation_id=adaptation.id,
            exposure_type=need.exposure_type,
            target_scope=need.target_scope,
            dose_unit=policy.dose_unit,
            sets=policy.sets,
            dose_per_set=policy.dose_per_set,
            total_dose=total_dose,
            rest_seconds=policy.rest_seconds,
            effort_rpe_minimum=policy.effort_rpe_minimum,
            effort_rpe_maximum=policy.effort_rpe_maximum,
            technique_constraints=policy.technique_constraints,
            planned_duration_minutes=policy.planned_duration_minutes,
            source_observation_ids=need.source_observation_ids,
            evidence_claim_ids=policy.evidence_claim_ids,
            numeric_value_origin=policy.numeric_value_origin,
            authority_reference=policy.authority_reference,
            rationale=(
                f"Apply {policy.policy_version} to unmet exposure need {need.id}; "
                f"{policy.rationale}"
            ),
            uncertainty=policy.uncertainty,
            derived_at=derived_at,
            rule_version=f"{self.rule_version};policy={policy.policy_version}",
        )


class DerivedRepetitionDose(BaseModel):
    """Inspectible output of one exact estimate and one exact dose-policy version."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    adaptation_id: UUID
    capability_estimate_id: UUID
    repetition_dose_policy_id: UUID
    progression_policy_id: UUID
    sets: int = Field(ge=1)
    repetitions_per_set: int = Field(ge=1)
    rest_seconds: int = Field(ge=0)
    effort_rpe_minimum: float = Field(ge=0, le=10)
    effort_rpe_maximum: float = Field(ge=0, le=10)
    technique_constraints: tuple[str, ...]
    planned_duration_minutes: int = Field(gt=0)
    derived_at: datetime
    calculation_method: str
    rule_version: str


class DerivedFixedRepetitionDose(BaseModel):
    """Inspectible fixed dose whose repetitions do not come from estimate arithmetic."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    adaptation_id: UUID
    adaptation_priority_id: UUID
    capability_need_id: UUID
    capability_estimate_id: UUID
    fixed_repetition_dose_policy_id: UUID
    progression_policy_id: UUID
    sets: int = Field(ge=1)
    repetitions_per_set: int = Field(ge=1)
    rest_seconds: int = Field(ge=0)
    effort_rpe_minimum: float = Field(ge=0, le=10)
    effort_rpe_maximum: float = Field(ge=0, le=10)
    technique_constraints: tuple[str, ...]
    planned_duration_minutes: int = Field(gt=0)
    source_observation_ids: tuple[UUID, ...]
    evidence_claim_ids: tuple[UUID, ...]
    numeric_value_origin: str
    authority_reference: str
    derived_at: datetime
    calculation_method: str
    rule_version: str


class DerivedFixedDurationDose(BaseModel):
    """Inspectible duration dose whose seconds do not come from estimate arithmetic."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    adaptation_id: UUID
    adaptation_priority_id: UUID
    capability_need_id: UUID
    capability_estimate_id: UUID
    fixed_duration_dose_policy_id: UUID
    progression_policy_id: UUID
    sets: int = Field(ge=1)
    duration_seconds_per_set: int = Field(ge=1)
    rest_seconds: int = Field(ge=0)
    effort_rpe_minimum: float = Field(ge=0, le=10)
    effort_rpe_maximum: float = Field(ge=0, le=10)
    technique_constraints: tuple[str, ...]
    planned_duration_minutes: int = Field(gt=0)
    source_observation_ids: tuple[UUID, ...]
    evidence_claim_ids: tuple[UUID, ...]
    numeric_value_origin: str
    authority_reference: str
    derived_at: datetime
    calculation_method: str
    rule_version: str


class FixedDurationDosePlanner:
    """Apply one explicit duration dose to one exact governed priority lineage."""

    def derive(
        self,
        *,
        adaptation: Adaptation,
        priority: AdaptationPriority,
        need: CapabilityNeed,
        estimate: CapabilityEstimate,
        policy: FixedDurationDosePolicy,
        derived_at: datetime,
    ) -> DerivedFixedDurationDose:
        self._require_aware(derived_at)
        if priority.state is not policy.priority_state:
            raise FixedDurationDoseError(
                f"fixed duration requires a {policy.priority_state.value.upper()} priority under "
                "this policy"
            )
        if priority.adaptation_id != adaptation.id or priority.capability_need_id != need.id:
            raise FixedDurationDoseError("priority lineage does not match adaptation and need")
        expected_need_statuses = {
            TrainingPriorityState.DEVELOP: {CompetencyStatus.BELOW_FLOOR},
            TrainingPriorityState.MAINTAIN: {
                CompetencyStatus.MEETS_FLOOR,
                CompetencyStatus.ABOVE_FLOOR,
            },
        }[policy.priority_state]
        if need.status not in expected_need_statuses:
            expected_label = (
                "below-floor"
                if policy.priority_state is TrainingPriorityState.DEVELOP
                else "at-or-above-floor"
            )
            raise FixedDurationDoseError(
                f"fixed duration requires {expected_label} capability-need lineage"
            )
        if need.capability_estimate_id != estimate.id:
            raise FixedDurationDoseError("capability need does not reference the supplied estimate")
        if need.athlete_id != estimate.athlete_id:
            raise FixedDurationDoseError(
                "capability need and estimate belong to different athletes"
            )
        if adaptation.id != policy.adaptation_id:
            raise FixedDurationDoseError("dose policy belongs to a different adaptation")
        if need.domain is not adaptation.domain or estimate.domain is not adaptation.domain:
            raise FixedDurationDoseError("capability lineage does not match the adaptation domain")
        if need.identified_at > derived_at or estimate.estimated_at > derived_at:
            raise FixedDurationDoseError("capability lineage cannot come from the future")
        if estimate.valid_until is not None and estimate.valid_until <= derived_at:
            raise FixedDurationDoseError("capability estimate is stale")
        if estimate.estimate_scope != policy.estimate_scope:
            raise FixedDurationDoseError("capability estimate scope does not match the dose policy")
        total_duration = policy.sets * policy.duration_seconds_per_set
        if total_duration > policy.maximum_initial_total_duration_seconds:
            raise FixedDurationDoseError("fixed starting duration exceeds the policy maximum")
        return DerivedFixedDurationDose(
            adaptation_id=adaptation.id,
            adaptation_priority_id=priority.id,
            capability_need_id=need.id,
            capability_estimate_id=estimate.id,
            fixed_duration_dose_policy_id=policy.id,
            progression_policy_id=policy.progression_policy_id,
            sets=policy.sets,
            duration_seconds_per_set=policy.duration_seconds_per_set,
            rest_seconds=policy.rest_seconds,
            effort_rpe_minimum=policy.effort_rpe_minimum,
            effort_rpe_maximum=policy.effort_rpe_maximum,
            technique_constraints=policy.technique_constraints,
            planned_duration_minutes=policy.planned_duration_minutes,
            source_observation_ids=estimate.source_observation_ids,
            evidence_claim_ids=policy.evidence_claim_ids,
            numeric_value_origin=policy.numeric_value_origin,
            authority_reference=policy.authority_reference,
            derived_at=derived_at,
            calculation_method=(
                f"fixed {policy.sets}x{policy.duration_seconds_per_set} seconds under "
                f"{policy.policy_version}; estimate value not used as dose arithmetic"
            ),
            rule_version=policy.policy_version,
        )

    @staticmethod
    def _require_aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise FixedDurationDoseError("dose derivation timestamps must include a timezone")


class FixedRepetitionDosePlanner:
    """Apply one explicit fixed dose to one exact governed priority lineage."""

    def derive(
        self,
        *,
        adaptation: Adaptation,
        priority: AdaptationPriority,
        need: CapabilityNeed,
        estimate: CapabilityEstimate,
        policy: FixedRepetitionDosePolicy,
        derived_at: datetime,
    ) -> DerivedFixedRepetitionDose:
        self._require_aware(derived_at)
        if priority.state is not policy.priority_state:
            raise FixedRepetitionDoseError(
                f"fixed dose requires a {policy.priority_state.value.upper()} priority under "
                "this policy"
            )
        if priority.adaptation_id != adaptation.id or priority.capability_need_id != need.id:
            raise FixedRepetitionDoseError("priority lineage does not match adaptation and need")
        expected_need_statuses = {
            TrainingPriorityState.DEVELOP: {CompetencyStatus.BELOW_FLOOR},
            TrainingPriorityState.MAINTAIN: {
                CompetencyStatus.MEETS_FLOOR,
                CompetencyStatus.ABOVE_FLOOR,
            },
        }[policy.priority_state]
        if need.status not in expected_need_statuses:
            expected_label = (
                "below-floor"
                if policy.priority_state is TrainingPriorityState.DEVELOP
                else "at-or-above-floor"
            )
            raise FixedRepetitionDoseError(
                f"fixed dose requires {expected_label} capability-need lineage"
            )
        if need.capability_estimate_id != estimate.id:
            raise FixedRepetitionDoseError(
                "capability need does not reference the supplied estimate"
            )
        if need.athlete_id != estimate.athlete_id:
            raise FixedRepetitionDoseError(
                "capability need and estimate belong to different athletes"
            )
        if adaptation.id != policy.adaptation_id:
            raise FixedRepetitionDoseError("dose policy belongs to a different adaptation")
        if need.domain is not adaptation.domain or estimate.domain is not adaptation.domain:
            raise FixedRepetitionDoseError(
                "capability lineage does not match the adaptation domain"
            )
        if need.identified_at > derived_at or estimate.estimated_at > derived_at:
            raise FixedRepetitionDoseError("capability lineage cannot come from the future")
        if estimate.valid_until is not None and estimate.valid_until <= derived_at:
            raise FixedRepetitionDoseError("capability estimate is stale")
        if estimate.estimate_scope != policy.estimate_scope:
            raise FixedRepetitionDoseError(
                "capability estimate scope does not match the dose policy"
            )
        total_repetitions = policy.sets * policy.repetitions_per_set
        if total_repetitions > policy.maximum_initial_total_repetitions:
            raise FixedRepetitionDoseError("fixed starting dose exceeds the policy maximum")
        return DerivedFixedRepetitionDose(
            adaptation_id=adaptation.id,
            adaptation_priority_id=priority.id,
            capability_need_id=need.id,
            capability_estimate_id=estimate.id,
            fixed_repetition_dose_policy_id=policy.id,
            progression_policy_id=policy.progression_policy_id,
            sets=policy.sets,
            repetitions_per_set=policy.repetitions_per_set,
            rest_seconds=policy.rest_seconds,
            effort_rpe_minimum=policy.effort_rpe_minimum,
            effort_rpe_maximum=policy.effort_rpe_maximum,
            technique_constraints=policy.technique_constraints,
            planned_duration_minutes=policy.planned_duration_minutes,
            source_observation_ids=estimate.source_observation_ids,
            evidence_claim_ids=policy.evidence_claim_ids,
            numeric_value_origin=policy.numeric_value_origin,
            authority_reference=policy.authority_reference,
            derived_at=derived_at,
            calculation_method=(
                f"fixed {policy.sets}x{policy.repetitions_per_set} under "
                f"{policy.policy_version}; estimate value not used as dose arithmetic"
            ),
            rule_version=policy.policy_version,
        )

    @staticmethod
    def _require_aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise FixedRepetitionDoseError("dose derivation timestamps must include a timezone")


class RepetitionDosePlanner:
    """Derive a conservative, bounded repetition dose from governed inputs."""

    def derive(
        self,
        *,
        adaptation: Adaptation,
        estimate: CapabilityEstimate,
        policy: RepetitionDosePolicy,
        derived_at: datetime,
    ) -> DerivedRepetitionDose:
        self._require_aware(derived_at)
        if adaptation.id != policy.adaptation_id:
            raise RepetitionDoseError("dose policy belongs to a different adaptation")
        if estimate.domain is not adaptation.domain:
            raise RepetitionDoseError("capability estimate domain does not match the adaptation")
        if estimate.estimated_at > derived_at:
            raise RepetitionDoseError("capability estimate cannot come from the future")
        if estimate.valid_until is not None and estimate.valid_until <= derived_at:
            raise RepetitionDoseError("capability estimate is stale")
        if estimate.estimate_scope != policy.estimate_scope:
            raise RepetitionDoseError("capability estimate scope does not match the dose policy")
        if estimate.unit_or_scale != policy.unit_or_scale:
            raise RepetitionDoseError("capability estimate unit does not match the dose policy")

        value = self._numeric_estimate(estimate.estimate)
        if value < policy.minimum_eligible_estimate:
            raise RepetitionDoseError("capability estimate is below the policy eligibility minimum")

        raw_target = floor(value * policy.target_fraction_of_estimate)
        repetitions = min(
            policy.maximum_repetitions_per_set,
            max(policy.minimum_repetitions_per_set, raw_target),
        )
        return DerivedRepetitionDose(
            adaptation_id=adaptation.id,
            capability_estimate_id=estimate.id,
            repetition_dose_policy_id=policy.id,
            progression_policy_id=policy.progression_policy_id,
            sets=policy.sets,
            repetitions_per_set=repetitions,
            rest_seconds=policy.rest_seconds,
            effort_rpe_minimum=policy.effort_rpe_minimum,
            effort_rpe_maximum=policy.effort_rpe_maximum,
            technique_constraints=policy.technique_constraints,
            planned_duration_minutes=policy.planned_duration_minutes,
            derived_at=derived_at,
            calculation_method=(
                f"floor(estimate*{policy.target_fraction_of_estimate:g}),"
                f"clamped[{policy.minimum_repetitions_per_set},"
                f"{policy.maximum_repetitions_per_set}]"
            ),
            rule_version=policy.policy_version,
        )

    @staticmethod
    def _numeric_estimate(value: object) -> float:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise RepetitionDoseError("capability estimate must be a finite numeric value")
        numeric = float(value)
        if not isfinite(numeric):
            raise RepetitionDoseError("capability estimate must be a finite numeric value")
        return numeric

    @staticmethod
    def _require_aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise RepetitionDoseError("dose derivation timestamps must include a timezone")
