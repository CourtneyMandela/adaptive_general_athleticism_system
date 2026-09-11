from __future__ import annotations

from datetime import datetime
from math import floor, isfinite
from numbers import Real
from uuid import UUID

from agas_domain import Adaptation, CapabilityEstimate, RepetitionDosePolicy
from pydantic import BaseModel, ConfigDict, Field


class RepetitionDoseError(ValueError):
    """Raised when a governed repetition dose cannot be derived safely."""


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
