from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from agas_domain import (
    AvailableEquipmentSnapshot,
    CostLevel,
    EnvironmentSnapshot,
    Exercise,
    ExerciseResolution,
    ExerciseResolverPolicy,
    ImpactLevel,
    Loadability,
    ResolutionIssueCode,
    ResolutionStatus,
    StimulusRequirement,
    TrainingPriorityState,
)
from agas_planner import ExerciseResolver
from pydantic import ValidationError

NOW = datetime(2026, 8, 19, 14, 0, tzinfo=UTC)


def resolver_policy() -> ExerciseResolverPolicy:
    return ExerciseResolverPolicy(
        adaptation_role_weight=2,
        movement_pattern_weight=2,
        loading_type_weight=1,
        loadability_weight=3,
        velocity_weight=1,
        secondary_adaptation_credit=0.5,
        partial_match_threshold=0.7,
        full_match_threshold=0.95,
        max_ranked_candidates=5,
        policy_version="counterfactual-resolver@1.0.0",
    )


def requirement(athlete_id: UUID, adaptation_id: UUID) -> StimulusRequirement:
    return StimulusRequirement(
        athlete_id=athlete_id,
        long_range_strategy_id=uuid4(),
        adaptation_priority_id=uuid4(),
        adaptation_id=adaptation_id,
        priority_state=TrainingPriorityState.DEVELOP,
        movement_patterns=("knee_dominant",),
        allowed_loading_types=("external",),
        minimum_loadability=Loadability.HIGH,
        required_velocity_characteristics=("controlled",),
        maximum_skill_complexity=CostLevel.MODERATE,
        maximum_impact_level=ImpactLevel.LOW,
        maximum_stability_demand=CostLevel.MODERATE,
        maximum_fatigue_cost=CostLevel.MODERATE,
        maximum_soreness_cost=CostLevel.MODERATE,
        source_observation_ids=(uuid4(),),
        evidence_claim_ids=(uuid4(),),
        rationale="Synthetic high-force strength stimulus.",
        generated_at=NOW,
        rule_version="fixture@1.0.0",
    )


def exercise(
    *,
    name: str,
    adaptation_id: UUID,
    equipment_id: UUID,
    loadability: Loadability,
) -> Exercise:
    return Exercise(
        name=name,
        movement_patterns=("knee_dominant",),
        primary_adaptation_ids=(adaptation_id,),
        equipment_requirement_ids=(equipment_id,),
        loading_type="external",
        loadability=loadability,
        skill_complexity=CostLevel.MODERATE,
        impact_level=ImpactLevel.LOW,
        velocity_characteristics=("controlled",),
        stability_demand=CostLevel.MODERATE,
        fatigue_cost=CostLevel.MODERATE,
        soreness_cost=CostLevel.MODERATE,
    )


def test_equipment_change_changes_exercise_not_adaptation_and_marks_partial_fidelity() -> None:
    athlete_id = uuid4()
    adaptation_id = uuid4()
    barbell_id = uuid4()
    dumbbell_id = uuid4()
    stimulus = requirement(athlete_id, adaptation_id)
    barbell_squat = exercise(
        name="Fixture barbell squat",
        adaptation_id=adaptation_id,
        equipment_id=barbell_id,
        loadability=Loadability.HIGH,
    )
    dumbbell_split_squat = exercise(
        name="Fixture dumbbell split squat",
        adaptation_id=adaptation_id,
        equipment_id=dumbbell_id,
        loadability=Loadability.MODERATE,
    )
    gym = EnvironmentSnapshot(
        athlete_id=athlete_id,
        environment_id=uuid4(),
        captured_at=NOW,
        available_equipment=(
            AvailableEquipmentSnapshot(equipment_id=barbell_id, category="external_load"),
        ),
        source_availability_ids=(uuid4(),),
        floor_area_m2=20,
        max_noise_level=CostLevel.HIGH,
        outdoor_access=False,
    )
    hotel = gym.model_copy(
        update={
            "environment_id": uuid4(),
            "available_equipment": (
                AvailableEquipmentSnapshot(
                    equipment_id=dumbbell_id,
                    category="external_load",
                ),
            ),
            "source_availability_ids": (uuid4(),),
            "floor_area_m2": 8,
        }
    )
    resolver = ExerciseResolver()

    gym_result = resolver.resolve(
        requirement=stimulus,
        environment=gym,
        exercises=(barbell_squat, dumbbell_split_squat),
        policy=resolver_policy(),
        resolved_at=NOW,
    )
    hotel_result = resolver.resolve(
        requirement=stimulus,
        environment=hotel,
        exercises=(barbell_squat, dumbbell_split_squat),
        policy=resolver_policy(),
        resolved_at=NOW,
    )

    assert gym_result.status is ResolutionStatus.FULL
    assert gym_result.selected_exercise_id == barbell_squat.id
    assert hotel_result.status is ResolutionStatus.PARTIAL
    assert hotel_result.selected_exercise_id == dumbbell_split_squat.id
    assert any(
        issue.code is ResolutionIssueCode.INSUFFICIENT_LOADABILITY
        for issue in hotel_result.unresolved_issues
    )
    assert gym_result.stimulus_requirement_id == hotel_result.stimulus_requirement_id == stimulus.id
    assert stimulus.adaptation_id == adaptation_id


def test_missing_required_equipment_is_explicitly_infeasible() -> None:
    athlete_id = uuid4()
    adaptation_id = uuid4()
    barbell_id = uuid4()
    stimulus = requirement(athlete_id, adaptation_id)
    barbell_squat = exercise(
        name="Fixture barbell squat",
        adaptation_id=adaptation_id,
        equipment_id=barbell_id,
        loadability=Loadability.HIGH,
    )
    empty_environment = EnvironmentSnapshot(
        athlete_id=athlete_id,
        environment_id=uuid4(),
        captured_at=NOW,
        max_noise_level=CostLevel.LOW,
        outdoor_access=False,
    )

    result = ExerciseResolver().resolve(
        requirement=stimulus,
        environment=empty_environment,
        exercises=(barbell_squat,),
        policy=resolver_policy(),
        resolved_at=NOW,
    )

    assert result.status is ResolutionStatus.INFEASIBLE
    assert result.selected_exercise_id is None
    assert any(
        issue.code is ResolutionIssueCode.MISSING_EQUIPMENT for issue in result.unresolved_issues
    )


def test_resolution_contract_rejects_hidden_or_inconsistent_limitations() -> None:
    athlete_id = uuid4()
    adaptation_id = uuid4()
    dumbbell_id = uuid4()
    stimulus = requirement(athlete_id, adaptation_id)
    candidate = exercise(
        name="Fixture limited dumbbell squat",
        adaptation_id=adaptation_id,
        equipment_id=dumbbell_id,
        loadability=Loadability.MODERATE,
    )
    environment = EnvironmentSnapshot(
        athlete_id=athlete_id,
        environment_id=uuid4(),
        captured_at=NOW,
        available_equipment=(
            AvailableEquipmentSnapshot(equipment_id=dumbbell_id, category="external_load"),
        ),
        source_availability_ids=(uuid4(),),
        max_noise_level=CostLevel.HIGH,
        outdoor_access=False,
    )
    result = ExerciseResolver().resolve(
        requirement=stimulus,
        environment=environment,
        exercises=(candidate,),
        policy=resolver_policy(),
        resolved_at=NOW,
    )
    assert result.status is ResolutionStatus.PARTIAL

    common = {
        "stimulus_requirement_id": result.stimulus_requirement_id,
        "environment_id": result.environment_id,
        "resolver_policy_id": result.resolver_policy_id,
        "source_availability_ids": result.source_availability_ids,
        "rationale": result.rationale,
        "resolved_at": result.resolved_at,
        "rule_version": result.rule_version,
    }
    with pytest.raises(ValidationError, match="resolution issues must match"):
        ExerciseResolution(
            **common,
            status=ResolutionStatus.PARTIAL,
            selected_exercise_id=candidate.id,
            ranked_matches=result.ranked_matches,
            unresolved_issues=(),
        )
    with pytest.raises(ValidationError, match="cannot retain ranked matches"):
        ExerciseResolution(
            **common,
            status=ResolutionStatus.INFEASIBLE,
            ranked_matches=result.ranked_matches,
            unresolved_issues=result.unresolved_issues,
        )
