from datetime import UTC, datetime, timedelta
from uuid import uuid4

from agas_domain import (
    Adaptation,
    AdaptationPriority,
    CapabilityDomain,
    CostLevel,
    Environment,
    Equipment,
    EquipmentAvailability,
    ImpactLevel,
    Loadability,
    LongRangeStrategy,
    PlanningReason,
    RoadmapItem,
    StimulusSpecification,
    TrainingPriorityState,
)
from agas_planner import EnvironmentSnapshotBuilder, StimulusRequirementBuilder

NOW = datetime(2026, 8, 19, 14, 0, tzinfo=UTC)


def test_environment_snapshot_honors_temporary_availability_windows() -> None:
    athlete_id = uuid4()
    environment = Environment(athlete_id=athlete_id, name="Gym")
    barbell = Equipment(name="Barbell", category="external_load")
    available = EquipmentAvailability(
        environment_id=environment.id,
        equipment_id=barbell.id,
        is_available=True,
        effective_from=NOW,
    )
    temporary_outage = EquipmentAvailability(
        environment_id=environment.id,
        equipment_id=barbell.id,
        is_available=False,
        effective_from=NOW + timedelta(days=1),
        effective_until=NOW + timedelta(days=2),
        reason="maintenance",
    )
    builder = EnvironmentSnapshotBuilder()

    during = builder.build(
        environment,
        (barbell,),
        (available, temporary_outage),
        NOW + timedelta(days=1, hours=1),
    )
    after = builder.build(
        environment,
        (barbell,),
        (available, temporary_outage),
        NOW + timedelta(days=3),
    )

    assert during.available_equipment == ()
    assert during.source_availability_ids == (temporary_outage.id,)
    assert tuple(item.equipment_id for item in after.available_equipment) == (barbell.id,)
    assert after.source_availability_ids == (available.id,)


def test_stimulus_requirement_binds_to_existing_non_deferred_priority() -> None:
    athlete_id = uuid4()
    adaptation = Adaptation(name="Maximum strength", domain=CapabilityDomain.MAXIMUM_STRENGTH)
    priority = AdaptationPriority(
        adaptation_id=adaptation.id,
        capability_need_id=uuid4(),
        state=TrainingPriorityState.DEVELOP,
        score=0.8,
        rank=1,
        development_allocation=1,
        score_components={"final_score": 0.8},
        reason_codes=(PlanningReason.COMPETENCY_DEFICIT,),
        rationale=("Synthetic fixture deficit",),
    )
    roadmap = RoadmapItem(
        adaptation_id=adaptation.id,
        current_state=priority.state,
        sequence_group=1,
        rationale="Synthetic fixture roadmap",
        review_trigger="scheduled review",
    )
    evidence_id = uuid4()
    observation_id = uuid4()
    strategy = LongRangeStrategy(
        athlete_id=athlete_id,
        priority_policy_id=uuid4(),
        horizon_months=12,
        priorities=(priority,),
        roadmap=(roadmap,),
        block_hypothesis="Develop fixture strength; reassess.",
        source_observation_ids=(observation_id,),
        source_capability_estimate_ids=(uuid4(),),
        competency_floor_ids=(uuid4(),),
        evidence_claim_ids=(evidence_id,),
        generated_at=NOW,
        next_review_at=NOW + timedelta(days=42),
        rule_version="fixture@1.0.0",
    )
    specification = StimulusSpecification(
        movement_patterns=("knee_dominant",),
        allowed_loading_types=("external_load",),
        allowed_lateralities=("bilateral", "unilateral"),
        minimum_loadability=Loadability.HIGH,
        maximum_skill_complexity=CostLevel.MODERATE,
        maximum_impact_level=ImpactLevel.LOW,
        maximum_stability_demand=CostLevel.MODERATE,
        maximum_fatigue_cost=CostLevel.MODERATE,
        maximum_soreness_cost=CostLevel.MODERATE,
        source_observation_ids=(observation_id,),
        evidence_claim_ids=(evidence_id,),
        rationale="High-force knee-dominant stimulus fixture.",
    )

    requirement = StimulusRequirementBuilder().build(
        strategy=strategy,
        priority=priority,
        adaptation=adaptation,
        specification=specification,
        generated_at=NOW,
    )

    assert requirement.adaptation_id == adaptation.id
    assert requirement.adaptation_priority_id == priority.id
    assert requirement.long_range_strategy_id == strategy.id
    assert "sets" not in requirement.model_dump()
    assert "repetitions" not in requirement.model_dump()
