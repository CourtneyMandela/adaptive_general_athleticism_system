from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from enum import StrEnum
from typing import Literal
from uuid import UUID

from agas_domain import (
    BlockPlan,
    ExerciseResolution,
    LongRangeStrategy,
    SessionPrescription,
    StimulusRequirement,
    WeeklyPlan,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AntiSludgeDimension(StrEnum):
    PRIORITY_STRUCTURE = "priority_structure"
    RESOURCE_ALLOCATION = "resource_allocation"
    EXERCISE_SELECTION = "exercise_selection"
    PRESCRIPTION_DOSE = "prescription_dose"
    WEEKLY_STRUCTURE = "weekly_structure"


class AntiSludgeInputError(ValueError):
    """Raised when a signature would depend on opaque record identity."""


class PrioritySignature(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    adaptation: str
    state: str
    rank: int
    development_allocation: float


class ResourceAllocationSignature(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    adaptation: str
    priority_state: str
    minimum_weekly_minutes: int
    target_weekly_minutes: int
    allocated_weekly_minutes: int
    sessions_per_week: int
    status: str


class ExerciseSelectionSignature(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    adaptation: str
    exercise: str | None
    resolution_status: str
    issue_codes: tuple[str, ...]


class PrescriptionDoseSignature(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    adaptation: str
    exercise: str
    sets: int
    repetitions_per_set: int | None
    duration_seconds: int | None
    rest_seconds: int
    planned_duration_minutes: int
    intensity_kinds: tuple[str, ...]


class WeeklySessionSignature(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    weekday: int
    start_minute: int
    planned_duration_minutes: int
    fatigue_cost: str


class ProgramSignature(BaseModel):
    """Identity-free behavioral summary suitable for paired plan comparisons."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str = Field(min_length=1)
    priority_structure: tuple[PrioritySignature, ...]
    resource_allocation: tuple[ResourceAllocationSignature, ...] = ()
    exercise_selection: tuple[ExerciseSelectionSignature, ...] = ()
    prescription_dose: tuple[PrescriptionDoseSignature, ...] = ()
    weekly_structure: tuple[WeeklySessionSignature, ...] = ()
    signature_version: str = "program-signature@1.0.0"

    @classmethod
    def from_artifacts(
        cls,
        *,
        label: str,
        strategy: LongRangeStrategy,
        adaptation_names: Mapping[UUID, str],
        block: BlockPlan | None = None,
        stimulus_requirements: Iterable[StimulusRequirement] = (),
        resolutions: Iterable[ExerciseResolution] = (),
        prescriptions: Iterable[SessionPrescription] = (),
        weekly_plan: WeeklyPlan | None = None,
        exercise_names: Mapping[UUID, str] | None = None,
    ) -> ProgramSignature:
        names = exercise_names or {}

        def adaptation_name(adaptation_id: UUID) -> str:
            try:
                return adaptation_names[adaptation_id]
            except KeyError:
                raise AntiSludgeInputError(
                    f"missing semantic name for adaptation {adaptation_id}"
                ) from None

        def exercise_name(exercise_id: UUID) -> str:
            try:
                return names[exercise_id]
            except KeyError:
                raise AntiSludgeInputError(
                    f"missing semantic name for exercise {exercise_id}"
                ) from None

        priorities = tuple(
            sorted(
                (
                    PrioritySignature(
                        adaptation=adaptation_name(item.adaptation_id),
                        state=item.state.value,
                        rank=item.rank,
                        development_allocation=round(item.development_allocation, 8),
                    )
                    for item in strategy.priorities
                ),
                key=lambda item: item.adaptation,
            )
        )
        allocations: tuple[ResourceAllocationSignature, ...] = ()
        if block is not None:
            allocations = tuple(
                sorted(
                    (
                        ResourceAllocationSignature(
                            adaptation=adaptation_name(item.adaptation_id),
                            priority_state=item.priority_state.value,
                            minimum_weekly_minutes=item.minimum_weekly_minutes,
                            target_weekly_minutes=item.target_weekly_minutes,
                            allocated_weekly_minutes=item.allocated_weekly_minutes,
                            sessions_per_week=item.sessions_per_week,
                            status=item.status.value,
                        )
                        for item in block.allocations
                    ),
                    key=lambda item: item.adaptation,
                )
            )
        requirement_adaptations = {
            item.id: adaptation_name(item.adaptation_id) for item in stimulus_requirements
        }
        selections = tuple(
            sorted(
                (
                    ExerciseSelectionSignature(
                        adaptation=_required_requirement_adaptation(
                            requirement_adaptations, item.stimulus_requirement_id
                        ),
                        exercise=(
                            None
                            if item.selected_exercise_id is None
                            else exercise_name(item.selected_exercise_id)
                        ),
                        resolution_status=item.status.value,
                        issue_codes=tuple(
                            sorted(issue.code.value for issue in item.unresolved_issues)
                        ),
                    )
                    for item in resolutions
                ),
                key=lambda item: (item.adaptation, item.exercise or ""),
            )
        )
        doses = tuple(
            sorted(
                (
                    PrescriptionDoseSignature(
                        adaptation=adaptation_name(item.adaptation_id),
                        exercise=exercise_name(item.exercise_id),
                        sets=item.sets,
                        repetitions_per_set=item.repetitions_per_set,
                        duration_seconds=item.duration_seconds,
                        rest_seconds=item.rest_seconds,
                        planned_duration_minutes=item.planned_duration_minutes,
                        intensity_kinds=tuple(
                            sorted(target.kind for target in item.intensity_targets)
                        ),
                    )
                    for item in prescriptions
                ),
                key=lambda item: (item.adaptation, item.exercise),
            )
        )
        weekly: tuple[WeeklySessionSignature, ...] = ()
        if weekly_plan is not None:
            weekly = tuple(
                WeeklySessionSignature(
                    weekday=item.starts_at.weekday(),
                    start_minute=item.starts_at.hour * 60 + item.starts_at.minute,
                    planned_duration_minutes=item.planned_duration_minutes,
                    fatigue_cost=item.fatigue_cost.value,
                )
                for item in sorted(weekly_plan.sessions, key=lambda item: item.starts_at)
            )
        return cls(
            label=label,
            priority_structure=priorities,
            resource_allocation=allocations,
            exercise_selection=selections,
            prescription_dose=doses,
            weekly_structure=weekly,
        )


class CounterfactualExpectation(BaseModel):
    """Reviewable statement of how one meaningful input should affect a program."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    changed_input: str = Field(min_length=1)
    must_change: tuple[AntiSludgeDimension, ...] = Field(min_length=1)
    must_remain_stable: tuple[AntiSludgeDimension, ...] = ()
    rationale: str = Field(min_length=1)
    expectation_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_dimensions(self) -> CounterfactualExpectation:
        if len(set(self.must_change)) != len(self.must_change):
            raise ValueError("must_change dimensions must be unique")
        if len(set(self.must_remain_stable)) != len(self.must_remain_stable):
            raise ValueError("must_remain_stable dimensions must be unique")
        if set(self.must_change) & set(self.must_remain_stable):
            raise ValueError("a dimension cannot be both changed and stable")
        return self


class AntiSludgeReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    baseline_label: str
    counterfactual_label: str
    changed_input: str
    dimension_similarity: dict[AntiSludgeDimension, float]
    overall_similarity: float
    changed_dimensions: tuple[AntiSludgeDimension, ...]
    missing_required_changes: tuple[AntiSludgeDimension, ...]
    violated_stability: tuple[AntiSludgeDimension, ...]
    verdict: Literal["responsive", "generic_program_alert", "invariant_violation_alert"]
    alert: bool
    analyzer_version: str = "anti-sludge-analyzer@1.0.0"


class AntiSludgeAnalyzer:
    """Compare paired plans against explicit responsiveness and stability expectations."""

    dimensions = tuple(AntiSludgeDimension)

    def compare(
        self,
        baseline: ProgramSignature,
        counterfactual: ProgramSignature,
        expectation: CounterfactualExpectation,
    ) -> AntiSludgeReport:
        similarities = {
            dimension: self._sequence_similarity(
                getattr(baseline, dimension.value), getattr(counterfactual, dimension.value)
            )
            for dimension in self.dimensions
        }
        changed = tuple(dimension for dimension in self.dimensions if similarities[dimension] < 1)
        missing = tuple(
            dimension for dimension in expectation.must_change if dimension not in changed
        )
        violated = tuple(
            dimension for dimension in expectation.must_remain_stable if dimension in changed
        )
        if missing:
            verdict = "generic_program_alert"
        elif violated:
            verdict = "invariant_violation_alert"
        else:
            verdict = "responsive"
        return AntiSludgeReport(
            baseline_label=baseline.label,
            counterfactual_label=counterfactual.label,
            changed_input=expectation.changed_input,
            dimension_similarity=similarities,
            overall_similarity=round(sum(similarities.values()) / len(similarities), 8),
            changed_dimensions=changed,
            missing_required_changes=missing,
            violated_stability=violated,
            verdict=verdict,
            alert=bool(missing or violated),
        )

    @staticmethod
    def _sequence_similarity(baseline: Sequence[BaseModel], variant: Sequence[BaseModel]) -> float:
        left = Counter(AntiSludgeAnalyzer._canonical(item) for item in baseline)
        right = Counter(AntiSludgeAnalyzer._canonical(item) for item in variant)
        union = sum((left | right).values())
        if union == 0:
            return 1.0
        intersection = sum((left & right).values())
        return round(intersection / union, 8)

    @staticmethod
    def _canonical(item: BaseModel) -> str:
        return json.dumps(item.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def _required_requirement_adaptation(values: Mapping[UUID, str], requirement_id: UUID) -> str:
    try:
        return values[requirement_id]
    except KeyError:
        raise AntiSludgeInputError(
            f"missing stimulus requirement {requirement_id} for exercise resolution"
        ) from None
