from datetime import UTC, datetime
from uuid import uuid4

from agas_domain import (
    AssessmentContext,
    AssessmentDecision,
    AssessmentDefinition,
    AssessmentIntensity,
    CapabilityDomain,
)
from agas_planner import AdaptiveAssessmentSelector

NOW = datetime(2026, 8, 19, 14, 0, tzinfo=UTC)


def test_training_history_changes_maximal_test_selection() -> None:
    intake_id = uuid4()
    athlete_id = uuid4()
    definitions = (
        AssessmentDefinition(
            slug="comfortable_walk",
            name="Comfortable walk",
            domain=CapabilityDomain.AEROBIC_CAPACITY,
            observation_type="comfortable_walk_distance",
            intensity=AssessmentIntensity.LOW,
            unit_or_scale="m",
            protocol_version="comfortable-walk@1.0.0",
        ),
        AssessmentDefinition(
            slug="maximal_jump",
            name="Maximal jump",
            domain=CapabilityDomain.EXPLOSIVE_POWER,
            observation_type="maximal_jump_height",
            intensity=AssessmentIntensity.MAXIMAL,
            unit_or_scale="cm",
            protocol_version="maximal-jump@1.0.0",
            min_training_age_months=12,
            required_skill_tags=("landing_competency",),
            required_recent_exposure_tags=("jumping",),
        ),
    )
    beginner = AssessmentContext(
        athlete_id=athlete_id,
        source_observation_ids=(intake_id,),
        health_screening_completed=True,
        training_age_months_by_domain={CapabilityDomain.EXPLOSIVE_POWER.value: 1},
        evaluated_at=NOW,
    )
    trained = beginner.model_copy(
        update={
            "training_age_months_by_domain": {CapabilityDomain.EXPLOSIVE_POWER.value: 36},
            "exercise_skill_tags": ("landing_competency",),
            "recent_exposure_tags": ("jumping",),
        }
    )

    selector = AdaptiveAssessmentSelector()
    beginner_decisions = [item.decision for item in selector.select(beginner, definitions)]
    trained_decisions = [item.decision for item in selector.select(trained, definitions)]

    assert beginner_decisions == [AssessmentDecision.SELECTED, AssessmentDecision.DEFERRED]
    assert trained_decisions == [AssessmentDecision.SELECTED, AssessmentDecision.SELECTED]


def test_symptom_and_environment_counterfactuals_change_only_applicable_tests() -> None:
    athlete_id = uuid4()
    context = AssessmentContext(
        athlete_id=athlete_id,
        source_observation_ids=(uuid4(),),
        health_screening_completed=True,
        available_equipment_categories=("cycle_ergometer",),
        evaluated_at=NOW,
    )
    cycle = AssessmentDefinition(
        slug="submax_cycle",
        name="Submaximal cycle",
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        observation_type="submax_cycle_result",
        intensity=AssessmentIntensity.MODERATE,
        unit_or_scale="w",
        protocol_version="submax-cycle@1.0.0",
        required_equipment_categories=("cycle_ergometer",),
    )
    hop = AssessmentDefinition(
        slug="repeated_hop",
        name="Repeated hop",
        domain=CapabilityDomain.TISSUE_EXPOSURE,
        observation_type="repeated_hop_count",
        intensity=AssessmentIntensity.HIGH,
        unit_or_scale="count",
        protocol_version="repeated-hop@1.0.0",
        blocked_by_symptom_flags=("lower_limb_pain",),
    )
    selector = AdaptiveAssessmentSelector()

    baseline = selector.select(context, (cycle, hop))
    changed = selector.select(
        context.model_copy(
            update={
                "available_equipment_categories": (),
                "current_symptom_flags": ("lower_limb_pain",),
            }
        ),
        (cycle, hop),
    )

    assert [item.decision for item in baseline] == [
        AssessmentDecision.SELECTED,
        AssessmentDecision.SELECTED,
    ]
    assert [item.decision for item in changed] == [
        AssessmentDecision.DEFERRED,
        AssessmentDecision.EXCLUDED,
    ]


def test_incomplete_screening_excludes_and_missing_body_mass_defers() -> None:
    assessment = AssessmentDefinition(
        slug="relative_strength_test",
        name="Relative strength test",
        domain=CapabilityDomain.RELATIVE_STRENGTH,
        observation_type="relative_strength_result",
        intensity=AssessmentIntensity.HIGH,
        unit_or_scale="ratio",
        protocol_version="relative-strength@1.0.0",
        requires_body_mass=True,
    )
    context = AssessmentContext(
        athlete_id=uuid4(),
        source_observation_ids=(uuid4(),),
        evaluated_at=NOW,
    )
    selector = AdaptiveAssessmentSelector()

    incomplete = selector.select(context, (assessment,))[0]
    screened = selector.select(
        context.model_copy(update={"health_screening_completed": True}), (assessment,)
    )[0]
    fully_observed = selector.select(
        context.model_copy(update={"health_screening_completed": True, "body_mass_kg": 81.4}),
        (assessment,),
    )[0]

    assert incomplete.decision is AssessmentDecision.EXCLUDED
    assert screened.decision is AssessmentDecision.DEFERRED
    assert fully_observed.decision is AssessmentDecision.SELECTED


def test_movement_precheck_excludes_only_the_affected_assessment() -> None:
    context = AssessmentContext(
        athlete_id=uuid4(),
        source_observation_ids=(uuid4(),),
        health_screening_completed=True,
        health_screening_flags=("upper_body_wrist_or_hand_concern",),
        evaluated_at=NOW,
    )
    chair_stand = AssessmentDefinition(
        slug="chair_stand_fixture",
        name="Chair stand fixture",
        domain=CapabilityDomain.MUSCULAR_ENDURANCE,
        observation_type="chair_stand_fixture_count",
        intensity=AssessmentIntensity.MODERATE,
        unit_or_scale="repetitions",
        protocol_version="chair-stand-fixture@1.0.0",
        blocked_by_health_screening_flags=("lower_body_or_balance_concern",),
    )
    standard_pushup = AssessmentDefinition(
        slug="standard_pushup_fixture",
        name="Standard push-up fixture",
        domain=CapabilityDomain.MUSCULAR_ENDURANCE,
        observation_type="standard_pushup_fixture_count",
        intensity=AssessmentIntensity.HIGH,
        unit_or_scale="repetitions",
        protocol_version="standard-pushup-fixture@1.0.0",
        blocked_by_health_screening_flags=("upper_body_wrist_or_hand_concern",),
    )

    decisions = AdaptiveAssessmentSelector().select(context, (chair_stand, standard_pushup))

    assert decisions[0].decision is AssessmentDecision.SELECTED
    assert decisions[1].decision is AssessmentDecision.EXCLUDED


def test_recent_jump_exposure_gate_excludes_jump_without_blocking_unrelated_assessment() -> None:
    context = AssessmentContext(
        athlete_id=uuid4(),
        source_observation_ids=(uuid4(),),
        health_screening_completed=True,
        health_screening_flags=("recent_jump_exposure_not_confirmed",),
        evaluated_at=NOW,
    )
    chair_stand = AssessmentDefinition(
        slug="chair_stand_unaffected_fixture",
        name="Chair stand unaffected fixture",
        domain=CapabilityDomain.MUSCULAR_ENDURANCE,
        observation_type="chair_stand_unaffected_fixture_count",
        intensity=AssessmentIntensity.MODERATE,
        unit_or_scale="repetitions",
        protocol_version="chair-stand-unaffected-fixture@1.0.0",
    )
    jump = AssessmentDefinition(
        slug="countermovement_jump_fixture",
        name="Countermovement jump fixture",
        domain=CapabilityDomain.EXPLOSIVE_POWER,
        observation_type="countermovement_jump_fixture_height",
        intensity=AssessmentIntensity.HIGH,
        unit_or_scale="centimeters",
        protocol_version="countermovement-jump-fixture@1.0.0",
        blocked_by_health_screening_flags=("recent_jump_exposure_not_confirmed",),
    )

    decisions = AdaptiveAssessmentSelector().select(context, (chair_stand, jump))

    assert decisions[0].decision is AssessmentDecision.SELECTED
    assert decisions[1].decision is AssessmentDecision.EXCLUDED
