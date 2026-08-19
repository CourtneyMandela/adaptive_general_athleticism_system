from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from numbers import Real
from typing import ClassVar
from uuid import UUID

from agas_domain import (
    Adaptation,
    AdaptationPriority,
    AvailableEquipmentSnapshot,
    CostLevel,
    Environment,
    EnvironmentSnapshot,
    Equipment,
    EquipmentAvailability,
    Exercise,
    ExerciseMatch,
    ExerciseResolution,
    ExerciseResolverPolicy,
    ImpactLevel,
    Loadability,
    LongRangeStrategy,
    ResolutionIssue,
    ResolutionIssueCode,
    ResolutionStatus,
    StimulusRequirement,
    StimulusSpecification,
)


class ResolutionError(ValueError):
    """Raised when stimulus resolution inputs violate a domain invariant."""


class EnvironmentSnapshotBuilder:
    """Derive one conservative environment state from effective-dated availability history."""

    def build(
        self,
        environment: Environment,
        equipment: Iterable[Equipment],
        availability_history: Iterable[EquipmentAvailability],
        captured_at: datetime,
    ) -> EnvironmentSnapshot:
        self._require_aware(captured_at)
        equipment_by_id = self._equipment_by_id(equipment)
        events_by_equipment: dict[UUID, list[EquipmentAvailability]] = {
            equipment_id: [] for equipment_id in equipment_by_id
        }
        for event in availability_history:
            if event.environment_id != environment.id:
                raise ResolutionError("availability record belongs to another environment")
            if event.equipment_id not in equipment_by_id:
                raise ResolutionError("availability record references unknown equipment")
            events_by_equipment[event.equipment_id].append(event)

        available = []
        source_ids = []
        for equipment_id in sorted(equipment_by_id, key=str):
            active_events = [
                event
                for event in events_by_equipment[equipment_id]
                if event.effective_from <= captured_at
                and (event.effective_until is None or captured_at < event.effective_until)
            ]
            if not active_events:
                continue
            current = max(
                active_events,
                key=lambda event: (event.effective_from, event.created_at, str(event.id)),
            )
            source_ids.append(current.id)
            if not current.is_available:
                continue
            item = equipment_by_id[equipment_id]
            available.append(
                AvailableEquipmentSnapshot(
                    equipment_id=item.id,
                    category=item.category,
                    capabilities={**item.capabilities, **current.capabilities},
                    load_limits=current.load_limits,
                )
            )

        return EnvironmentSnapshot(
            athlete_id=environment.athlete_id,
            environment_id=environment.id,
            captured_at=captured_at,
            available_equipment=tuple(available),
            source_availability_ids=tuple(source_ids),
            floor_area_m2=self._floor_area(environment.space_constraints.get("floor_area_m2")),
            max_noise_level=environment.max_noise_level,
            outdoor_access=environment.outdoor_access,
        )

    @staticmethod
    def _equipment_by_id(equipment: Iterable[Equipment]) -> dict[UUID, Equipment]:
        result: dict[UUID, Equipment] = {}
        for item in equipment:
            if item.id in result:
                raise ResolutionError("equipment contains duplicate ids")
            result[item.id] = item
        return result

    @staticmethod
    def _floor_area(value: object) -> float | None:
        if isinstance(value, bool) or not isinstance(value, Real) or value <= 0:
            return None
        return float(value)

    @staticmethod
    def _require_aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ResolutionError("resolution timestamps must include a timezone")


class StimulusRequirementBuilder:
    """Bind an explicit stimulus specification to an existing adaptation priority."""

    def __init__(self, rule_version: str = "stimulus-requirement@1.0.0") -> None:
        self.rule_version = rule_version

    def build(
        self,
        *,
        strategy: LongRangeStrategy,
        priority: AdaptationPriority,
        adaptation: Adaptation,
        specification: StimulusSpecification,
        generated_at: datetime,
    ) -> StimulusRequirement:
        EnvironmentSnapshotBuilder._require_aware(generated_at)
        if generated_at < strategy.generated_at:
            raise ResolutionError("stimulus requirement cannot predate its strategy")
        strategy_priority = next(
            (item for item in strategy.priorities if item.id == priority.id), None
        )
        if strategy_priority is None:
            raise ResolutionError("priority does not belong to the supplied strategy")
        if strategy_priority != priority:
            raise ResolutionError("priority differs from the strategy's immutable priority")
        if priority.adaptation_id != adaptation.id:
            raise ResolutionError("priority and adaptation do not match")

        return StimulusRequirement(
            athlete_id=strategy.athlete_id,
            long_range_strategy_id=strategy.id,
            adaptation_priority_id=priority.id,
            adaptation_id=adaptation.id,
            priority_state=priority.state,
            movement_patterns=specification.movement_patterns,
            allowed_loading_types=specification.allowed_loading_types,
            minimum_loadability=specification.minimum_loadability,
            required_velocity_characteristics=specification.required_velocity_characteristics,
            maximum_skill_complexity=specification.maximum_skill_complexity,
            maximum_impact_level=specification.maximum_impact_level,
            maximum_stability_demand=specification.maximum_stability_demand,
            maximum_fatigue_cost=specification.maximum_fatigue_cost,
            maximum_soreness_cost=specification.maximum_soreness_cost,
            requires_outdoor_access=specification.requires_outdoor_access,
            minimum_floor_area_m2=specification.minimum_floor_area_m2,
            contraindication_tags=specification.contraindication_tags,
            source_observation_ids=specification.source_observation_ids,
            evidence_claim_ids=specification.evidence_claim_ids,
            rationale=specification.rationale,
            generated_at=generated_at,
            rule_version=self.rule_version,
        )


class ExerciseResolver:
    """Resolve a stimulus honestly against exercise metadata and one environment snapshot."""

    _cost_rank: ClassVar[dict[CostLevel, int]] = {
        CostLevel.LOW: 1,
        CostLevel.MODERATE: 2,
        CostLevel.HIGH: 3,
    }
    _impact_rank: ClassVar[dict[ImpactLevel, int]] = {
        ImpactLevel.NONE: 0,
        ImpactLevel.LOW: 1,
        ImpactLevel.MODERATE: 2,
        ImpactLevel.HIGH: 3,
    }
    _loadability_rank: ClassVar[dict[Loadability, int]] = {
        Loadability.LIMITED: 1,
        Loadability.MODERATE: 2,
        Loadability.HIGH: 3,
    }

    def __init__(self, rule_version: str = "exercise-resolution@1.0.0") -> None:
        self.rule_version = rule_version

    def resolve(
        self,
        *,
        requirement: StimulusRequirement,
        environment: EnvironmentSnapshot,
        exercises: Iterable[Exercise],
        policy: ExerciseResolverPolicy,
        resolved_at: datetime,
    ) -> ExerciseResolution:
        EnvironmentSnapshotBuilder._require_aware(resolved_at)
        if environment.athlete_id != requirement.athlete_id:
            raise ResolutionError("environment snapshot belongs to a different athlete")
        if resolved_at < requirement.generated_at or resolved_at < environment.captured_at:
            raise ResolutionError(
                "resolution cannot predate its requirement or environment snapshot"
            )

        exercise_list = tuple(exercises)
        exercise_ids = [item.id for item in exercise_list]
        if len(set(exercise_ids)) != len(exercise_ids):
            raise ResolutionError("exercise candidates must not contain duplicate ids")

        ranked = []
        rejected_issues: list[ResolutionIssue] = []
        for exercise in exercise_list:
            match, issues = self._evaluate(requirement, environment, exercise, policy)
            if match is None:
                rejected_issues.extend(issues)
                continue
            if match.score < policy.partial_match_threshold:
                rejected_issues.extend(
                    (
                        *issues,
                        ResolutionIssue(
                            code=ResolutionIssueCode.BELOW_PARTIAL_THRESHOLD,
                            detail=(
                                f"{exercise.name} scored {match.score:.3f}, below the configured "
                                f"partial threshold {policy.partial_match_threshold:.3f}"
                            ),
                        ),
                    )
                )
                continue
            ranked.append(match)

        ranked.sort(key=lambda item: (-item.score, str(item.exercise_id)))
        ranked = ranked[: policy.max_ranked_candidates]
        if not ranked:
            issues = self._unique_issues(rejected_issues)
            if not issues:
                issues = (
                    ResolutionIssue(
                        code=ResolutionIssueCode.NO_CANDIDATE,
                        detail="no exercise candidate was supplied",
                    ),
                )
            return ExerciseResolution(
                stimulus_requirement_id=requirement.id,
                environment_id=environment.environment_id,
                resolver_policy_id=policy.id,
                status=ResolutionStatus.INFEASIBLE,
                ranked_matches=(),
                unresolved_issues=issues,
                source_availability_ids=environment.source_availability_ids,
                rationale="the active environment cannot reproduce the required stimulus",
                resolved_at=resolved_at,
                rule_version=f"{self.rule_version};policy={policy.policy_version}",
            )

        selected = ranked[0]
        return ExerciseResolution(
            stimulus_requirement_id=requirement.id,
            environment_id=environment.environment_id,
            resolver_policy_id=policy.id,
            status=selected.quality,
            selected_exercise_id=selected.exercise_id,
            ranked_matches=tuple(ranked),
            unresolved_issues=selected.issues,
            source_availability_ids=environment.source_availability_ids,
            rationale=(
                "selected a full-fidelity exercise match"
                if selected.quality is ResolutionStatus.FULL
                else "selected the best partial match; listed limitations remain unresolved"
            ),
            resolved_at=resolved_at,
            rule_version=f"{self.rule_version};policy={policy.policy_version}",
        )

    def _evaluate(
        self,
        requirement: StimulusRequirement,
        environment: EnvironmentSnapshot,
        exercise: Exercise,
        policy: ExerciseResolverPolicy,
    ) -> tuple[ExerciseMatch | None, tuple[ResolutionIssue, ...]]:
        hard_issues = self._hard_constraint_issues(requirement, environment, exercise)
        if hard_issues:
            return None, hard_issues

        if requirement.adaptation_id in exercise.primary_adaptation_ids:
            adaptation_score = 1.0
        elif requirement.adaptation_id in exercise.secondary_adaptation_ids:
            adaptation_score = policy.secondary_adaptation_credit
        else:
            issue = ResolutionIssue(
                code=ResolutionIssueCode.ADAPTATION_MISMATCH,
                detail=f"{exercise.name} does not target the required adaptation",
            )
            return None, (issue,)

        required_movements = set(requirement.movement_patterns)
        movement_score = len(required_movements & set(exercise.movement_patterns)) / len(
            required_movements
        )
        loading_score = float(exercise.loading_type in requirement.allowed_loading_types)
        loadability_score = min(
            1.0,
            self._loadability_rank[exercise.loadability]
            / self._loadability_rank[requirement.minimum_loadability],
        )
        required_velocity = set(requirement.required_velocity_characteristics)
        velocity_score = (
            len(required_velocity & set(exercise.velocity_characteristics)) / len(required_velocity)
            if required_velocity
            else 1.0
        )
        components = {
            "adaptation_role": adaptation_score,
            "movement_pattern": movement_score,
            "loading_type": loading_score,
            "loadability": loadability_score,
            "velocity": velocity_score,
        }
        weights = {
            "adaptation_role": policy.adaptation_role_weight,
            "movement_pattern": policy.movement_pattern_weight,
            "loading_type": policy.loading_type_weight,
            "loadability": policy.loadability_weight,
            "velocity": policy.velocity_weight,
        }
        weight_total = sum(weights.values())
        score = sum(components[name] * weight for name, weight in weights.items()) / weight_total

        issues = []
        if adaptation_score < 1:
            issues.append(
                ResolutionIssue(
                    code=ResolutionIssueCode.ADAPTATION_MISMATCH,
                    detail=f"{exercise.name} targets the adaptation only secondarily",
                )
            )
        if movement_score < 1:
            issues.append(
                ResolutionIssue(
                    code=ResolutionIssueCode.MOVEMENT_PATTERN_MISMATCH,
                    detail=f"{exercise.name} does not cover every required movement pattern",
                )
            )
        if loading_score < 1:
            issues.append(
                ResolutionIssue(
                    code=ResolutionIssueCode.LOADING_TYPE_MISMATCH,
                    detail=f"{exercise.name} uses a non-preferred loading type",
                )
            )
        if loadability_score < 1:
            issues.append(
                ResolutionIssue(
                    code=ResolutionIssueCode.INSUFFICIENT_LOADABILITY,
                    detail=f"{exercise.name} cannot fully reproduce required loadability",
                )
            )
        if velocity_score < 1:
            issues.append(
                ResolutionIssue(
                    code=ResolutionIssueCode.VELOCITY_MISMATCH,
                    detail=f"{exercise.name} does not cover every required velocity characteristic",
                )
            )

        full_fidelity = all(value == 1 for value in components.values())
        quality = (
            ResolutionStatus.FULL
            if full_fidelity and score >= policy.full_match_threshold
            else ResolutionStatus.PARTIAL
        )
        return (
            ExerciseMatch(
                exercise_id=exercise.id,
                quality=quality,
                score=score,
                score_components=components,
                issues=tuple(issues),
            ),
            tuple(issues),
        )

    def _hard_constraint_issues(
        self,
        requirement: StimulusRequirement,
        environment: EnvironmentSnapshot,
        exercise: Exercise,
    ) -> tuple[ResolutionIssue, ...]:
        issues = []
        available_equipment_ids = {item.equipment_id for item in environment.available_equipment}
        missing_equipment = set(exercise.equipment_requirement_ids) - available_equipment_ids
        if missing_equipment:
            issues.append(
                ResolutionIssue(
                    code=ResolutionIssueCode.MISSING_EQUIPMENT,
                    detail=(
                        f"{exercise.name} is missing equipment ids: "
                        + ", ".join(sorted(map(str, missing_equipment)))
                    ),
                )
            )
        if (
            self._cost_rank[exercise.skill_complexity]
            > self._cost_rank[requirement.maximum_skill_complexity]
        ):
            issues.append(
                ResolutionIssue(
                    code=ResolutionIssueCode.SKILL_CONSTRAINT,
                    detail=f"{exercise.name} exceeds the current skill ceiling",
                )
            )
        if (
            self._impact_rank[exercise.impact_level]
            > self._impact_rank[requirement.maximum_impact_level]
        ):
            issues.append(
                ResolutionIssue(
                    code=ResolutionIssueCode.IMPACT_CONSTRAINT,
                    detail=f"{exercise.name} exceeds the current impact ceiling",
                )
            )
        for code, exercise_level, maximum, label in (
            (
                ResolutionIssueCode.STABILITY_CONSTRAINT,
                exercise.stability_demand,
                requirement.maximum_stability_demand,
                "stability demand",
            ),
            (
                ResolutionIssueCode.FATIGUE_CONSTRAINT,
                exercise.fatigue_cost,
                requirement.maximum_fatigue_cost,
                "fatigue cost",
            ),
            (
                ResolutionIssueCode.SORENESS_CONSTRAINT,
                exercise.soreness_cost,
                requirement.maximum_soreness_cost,
                "soreness cost",
            ),
        ):
            if self._cost_rank[exercise_level] > self._cost_rank[maximum]:
                issues.append(
                    ResolutionIssue(
                        code=code,
                        detail=f"{exercise.name} exceeds the allowed {label}",
                    )
                )
        contraindications = set(requirement.contraindication_tags) & set(
            exercise.contraindication_tags
        )
        if contraindications:
            issues.append(
                ResolutionIssue(
                    code=ResolutionIssueCode.CONTRAINDICATION,
                    detail=(
                        f"{exercise.name} conflicts with tags: "
                        + ", ".join(sorted(contraindications))
                    ),
                )
            )
        if (requirement.requires_outdoor_access or exercise.requires_outdoor_access) and not (
            environment.outdoor_access
        ):
            issues.append(
                ResolutionIssue(
                    code=ResolutionIssueCode.OUTDOOR_ACCESS_REQUIRED,
                    detail=f"{exercise.name} requires outdoor access",
                )
            )
        required_area = max(
            value
            for value in (requirement.minimum_floor_area_m2, exercise.minimum_floor_area_m2, 0)
            if value is not None
        )
        if required_area and (
            environment.floor_area_m2 is None or environment.floor_area_m2 < required_area
        ):
            issues.append(
                ResolutionIssue(
                    code=ResolutionIssueCode.INSUFFICIENT_SPACE,
                    detail=f"{exercise.name} requires at least {required_area:g} m² of floor area",
                )
            )
        if self._cost_rank[exercise.noise_level] > self._cost_rank[environment.max_noise_level]:
            issues.append(
                ResolutionIssue(
                    code=ResolutionIssueCode.NOISE_CONSTRAINT,
                    detail=f"{exercise.name} exceeds the environment noise ceiling",
                )
            )
        return tuple(issues)

    @staticmethod
    def _unique_issues(issues: Iterable[ResolutionIssue]) -> tuple[ResolutionIssue, ...]:
        result = []
        seen = set()
        for issue in issues:
            key = (issue.code, issue.detail)
            if key not in seen:
                seen.add(key)
                result.append(issue)
        return tuple(result)
