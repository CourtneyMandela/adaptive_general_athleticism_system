import json
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from agas_api.block_creation import (
    BlockCreationNotFoundError,
    BlockCreationValidationError,
    CreateBlockPlanCommand,
    PersistedBlockCreationService,
)
from agas_api.block_preparation import BlockPreparationProjector
from agas_api.block_review_application import (
    BlockReviewConflictError,
    BlockReviewValidationError,
    CreateBlockReviewCommand,
    PersistedBlockReviewService,
)
from agas_api.current_week import CurrentWeekProjection, CurrentWeekProjector
from agas_api.database import database_session_dependency
from agas_api.environment_prescription_revision import (
    CreateEnvironmentPrescriptionRevisionsCommand,
    EnvironmentPrescriptionRevisionDraft,
    EnvironmentPrescriptionRevisionResult,
    EnvironmentPrescriptionRevisionValidationError,
    PersistedEnvironmentPrescriptionRevisionService,
)
from agas_api.exercise_reresolution import (
    ExerciseReResolutionNotFoundError,
    ExerciseReResolutionResult,
    ExerciseReResolutionValidationError,
    PersistedExerciseReResolutionService,
    ReResolveExerciseCommand,
)
from agas_api.first_week_preparation import FirstWeekPreparationProjector
from agas_api.identity import AuthorizedRole, authenticated_principal_dependency
from agas_api.identity_admin import set_account_role
from agas_api.main import app
from agas_api.operator_planning_queue import PlanningReviewQueueProjector
from agas_api.operator_post_block import (
    OperatorBlockReviewRequest,
    OperatorReplanningRequest,
    execute_operator_block_review,
    execute_operator_replanning,
)
from agas_api.operator_review_queue import (
    EnvironmentReviewQueueProjector,
    PostBlockReviewQueueProjector,
)
from agas_api.planning_authoring_admin import (
    load_block_plan_command,
    load_exercise_reresolution_command,
    load_resource_demand_command,
)
from agas_api.planning_governance_admin import record_weekly_scheduling_policy_review
from agas_api.planning_status import get_planning_status_projection
from agas_api.post_block_admin import load_block_review_command, load_replanning_command
from agas_api.post_block_preparation import (
    BlockReviewPreparationProjector,
    ReplanningPreparationProjector,
)
from agas_api.progression_application import (
    CreateProgressionDecisionCommand,
    PersistedProgressionService,
    ProgressionConflictError,
    ProgressionCreationResult,
    ProgressionValidationError,
)
from agas_api.replanning import (
    PersistedReplanningService,
    PostBlockReplanningCommand,
    ReplanningConflictError,
    ReplanningValidationError,
)
from agas_api.resource_preparation import (
    ActiveResourceDemandCommand,
    DeferredResourceDemandCommand,
    PersistedResourcePreparationService,
    ResourcePreparationNotFoundError,
    ResourcePreparationValidationError,
)
from agas_api.session_recording import (
    SessionExecutionCreationResult,
    SessionSafetyCreationResult,
)
from agas_api.weekly_availability_confirmation import (
    ConfirmWeeklyAvailabilityCommand,
    PersistedWeeklyAvailabilityConfirmationService,
    WeeklyAvailabilityConfirmationResult,
)
from agas_api.weekly_planning import (
    CreateWeeklyPlanCommand,
    PersistedWeeklyPlanService,
    WeeklyPlanValidationError,
)
from agas_api.weekly_planning_admin import load_weekly_plan_command
from agas_api.weekly_revision_admin import (
    load_environment_prescription_revisions_command,
)
from agas_api.weekly_roll_forward import (
    PersistedWeeklyPlanRollForwardService,
    RollForwardWeeklyPlanCommand,
    WeeklyPlanRollForwardResult,
)
from agas_domain import (
    AccountRole,
    AccountRoleStatus,
    Adaptation,
    AdaptationPlanningCandidate,
    AdaptationResourceDemand,
    Applicability,
    AssessmentReviewDecision,
    Athlete,
    AthleteSafetyPolicyAssignment,
    AvailabilityWindow,
    BlockPlan,
    BlockPlanStatus,
    BlockReviewOutcome,
    BlockReviewPolicy,
    CapabilityDomain,
    CapabilityEstimate,
    ComparisonDirection,
    CompetencyFloor,
    Confidence,
    CostLevel,
    EffortRpeTarget,
    Environment,
    Equipment,
    EquipmentAvailability,
    EvidenceClaim,
    EvidenceSourceIdentifier,
    EvidenceStrength,
    Exercise,
    ExerciseResolution,
    ExerciseResolverPolicy,
    ExposureDefinition,
    ExposureProgressionPolicy,
    ExposureTarget,
    ExposureType,
    ImpactLevel,
    Loadability,
    LongRangeStrategy,
    Observation,
    ObservationSource,
    PrescriptionAdjustment,
    PrescriptionModification,
    PriorityPolicy,
    ProgressionDimension,
    ProgressionOutcome,
    ProgressionPolicy,
    Provenance,
    ReadinessLevel,
    ReplanningCandidateContext,
    ResolutionIssueCode,
    ResolutionStatus,
    ResourceAllocationPolicy,
    ResponseEvaluationTarget,
    SafetyGateOutcome,
    SafetyGateTiming,
    SafetySignal,
    SafetySignalClass,
    SessionAdherence,
    SessionExecution,
    SessionExecutionInput,
    SessionExecutionStatus,
    SessionItemExecutionInput,
    SessionPrescription,
    SessionSafetyCheckInput,
    SessionSafetyDecision,
    SessionSafetyPolicy,
    SessionSection,
    SessionTemplate,
    SessionTemplateItem,
    SetPerformance,
    StimulusRequirement,
    StimulusSpecification,
    WeeklyAvailability,
    WeeklyPlan,
    WeeklyPlanStatus,
    WeeklySchedulingPolicy,
    WeeklySchedulingPolicyReview,
)
from agas_domain.persistence.models import (
    AdaptationResourceDemandRecord,
    BlockPlanRecord,
    BlockReviewRecord,
    CapabilityNeedRecord,
    DecisionRecordRecord,
    ExerciseResolutionRecord,
    ExposureEntryRecord,
    ExposureValidationDecisionRecord,
    ImmutableHistoricalRecordError,
    LongRangeStrategyRecord,
    ObservationRecord,
    ProgressionDecisionRecord,
    SessionAdherenceRecord,
    SessionExecutionRecord,
    SessionPrescriptionRecord,
    SessionPrescriptionRevisionRecord,
    SessionSafetyDecisionRecord,
    SessionTemplateRecord,
    StimulusRequirementRecord,
    TrainingResponseRecord,
    WeeklyAvailabilityRecord,
    WeeklyPlanRecord,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import (
    BlockPlanner,
    BlockReviewEngine,
    CompetencyFloorDetector,
    EnvironmentSnapshotBuilder,
    ExerciseResolver,
    ExposureEntryCalculator,
    ExposureProgressionValidator,
    LongRangeStrategyPlanner,
    PrescriptionProgressionApplicator,
    ProgressionEngine,
    SessionAdherenceCalculator,
    SessionExecutionRecorder,
    StimulusRequirementBuilder,
    TrainingResponseCalculator,
    WeeklyScheduler,
)
from agas_safety import SessionSafetyGate
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

NOW = datetime(2026, 8, 19, 14, 0, tzinfo=UTC)


def evidence_claim() -> EvidenceClaim:
    return EvidenceClaim(
        claim="Software fixture: a configured threshold remains linked to its provenance.",
        domain="software_test",
        population="synthetic persistence fixture",
        intervention="not applicable",
        outcome="referential integrity",
        study_design="software test fixture",
        uncertainty="This is not a scientific training claim.",
        limitations=("Not operational evidence",),
        evidence_strength=EvidenceStrength.INSUFFICIENT,
        athlete_applicability=Applicability.UNKNOWN,
        applicability_notes="Used only to verify software provenance.",
        source_identifiers=(
            EvidenceSourceIdentifier(scheme="other", value="fixture:planning-persistence"),
        ),
        reviewer="automated-test",
        claim_version="fixture@1.0.0",
    )


def priority_policy() -> PriorityPolicy:
    return PriorityPolicy(
        deficit_weight=4,
        general_relevance_weight=1,
        goal_relevance_weight=1,
        prerequisite_value_weight=1,
        expected_trainability_weight=1,
        transfer_value_weight=1,
        fatigue_cost_weight=1,
        time_cost_weight=1,
        interference_cost_weight=1,
        cost_penalty=0.2,
        confidence_multipliers={
            Confidence.UNKNOWN: 0.0,
            Confidence.LOW: 0.5,
            Confidence.MODERATE: 0.75,
            Confidence.HIGH: 1.0,
        },
        develop_score_threshold=0.3,
        comparative_advantage_threshold=0.5,
        severe_deficit_threshold=0.25,
        max_develop_adaptations=2,
        policy_version="persistence-fixture@1.0.0",
    )


def build_and_persist_strategy(
    session: Session, *, safe_to_train: bool = True
) -> tuple[DomainRepository, LongRangeStrategy]:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Planning persistence athlete")
    claim = evidence_claim()
    repository.add_athlete(athlete)
    repository.add_evidence_claim(claim)
    observation = Observation(
        athlete_id=athlete.id,
        observed_at=NOW,
        observation_type="fixture_strength_test",
        measurement=60,
        unit="fixture_unit",
        source=ObservationSource.TEST_RESULT,
        reliability=Confidence.MODERATE,
        provenance=Provenance(
            recorded_by="automated-test",
            source_system="pytest",
            ingestion_method="fixture",
        ),
    )
    repository.add_observation(observation)
    session.flush()
    estimate = CapabilityEstimate(
        athlete_id=athlete.id,
        domain=CapabilityDomain.MAXIMUM_STRENGTH,
        estimate=60,
        unit_or_scale="fixture_unit",
        estimate_scope="assessment_specific:fixture_strength_test",
        confidence=Confidence.MODERATE,
        calculation_method="fixture",
        source_observation_ids=(observation.id,),
        estimated_at=NOW,
        valid_until=NOW + timedelta(days=30),
        rule_version="fixture@1.0.0",
    )
    repository.add_capability_estimate(estimate)
    adaptation = Adaptation(
        name="Maximum strength",
        domain=CapabilityDomain.MAXIMUM_STRENGTH,
    )
    repository.add_adaptation(adaptation)
    floor = CompetencyFloor(
        domain=CapabilityDomain.MAXIMUM_STRENGTH,
        estimate_scope=estimate.estimate_scope,
        unit_or_scale="fixture_unit",
        threshold=100,
        comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
        population="synthetic test population",
        applicability_notes="Software fixture only.",
        uncertainty="Not an operational scientific threshold.",
        evidence_claim_ids=(claim.id,),
        floor_version="fixture@1.0.0",
    )
    repository.add_competency_floor(floor)
    session.flush()
    need = CompetencyFloorDetector().identify(athlete.id, floor, estimate, NOW)
    repository.add_capability_need(need)
    policy = priority_policy()
    repository.add_priority_policy(policy)
    session.flush()
    candidate = AdaptationPlanningCandidate(
        adaptation_id=adaptation.id,
        capability_need_id=need.id,
        general_relevance=0.9,
        goal_relevance=0.8,
        prerequisite_value=0.7,
        expected_trainability=0.7,
        transfer_value=0.8,
        fatigue_cost=0.3,
        time_cost=0.3,
        interference_cost=0.2,
        safe_to_train=safe_to_train,
        source_observation_ids=(observation.id,),
        evidence_claim_ids=(claim.id,),
    )
    strategy = LongRangeStrategyPlanner().build(
        athlete_id=athlete.id,
        adaptations=(adaptation,),
        needs=(need,),
        candidates=(candidate,),
        policy=policy,
        generated_at=NOW,
        horizon_months=12,
        review_after_days=42,
    )
    repository.add_long_range_strategy(strategy)
    session.commit()
    return repository, strategy


def test_planning_chain_round_trip_preserves_rules_scores_and_provenance(
    session: Session,
) -> None:
    repository, strategy = build_and_persist_strategy(session)
    session.expire_all()

    restored = repository.get_long_range_strategy(strategy.id)

    assert restored == strategy
    assert repository.get_priority_policy(strategy.priority_policy_id) is not None
    assert repository.get_capability_need(strategy.priorities[0].capability_need_id) is not None
    assert repository.get_competency_floor(strategy.competency_floor_ids[0]) is not None
    assert restored is not None
    assert restored.source_observation_ids == strategy.source_observation_ids
    assert restored.source_capability_estimate_ids == strategy.source_capability_estimate_ids
    assert restored.evidence_claim_ids == strategy.evidence_claim_ids
    assert restored.priorities[0].score_components == strategy.priorities[0].score_components


def test_long_range_strategy_history_is_append_only(session: Session) -> None:
    _, strategy = build_and_persist_strategy(session)
    record = session.get(LongRangeStrategyRecord, strategy.id)
    assert record is not None
    record.block_hypothesis = "silently rewritten"

    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.flush()


def test_competency_floor_rejects_unknown_evidence(session: Session) -> None:
    floor = CompetencyFloor(
        domain=CapabilityDomain.AEROBIC_CAPACITY,
        estimate_scope="assessment_specific:fixture",
        unit_or_scale="fixture_unit",
        threshold=100,
        comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
        population="synthetic test population",
        applicability_notes="Software fixture only.",
        uncertainty="Not an operational scientific threshold.",
        evidence_claim_ids=(uuid4(),),
        floor_version="fixture@1.0.0",
    )

    with pytest.raises(DomainIntegrityError, match="evidence claims"):
        DomainRepository(session).add_competency_floor(floor)


def build_and_persist_resolution_chain(
    session: Session,
) -> tuple[
    DomainRepository,
    LongRangeStrategy,
    StimulusRequirement,
    ExerciseResolution,
    ExerciseResolverPolicy,
    Environment,
    EquipmentAvailability,
    Exercise,
]:
    repository, strategy = build_and_persist_strategy(session)
    priority = strategy.priorities[0]
    adaptation = repository.get_adaptation(priority.adaptation_id)
    assert adaptation is not None
    environment = Environment(
        athlete_id=strategy.athlete_id,
        name="Hotel fixture",
        space_constraints={"floor_area_m2": 8},
        max_noise_level=CostLevel.MODERATE,
    )
    dumbbell = Equipment(name="Fixture dumbbell", category="external_load")
    availability = EquipmentAvailability(
        environment_id=environment.id,
        equipment_id=dumbbell.id,
        is_available=True,
        effective_from=NOW,
        load_limits={"maximum_total_kg": 40},
    )
    exercise = Exercise(
        name="Fixture dumbbell split squat",
        movement_patterns=("knee_dominant",),
        primary_adaptation_ids=(adaptation.id,),
        equipment_requirement_ids=(dumbbell.id,),
        loading_type="external_load",
        laterality="unilateral",
        loadability=Loadability.MODERATE,
        skill_complexity=CostLevel.MODERATE,
        impact_level=ImpactLevel.LOW,
        velocity_characteristics=("controlled",),
        stability_demand=CostLevel.MODERATE,
        fatigue_cost=CostLevel.MODERATE,
        soreness_cost=CostLevel.MODERATE,
    )
    repository.add_environment(environment)
    repository.add_equipment(dumbbell)
    session.flush()
    repository.add_equipment_availability(availability)
    repository.add_exercise(exercise)
    specification = StimulusSpecification(
        movement_patterns=("knee_dominant",),
        allowed_loading_types=("external_load",),
        allowed_lateralities=("bilateral", "unilateral"),
        minimum_loadability=Loadability.HIGH,
        required_velocity_characteristics=("controlled",),
        maximum_skill_complexity=CostLevel.MODERATE,
        maximum_impact_level=ImpactLevel.LOW,
        maximum_stability_demand=CostLevel.MODERATE,
        maximum_fatigue_cost=CostLevel.MODERATE,
        maximum_soreness_cost=CostLevel.MODERATE,
        source_observation_ids=strategy.source_observation_ids,
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic high-force stimulus persistence fixture.",
    )
    requirement = StimulusRequirementBuilder().build(
        strategy=strategy,
        priority=priority,
        adaptation=adaptation,
        specification=specification,
        generated_at=NOW,
    )
    policy = ExerciseResolverPolicy(
        adaptation_role_weight=2,
        movement_pattern_weight=2,
        loading_type_weight=1,
        loadability_weight=3,
        velocity_weight=1,
        laterality_weight=1,
        secondary_adaptation_credit=0.5,
        partial_match_threshold=0.7,
        full_match_threshold=0.95,
        max_ranked_candidates=5,
        policy_version="persistence-resolver@1.0.0",
    )
    snapshot = EnvironmentSnapshotBuilder().build(
        environment,
        (dumbbell,),
        (availability,),
        NOW,
    )
    resolution = ExerciseResolver().resolve(
        requirement=requirement,
        environment=snapshot,
        exercises=(exercise,),
        policy=policy,
        resolved_at=NOW,
    )
    repository.add_stimulus_requirement(requirement)
    repository.add_exercise_resolver_policy(policy)
    session.flush()
    repository.add_exercise_resolution(resolution)
    session.commit()
    session.expire_all()

    return (
        repository,
        strategy,
        requirement,
        resolution,
        policy,
        environment,
        availability,
        exercise,
    )


def resource_demand_for(
    strategy: LongRangeStrategy,
    requirement: StimulusRequirement,
    resolution: ExerciseResolution,
) -> AdaptationResourceDemand:
    priority = strategy.priorities[0]
    return AdaptationResourceDemand(
        long_range_strategy_id=strategy.id,
        adaptation_priority_id=priority.id,
        adaptation_id=priority.adaptation_id,
        priority_state=priority.state,
        stimulus_requirement_id=requirement.id,
        exercise_resolution_id=resolution.id,
        minimum_weekly_minutes=60,
        target_weekly_minutes=60,
        sessions_per_week=2,
        source_observation_ids=strategy.source_observation_ids,
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic resource-readiness fixture.",
        demand_version="fixture-resource-readiness@1.0.0",
    )


def test_planning_status_tracks_governed_first_block_readiness(session: Session) -> None:
    repository, strategy, requirement, resolution, _, _, _, _ = build_and_persist_resolution_chain(
        session
    )

    initial = get_planning_status_projection(session, strategy.athlete_id, NOW)
    assert initial.status == "resource_demand_preparation_required"
    assert initial.first_block_readiness is not None
    assert initial.first_block_readiness.historical_resource_demand_count == 0

    demand = resource_demand_for(strategy, requirement, resolution)
    repository.add_adaptation_resource_demand(demand)
    session.commit()

    without_policy = get_planning_status_projection(session, strategy.athlete_id, NOW)
    assert without_policy.status == "resource_allocation_policy_required"
    assert without_policy.first_block_readiness is not None
    assert without_policy.first_block_readiness.priorities_with_resource_demand_count == 1
    assert without_policy.first_block_readiness.partial_resolution_count == 1
    assert without_policy.first_block_readiness.block_eligible_priority_count == 0

    strict_policy = ResourceAllocationPolicy(
        develop_weight=1,
        maintain_weight=1,
        expose_weight=1,
        allow_partial_exercise_resolution=False,
        policy_version="fixture-resource-readiness@strict",
    )
    repository.add_resource_allocation_policy(strict_policy)
    session.commit()

    strict = get_planning_status_projection(session, strategy.athlete_id, NOW)
    assert strict.status == "exercise_resolution_review_required"
    assert strict.first_block_readiness is not None
    assert strict.first_block_readiness.block_eligible_priority_count == 0

    partial_policy = ResourceAllocationPolicy(
        develop_weight=1,
        maintain_weight=1,
        expose_weight=1,
        allow_partial_exercise_resolution=True,
        policy_version="fixture-resource-readiness@partial",
    )
    repository.add_resource_allocation_policy(partial_policy)
    session.commit()

    ready = get_planning_status_projection(session, strategy.athlete_id, NOW)
    assert ready.status == "block_context_review_required"
    assert ready.first_block_readiness is not None
    assert ready.first_block_readiness.block_eligible_priority_count == 1
    assert ready.first_block_readiness.resource_allocation_policy_count == 2
    assert [requirement.satisfied for requirement in ready.requirements] == [
        True,
        True,
        True,
        False,
    ]

    block = BlockPlanner().build(
        strategy=strategy,
        demands=(demand,),
        resolutions=(resolution,),
        policy=partial_policy,
        weekly_budget_minutes=60,
        starts_on=date(2026, 8, 24),
        duration_weeks=4,
        constraints=("Synthetic first-block readiness constraint",),
        generated_at=NOW,
    )
    repository.add_block_plan(block)
    session.commit()

    created = get_planning_status_projection(session, strategy.athlete_id, NOW)
    assert created.status == "weekly_scheduling_policy_required"
    assert created.first_block_readiness is not None
    assert created.first_block_readiness.block_plan_count == 1
    assert created.first_block_readiness.block_plan is not None
    assert created.first_block_readiness.block_plan.block_plan_id == block.id
    assert created.first_block_readiness.block_plan.status is BlockPlanStatus.PARTIAL
    assert created.first_week_readiness is not None
    assert created.first_week_readiness.active_resource_allocation_count == 1
    assert created.first_week_readiness.weekly_scheduling_policy_count == 0
    assert created.first_week_readiness.first_week_plan_count == 0
    assert [requirement.satisfied for requirement in created.requirements] == [
        False,
        False,
        False,
        False,
    ]

    scheduling_policy = WeeklySchedulingPolicy(
        minimum_high_fatigue_recovery_hours=24,
        maximum_sessions_per_day=1,
        maximum_high_fatigue_sessions_per_day=1,
        allow_partial_exercise_resolution=True,
        policy_version="fixture-resource-readiness@scheduling",
    )
    repository.add_weekly_scheduling_policy(scheduling_policy)
    session.commit()

    unreviewed_policy = get_planning_status_projection(session, strategy.athlete_id, NOW)
    assert unreviewed_policy.status == "weekly_scheduling_policy_required"
    assert unreviewed_policy.first_week_readiness is not None
    assert unreviewed_policy.first_week_readiness.weekly_scheduling_policy_count == 0

    scheduling_review = WeeklySchedulingPolicyReview(
        weekly_scheduling_policy_id=scheduling_policy.id,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=1,
        evidence_claim_ids=strategy.evidence_claim_ids,
        reviewed_at=NOW - timedelta(minutes=1),
        reviewed_by="automated-test-reviewer",
        applicability_rationale="Reviewed only for software behavior testing.",
        uncertainty="This approval is not operational training guidance.",
        review_version="fixture-scheduling-review@1.0.0",
    )
    repository.add_weekly_scheduling_policy_review(scheduling_review)
    session.commit()

    weekly_context = get_planning_status_projection(session, strategy.athlete_id, NOW)
    assert weekly_context.status == "weekly_plan_context_review_required"
    assert weekly_context.first_week_readiness is not None
    assert weekly_context.first_week_readiness.weekly_scheduling_policy_count == 1
    assert [requirement.satisfied for requirement in weekly_context.requirements] == [
        True,
        False,
        False,
        False,
    ]


def test_planning_status_preserves_infeasible_and_ambiguous_block_states(
    session: Session,
) -> None:
    repository, strategy, requirement, resolution, _, _, _, _ = build_and_persist_resolution_chain(
        session
    )
    demand = resource_demand_for(strategy, requirement, resolution)
    policy = ResourceAllocationPolicy(
        develop_weight=1,
        maintain_weight=1,
        expose_weight=1,
        allow_partial_exercise_resolution=True,
        policy_version="fixture-resource-readiness@infeasible",
    )
    repository.add_adaptation_resource_demand(demand)
    repository.add_resource_allocation_policy(policy)
    session.flush()
    infeasible_block = BlockPlanner().build(
        strategy=strategy,
        demands=(demand,),
        resolutions=(resolution,),
        policy=policy,
        weekly_budget_minutes=30,
        starts_on=date(2026, 8, 24),
        duration_weeks=4,
        constraints=("Budget intentionally below the synthetic minimum",),
        generated_at=NOW,
    )
    repository.add_block_plan(infeasible_block)
    session.commit()

    infeasible = get_planning_status_projection(session, strategy.athlete_id, NOW)
    assert infeasible.status == "block_infeasible"
    assert infeasible.first_block_readiness is not None
    assert infeasible.first_block_readiness.block_plan is not None
    assert infeasible.first_block_readiness.block_plan.status is BlockPlanStatus.INFEASIBLE

    alternate_block = BlockPlanner().build(
        strategy=strategy,
        demands=(demand,),
        resolutions=(resolution,),
        policy=policy,
        weekly_budget_minutes=60,
        starts_on=date(2026, 8, 31),
        duration_weeks=4,
        constraints=("Alternate historical block fixture",),
        generated_at=NOW,
    )
    repository.add_block_plan(alternate_block)
    session.commit()

    ambiguous = get_planning_status_projection(session, strategy.athlete_id, NOW)
    assert ambiguous.status == "block_selection_review_required"
    assert ambiguous.first_block_readiness is not None
    assert ambiguous.first_block_readiness.block_plan_count == 2
    assert ambiguous.first_block_readiness.block_plan is None
    assert len(ambiguous.requirements) == 1
    assert ambiguous.requirements[0].code == "unambiguous_block_selection_required"
    assert ambiguous.requirements[0].satisfied is False


def test_stimulus_and_partial_exercise_resolution_round_trip_preserves_provenance(
    session: Session,
) -> None:
    (
        repository,
        strategy,
        requirement,
        resolution,
        policy,
        _,
        availability,
        _,
    ) = build_and_persist_resolution_chain(session)
    priority = strategy.priorities[0]

    assert repository.get_stimulus_requirement(requirement.id) == requirement
    assert repository.get_exercise_resolver_policy(policy.id) == policy
    assert repository.get_exercise_resolution(resolution.id) == resolution
    assert resolution.status is ResolutionStatus.PARTIAL
    assert resolution.source_availability_ids == (availability.id,)
    assert any(
        issue.code is ResolutionIssueCode.INSUFFICIENT_LOADABILITY
        for issue in resolution.unresolved_issues
    )
    assert requirement.adaptation_id == priority.adaptation_id

    record = session.get(ExerciseResolutionRecord, resolution.id)
    assert record is not None
    record.rationale = "silently rewritten"
    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.flush()


def test_operator_resource_preparation_resolves_environment_and_persists_atomically(
    session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (
        repository,
        strategy,
        _,
        _,
        policy,
        environment,
        availability,
        exercise,
    ) = build_and_persist_resolution_chain(session)
    priority = strategy.priorities[0]
    prepared_at = NOW + timedelta(minutes=1)
    specification = StimulusSpecification(
        movement_patterns=("knee_dominant",),
        allowed_loading_types=("external_load",),
        allowed_lateralities=("bilateral", "unilateral"),
        minimum_loadability=Loadability.HIGH,
        required_velocity_characteristics=("controlled",),
        maximum_skill_complexity=CostLevel.MODERATE,
        maximum_impact_level=ImpactLevel.LOW,
        maximum_stability_demand=CostLevel.MODERATE,
        maximum_fatigue_cost=CostLevel.MODERATE,
        maximum_soreness_cost=CostLevel.MODERATE,
        source_observation_ids=strategy.source_observation_ids,
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Explicit synthetic stimulus input for the API boundary.",
    )
    request_body = {
        "mode": "active",
        "environment_id": str(environment.id),
        "exercise_candidate_ids": [str(exercise.id)],
        "exercise_resolver_policy_id": str(policy.id),
        "stimulus_specification": specification.model_dump(mode="json"),
        "minimum_weekly_minutes": 60,
        "target_weekly_minutes": 60,
        "sessions_per_week": 2,
        "demand_rationale": "Explicit synthetic resource demand.",
        "demand_version": "fixture-resource-preparation@1.0.0",
        "prepared_at": prepared_at.isoformat(),
        "reviewed_by": "fixture resource-demand reviewer",
        "applicability_rationale": "Explicit synthetic inputs exercise the governed boundary.",
        "uncertainty": "Software fixture only; no operational training claim is made.",
    }
    with pytest.raises(ValueError, match="operator review metadata"):
        ActiveResourceDemandCommand.model_validate({**request_body, "reviewed_by": "   "})
    command = ActiveResourceDemandCommand.model_validate(request_body)
    input_path = tmp_path / "reviewed-resource-demand.json"
    input_path.write_text(json.dumps(command.model_dump(mode="json")), encoding="utf-8")
    assert load_resource_demand_command(input_path) == command

    other_athlete = Athlete(display_name="Other environment owner")
    other_environment = Environment(athlete_id=other_athlete.id, name="Other gym")
    repository.add_athlete(other_athlete)
    session.flush()
    repository.add_environment(other_environment)
    session.commit()

    record_types = (
        StimulusRequirementRecord,
        ExerciseResolutionRecord,
        AdaptationResourceDemandRecord,
        DecisionRecordRecord,
    )
    counts_before = tuple(
        session.scalar(select(func.count()).select_from(record_type))
        for record_type in record_types
    )

    with pytest.raises(ResourcePreparationNotFoundError, match="exercise candidate"):
        PersistedResourcePreparationService(session).execute(
            strategy.id,
            priority.id,
            command.model_copy(update={"exercise_candidate_ids": (uuid4(),)}),
        )
    with pytest.raises(ResourcePreparationValidationError):
        PersistedResourcePreparationService(session).execute(
            strategy.id,
            priority.id,
            command.model_copy(update={"environment_id": other_environment.id}),
        )
    deferred_command = DeferredResourceDemandCommand(
        mode="deferred",
        source_observation_ids=strategy.source_observation_ids,
        evidence_claim_ids=strategy.evidence_claim_ids,
        demand_rationale="Invalid deferred request for an active priority.",
        demand_version="fixture@1.0.0",
        prepared_at=prepared_at,
        reviewed_by="fixture resource-demand reviewer",
        applicability_rationale="Exercise the state mismatch guard.",
        uncertainty="Software fixture only.",
    )
    with pytest.raises(ResourcePreparationValidationError, match="DEFER priority"):
        PersistedResourcePreparationService(session).execute(
            strategy.id,
            priority.id,
            deferred_command,
        )

    def reject_demand(_repository: DomainRepository, _demand: AdaptationResourceDemand) -> None:
        raise DomainIntegrityError("synthetic late persistence failure")

    with monkeypatch.context() as context:
        context.setattr(DomainRepository, "add_adaptation_resource_demand", reject_demand)
        with pytest.raises(ResourcePreparationValidationError, match="synthetic late"):
            PersistedResourcePreparationService(session).execute(
                strategy.id,
                priority.id,
                command,
            )

    def reject_decision(_repository: DomainRepository, _decision: object) -> None:
        raise DomainIntegrityError("synthetic resource decision-audit failure")

    with monkeypatch.context() as context:
        context.setattr(DomainRepository, "add_decision_record", reject_decision)
        with pytest.raises(ResourcePreparationValidationError, match="decision-audit"):
            PersistedResourcePreparationService(session).execute(
                strategy.id,
                priority.id,
                command,
            )
    counts_after_invalid = tuple(
        session.scalar(select(func.count()).select_from(record_type))
        for record_type in record_types
    )
    assert counts_after_invalid == counts_before

    result = PersistedResourcePreparationService(session).execute(
        strategy.id,
        priority.id,
        command,
    )
    assert result.stimulus_requirement is not None
    assert result.exercise_resolution is not None
    assert result.exercise_resolution.status is ResolutionStatus.PARTIAL
    assert result.exercise_resolution.source_availability_ids == (availability.id,)
    assert result.resource_demand.exercise_resolution_id == result.exercise_resolution.id
    assert result.decision_record.reason.startswith("Reviewed by fixture resource-demand reviewer.")
    assert f"adaptation_resource_demand:{result.resource_demand.id}" in (
        result.decision_record.evidence
    )
    assert f"equipment_availability:{availability.id}" in result.decision_record.evidence
    session.expire_all()
    assert repository.get_environment(environment.id) == environment
    assert repository.list_equipment_availability(environment.id) == (availability,)
    assert (
        repository.get_stimulus_requirement(result.stimulus_requirement.id)
        == result.stimulus_requirement
    )
    assert (
        repository.get_exercise_resolution(result.exercise_resolution.id)
        == result.exercise_resolution
    )
    assert (
        repository.get_adaptation_resource_demand(result.resource_demand.id)
        == result.resource_demand
    )
    assert session.get(DecisionRecordRecord, result.decision_record.id) is not None


def test_authenticated_resource_preparation_projects_exact_inputs_and_owns_reviewer_identity(
    session: Session,
) -> None:
    (
        repository,
        strategy,
        _,
        _,
        policy,
        environment,
        availability,
        exercise,
    ) = build_and_persist_resolution_chain(session)
    priority = strategy.priorities[0]
    resource_queue = PlanningReviewQueueProjector(session).project(NOW)
    assert len(resource_queue.items) == 1
    assert resource_queue.items[0].workflow_stage == "resource_demands"
    assert resource_queue.items[0].strategy_id == strategy.id
    assert resource_queue.items[0].readiness == "ready"
    reviewer, assignment, _, _ = set_account_role(
        session,
        issuer="urn:agas:development",
        subject="resource-reviewer",
        role=AccountRole.PLANNING_REVIEWER,
        status=AccountRoleStatus.ACTIVE,
        assigned_at=NOW,
        rationale="Exercise authenticated resource-demand review.",
    )
    prepared_at = NOW + timedelta(minutes=2)
    specification = StimulusSpecification(
        movement_patterns=("knee_dominant",),
        allowed_loading_types=("external_load",),
        allowed_lateralities=("bilateral", "unilateral"),
        minimum_loadability=Loadability.HIGH,
        required_velocity_characteristics=("controlled",),
        maximum_skill_complexity=CostLevel.MODERATE,
        maximum_impact_level=ImpactLevel.LOW,
        maximum_stability_demand=CostLevel.MODERATE,
        maximum_fatigue_cost=CostLevel.MODERATE,
        maximum_soreness_cost=CostLevel.MODERATE,
        source_observation_ids=strategy.source_observation_ids,
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Reviewed synthetic stimulus for authenticated transport testing.",
    )
    request_body = {
        "mode": "active",
        "environment_id": str(environment.id),
        "exercise_candidate_ids": [str(exercise.id)],
        "exercise_resolver_policy_id": str(policy.id),
        "stimulus_specification": specification.model_dump(mode="json"),
        "minimum_weekly_minutes": 60,
        "target_weekly_minutes": 60,
        "sessions_per_week": 2,
        "demand_rationale": "Reviewed synthetic resource demand.",
        "demand_version": "fixture-authenticated-resource-demand@1.0.0",
        "prepared_at": prepared_at.isoformat(),
        "applicability_rationale": "Exercise the server-owned reviewer boundary.",
        "uncertainty": "Software fixture only; no operational training claim is made.",
    }

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    headers = {"Authorization": "Bearer dev.resource-reviewer"}
    try:
        preparation = TestClient(app).get(
            f"/v1/operator/strategies/{strategy.id}/resource-demand-preparation",
            params={"at": prepared_at.isoformat()},
            headers=headers,
        )
        spoofed = TestClient(app).post(
            f"/v1/operator/strategies/{strategy.id}/priorities/{priority.id}/resource-demands",
            json={**request_body, "reviewed_by": "spoofed-reviewer"},
            headers=headers,
        )
        created = TestClient(app).post(
            f"/v1/operator/strategies/{strategy.id}/priorities/{priority.id}/resource-demands",
            json=request_body,
            headers=headers,
        )
        refreshed = TestClient(app).get(
            f"/v1/operator/strategies/{strategy.id}/resource-demand-preparation",
            params={"at": prepared_at.isoformat()},
            headers=headers,
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert preparation.status_code == 200
    projection = preparation.json()
    assert projection["strategy"]["id"] == str(strategy.id)
    assert projection["priorities"][0]["adaptation"]["id"] == str(priority.adaptation_id)
    assert projection["priorities"][0]["demand_history"] == []
    assert projection["source_observations"][0]["id"] == str(strategy.source_observation_ids[0])
    assert projection["evidence_claims"][0]["id"] == str(strategy.evidence_claim_ids[0])
    assert projection["environments"][0]["environment"]["id"] == str(environment.id)
    assert projection["environments"][0]["snapshot"]["source_availability_ids"] == [
        str(availability.id)
    ]
    assert projection["exercise_resolver_policies"][0]["id"] == str(policy.id)
    assert projection["exercise_catalog"][0]["id"] == str(exercise.id)
    assert spoofed.status_code == 422
    assert created.status_code == 201
    result = created.json()
    assert result["decision_record"]["reason"].startswith(f"Reviewed by account:{reviewer.id}.")
    assert f"account_role_assignment:{assignment.id}" in result["decision_record"]["evidence"]
    assert "reviewed_by" not in result
    assert refreshed.status_code == 200
    assert len(refreshed.json()["priorities"][0]["demand_history"]) == 1
    demand_id = UUID(result["resource_demand"]["id"])
    assert repository.get_adaptation_resource_demand(demand_id) is not None
    block_queue = PlanningReviewQueueProjector(session).project(prepared_at)
    assert len(block_queue.items) == 1
    assert block_queue.items[0].workflow_stage == "block_creation"
    assert block_queue.items[0].strategy_id == strategy.id
    assert block_queue.items[0].readiness == "blocked"


def test_authenticated_block_preparation_projects_history_and_owns_reviewer_identity(
    session: Session,
) -> None:
    (
        repository,
        strategy,
        requirement,
        resolution,
        _,
        _,
        _,
        _,
    ) = build_and_persist_resolution_chain(session)
    demand = resource_demand_for(strategy, requirement, resolution)
    allocation_policy = ResourceAllocationPolicy(
        develop_weight=1,
        maintain_weight=1,
        expose_weight=1,
        allow_partial_exercise_resolution=True,
        policy_version="fixture-authenticated-block@1.0.0",
    )

    empty = BlockPreparationProjector(session).project(strategy.id, NOW)
    assert empty.priorities[0].demand_history == ()
    assert empty.resource_allocation_policies == ()
    assert empty.existing_blocks == ()
    assert tuple(item.id for item in empty.source_observations) == (strategy.source_observation_ids)
    assert tuple(item.id for item in empty.evidence_claims) == strategy.evidence_claim_ids

    repository.add_adaptation_resource_demand(demand)
    repository.add_resource_allocation_policy(allocation_policy)
    session.commit()
    reviewer, assignment, _, _ = set_account_role(
        session,
        issuer="urn:agas:development",
        subject="block-reviewer",
        role=AccountRole.PLANNING_REVIEWER,
        status=AccountRoleStatus.ACTIVE,
        assigned_at=NOW,
        rationale="Exercise authenticated block-context review.",
    )
    generated_at = NOW + timedelta(minutes=3)
    request_body = {
        "resource_demand_ids": [str(demand.id)],
        "resource_allocation_policy_id": str(allocation_policy.id),
        "weekly_budget_minutes": 60,
        "starts_on": "2026-08-24",
        "duration_weeks": 4,
        "constraints": ["Synthetic reviewed block constraint"],
        "generated_at": generated_at.isoformat(),
        "applicability_rationale": "Exercise the server-owned block reviewer boundary.",
        "uncertainty": "Software fixture only; no operational training claim is made.",
    }

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    headers = {"Authorization": "Bearer dev.block-reviewer"}
    try:
        preparation = TestClient(app).get(
            f"/v1/operator/strategies/{strategy.id}/block-preparation",
            params={"at": generated_at.isoformat()},
            headers=headers,
        )
        spoofed = TestClient(app).post(
            f"/v1/operator/strategies/{strategy.id}/blocks",
            json={**request_body, "reviewed_by": "spoofed-reviewer"},
            headers=headers,
        )
        created = TestClient(app).post(
            f"/v1/operator/strategies/{strategy.id}/blocks",
            json=request_body,
            headers=headers,
        )
        refreshed = TestClient(app).get(
            f"/v1/operator/strategies/{strategy.id}/block-preparation",
            params={"at": generated_at.isoformat()},
            headers=headers,
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert preparation.status_code == 200
    projection = preparation.json()
    assert projection["strategy"]["id"] == str(strategy.id)
    assert projection["priorities"][0]["adaptation"]["id"] == str(
        strategy.priorities[0].adaptation_id
    )
    history = projection["priorities"][0]["demand_history"][0]
    assert history["resource_demand"]["id"] == str(demand.id)
    assert history["stimulus_requirement"]["id"] == str(requirement.id)
    assert history["exercise_resolution"]["id"] == str(resolution.id)
    assert projection["resource_allocation_policies"][0]["id"] == str(allocation_policy.id)
    assert projection["existing_blocks"] == []
    assert spoofed.status_code == 422
    assert created.status_code == 201
    result = created.json()
    assert result["block_plan"]["status"] == "partial"
    assert result["block_plan"]["allocations"][0]["resource_demand_id"] == str(demand.id)
    assert result["decision_record"]["reason"].startswith(f"Reviewed by account:{reviewer.id}.")
    assert f"account_role_assignment:{assignment.id}" in result["decision_record"]["evidence"]
    assert "reviewed_by" not in result
    assert refreshed.status_code == 200
    assert len(refreshed.json()["existing_blocks"]) == 1
    block_id = UUID(result["block_plan"]["id"])
    assert repository.get_block_plan(block_id) is not None
    first_week_queue = PlanningReviewQueueProjector(session).project(generated_at)
    assert len(first_week_queue.items) == 1
    assert first_week_queue.items[0].workflow_stage == "first_week"
    assert first_week_queue.items[0].block_id == block_id
    assert first_week_queue.items[0].readiness == "blocked"


def test_block_creation_revalidates_exact_current_reviewer_assignment(session: Session) -> None:
    repository, strategy, requirement, resolution, _, _, _, _ = build_and_persist_resolution_chain(
        session
    )
    demand = resource_demand_for(strategy, requirement, resolution)
    allocation_policy = ResourceAllocationPolicy(
        develop_weight=1,
        maintain_weight=1,
        expose_weight=1,
        allow_partial_exercise_resolution=True,
        policy_version="fixture-block-authority@1.0.0",
    )
    repository.add_adaptation_resource_demand(demand)
    repository.add_resource_allocation_policy(allocation_policy)
    session.commit()
    reviewer, assignment, _, _ = set_account_role(
        session,
        issuer="urn:agas:development",
        subject="block-authority-reviewer",
        role=AccountRole.PLANNING_REVIEWER,
        status=AccountRoleStatus.ACTIVE,
        assigned_at=NOW,
        rationale="Create the exact grant exercised by the block service.",
    )
    command = CreateBlockPlanCommand(
        resource_demand_ids=(demand.id,),
        resource_allocation_policy_id=allocation_policy.id,
        weekly_budget_minutes=60,
        starts_on=date(2026, 8, 24),
        duration_weeks=4,
        constraints=("Synthetic exact-authority constraint",),
        generated_at=NOW + timedelta(minutes=2),
        reviewed_by=f"account:{reviewer.id}",
        review_authority_assignment_id=assignment.id,
        applicability_rationale="Exercise application-layer authority validation.",
        uncertainty="Software fixture only.",
    )
    with pytest.raises(BlockCreationValidationError, match="does not match"):
        PersistedBlockCreationService(session).execute(
            strategy.id,
            command.model_copy(update={"reviewed_by": "account:forged"}),
        )

    set_account_role(
        session,
        issuer="urn:agas:development",
        subject="block-authority-reviewer",
        role=AccountRole.PLANNING_REVIEWER,
        status=AccountRoleStatus.REVOKED,
        assigned_at=NOW + timedelta(minutes=1),
        rationale="Revoke the exact grant before block creation.",
    )
    with pytest.raises(BlockCreationValidationError, match="not a current"):
        PersistedBlockCreationService(session).execute(strategy.id, command)


def test_operator_exercise_reresolution_preserves_stimulus_and_prior_history(
    session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (
        repository,
        strategy,
        requirement,
        prior_resolution,
        policy,
        _,
        _,
        partial_exercise,
    ) = build_and_persist_resolution_chain(session)
    equipment_id = partial_exercise.equipment_requirement_ids[0]
    equipment = repository.get_equipment(equipment_id)
    assert equipment is not None

    travel_environment = Environment(
        athlete_id=strategy.athlete_id,
        name="Travel re-resolution fixture",
        space_constraints={"floor_area_m2": 8},
        max_noise_level=CostLevel.MODERATE,
    )
    unavailable = EquipmentAvailability(
        environment_id=travel_environment.id,
        equipment_id=equipment.id,
        is_available=False,
        effective_from=NOW + timedelta(minutes=1),
        reason="Synthetic travel environment starts without the required equipment.",
    )
    available = EquipmentAvailability(
        environment_id=travel_environment.id,
        equipment_id=equipment.id,
        is_available=True,
        effective_from=NOW + timedelta(minutes=2),
        load_limits={"maximum_total_kg": 100},
        reason="Synthetic equipment becomes available later without changing the athlete.",
    )
    full_exercise = partial_exercise.model_copy(
        update={
            "id": uuid4(),
            "name": "Fixture highly loadable travel split squat",
            "loadability": Loadability.HIGH,
        }
    )
    repository.add_environment(travel_environment)
    repository.add_exercise(full_exercise)
    session.flush()
    repository.add_equipment_availability(unavailable)
    repository.add_equipment_availability(available)
    session.commit()

    base_command = ReResolveExerciseCommand(
        environment_id=travel_environment.id,
        exercise_candidate_ids=(partial_exercise.id,),
        exercise_resolver_policy_id=policy.id,
        resolved_at=NOW + timedelta(minutes=1),
        reviewed_by="fixture exercise-resolution reviewer",
        applicability_rationale=(
            "The original stimulus is fixed while the synthetic environment state changes."
        ),
        uncertainty="Software fixture only; no exercise is recommended to a real athlete.",
    )
    input_path = tmp_path / "reviewed-exercise-reresolution.json"
    input_path.write_text(json.dumps(base_command.model_dump(mode="json")), encoding="utf-8")
    assert load_exercise_reresolution_command(input_path) == base_command
    with pytest.raises(ValueError, match="operator review metadata"):
        ReResolveExerciseCommand.model_validate(
            {**base_command.model_dump(), "applicability_rationale": "   "}
        )
    with pytest.raises(ValueError, match="duplicates"):
        ReResolveExerciseCommand.model_validate(
            {
                **base_command.model_dump(),
                "exercise_candidate_ids": (partial_exercise.id, partial_exercise.id),
            }
        )
    with pytest.raises(ExerciseReResolutionNotFoundError, match="exercise candidate"):
        PersistedExerciseReResolutionService(session).execute(
            requirement.id,
            base_command.model_copy(update={"exercise_candidate_ids": (uuid4(),)}),
        )

    other_athlete = Athlete(display_name="Other re-resolution owner")
    other_environment = Environment(athlete_id=other_athlete.id, name="Other athlete gym")
    repository.add_athlete(other_athlete)
    session.flush()
    repository.add_environment(other_environment)
    session.commit()
    with pytest.raises(ExerciseReResolutionValidationError, match="different athlete"):
        PersistedExerciseReResolutionService(session).execute(
            requirement.id,
            base_command.model_copy(update={"environment_id": other_environment.id}),
        )

    resolution_count = session.scalar(select(func.count()).select_from(ExerciseResolutionRecord))
    decision_count = session.scalar(select(func.count()).select_from(DecisionRecordRecord))

    def reject_decision(_repository: DomainRepository, _decision: object) -> None:
        raise DomainIntegrityError("synthetic re-resolution decision-audit failure")

    with monkeypatch.context() as context:
        context.setattr(DomainRepository, "add_decision_record", reject_decision)
        with pytest.raises(ExerciseReResolutionValidationError, match="decision-audit"):
            PersistedExerciseReResolutionService(session).execute(requirement.id, base_command)
    assert session.scalar(select(func.count()).select_from(ExerciseResolutionRecord)) == (
        resolution_count
    )
    assert session.scalar(select(func.count()).select_from(DecisionRecordRecord)) == decision_count

    infeasible_result = PersistedExerciseReResolutionService(session).execute(
        requirement.id,
        base_command,
    )
    assert infeasible_result.exercise_resolution.status is ResolutionStatus.INFEASIBLE
    assert infeasible_result.exercise_resolution.selected_exercise_id is None
    assert infeasible_result.exercise_resolution.source_availability_ids == (unavailable.id,)
    assert any(
        issue.code is ResolutionIssueCode.MISSING_EQUIPMENT
        for issue in infeasible_result.exercise_resolution.unresolved_issues
    )

    partial_result = PersistedExerciseReResolutionService(session).execute(
        requirement.id,
        base_command.model_copy(update={"resolved_at": NOW + timedelta(minutes=2)}),
    )
    assert partial_result.exercise_resolution.status is ResolutionStatus.PARTIAL
    assert partial_result.exercise_resolution.selected_exercise_id == partial_exercise.id
    assert partial_result.exercise_resolution.source_availability_ids == (available.id,)

    full_result = PersistedExerciseReResolutionService(session).execute(
        requirement.id,
        base_command.model_copy(
            update={
                "exercise_candidate_ids": (full_exercise.id,),
                "resolved_at": NOW + timedelta(minutes=3),
            }
        ),
    )
    assert full_result.exercise_resolution.status is ResolutionStatus.FULL
    assert full_result.exercise_resolution.selected_exercise_id == full_exercise.id
    assert full_result.exercise_resolution.stimulus_requirement_id == requirement.id
    assert f"stimulus_requirement:{requirement.id}" in full_result.decision_record.evidence
    assert f"adaptation:{requirement.adaptation_id}" in full_result.decision_record.evidence
    assert f"observation:{requirement.source_observation_ids[0]}" in (
        full_result.decision_record.evidence
    )
    assert f"evidence_claim:{requirement.evidence_claim_ids[0]}" in (
        full_result.decision_record.evidence
    )
    assert f"equipment_availability:{available.id}" in full_result.decision_record.evidence
    assert f"exercise_resolution:{full_result.exercise_resolution.id}" in (
        full_result.decision_record.evidence
    )

    session.expire_all()
    assert repository.get_stimulus_requirement(requirement.id) == requirement
    assert repository.get_exercise_resolution(prior_resolution.id) == prior_resolution
    assert repository.get_exercise_resolution(infeasible_result.exercise_resolution.id) == (
        infeasible_result.exercise_resolution
    )
    assert repository.get_exercise_resolution(partial_result.exercise_resolution.id) == (
        partial_result.exercise_resolution
    )
    assert repository.get_exercise_resolution(full_result.exercise_resolution.id) == (
        full_result.exercise_resolution
    )


def test_athlete_api_cannot_request_exercise_reresolution() -> None:
    identity = uuid4()

    response = TestClient(app).post(
        f"/v1/stimulus-requirements/{identity}/exercise-resolutions",
        json={},
    )

    assert response.status_code == 404


def test_deferred_priority_preparation_creates_zero_resource_demand(session: Session) -> None:
    repository, strategy = build_and_persist_strategy(session, safe_to_train=False)
    priority = strategy.priorities[0]
    assert priority.state.value == "defer"

    command = DeferredResourceDemandCommand(
        mode="deferred",
        source_observation_ids=strategy.source_observation_ids,
        evidence_claim_ids=strategy.evidence_claim_ids,
        demand_rationale="Explicitly deferred by the persisted safety constraint.",
        demand_version="fixture-deferred-demand@1.0.0",
        prepared_at=NOW,
        reviewed_by="fixture deferred-demand reviewer",
        applicability_rationale="The persisted strategy explicitly marks this priority DEFER.",
        uncertainty="Software fixture only.",
    )
    result = PersistedResourcePreparationService(session).execute(
        strategy.id,
        priority.id,
        command,
    )
    assert result.stimulus_requirement is None
    assert result.exercise_resolution is None
    assert result.resource_demand.minimum_weekly_minutes == 0
    assert result.resource_demand.target_weekly_minutes == 0
    assert result.resource_demand.sessions_per_week == 0
    assert result.decision_record.decided_on == NOW.date()
    session.expire_all()
    assert (
        repository.get_adaptation_resource_demand(result.resource_demand.id)
        == result.resource_demand
    )


def test_athlete_api_cannot_submit_resource_or_block_authoring_inputs() -> None:
    identity = uuid4()

    demand_response = TestClient(app).post(
        f"/v1/strategies/{identity}/priorities/{identity}/resource-demands",
        json={},
    )
    block_response = TestClient(app).post(f"/v1/strategies/{identity}/blocks", json={})
    environment_revision_response = TestClient(app).post(
        f"/v1/weekly-plans/{identity}/environment-prescription-revisions",
        json={},
    )

    assert demand_response.status_code == 404
    assert block_response.status_code == 404
    assert environment_revision_response.status_code == 404


def build_and_persist_weekly_chain(
    session: Session,
    *,
    availability_window_count: int = 2,
    allow_partial_reresolution: bool = True,
) -> tuple[
    DomainRepository,
    LongRangeStrategy,
    StimulusRequirement,
    ExerciseResolution,
    AdaptationResourceDemand,
    ResourceAllocationPolicy,
    BlockPlan,
    SessionPrescription,
    SessionTemplate,
    WeeklyAvailability,
    WeeklySchedulingPolicy,
    WeeklyPlan,
]:
    (
        repository,
        strategy,
        requirement,
        resolution,
        _,
        environment,
        _,
        exercise,
    ) = build_and_persist_resolution_chain(session)
    priority = strategy.priorities[0]
    demand = AdaptationResourceDemand(
        long_range_strategy_id=strategy.id,
        adaptation_priority_id=priority.id,
        adaptation_id=priority.adaptation_id,
        priority_state=priority.state,
        stimulus_requirement_id=requirement.id,
        exercise_resolution_id=resolution.id,
        minimum_weekly_minutes=60,
        target_weekly_minutes=60,
        sessions_per_week=2,
        source_observation_ids=strategy.source_observation_ids,
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic resource persistence fixture.",
        demand_version="fixture@1.0.0",
    )
    allocation_policy = ResourceAllocationPolicy(
        develop_weight=1,
        maintain_weight=1,
        expose_weight=1,
        allow_partial_exercise_resolution=True,
        policy_version="fixture@1.0.0",
    )
    block = BlockPlanner().build(
        strategy=strategy,
        demands=(demand,),
        resolutions=(resolution,),
        policy=allocation_policy,
        weekly_budget_minutes=60,
        starts_on=date(2026, 8, 24),
        duration_weeks=4,
        constraints=("Synthetic fixture constraint",),
        generated_at=NOW,
    )
    assert block.status is BlockPlanStatus.PARTIAL
    allocation = block.allocations[0]
    assert resolution.selected_exercise_id == exercise.id
    prescription = SessionPrescription(
        athlete_id=strategy.athlete_id,
        block_plan_id=block.id,
        resource_allocation_id=allocation.id,
        exercise_resolution_id=resolution.id,
        exercise_id=exercise.id,
        adaptation_id=priority.adaptation_id,
        reason_for_inclusion="Synthetic persistence prescription.",
        sets=3,
        repetitions_per_set=5,
        intensity_targets=(EffortRpeTarget(minimum=6, maximum=8),),
        rest_seconds=120,
        progression_rule_reference="fixture:no-automatic-progression@1.0.0",
        substitution_class="fixture_resolution_candidates",
        planned_duration_minutes=30,
        fatigue_cost=CostLevel.MODERATE,
        source_observation_ids=strategy.source_observation_ids,
        evidence_claim_ids=strategy.evidence_claim_ids,
        prescribed_at=NOW,
        rule_version="fixture@1.0.0",
    )
    session_template = SessionTemplate(
        athlete_id=strategy.athlete_id,
        block_plan_id=block.id,
        name="Synthetic persisted training session",
        items=(
            SessionTemplateItem(
                prescription_id=prescription.id,
                order_index=1,
                section=SessionSection.PRIMARY,
            ),
        ),
        sessions_per_week=allocation.sessions_per_week,
        planned_duration_minutes=prescription.planned_duration_minutes,
        fatigue_cost=prescription.fatigue_cost,
        source_observation_ids=strategy.source_observation_ids,
        evidence_claim_ids=strategy.evidence_claim_ids,
        created_for_block_at=NOW,
        rule_version="fixture@1.0.0",
    )
    weekly_availability = WeeklyAvailability(
        athlete_id=strategy.athlete_id,
        week_start=block.starts_on,
        windows=(
            AvailabilityWindow(
                environment_id=environment.id,
                starts_at=datetime(2026, 8, 24, 18, 0, tzinfo=UTC),
                ends_at=datetime(2026, 8, 24, 18, 30, tzinfo=UTC),
            ),
            AvailabilityWindow(
                environment_id=environment.id,
                starts_at=datetime(2026, 8, 27, 18, 0, tzinfo=UTC),
                ends_at=datetime(2026, 8, 27, 18, 30, tzinfo=UTC),
            ),
        )[:availability_window_count],
        source_observation_ids=strategy.source_observation_ids,
        recorded_at=NOW,
        rule_version="fixture@1.0.0",
    )
    scheduling_policy = WeeklySchedulingPolicy(
        minimum_high_fatigue_recovery_hours=24,
        maximum_sessions_per_day=1,
        maximum_high_fatigue_sessions_per_day=1,
        allow_partial_exercise_resolution=allow_partial_reresolution,
        policy_version="fixture@1.0.0",
    )
    scheduling_policy_review = WeeklySchedulingPolicyReview(
        weekly_scheduling_policy_id=scheduling_policy.id,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=1,
        evidence_claim_ids=strategy.evidence_claim_ids,
        reviewed_at=NOW - timedelta(minutes=1),
        reviewed_by="automated-test-reviewer",
        applicability_rationale="Reviewed only for software behavior testing.",
        uncertainty="This approval is not operational training guidance.",
        review_version="fixture-weekly-scheduling-review@1.0.0",
    )
    scheduled = WeeklyScheduler().schedule(
        block=block,
        availability=weekly_availability,
        prescriptions=(prescription,),
        session_templates=(session_template,),
        resolutions=(resolution,),
        policy=scheduling_policy,
        generated_at=NOW,
    )
    weekly_plan = scheduled.model_copy(
        update={"scheduling_policy_review_id": scheduling_policy_review.id}
    )
    expected_status = (
        WeeklyPlanStatus.FEASIBLE if availability_window_count == 2 else WeeklyPlanStatus.INFEASIBLE
    )
    assert weekly_plan.status is expected_status

    repository.add_adaptation_resource_demand(demand)
    repository.add_resource_allocation_policy(allocation_policy)
    session.flush()
    repository.add_block_plan(block)
    session.flush()
    repository.add_session_prescription(prescription)
    repository.add_session_template(session_template)
    repository.add_weekly_availability(weekly_availability)
    repository.add_weekly_scheduling_policy(scheduling_policy)
    session.flush()
    repository.add_weekly_scheduling_policy_review(scheduling_policy_review)
    session.flush()
    repository.add_weekly_plan(weekly_plan)
    session.commit()
    session.expire_all()

    return (
        repository,
        strategy,
        requirement,
        resolution,
        demand,
        allocation_policy,
        block,
        prescription,
        session_template,
        weekly_availability,
        scheduling_policy,
        weekly_plan,
    )


def test_planning_status_projects_created_and_ambiguous_first_week(session: Session) -> None:
    (
        repository,
        strategy,
        _,
        _,
        _,
        _,
        _,
        _,
        _,
        _,
        _,
        weekly_plan,
    ) = build_and_persist_weekly_chain(session)

    created = get_planning_status_projection(session, strategy.athlete_id, NOW)
    assert created.status == "first_week_created"
    assert created.first_week_readiness is not None
    assert created.first_week_readiness.first_week_plan_count == 1
    summary = created.first_week_readiness.first_week_plan
    assert summary is not None
    assert summary.weekly_plan_id == weekly_plan.id
    assert summary.status is WeeklyPlanStatus.FEASIBLE
    assert summary.prescription_count == 1
    assert summary.session_template_count == 1
    assert summary.availability_window_count == 2
    assert summary.scheduled_session_count == 2
    assert summary.scheduling_issue_count == 0

    duplicate_plan = weekly_plan.model_copy(
        update={
            "id": uuid4(),
            "sessions": tuple(
                item.model_copy(update={"id": uuid4()}) for item in weekly_plan.sessions
            ),
        }
    )
    repository.add_weekly_plan(duplicate_plan)
    session.commit()

    ambiguous = get_planning_status_projection(session, strategy.athlete_id, NOW)
    assert ambiguous.status == "first_week_selection_review_required"
    assert ambiguous.first_week_readiness is not None
    assert ambiguous.first_week_readiness.first_week_plan_count == 2
    assert ambiguous.first_week_readiness.first_week_plan is None
    assert len(ambiguous.requirements) == 1
    assert ambiguous.requirements[0].code == "unambiguous_first_week_selection_required"


def test_planning_status_preserves_infeasible_first_week(session: Session) -> None:
    (
        _,
        strategy,
        _,
        _,
        _,
        _,
        _,
        _,
        _,
        _,
        _,
        weekly_plan,
    ) = build_and_persist_weekly_chain(session, availability_window_count=1)

    projection = get_planning_status_projection(session, strategy.athlete_id, NOW)
    assert projection.status == "first_week_infeasible"
    assert projection.first_week_readiness is not None
    summary = projection.first_week_readiness.first_week_plan
    assert summary is not None
    assert summary.weekly_plan_id == weekly_plan.id
    assert summary.status is WeeklyPlanStatus.INFEASIBLE
    assert summary.prescription_count == 1
    assert summary.session_template_count == 1
    assert summary.availability_window_count == 1
    assert summary.scheduled_session_count == 1
    assert summary.scheduling_issue_count == 1


def build_and_persist_execution_for_planned_session(
    session: Session,
    repository: DomainRepository,
    *,
    athlete_id: UUID,
    weekly_plan: WeeklyPlan,
    planned_session_index: int,
    session_template: SessionTemplate,
    prescription: SessionPrescription,
    safety_policy: SessionSafetyPolicy,
    provenance: Provenance,
) -> tuple[SessionExecution, SessionAdherence]:
    planned = weekly_plan.sessions[planned_session_index]
    pre_check = SessionSafetyCheckInput(
        athlete_id=athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned.id,
        timing=SafetyGateTiming.PRE_SESSION,
        readiness=ReadinessLevel.READY,
        reported_at=planned.starts_at - timedelta(minutes=2),
        reliability=Confidence.HIGH,
        provenance=provenance,
    )
    safety_observation, safety_decision = SessionSafetyGate().evaluate(
        check=pre_check,
        weekly_plan=weekly_plan,
        planned_session=planned,
        policy=safety_policy,
        decided_at=planned.starts_at - timedelta(minutes=1),
    )
    repository.add_observation(safety_observation)
    session.flush()
    repository.add_session_safety_decision(safety_decision)
    session.flush()
    execution_input = SessionExecutionInput(
        athlete_id=athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned.id,
        pre_session_safety_decision_id=safety_decision.id,
        status=SessionExecutionStatus.COMPLETED,
        started_at=planned.starts_at,
        ended_at=planned.ends_at,
        items=(
            SessionItemExecutionInput(
                prescription_id=prescription.id,
                status=SessionExecutionStatus.COMPLETED,
                performances=tuple(
                    SetPerformance(
                        set_index=index,
                        performed=True,
                        target_completed=True,
                        actual_repetitions=prescription.repetitions_per_set,
                        effort_rpe=7,
                        technique_constraint_met=True,
                    )
                    for index in range(1, prescription.sets + 1)
                ),
                item_rpe=7,
            ),
        ),
        session_rpe=7,
        logged_at=planned.ends_at + timedelta(minutes=1),
        reliability=Confidence.HIGH,
        provenance=provenance,
    )
    performance_observation, execution = SessionExecutionRecorder().record(
        execution_input=execution_input,
        weekly_plan=weekly_plan,
        planned_session=planned,
        session_template=session_template,
        prescriptions=(prescription,),
        pre_session_decision=safety_decision,
    )
    repository.add_observation(performance_observation)
    session.flush()
    repository.add_session_execution(execution)
    session.flush()
    adherence = SessionAdherenceCalculator().calculate(
        execution=execution,
        planned_session=planned,
        prescription=prescription,
        calculated_at=execution.logged_at + timedelta(minutes=1),
    )
    repository.add_session_adherence(adherence)
    session.commit()
    return execution, adherence


def persist_remaining_weekly_plans(
    session: Session,
    repository: DomainRepository,
    *,
    strategy: LongRangeStrategy,
    block: BlockPlan,
    prescription: SessionPrescription,
    session_template: SessionTemplate,
    resolution: ExerciseResolution,
    first_availability: WeeklyAvailability,
    scheduling_policy: WeeklySchedulingPolicy,
) -> tuple[WeeklyPlan, ...]:
    plans = [repository.list_weekly_plans_for_block(block.id)[0]]
    environment_id = first_availability.windows[0].environment_id
    for block_week in range(2, block.duration_weeks + 1):
        week_start = block.starts_on + timedelta(weeks=block_week - 1)
        first_window_start = datetime.combine(week_start, datetime.min.time(), tzinfo=UTC) + (
            timedelta(hours=18)
        )
        availability = WeeklyAvailability(
            athlete_id=strategy.athlete_id,
            week_start=week_start,
            windows=(
                AvailabilityWindow(
                    environment_id=environment_id,
                    starts_at=first_window_start,
                    ends_at=first_window_start + timedelta(minutes=30),
                ),
                AvailabilityWindow(
                    environment_id=environment_id,
                    starts_at=first_window_start + timedelta(days=3),
                    ends_at=first_window_start + timedelta(days=3, minutes=30),
                ),
            ),
            source_observation_ids=strategy.source_observation_ids,
            recorded_at=NOW,
            rule_version="fixture@1.0.0",
        )
        plan = WeeklyScheduler().schedule(
            block=block,
            availability=availability,
            prescriptions=(prescription,),
            session_templates=(session_template,),
            resolutions=(resolution,),
            policy=scheduling_policy,
            generated_at=NOW,
        )
        assert plan.status is WeeklyPlanStatus.FEASIBLE
        repository.add_weekly_availability(availability)
        session.flush()
        repository.add_weekly_plan(plan)
        plans.append(plan)
    session.commit()
    return tuple(plans)


def persist_post_session_safety(
    session: Session,
    repository: DomainRepository,
    *,
    weekly_plan: WeeklyPlan,
    execution: SessionExecution,
    safety_policy: SessionSafetyPolicy,
    provenance: Provenance,
    signals: tuple[SafetySignal, ...] = (),
    reported_after_minutes: int = 2,
) -> SessionSafetyDecision:
    planned = next(item for item in weekly_plan.sessions if item.id == execution.planned_session_id)
    post_check = SessionSafetyCheckInput(
        athlete_id=execution.athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned.id,
        related_session_execution_id=execution.id,
        timing=SafetyGateTiming.POST_SESSION,
        signals=signals,
        reported_at=execution.logged_at + timedelta(minutes=reported_after_minutes),
        reliability=Confidence.HIGH,
        provenance=provenance,
    )
    observation, decision = SessionSafetyGate().evaluate(
        check=post_check,
        weekly_plan=weekly_plan,
        planned_session=planned,
        policy=safety_policy,
        decided_at=post_check.reported_at + timedelta(minutes=1),
        related_execution=execution,
    )
    repository.add_observation(observation)
    session.flush()
    repository.add_session_safety_decision(decision)
    session.commit()
    return decision


def test_current_week_projection_exposes_schedule_and_persisted_completion(
    session: Session,
) -> None:
    (
        repository,
        strategy,
        _,
        _,
        _,
        _,
        _,
        prescription,
        session_template,
        weekly_availability,
        _,
        weekly_plan,
    ) = build_and_persist_weekly_chain(session)
    provenance = Provenance(
        recorded_by="automated-test",
        source_system="pytest",
        ingestion_method="fixture",
    )
    safety_policy = SessionSafetyPolicy(
        allowed_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        limited_readiness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        unusual_soreness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        sleep_disruption_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        schedule_limitation_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic current-week safety policy.",
        policy_version="fixture-current-week-safety@1.0.0",
    )
    progression_policy = ProgressionPolicy(
        reference=prescription.progression_rule_reference,
        minimum_set_completion_ratio=1,
        minimum_dose_completion_ratio=1,
        maximum_session_rpe=8,
        require_technique_constraint=False,
        adjustment=PrescriptionAdjustment(
            dimension=ProgressionDimension.REPETITIONS,
            amount=1,
            unit="repetitions_per_set",
            description="add one repetition per set",
        ),
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic current-week progression policy.",
        policy_version="fixture-current-week-progression@1.0.0",
    )
    repository.add_session_safety_policy(safety_policy)
    repository.add_progression_policy(progression_policy)
    session.commit()

    def override_session() -> Iterator[Session]:
        yield session

    path = f"/v1/athletes/{strategy.athlete_id}/current-week"
    app.dependency_overrides[database_session_dependency] = override_session
    try:
        scheduled_response = TestClient(app).get(path, params={"on": "2026-08-25"})
        no_plan_response = TestClient(app).get(path, params={"on": "2026-08-23"})
        execution, adherence = build_and_persist_execution_for_planned_session(
            session,
            repository,
            athlete_id=strategy.athlete_id,
            weekly_plan=weekly_plan,
            planned_session_index=0,
            session_template=session_template,
            prescription=prescription,
            safety_policy=safety_policy,
            provenance=provenance,
        )
        awaiting_safety_response = TestClient(app).get(path, params={"on": "2026-08-25"})
        post_safety = persist_post_session_safety(
            session,
            repository,
            weekly_plan=weekly_plan,
            execution=execution,
            safety_policy=safety_policy,
            provenance=provenance,
        )
        completed_response = TestClient(app).get(path, params={"on": "2026-08-25"})
        progression_response = TestClient(app).post(
            f"/v1/session-executions/{execution.id}/prescriptions/{prescription.id}/progression",
            json={
                "decided_at": (post_safety.decided_at + timedelta(minutes=1)).isoformat(),
            },
        )
        progressed_response = TestClient(app).get(path, params={"on": "2026-08-25"})
        second_execution, _ = build_and_persist_execution_for_planned_session(
            session,
            repository,
            athlete_id=strategy.athlete_id,
            weekly_plan=weekly_plan,
            planned_session_index=1,
            session_template=session_template,
            prescription=prescription,
            safety_policy=safety_policy,
            provenance=provenance,
        )
        persist_post_session_safety(
            session,
            repository,
            weekly_plan=weekly_plan,
            execution=second_execution,
            safety_policy=safety_policy,
            provenance=provenance,
        )
        closed_week_response = TestClient(app).get(path, params={"on": "2026-08-25"})

        duplicate_plan = weekly_plan.model_copy(
            update={
                "id": uuid4(),
                "sessions": tuple(
                    item.model_copy(update={"id": uuid4()}) for item in weekly_plan.sessions
                ),
            }
        )
        repository.add_weekly_plan(duplicate_plan)
        session.commit()
        ambiguous_response = TestClient(app).get(path, params={"on": "2026-08-25"})
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert scheduled_response.status_code == 200
    scheduled = CurrentWeekProjection.model_validate(scheduled_response.json())
    assert scheduled.athlete_display_name == "Planning persistence athlete"
    assert scheduled.week is not None
    assert scheduled.week.week_start == weekly_plan.week_start
    assert tuple(item.status for item in scheduled.week.sessions) == (
        "scheduled",
        "scheduled",
    )
    first_prescription = scheduled.week.sessions[0].prescriptions[0]
    assert first_prescription.exercise_name == "Fixture dumbbell split squat"
    assert first_prescription.adaptation_name == "Maximum strength"
    assert first_prescription.intensity_targets == ("RPE 6-8",)
    assert first_prescription.reason_for_inclusion == prescription.reason_for_inclusion
    assert first_prescription.progression_action.status == "awaiting_execution"
    assert scheduled.week.review.status == "awaiting_sessions"
    assert scheduled.week.review.recorded_sessions == 0
    assert scheduled.week.review.scheduled_sessions == 2
    assert len(scheduled.week.availability.windows) == 2
    assert (
        scheduled.week.availability.source_observation_ids
        == weekly_availability.source_observation_ids
    )
    assert no_plan_response.status_code == 200
    assert CurrentWeekProjection.model_validate(no_plan_response.json()).week is None

    assert awaiting_safety_response.status_code == 200
    awaiting_safety = CurrentWeekProjection.model_validate(awaiting_safety_response.json())
    assert awaiting_safety.week is not None
    assert (
        awaiting_safety.week.sessions[0].prescriptions[0].progression_action.status
        == "awaiting_post_session_safety"
    )

    assert completed_response.status_code == 200
    completed = CurrentWeekProjection.model_validate(completed_response.json())
    assert completed.week is not None
    completed_session = completed.week.sessions[0]
    assert completed_session.status == "completed"
    assert completed_session.execution is not None
    assert completed_session.execution.execution_id == execution.id
    assert completed_session.execution.post_session_safety_outcomes == (post_safety.outcome,)
    assert completed_session.prescriptions[0].adherence is not None
    assert completed_session.prescriptions[0].adherence.adherence_id == adherence.id
    action = completed_session.prescriptions[0].progression_action
    assert action.status == "ready"
    assert action.progression_policy_id == progression_policy.id
    assert action.adjustment_dimension == "repetitions"
    assert completed.week.sessions[1].status == "scheduled"
    assert progression_response.status_code == 201
    assert progressed_response.status_code == 200
    progressed = CurrentWeekProjection.model_validate(progressed_response.json())
    assert progressed.week is not None
    progressed_prescription = progressed.week.sessions[0].prescriptions[0]
    assert progressed_prescription.progression is not None
    assert progressed_prescription.progression.outcome == "progress"
    assert progressed_prescription.progression_action.status == "completed"
    assert progressed_prescription.progression_action.progression_policy_id is None
    assert progressed.week.review.status == "awaiting_sessions"
    assert closed_week_response.status_code == 200
    closed_week = CurrentWeekProjection.model_validate(closed_week_response.json())
    assert closed_week.week is not None
    assert closed_week.week.review.status == "ready_to_prepare_next_week"
    assert closed_week.week.review.recorded_sessions == 2
    assert closed_week.week.review.post_session_closed == 2
    assert closed_week.week.review.resolved_progression_items == 2
    assert closed_week.week.review.progression_outcomes.progress == 1
    assert (
        closed_week.week.sessions[1].prescriptions[0].progression_action.reason
        == "this prescription already has an immutable revision descendant"
    )
    assert ambiguous_response.status_code == 409


def test_current_week_progression_action_fails_closed_for_exposure_and_ambiguity(
    session: Session,
) -> None:
    (
        repository,
        strategy,
        _,
        _,
        _,
        _,
        _,
        prescription,
        session_template,
        _,
        _,
        weekly_plan,
    ) = build_and_persist_weekly_chain(session)
    provenance = Provenance(
        recorded_by="automated-test",
        source_system="pytest",
        ingestion_method="fixture",
    )
    safety_policy = SessionSafetyPolicy(
        allowed_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        limited_readiness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        unusual_soreness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        sleep_disruption_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        schedule_limitation_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic fail-closed safety policy.",
        policy_version="fixture-fail-closed-safety@1.0.0",
    )
    exposure_policy = ProgressionPolicy(
        reference=prescription.progression_rule_reference,
        minimum_set_completion_ratio=1,
        minimum_dose_completion_ratio=1,
        maximum_session_rpe=8,
        require_technique_constraint=False,
        adjustment=PrescriptionAdjustment(
            dimension=ProgressionDimension.REPETITIONS,
            amount=1,
            unit="repetitions_per_set",
            description="add one repetition per set",
        ),
        exposure_type=ExposureType.JUMPING,
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic exposure-sensitive progression policy.",
        policy_version="fixture-exposure-sensitive@1.0.0",
    )
    repository.add_session_safety_policy(safety_policy)
    repository.add_progression_policy(exposure_policy)
    session.commit()
    execution, _ = build_and_persist_execution_for_planned_session(
        session,
        repository,
        athlete_id=strategy.athlete_id,
        weekly_plan=weekly_plan,
        planned_session_index=0,
        session_template=session_template,
        prescription=prescription,
        safety_policy=safety_policy,
        provenance=provenance,
    )
    persist_post_session_safety(
        session,
        repository,
        weekly_plan=weekly_plan,
        execution=execution,
        safety_policy=safety_policy,
        provenance=provenance,
    )
    projected = CurrentWeekProjector(session).project(strategy.athlete_id, date(2026, 8, 25))
    assert projected.week is not None
    manual_action = projected.week.sessions[0].prescriptions[0].progression_action
    assert manual_action.status == "manual_configuration_required"
    assert manual_action.progression_policy_id is None
    assert "explicit reviewed exposure target" in manual_action.reason

    duplicate = exposure_policy.model_copy(
        update={
            "id": uuid4(),
            "exposure_type": None,
            "policy_version": "fixture-ambiguous@1.0.0",
        }
    )
    repository.add_progression_policy(duplicate)
    session.commit()
    ambiguous = CurrentWeekProjector(session).project(strategy.athlete_id, date(2026, 8, 25))
    assert ambiguous.week is not None
    unavailable = ambiguous.week.sessions[0].prescriptions[0].progression_action
    assert unavailable.status == "policy_unavailable"
    assert unavailable.progression_policy_id is None
    assert "multiple progression policies" in unavailable.reason


def test_completed_block_review_requires_full_history_and_is_atomic(
    session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (
        repository,
        strategy,
        _,
        resolution,
        _,
        _,
        block,
        prescription,
        session_template,
        first_availability,
        scheduling_policy,
        _,
    ) = build_and_persist_weekly_chain(session)
    provenance = Provenance(
        recorded_by="automated-test",
        source_system="pytest",
        ingestion_method="fixture",
    )
    safety_policy = SessionSafetyPolicy(
        allowed_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        limited_readiness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        unusual_soreness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        sleep_disruption_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        schedule_limitation_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic completed-block safety policy.",
        policy_version="fixture-block-review-safety@1.0.0",
    )
    review_policy = BlockReviewPolicy(
        minimum_adherence_ratio=0.8,
        minimum_response_confidence=Confidence.LOW,
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Software fixture only.",
        policy_version="fixture-block-review@1.0.0",
    )
    repository.add_session_safety_policy(safety_policy)
    repository.add_block_review_policy(review_policy)
    baseline = repository.get_capability_estimate(strategy.source_capability_estimate_ids[0])
    assert baseline is not None
    review_time = datetime(2026, 9, 21, 14, 0, tzinfo=UTC)
    followup_observation = Observation(
        athlete_id=strategy.athlete_id,
        observed_at=review_time - timedelta(hours=1),
        observation_type="fixture_strength_test",
        measurement=110,
        unit=baseline.unit_or_scale,
        source=ObservationSource.TEST_RESULT,
        reliability=Confidence.MODERATE,
        provenance=provenance,
    )
    repository.add_observation(followup_observation)
    session.flush()
    followup = CapabilityEstimate(
        athlete_id=strategy.athlete_id,
        domain=baseline.domain,
        estimate=110,
        unit_or_scale=baseline.unit_or_scale,
        estimate_scope=baseline.estimate_scope,
        confidence=Confidence.MODERATE,
        calculation_method="fixture follow-up",
        source_observation_ids=(followup_observation.id,),
        estimated_at=review_time,
        valid_until=review_time + timedelta(days=30),
        rule_version="fixture@1.0.0",
    )
    repository.add_capability_estimate(followup)
    future_observation = followup_observation.model_copy(
        update={
            "id": uuid4(),
            "observed_at": review_time + timedelta(days=1),
        }
    )
    future_followup = followup.model_copy(
        update={
            "id": uuid4(),
            "source_observation_ids": (future_observation.id,),
            "estimated_at": review_time + timedelta(days=1),
            "valid_until": review_time + timedelta(days=31),
        }
    )
    repository.add_observation(future_observation)
    session.flush()
    repository.add_capability_estimate(future_followup)
    session.commit()

    incomplete_queue = PostBlockReviewQueueProjector(session).project(
        review_time + timedelta(minutes=1)
    )
    assert len(incomplete_queue.items) == 1
    assert incomplete_queue.items[0].block_id == block.id
    assert incomplete_queue.items[0].workflow_stage == "block_review"
    assert incomplete_queue.items[0].status == "incomplete_history"
    assert incomplete_queue.items[0].issues

    response_draft = {
        "adaptation_id": str(prescription.adaptation_id),
        "prescription_ids": [str(prescription.id)],
        "baseline_capability_estimate_id": str(baseline.id),
        "followup_capability_estimate_id": str(followup.id),
        "intervention_summary": "Synthetic completed strength prescription.",
        "measurement_uncertainty": "Software fixture; no operational claim.",
        "contextual_factors": ["synthetic fixture"],
        "comparison_direction": "higher_is_better",
        "minimum_meaningful_change": 5,
    }
    request_body = {
        "block_review_policy_id": str(review_policy.id),
        "response_drafts": [response_draft],
        "responses_calculated_at": (review_time + timedelta(minutes=1)).isoformat(),
        "reviewed_at": (review_time + timedelta(minutes=2)).isoformat(),
        "reviewed_by": "fixture block-review operator",
        "applicability_rationale": "Interpret the completed synthetic block history.",
        "uncertainty": "Software fixture only; no causal or operational claim is made.",
    }
    with pytest.raises(ValueError, match="operator review metadata"):
        CreateBlockReviewCommand.model_validate({**request_body, "reviewed_by": "   "})
    command = CreateBlockReviewCommand.model_validate(request_body)
    input_path = tmp_path / "reviewed-block-review.json"
    input_path.write_text(json.dumps(command.model_dump(mode="json")), encoding="utf-8")
    assert load_block_review_command(input_path) == command

    with pytest.raises(BlockReviewValidationError, match="exactly one persisted weekly plan"):
        PersistedBlockReviewService(session).execute(block.id, command)
    weekly_plans = persist_remaining_weekly_plans(
        session,
        repository,
        strategy=strategy,
        block=block,
        prescription=prescription,
        session_template=session_template,
        resolution=resolution,
        first_availability=first_availability,
        scheduling_policy=scheduling_policy,
    )
    executions = []
    for weekly_plan in weekly_plans:
        for session_index in range(len(weekly_plan.sessions)):
            execution, _ = build_and_persist_execution_for_planned_session(
                session,
                repository,
                athlete_id=strategy.athlete_id,
                weekly_plan=weekly_plan,
                planned_session_index=session_index,
                session_template=session_template,
                prescription=prescription,
                safety_policy=safety_policy,
                provenance=provenance,
            )
            executions.append((weekly_plan, execution))
    for weekly_plan, execution in executions[:-1]:
        persist_post_session_safety(
            session,
            repository,
            weekly_plan=weekly_plan,
            execution=execution,
            safety_policy=safety_policy,
            provenance=provenance,
        )
    with pytest.raises(BlockReviewValidationError, match="post-session safety decision"):
        PersistedBlockReviewService(session).execute(block.id, command)
    final_plan, final_execution = executions[-1]
    persist_post_session_safety(
        session,
        repository,
        weekly_plan=final_plan,
        execution=final_execution,
        safety_policy=safety_policy,
        provenance=provenance,
    )
    persist_post_session_safety(
        session,
        repository,
        weekly_plan=executions[0][0],
        execution=executions[0][1],
        safety_policy=safety_policy,
        provenance=provenance,
    )
    preparation = BlockReviewPreparationProjector(session).project(
        block.id, projected_at=review_time + timedelta(minutes=1)
    )
    assert preparation.status == "ready_for_explicit_review"
    assert preparation.issues == ()
    assert len(preparation.weekly_plans) == block.duration_weeks
    assert len(preparation.session_history) == 8
    assert preparation.prescriptions == (prescription,)
    assert baseline in preparation.baseline_estimates
    assert followup in preparation.followup_estimates
    assert future_followup not in preparation.followup_estimates
    assert review_policy in preparation.block_review_policies
    assert followup_observation in preparation.source_observations
    ready_queue = PostBlockReviewQueueProjector(session).project(review_time + timedelta(minutes=1))
    assert len(ready_queue.items) == 1
    assert ready_queue.items[0].workflow_stage == "block_review"
    assert ready_queue.items[0].status == "ready_for_explicit_review"
    assert ready_queue.items[0].issues == ()
    invalid_partition_command = CreateBlockReviewCommand.model_validate(
        {
            **request_body,
            "response_drafts": [
                {
                    **response_draft,
                    "prescription_ids": [str(prescription.id), str(uuid4())],
                }
            ],
        }
    )
    with pytest.raises(BlockReviewValidationError, match="exactly partition"):
        PersistedBlockReviewService(session).execute(block.id, invalid_partition_command)
    record_types = (TrainingResponseRecord, BlockReviewRecord, DecisionRecordRecord)
    counts_before = tuple(
        session.scalar(select(func.count()).select_from(record_type))
        for record_type in record_types
    )

    def reject_review(_repository: DomainRepository, _review: object) -> None:
        raise DomainIntegrityError("synthetic late block-review persistence failure")

    with monkeypatch.context() as patch_context:
        patch_context.setattr(DomainRepository, "add_block_review", reject_review)
        with pytest.raises(BlockReviewValidationError, match="late block-review"):
            PersistedBlockReviewService(session).execute(block.id, command)

    def reject_decision(_repository: DomainRepository, _decision: object) -> None:
        raise DomainIntegrityError("synthetic block-review decision-audit failure")

    with monkeypatch.context() as patch_context:
        patch_context.setattr(DomainRepository, "add_decision_record", reject_decision)
        with pytest.raises(BlockReviewValidationError, match="decision-audit"):
            PersistedBlockReviewService(session).execute(block.id, command)
    counts_after_failure = tuple(
        session.scalar(select(func.count()).select_from(record_type))
        for record_type in record_types
    )
    assert counts_after_failure == counts_before
    with pytest.raises(BlockReviewValidationError, match="review authority assignment"):
        PersistedBlockReviewService(session).execute(
            block.id,
            command.model_copy(update={"review_authority_assignment_id": uuid4()}),
        )

    reviewer, assignment, _, _ = set_account_role(
        session,
        issuer="urn:agas:development",
        subject="authenticated-block-reviewer",
        role=AccountRole.PLANNING_REVIEWER,
        status=AccountRoleStatus.ACTIVE,
        assigned_at=review_time - timedelta(days=1),
        rationale="Exercise authenticated completed-block review.",
    )
    authority = AuthorizedRole(
        account_id=reviewer.id,
        assignment_id=assignment.id,
        role=assignment.role,
        assigned_at=assignment.assigned_at,
    )
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        OperatorBlockReviewRequest.model_validate(request_body)
    operator_request = OperatorBlockReviewRequest.model_validate(
        {key: value for key, value in request_body.items() if key != "reviewed_by"}
    )
    result = execute_operator_block_review(session, block.id, operator_request, authority)
    with pytest.raises(BlockReviewConflictError, match="already has a completed review"):
        PersistedBlockReviewService(session).execute(block.id, command)
    assert len(result.training_responses) == 1
    assert result.training_responses[0].prescribed_item_count == 8
    assert result.training_responses[0].prescribed_item_count == len(
        result.training_responses[0].session_adherence_ids
    )
    assert result.training_responses[0].rule_version == "training-response@1.1.0"
    assert result.training_responses[0].session_execution_ids == tuple(
        execution.id for _, execution in executions
    )
    assert result.block_review.outcome is BlockReviewOutcome.SUPPORTED
    assert len(result.block_review.post_session_safety_decision_ids) == 9
    assert result.decision_record.reason.startswith(f"Reviewed by account:{reviewer.id}.")
    assert f"block_review:{result.block_review.id}" in result.decision_record.evidence
    assert f"account_role_assignment:{assignment.id}" in result.decision_record.evidence
    assert f"training_response:{result.training_responses[0].id}" in (
        result.decision_record.evidence
    )
    session.expire_all()
    assert (
        repository.get_training_response(result.training_responses[0].id)
        == (result.training_responses[0])
    )
    assert repository.get_block_review_by_block(block.id) == result.block_review
    assert session.get(DecisionRecordRecord, result.decision_record.id) is not None
    completed_preparation = BlockReviewPreparationProjector(session).project(
        block.id, projected_at=review_time + timedelta(minutes=3)
    )
    assert completed_preparation.status == "already_reviewed"
    assert completed_preparation.existing_review == result.block_review
    replanning_queue = PostBlockReviewQueueProjector(session).project(
        review_time + timedelta(minutes=3)
    )
    assert len(replanning_queue.items) == 1
    assert replanning_queue.items[0].workflow_stage == "replanning"
    assert replanning_queue.items[0].status == "ready_for_explicit_replanning"
    assert replanning_queue.items[0].block_review_id == result.block_review.id
    assert replanning_queue.items[0].review_outcome == result.block_review.outcome.value


def test_block_prescription_and_weekly_plan_round_trip_preserves_full_chain(
    session: Session,
) -> None:
    (
        repository,
        strategy,
        requirement,
        _,
        demand,
        allocation_policy,
        block,
        prescription,
        session_template,
        weekly_availability,
        scheduling_policy,
        weekly_plan,
    ) = build_and_persist_weekly_chain(session)

    assert repository.get_adaptation_resource_demand(demand.id) == demand
    assert repository.get_resource_allocation_policy(allocation_policy.id) == allocation_policy
    assert repository.get_block_plan(block.id) == block
    assert repository.get_session_prescription(prescription.id) == prescription
    assert repository.get_session_template(session_template.id) == session_template
    assert repository.get_weekly_availability(weekly_availability.id) == weekly_availability
    assert repository.get_weekly_scheduling_policy(scheduling_policy.id) == scheduling_policy
    assert repository.get_weekly_plan(weekly_plan.id) == weekly_plan
    assert weekly_plan.sessions[0].session_template_id == session_template.id
    assert block.long_range_strategy_id == strategy.id
    assert demand.stimulus_requirement_id == requirement.id

    record = session.get(WeeklyPlanRecord, weekly_plan.id)
    assert record is not None
    record.rule_version = "silently rewritten"
    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.flush()


def test_first_week_preparation_projects_exact_lineage_without_choosing_inputs(
    session: Session,
) -> None:
    (
        repository,
        _strategy,
        requirement,
        resolution,
        demand,
        _,
        block,
        prescription,
        _,
        _,
        scheduling_policy,
        weekly_plan,
    ) = build_and_persist_weekly_chain(session)

    projection = FirstWeekPreparationProjector(session).project(block.id, NOW)

    assert projection.block == block
    assert projection.existing_first_week_plans == (weekly_plan,)
    assert len(projection.allocation_inputs) == 1
    allocation_input = projection.allocation_inputs[0]
    assert allocation_input.allocation == block.allocations[0]
    assert allocation_input.resource_demand == demand
    assert allocation_input.stimulus_requirement == requirement
    assert allocation_input.exercise_resolution == resolution
    assert allocation_input.selected_exercise is not None
    assert allocation_input.selected_exercise.id == prescription.exercise_id
    assert {item.id for item in projection.environments} == {resolution.environment_id}
    policy_option = next(
        item
        for item in projection.scheduling_policy_options
        if item.policy.id == scheduling_policy.id
    )
    assert policy_option.current_review == (
        repository.get_current_weekly_scheduling_policy_review(scheduling_policy.id)
    )
    assert policy_option.is_currently_approved is True
    assert {item.id for item in projection.source_observations} == set(block.source_observation_ids)
    assert {item.id for item in projection.evidence_claims}.issuperset(block.evidence_claim_ids)
    assert PlanningReviewQueueProjector(session).project(NOW).items == ()


def test_operator_weekly_plan_service_persists_explicit_session_chain_atomically(
    session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (
        repository,
        strategy,
        _,
        resolution,
        _,
        _,
        block,
        prescription,
        _,
        weekly_availability,
        scheduling_policy,
        _,
    ) = build_and_persist_weekly_chain(session)
    allocation = block.allocations[0]
    prepared_at = NOW + timedelta(minutes=1)
    scheduling_policy_review = repository.get_current_weekly_scheduling_policy_review(
        scheduling_policy.id
    )
    assert scheduling_policy_review is not None
    template_body: dict[str, object] = {
        "name": "Explicit API session container",
        "items": [
            {
                "resource_allocation_id": str(allocation.id),
                "order_index": 1,
                "section": "primary",
            }
        ],
        "sessions_per_week": allocation.sessions_per_week,
        "planned_duration_minutes": prescription.planned_duration_minutes,
        "fatigue_cost": prescription.fatigue_cost.value,
        "source_observation_ids": [str(item) for item in strategy.source_observation_ids],
        "evidence_claim_ids": [str(item) for item in strategy.evidence_claim_ids],
        "rule_version": "fixture-api-template@1.0.0",
    }
    request_body: dict[str, object] = {
        "prescriptions": [
            {
                "resource_allocation_id": str(allocation.id),
                "reason_for_inclusion": "Explicit API prescription fixture.",
                "sets": prescription.sets,
                "repetitions_per_set": prescription.repetitions_per_set,
                "intensity_targets": [
                    item.model_dump(mode="json") for item in prescription.intensity_targets
                ],
                "rest_seconds": prescription.rest_seconds,
                "progression_rule_reference": prescription.progression_rule_reference,
                "substitution_class": prescription.substitution_class,
                "planned_duration_minutes": prescription.planned_duration_minutes,
                "fatigue_cost": prescription.fatigue_cost.value,
                "source_observation_ids": [str(item) for item in strategy.source_observation_ids],
                "evidence_claim_ids": [str(item) for item in strategy.evidence_claim_ids],
                "rule_version": "fixture-api-prescription@1.0.0",
            }
        ],
        "session_templates": [template_body],
        "availability": {
            "week_start": weekly_availability.week_start.isoformat(),
            "windows": [
                {
                    "environment_id": str(item.environment_id),
                    "starts_at": item.starts_at.isoformat(),
                    "ends_at": item.ends_at.isoformat(),
                }
                for item in weekly_availability.windows
            ],
            "source_observation_ids": [str(item) for item in strategy.source_observation_ids],
            "rule_version": "fixture-api-availability@1.0.0",
        },
        "scheduling_policy_id": str(scheduling_policy.id),
        "scheduling_policy_review_id": str(scheduling_policy_review.id),
        "prepared_at": prepared_at.isoformat(),
        "reviewed_by": "fixture weekly-plan reviewer",
        "applicability_rationale": (
            "The synthetic prescriptions, composition, and availability are explicit "
            "fixture inputs."
        ),
        "uncertainty": "Software fixture only; no operational training claim is made.",
    }
    with pytest.raises(ValueError, match="operator review metadata"):
        CreateWeeklyPlanCommand.model_validate({**request_body, "reviewed_by": "   "})
    command = CreateWeeklyPlanCommand.model_validate(request_body)
    with pytest.raises(WeeklyPlanValidationError, match="authority assignment does not exist"):
        PersistedWeeklyPlanService(session).execute(
            block.id,
            command.model_copy(
                update={
                    "reviewed_by": f"account:{uuid4()}",
                    "review_authority_assignment_id": uuid4(),
                }
            ),
        )
    input_path = tmp_path / "reviewed-weekly-plan.json"
    input_path.write_text(json.dumps(command.model_dump(mode="json")), encoding="utf-8")
    assert load_weekly_plan_command(input_path) == command
    record_types = (
        SessionPrescriptionRecord,
        SessionTemplateRecord,
        WeeklyAvailabilityRecord,
        WeeklyPlanRecord,
        DecisionRecordRecord,
    )
    counts_before = tuple(
        session.scalar(select(func.count()).select_from(record_type))
        for record_type in record_types
    )

    def reject_plan(_repository: DomainRepository, _plan: WeeklyPlan) -> None:
        raise DomainIntegrityError("synthetic late weekly-plan persistence failure")

    invalid_frequency = command.model_copy(
        update={
            "session_templates": (
                command.session_templates[0].model_copy(update={"sessions_per_week": 1}),
            )
        }
    )
    with pytest.raises(WeeklyPlanValidationError):
        PersistedWeeklyPlanService(session).execute(block.id, invalid_frequency)
    later_week = command.model_copy(
        update={
            "availability": command.availability.model_copy(
                update={"week_start": command.availability.week_start + timedelta(days=7)}
            )
        }
    )
    with pytest.raises(WeeklyPlanValidationError, match="requires block week one"):
        PersistedWeeklyPlanService(session).execute(block.id, later_week)
    other_policy = scheduling_policy.model_copy(
        update={"id": uuid4(), "policy_version": "fixture-other-policy@1.0.0"}
    )
    other_review = WeeklySchedulingPolicyReview(
        weekly_scheduling_policy_id=other_policy.id,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=1,
        evidence_claim_ids=scheduling_policy_review.evidence_claim_ids,
        reviewed_at=prepared_at - timedelta(minutes=1),
        reviewed_by="automated-test-reviewer",
        applicability_rationale="Distinct policy used to test exact review matching.",
        uncertainty="Software fixture only.",
        review_version="fixture-other-policy-review@1.0.0",
    )
    repository.add_weekly_scheduling_policy(other_policy)
    session.flush()
    repository.add_weekly_scheduling_policy_review(other_review)
    session.commit()
    with pytest.raises(WeeklyPlanValidationError, match="exact current approved"):
        PersistedWeeklyPlanService(session).execute(
            block.id,
            command.model_copy(update={"scheduling_policy_review_id": other_review.id}),
        )
    with monkeypatch.context() as context:
        context.setattr(DomainRepository, "add_weekly_plan", reject_plan)
        with pytest.raises(WeeklyPlanValidationError, match="synthetic late"):
            PersistedWeeklyPlanService(session).execute(block.id, command)
    counts_after_failures = tuple(
        session.scalar(select(func.count()).select_from(record_type))
        for record_type in record_types
    )

    assert counts_after_failures == counts_before
    result = PersistedWeeklyPlanService(session).execute(block.id, command)
    assert result.weekly_plan.status is WeeklyPlanStatus.FEASIBLE
    assert len(result.weekly_plan.sessions) == allocation.sessions_per_week
    assert result.prescriptions[0].adaptation_id == allocation.adaptation_id
    assert result.prescriptions[0].exercise_resolution_id == resolution.id
    assert result.prescriptions[0].exercise_id == resolution.selected_exercise_id
    assert result.session_templates[0].items[0].prescription_id == result.prescriptions[0].id
    assert {item.environment_id for item in result.weekly_plan.sessions} == {
        resolution.environment_id
    }
    assert result.decision_record.reason.startswith("Reviewed by fixture weekly-plan reviewer.")
    assert f"weekly_plan:{result.weekly_plan.id}" in result.decision_record.evidence
    assert f"block_plan:{block.id}" in result.decision_record.evidence
    assert f"weekly_scheduling_policy:{scheduling_policy.id}" in result.decision_record.evidence
    assert result.weekly_plan.scheduling_policy_review_id == command.scheduling_policy_review_id
    assert (
        f"weekly_scheduling_policy_review:{command.scheduling_policy_review_id}"
        in result.decision_record.evidence
    )
    assert result.decision_record.decision_version.startswith("first-week-operator-review@1.0.0;")
    session.expire_all()
    assert (
        repository.get_session_prescription(result.prescriptions[0].id) == result.prescriptions[0]
    )
    assert (
        repository.get_session_template(result.session_templates[0].id)
        == result.session_templates[0]
    )
    assert repository.get_weekly_availability(result.availability.id) == result.availability
    assert repository.get_weekly_plan(result.weekly_plan.id) == result.weekly_plan
    assert session.get(DecisionRecordRecord, result.decision_record.id) is not None

    future_review = WeeklySchedulingPolicyReview(
        weekly_scheduling_policy_id=scheduling_policy.id,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=scheduling_policy_review.sequence_number + 1,
        supersedes_review_id=scheduling_policy_review.id,
        evidence_claim_ids=scheduling_policy_review.evidence_claim_ids,
        reviewed_at=prepared_at + timedelta(minutes=1),
        reviewed_by="automated-test-reviewer",
        applicability_rationale="Future review used to test time-aware authority.",
        uncertainty="Software fixture only.",
        review_version="fixture-future-policy-review@1.0.0",
    )
    repository.add_weekly_scheduling_policy_review(future_review)
    session.commit()
    with pytest.raises(WeeklyPlanValidationError, match="exact current approved"):
        PersistedWeeklyPlanService(session).execute(
            block.id,
            command.model_copy(update={"scheduling_policy_review_id": future_review.id}),
        )
    assert repository.get_weekly_plan(result.weekly_plan.id) == result.weekly_plan


def test_athlete_api_cannot_submit_first_week_authoring_inputs(session: Session) -> None:
    _, _, _, _, _, _, block, _, _, _, _, _ = build_and_persist_weekly_chain(session)
    app.dependency_overrides[database_session_dependency] = lambda: session
    try:
        response = TestClient(app).post(f"/v1/blocks/{block.id}/weekly-plans", json={})
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code in {404, 405}


def test_scheduling_policy_withdrawal_preserves_history_and_blocks_roll_forward(
    session: Session,
) -> None:
    (
        repository,
        strategy,
        _,
        _,
        _,
        _,
        _,
        _,
        _,
        source_availability,
        scheduling_policy,
        source_plan,
    ) = build_and_persist_weekly_chain(session)
    approved_review = repository.get_current_weekly_scheduling_policy_review(scheduling_policy.id)
    assert approved_review is not None
    assert source_plan.scheduling_policy_review_id == approved_review.id

    withdrawal = record_weekly_scheduling_policy_review(
        session,
        weekly_scheduling_policy_id=scheduling_policy.id,
        decision=AssessmentReviewDecision.NEEDS_REVISION,
        evidence_claim_ids=approved_review.evidence_claim_ids,
        reviewed_at=NOW + timedelta(minutes=1),
        reviewed_by="automated-test-reviewer",
        applicability_rationale="Withdrawn only to verify governed software behavior.",
        uncertainty="Software fixture only; no operational training claim is made.",
        review_version="fixture-scheduling-withdrawal@1.0.0",
    )
    assert withdrawal.supersedes_review_id == approved_review.id
    assert repository.get_weekly_scheduling_policy_review(approved_review.id) == approved_review
    assert (
        repository.get_current_weekly_scheduling_policy_review(scheduling_policy.id) == withdrawal
    )
    assert repository.get_weekly_plan(source_plan.id) == source_plan

    confirmation_observation = Observation(
        athlete_id=strategy.athlete_id,
        observed_at=NOW + timedelta(minutes=2),
        observation_type="weekly_availability_confirmation",
        measurement={"week_start": (source_plan.week_start + timedelta(days=7)).isoformat()},
        source=ObservationSource.USER_REPORT,
        reliability=Confidence.HIGH,
        provenance=Provenance(
            recorded_by="automated-test",
            source_system="pytest",
            ingestion_method="fixture",
        ),
    )
    confirmed_availability = WeeklyAvailability(
        athlete_id=strategy.athlete_id,
        source_weekly_plan_id=source_plan.id,
        week_start=source_plan.week_start + timedelta(days=7),
        windows=tuple(
            window.model_copy(
                update={
                    "id": uuid4(),
                    "starts_at": window.starts_at + timedelta(days=7),
                    "ends_at": window.ends_at + timedelta(days=7),
                }
            )
            for window in source_availability.windows
        ),
        source_observation_ids=(confirmation_observation.id,),
        recorded_at=confirmation_observation.observed_at,
        rule_version="fixture-confirmed-availability@1.0.0",
    )
    repository.add_observation(confirmation_observation)
    session.flush()
    repository.add_weekly_availability(confirmed_availability)
    session.commit()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    try:
        response = TestClient(app).post(
            f"/v1/weekly-plans/{source_plan.id}/roll-forward",
            json={
                "weekly_availability_id": str(confirmed_availability.id),
                "prepared_at": (NOW + timedelta(minutes=3)).isoformat(),
            },
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code == 422
    assert "current approved scheduling policy review" in response.json()["detail"]
    assert repository.get_weekly_plan(source_plan.id) == source_plan
    assert repository.get_athlete(strategy.athlete_id) is not None


def test_weekly_roll_forward_carries_progression_revision_with_immutable_lineage(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    (
        repository,
        strategy,
        _,
        _,
        _,
        _,
        _,
        prescription,
        source_template,
        source_availability,
        _,
        source_plan,
    ) = build_and_persist_weekly_chain(session)
    provenance = Provenance(
        recorded_by="automated-test",
        source_system="pytest",
        ingestion_method="fixture",
    )
    safety_policy = SessionSafetyPolicy(
        allowed_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        limited_readiness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        unusual_soreness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        sleep_disruption_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        schedule_limitation_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic roll-forward safety policy.",
        policy_version="fixture-roll-forward-safety@1.0.0",
    )
    progression_policy = ProgressionPolicy(
        reference=prescription.progression_rule_reference,
        minimum_set_completion_ratio=1,
        minimum_dose_completion_ratio=1,
        maximum_session_rpe=8,
        require_technique_constraint=True,
        adjustment=PrescriptionAdjustment(
            dimension=ProgressionDimension.REPETITIONS,
            amount=1,
            unit="repetitions_per_set",
            description="add one repetition per set",
        ),
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic roll-forward progression policy.",
        policy_version="fixture-roll-forward-progression@1.0.0",
    )
    repository.add_session_safety_policy(safety_policy)
    repository.add_progression_policy(progression_policy)
    session.commit()
    execution, _ = build_and_persist_execution_for_planned_session(
        session,
        repository,
        athlete_id=strategy.athlete_id,
        weekly_plan=source_plan,
        planned_session_index=0,
        session_template=source_template,
        prescription=prescription,
        safety_policy=safety_policy,
        provenance=provenance,
    )
    post_safety = persist_post_session_safety(
        session,
        repository,
        weekly_plan=source_plan,
        execution=execution,
        safety_policy=safety_policy,
        provenance=provenance,
    )
    progression_decided_at = post_safety.decided_at + timedelta(minutes=1)
    second_execution, _ = build_and_persist_execution_for_planned_session(
        session,
        repository,
        athlete_id=strategy.athlete_id,
        weekly_plan=source_plan,
        planned_session_index=1,
        session_template=source_template,
        prescription=prescription,
        safety_policy=safety_policy,
        provenance=provenance,
    )
    second_post_safety = persist_post_session_safety(
        session,
        repository,
        weekly_plan=source_plan,
        execution=second_execution,
        safety_policy=safety_policy,
        provenance=provenance,
    )
    prepared_at = second_post_safety.decided_at + timedelta(minutes=1)
    next_week_start = source_plan.week_start + timedelta(days=7)
    environment_id = source_availability.windows[0].environment_id
    next_windows = (
        {
            "environment_id": str(environment_id),
            "starts_at": datetime(2026, 8, 31, 18, 0, tzinfo=UTC).isoformat(),
            "ends_at": datetime(2026, 8, 31, 18, 30, tzinfo=UTC).isoformat(),
        },
        {
            "environment_id": str(environment_id),
            "starts_at": datetime(2026, 9, 3, 18, 0, tzinfo=UTC).isoformat(),
            "ends_at": datetime(2026, 9, 3, 18, 30, tzinfo=UTC).isoformat(),
        },
    )
    confirmation_body: dict[str, object] = {
        "windows": list(next_windows),
        "confirmed_at": prepared_at.isoformat(),
        "reliability": "high",
        "provenance": provenance.model_dump(mode="json"),
    }

    def override_session() -> Iterator[Session]:
        yield session

    def reject_plan(_repository: DomainRepository, _plan: WeeklyPlan) -> None:
        raise DomainIntegrityError("synthetic late roll-forward persistence failure")

    app.dependency_overrides[database_session_dependency] = override_session
    progression_path = (
        f"/v1/session-executions/{execution.id}/prescriptions/{prescription.id}/progression"
    )
    confirmation_path = f"/v1/weekly-plans/{source_plan.id}/availability-confirmations"
    roll_forward_path = f"/v1/weekly-plans/{source_plan.id}/roll-forward"
    try:
        progression_response = TestClient(app).post(
            progression_path,
            json={
                "decided_at": progression_decided_at.isoformat(),
            },
        )
        progression_result = ProgressionCreationResult.model_validate(progression_response.json())
        assert progression_result.revised_prescription is not None
        revised = progression_result.revised_prescription
        client_lineage_response = TestClient(app).post(
            confirmation_path,
            json={
                **confirmation_body,
                "week_start": next_week_start.isoformat(),
                "source_observation_ids": [str(item) for item in strategy.source_observation_ids],
                "rule_version": "client-authored-version@1.0.0",
            },
        )
        confirmation_response = TestClient(app).post(
            confirmation_path,
            json=confirmation_body,
        )
        confirmation_result = WeeklyAvailabilityConfirmationResult.model_validate(
            confirmation_response.json()
        )
        duplicate_confirmation_response = TestClient(app).post(
            confirmation_path,
            json=confirmation_body,
        )
        roll_forward_body: dict[str, object] = {
            "weekly_availability_id": str(confirmation_result.availability.id),
            "prepared_at": (prepared_at + timedelta(minutes=1)).isoformat(),
        }
        record_types = (
            ObservationRecord,
            SessionPrescriptionRecord,
            SessionTemplateRecord,
            WeeklyAvailabilityRecord,
            WeeklyPlanRecord,
        )
        counts_before = tuple(
            session.scalar(select(func.count()).select_from(record_type))
            for record_type in record_types
        )
        with monkeypatch.context() as context:
            context.setattr(DomainRepository, "add_weekly_plan", reject_plan)
            late_failure_response = TestClient(app).post(roll_forward_path, json=roll_forward_body)
        counts_after_failures = tuple(
            session.scalar(select(func.count()).select_from(record_type))
            for record_type in record_types
        )
        response = TestClient(app).post(roll_forward_path, json=roll_forward_body)
        duplicate_response = TestClient(app).post(roll_forward_path, json=roll_forward_body)
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert progression_response.status_code == 201
    assert prescription.repetitions_per_set is not None
    assert revised.repetitions_per_set == prescription.repetitions_per_set + 1
    assert client_lineage_response.status_code == 422
    assert confirmation_response.status_code == 201
    assert duplicate_confirmation_response.status_code == 409
    assert late_failure_response.status_code == 422
    assert counts_after_failures == counts_before
    assert response.status_code == 201
    result = WeeklyPlanRollForwardResult.model_validate(response.json())
    assert confirmation_result.availability_observation.observation_type == (
        "weekly_availability_confirmation"
    )
    assert result.availability == confirmation_result.availability
    assert result.availability.source_weekly_plan_id == source_plan.id
    assert result.availability.source_observation_ids == (
        confirmation_result.availability_observation.id,
    )
    assert result.availability.rule_version == "weekly-availability-confirmation@1.0.0"
    assert confirmation_result.availability_observation.context == {
        "source_weekly_plan_id": str(source_plan.id),
        "source_weekly_availability_id": str(source_availability.id),
    }
    assert result.prescriptions == (revised,)
    assert len(result.created_session_templates) == 1
    successor_template = result.created_session_templates[0]
    assert successor_template.previous_template_id == source_template.id
    assert successor_template.items[0].prescription_id == revised.id
    assert result.session_templates == (successor_template,)
    assert result.weekly_plan.previous_weekly_plan_id == source_plan.id
    assert result.weekly_plan.scheduling_policy_review_id == source_plan.scheduling_policy_review_id
    assert result.weekly_plan.block_week == source_plan.block_week + 1
    assert result.weekly_plan.week_start == next_week_start
    assert {item.session_template_id for item in result.weekly_plan.sessions} == {
        successor_template.id
    }
    assert duplicate_response.status_code == 409
    session.expire_all()
    assert repository.get_session_template(source_template.id) == source_template
    assert repository.get_session_prescription(prescription.id) == prescription
    assert repository.get_session_prescription(revised.id) == revised
    assert repository.get_observation(confirmation_result.availability_observation.id) == (
        confirmation_result.availability_observation
    )
    assert repository.get_weekly_availability_by_source_plan(source_plan.id) == (
        confirmation_result.availability
    )
    assert repository.get_session_template(successor_template.id) == successor_template
    assert repository.get_weekly_plan(result.weekly_plan.id) == result.weekly_plan
    assert repository.get_weekly_plan_successor(source_plan.id) == result.weekly_plan


def test_weekly_roll_forward_reuses_unchanged_prescription_and_template(
    session: Session,
) -> None:
    (
        repository,
        strategy,
        _,
        _,
        _,
        _,
        _,
        prescription,
        source_template,
        source_availability,
        _,
        source_plan,
    ) = build_and_persist_weekly_chain(session)
    environment_id = source_availability.windows[0].environment_id
    provenance = Provenance(
        recorded_by="automated-test",
        source_system="pytest",
        ingestion_method="fixture",
    )
    safety_policy = SessionSafetyPolicy(
        allowed_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        limited_readiness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        unusual_soreness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        sleep_disruption_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        schedule_limitation_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic unchanged roll-forward safety policy.",
        policy_version="fixture-unchanged-roll-forward-safety@1.0.0",
    )
    progression_policy = ProgressionPolicy(
        reference=prescription.progression_rule_reference,
        minimum_set_completion_ratio=1,
        minimum_dose_completion_ratio=1,
        maximum_session_rpe=6,
        require_technique_constraint=True,
        adjustment=PrescriptionAdjustment(
            dimension=ProgressionDimension.REPETITIONS,
            amount=1,
            unit="repetitions_per_set",
            description="add one repetition per set",
        ),
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic policy configured to repeat the unchanged prescription.",
        policy_version="fixture-unchanged-roll-forward-progression@1.0.0",
    )
    repository.add_session_safety_policy(safety_policy)
    repository.add_progression_policy(progression_policy)
    session.commit()
    confirmed_at = datetime(2026, 8, 28, 18, 0, tzinfo=UTC)
    confirmation_body = {
        "windows": [
            {
                "environment_id": str(environment_id),
                "starts_at": datetime(2026, 8, 31, 18, 0, tzinfo=UTC).isoformat(),
                "ends_at": datetime(2026, 8, 31, 18, 30, tzinfo=UTC).isoformat(),
            },
            {
                "environment_id": str(environment_id),
                "starts_at": datetime(2026, 9, 3, 18, 0, tzinfo=UTC).isoformat(),
                "ends_at": datetime(2026, 9, 3, 18, 30, tzinfo=UTC).isoformat(),
            },
        ],
        "confirmed_at": confirmed_at.isoformat(),
        "reliability": "moderate",
        "provenance": provenance.model_dump(mode="json"),
    }

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    try:
        incomplete_response = TestClient(app).post(
            f"/v1/weekly-plans/{source_plan.id}/availability-confirmations",
            json=confirmation_body,
        )
        for session_index in range(len(source_plan.sessions)):
            execution, _ = build_and_persist_execution_for_planned_session(
                session,
                repository,
                athlete_id=strategy.athlete_id,
                weekly_plan=source_plan,
                planned_session_index=session_index,
                session_template=source_template,
                prescription=prescription,
                safety_policy=safety_policy,
                provenance=provenance,
            )
            post_safety = persist_post_session_safety(
                session,
                repository,
                weekly_plan=source_plan,
                execution=execution,
                safety_policy=safety_policy,
                provenance=provenance,
            )
            progression = PersistedProgressionService(session).execute(
                execution.id,
                prescription.id,
                CreateProgressionDecisionCommand(
                    progression_policy_id=progression_policy.id,
                    decided_at=post_safety.decided_at + timedelta(minutes=1),
                ),
            )
            assert progression.progression_decision.outcome is ProgressionOutcome.REPEAT
            assert progression.revised_prescription is None
        ready_to_confirm = CurrentWeekProjector(session).project_week(source_plan).review
        stale_confirmation_response = TestClient(app).post(
            f"/v1/weekly-plans/{source_plan.id}/availability-confirmations",
            json={
                **confirmation_body,
                "confirmed_at": (source_plan.generated_at - timedelta(minutes=1)).isoformat(),
            },
        )
        confirmation_response = TestClient(app).post(
            f"/v1/weekly-plans/{source_plan.id}/availability-confirmations",
            json=confirmation_body,
        )
        confirmation_result = WeeklyAvailabilityConfirmationResult.model_validate(
            confirmation_response.json()
        )
        closed_review = CurrentWeekProjector(session).project_week(source_plan).review
        response = TestClient(app).post(
            f"/v1/weekly-plans/{source_plan.id}/roll-forward",
            json={
                "weekly_availability_id": str(confirmation_result.availability.id),
                "prepared_at": (confirmed_at + timedelta(minutes=1)).isoformat(),
            },
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert incomplete_response.status_code == 422
    assert "awaiting_sessions" in incomplete_response.json()["detail"]
    assert ready_to_confirm.status == "ready_to_prepare_next_week"
    assert stale_confirmation_response.status_code == 422
    assert "cannot predate source-week closure" in stale_confirmation_response.json()["detail"]
    assert confirmation_response.status_code == 201
    assert closed_review.status == "ready_to_finalize_next_week"
    assert response.status_code == 201
    result = WeeklyPlanRollForwardResult.model_validate(response.json())
    assert result.prescriptions == (prescription,)
    assert result.session_templates == (source_template,)
    assert result.created_session_templates == ()
    assert {item.session_template_id for item in result.weekly_plan.sessions} == {
        source_template.id
    }
    session.expire_all()
    assert repository.get_session_template(source_template.id) == source_template
    assert repository.get_weekly_plan(result.weekly_plan.id) == result.weekly_plan


def test_reviewed_environment_revision_flows_into_next_week_without_rewriting_history(
    session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (
        repository,
        strategy,
        requirement,
        original_resolution,
        _,
        _,
        block,
        source_prescription,
        source_template,
        _,
        _,
        source_plan,
    ) = build_and_persist_weekly_chain(session, allow_partial_reresolution=False)
    source_exercise = repository.get_exercise(source_prescription.exercise_id)
    assert source_exercise is not None
    equipment_id = source_exercise.equipment_requirement_ids[0]
    equipment = repository.get_equipment(equipment_id)
    assert equipment is not None
    reviewer_account, reviewer_assignment, _, _ = set_account_role(
        session,
        issuer="urn:agas:development",
        subject="environment-reviewer",
        role=AccountRole.PLANNING_REVIEWER,
        status=AccountRoleStatus.ACTIVE,
        assigned_at=datetime(2026, 8, 28, 14, 30, tzinfo=UTC),
        rationale="Exercise authenticated environment-review writes.",
    )
    provenance = Provenance(
        recorded_by="automated-test",
        source_system="pytest",
        ingestion_method="fixture",
    )

    travel_report = Observation(
        athlete_id=strategy.athlete_id,
        observed_at=datetime(2026, 8, 28, 14, 0, tzinfo=UTC),
        observation_type="fixture_travel_equipment_report",
        measurement={"equipment_id": str(equipment.id), "is_available": True},
        source=ObservationSource.USER_REPORT,
        reliability=Confidence.HIGH,
        provenance=provenance,
    )
    travel_environment = Environment(
        athlete_id=strategy.athlete_id,
        name="Reviewed travel revision fixture",
        space_constraints={"floor_area_m2": 8},
        max_noise_level=CostLevel.MODERATE,
    )
    travel_availability = EquipmentAvailability(
        environment_id=travel_environment.id,
        equipment_id=equipment.id,
        source_observation_id=travel_report.id,
        is_available=True,
        effective_from=travel_report.observed_at,
        load_limits={"maximum_total_kg": 100},
        reason="Synthetic travel equipment report.",
    )
    full_travel_exercise = source_exercise.model_copy(
        update={
            "id": uuid4(),
            "name": "Fixture high-loadability travel split squat",
            "loadability": Loadability.HIGH,
        }
    )
    repository.add_observation(travel_report)
    repository.add_environment(travel_environment)
    repository.add_exercise(full_travel_exercise)
    session.flush()
    repository.add_equipment_availability(travel_availability)
    session.commit()

    resolver_policy = repository.get_exercise_resolver_policy(
        original_resolution.resolver_policy_id
    )
    assert resolver_policy is not None
    partial_resolution = (
        PersistedExerciseReResolutionService(session)
        .execute(
            requirement.id,
            ReResolveExerciseCommand(
                environment_id=travel_environment.id,
                exercise_candidate_ids=(source_exercise.id,),
                exercise_resolver_policy_id=resolver_policy.id,
                resolved_at=datetime(2026, 8, 28, 15, 0, tzinfo=UTC),
                reviewed_by="fixture travel resolver",
                applicability_rationale="Exercise the partial-fidelity policy guard.",
                uncertainty="Software fixture only.",
            ),
        )
        .exercise_resolution
    )
    reresolution_body = {
        "environment_id": str(travel_environment.id),
        "exercise_candidate_ids": [str(full_travel_exercise.id)],
        "exercise_resolver_policy_id": str(resolver_policy.id),
        "resolved_at": datetime(2026, 8, 28, 15, 1, tzinfo=UTC).isoformat(),
        "applicability_rationale": "Exercise the full-fidelity replacement path.",
        "uncertainty": "Software fixture only.",
    }
    with pytest.raises(
        ExerciseReResolutionValidationError,
        match="reviewed_by does not match",
    ):
        PersistedExerciseReResolutionService(session).execute(
            requirement.id,
            ReResolveExerciseCommand.model_validate(
                {
                    **reresolution_body,
                    "reviewed_by": "spoofed core caller",
                    "review_authority_assignment_id": reviewer_assignment.id,
                }
            ),
        )

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    try:
        spoofed_reresolution = TestClient(app).post(
            f"/v1/operator/stimulus-requirements/{requirement.id}/exercise-reresolutions",
            json={**reresolution_body, "reviewed_by": "spoofed reviewer"},
            headers={"Authorization": "Bearer dev.environment-reviewer"},
        )
        predating_reresolution = TestClient(app).post(
            f"/v1/operator/stimulus-requirements/{requirement.id}/exercise-reresolutions",
            json={
                **reresolution_body,
                "resolved_at": datetime(2026, 8, 28, 14, 29, tzinfo=UTC).isoformat(),
            },
            headers={"Authorization": "Bearer dev.environment-reviewer"},
        )
        reresolution_response = TestClient(app).post(
            f"/v1/operator/stimulus-requirements/{requirement.id}/exercise-reresolutions",
            json=reresolution_body,
            headers={"Authorization": "Bearer dev.environment-reviewer"},
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert spoofed_reresolution.status_code == 422
    assert predating_reresolution.status_code == 422
    assert "reviewer role assignment" in predating_reresolution.json()["detail"]
    assert reresolution_response.status_code == 201
    reresolution_result = ExerciseReResolutionResult.model_validate(reresolution_response.json())
    full_resolution = reresolution_result.exercise_resolution
    assert reresolution_result.decision_record.reason.startswith(
        f"Reviewed by account:{reviewer_account.id}."
    )
    assert f"account_role_assignment:{reviewer_assignment.id}" in (
        reresolution_result.decision_record.evidence
    )
    assert partial_resolution.status is ResolutionStatus.PARTIAL
    assert full_resolution.status is ResolutionStatus.FULL

    revision_time = datetime(2026, 8, 28, 16, 0, tzinfo=UTC)

    def revision_command(resolution_id: UUID) -> CreateEnvironmentPrescriptionRevisionsCommand:
        return CreateEnvironmentPrescriptionRevisionsCommand(
            revisions=(
                EnvironmentPrescriptionRevisionDraft(
                    source_prescription_id=source_prescription.id,
                    exercise_resolution_id=resolution_id,
                    reason_for_inclusion=(
                        "Preserve the same synthetic strength stimulus in the travel environment."
                    ),
                    sets=4,
                    repetitions_per_set=6,
                    intensity_targets=(EffortRpeTarget(minimum=6, maximum=8),),
                    rest_seconds=90,
                    progression_rule_reference=source_prescription.progression_rule_reference,
                    substitution_class="reviewed_travel_resolution",
                    planned_duration_minutes=30,
                    fatigue_cost=CostLevel.MODERATE,
                    rule_version="fixture-travel-prescription@1.0.0",
                ),
            ),
            prepared_at=revision_time,
            reviewed_by="fixture prescription reviewer",
            applicability_rationale=(
                "The reviewed resolution preserves the immutable adaptation and stimulus."
            ),
            uncertainty="Software fixture only; replacement dose is not operational guidance.",
        )

    full_command = revision_command(full_resolution.id)
    input_path = tmp_path / "reviewed-environment-prescription-revision.json"
    input_path.write_text(json.dumps(full_command.model_dump(mode="json")), encoding="utf-8")
    assert load_environment_prescription_revisions_command(input_path) == full_command
    with pytest.raises(ValueError, match="operator review metadata"):
        CreateEnvironmentPrescriptionRevisionsCommand.model_validate(
            {**full_command.model_dump(), "reviewed_by": "   "}
        )
    with pytest.raises(EnvironmentPrescriptionRevisionValidationError, match="not ready"):
        PersistedEnvironmentPrescriptionRevisionService(session).execute(
            source_plan.id,
            full_command,
        )

    safety_policy = SessionSafetyPolicy(
        allowed_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        limited_readiness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        unusual_soreness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        sleep_disruption_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        schedule_limitation_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic environment-revision safety policy.",
        policy_version="fixture-environment-revision-safety@1.0.0",
    )
    progression_policy = ProgressionPolicy(
        reference=source_prescription.progression_rule_reference,
        minimum_set_completion_ratio=1,
        minimum_dose_completion_ratio=1,
        maximum_session_rpe=6,
        require_technique_constraint=True,
        adjustment=PrescriptionAdjustment(
            dimension=ProgressionDimension.REPETITIONS,
            amount=1,
            unit="repetitions_per_set",
            description="add one repetition per set",
        ),
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic policy configured to repeat before travel.",
        policy_version="fixture-environment-revision-progression@1.0.0",
    )
    repository.add_session_safety_policy(safety_policy)
    repository.add_progression_policy(progression_policy)
    session.commit()
    for session_index in range(len(source_plan.sessions)):
        execution, _ = build_and_persist_execution_for_planned_session(
            session,
            repository,
            athlete_id=strategy.athlete_id,
            weekly_plan=source_plan,
            planned_session_index=session_index,
            session_template=source_template,
            prescription=source_prescription,
            safety_policy=safety_policy,
            provenance=provenance,
        )
        post_safety = persist_post_session_safety(
            session,
            repository,
            weekly_plan=source_plan,
            execution=execution,
            safety_policy=safety_policy,
            provenance=provenance,
        )
        progression = PersistedProgressionService(session).execute(
            execution.id,
            source_prescription.id,
            CreateProgressionDecisionCommand(
                progression_policy_id=progression_policy.id,
                decided_at=post_safety.decided_at + timedelta(minutes=1),
            ),
        )
        assert progression.progression_decision.outcome is ProgressionOutcome.REPEAT
    assert CurrentWeekProjector(session).project_week(source_plan).review.status == (
        "ready_to_prepare_next_week"
    )
    confirmation = PersistedWeeklyAvailabilityConfirmationService(session).execute(
        source_plan.id,
        ConfirmWeeklyAvailabilityCommand.model_validate(
            {
                "windows": [
                    {
                        "environment_id": travel_environment.id,
                        "starts_at": datetime(2026, 8, 31, 18, 0, tzinfo=UTC),
                        "ends_at": datetime(2026, 8, 31, 18, 30, tzinfo=UTC),
                    },
                    {
                        "environment_id": travel_environment.id,
                        "starts_at": datetime(2026, 9, 3, 18, 0, tzinfo=UTC),
                        "ends_at": datetime(2026, 9, 3, 18, 30, tzinfo=UTC),
                    },
                ],
                "confirmed_at": datetime(2026, 8, 28, 15, 30, tzinfo=UTC),
                "reliability": Confidence.HIGH,
                "provenance": provenance,
            }
        ),
    )
    confirmed_review = CurrentWeekProjector(session).project_week(source_plan).review
    assert confirmed_review.status == "environment_revision_required"
    assert confirmed_review.unresolved_environment_prescriptions == 1
    assert confirmed_review.confirmed_availability is not None
    assert (
        confirmed_review.confirmed_availability.weekly_availability_id
        == confirmation.availability.id
    )
    review_queue = EnvironmentReviewQueueProjector(session).project(
        datetime(2026, 8, 28, 15, 31, tzinfo=UTC)
    )
    assert len(review_queue.items) == 1
    queued = review_queue.items[0]
    assert queued.source_weekly_plan_id == source_plan.id
    assert queued.athlete_id == strategy.athlete_id
    assert queued.confirmed_weekly_availability_id == confirmation.availability.id
    assert {item.environment_id for item in queued.confirmed_windows} == {travel_environment.id}
    assert len(queued.unresolved_prescriptions) == 1
    queued_prescription = queued.unresolved_prescriptions[0]
    assert queued_prescription.source_prescription_id == source_prescription.id
    assert queued_prescription.effective_prescription_id == source_prescription.id
    assert queued_prescription.stimulus_requirement_id == requirement.id
    assert queued_prescription.exercise_resolution_id == original_resolution.id
    assert queued_prescription.adaptation_id == source_prescription.adaptation_id

    with pytest.raises(
        EnvironmentPrescriptionRevisionValidationError,
        match="partial exercise re-resolution is disabled",
    ):
        PersistedEnvironmentPrescriptionRevisionService(session).execute(
            source_plan.id,
            revision_command(partial_resolution.id),
        )

    decision_count = session.scalar(select(func.count()).select_from(DecisionRecordRecord))
    prescription_count = session.scalar(select(func.count()).select_from(SessionPrescriptionRecord))

    def reject_revision(_repository: DomainRepository, _prescription: object) -> None:
        raise DomainIntegrityError("synthetic environment revision persistence failure")

    with monkeypatch.context() as context:
        context.setattr(DomainRepository, "add_session_prescription", reject_revision)
        with pytest.raises(
            EnvironmentPrescriptionRevisionValidationError,
            match="synthetic environment revision",
        ):
            PersistedEnvironmentPrescriptionRevisionService(session).execute(
                source_plan.id,
                full_command,
            )
    assert session.scalar(select(func.count()).select_from(DecisionRecordRecord)) == decision_count
    assert session.scalar(select(func.count()).select_from(SessionPrescriptionRecord)) == (
        prescription_count
    )

    operator_revision_body = full_command.model_dump(
        mode="json",
        exclude={"reviewed_by", "review_authority_assignment_id"},
    )
    app.dependency_overrides[database_session_dependency] = override_session
    try:
        spoofed_revision = TestClient(app).post(
            f"/v1/operator/weekly-plans/{source_plan.id}/environment-prescription-revisions",
            json={**operator_revision_body, "reviewed_by": "spoofed reviewer"},
            headers={"Authorization": "Bearer dev.environment-reviewer"},
        )
        revision_response = TestClient(app).post(
            f"/v1/operator/weekly-plans/{source_plan.id}/environment-prescription-revisions",
            json=operator_revision_body,
            headers={"Authorization": "Bearer dev.environment-reviewer"},
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)
    assert spoofed_revision.status_code == 422
    assert revision_response.status_code == 201
    revision_result = EnvironmentPrescriptionRevisionResult.model_validate(revision_response.json())
    assert revision_result.decision_record.reason.startswith(
        f"Reviewed by account:{reviewer_account.id}."
    )
    assert f"account_role_assignment:{reviewer_assignment.id}" in (
        revision_result.decision_record.evidence
    )
    assert (
        EnvironmentReviewQueueProjector(session).project(revision_time + timedelta(seconds=1)).items
        == ()
    )
    revised = revision_result.revised_prescriptions[0]
    assert revised.supersedes_prescription_id == source_prescription.id
    assert revised.progression_decision_id is None
    assert revised.planning_decision_record_id == revision_result.decision_record.id
    assert revised.exercise_resolution_id == full_resolution.id
    assert revised.exercise_id == full_travel_exercise.id
    assert revised.adaptation_id == source_prescription.adaptation_id
    assert travel_report.id in revised.source_observation_ids
    assert revised.sets == 4
    assert revised.repetitions_per_set == 6
    assert f"weekly_plan:{source_plan.id}" in revision_result.decision_record.evidence
    assert f"exercise_resolution:{full_resolution.id}" in (revision_result.decision_record.evidence)

    revision_record = session.get(SessionPrescriptionRevisionRecord, revised.id)
    assert revision_record is not None
    assert revision_record.progression_decision_id is None
    assert revision_record.planning_decision_record_id == revision_result.decision_record.id

    next_week = PersistedWeeklyPlanRollForwardService(session).execute(
        source_plan.id,
        RollForwardWeeklyPlanCommand(
            weekly_availability_id=confirmation.availability.id,
            prepared_at=revision_time + timedelta(minutes=1),
        ),
    )
    assert next_week.prescriptions == (revised,)
    assert len(next_week.created_session_templates) == 1
    assert next_week.created_session_templates[0].previous_template_id == source_template.id
    assert next_week.created_session_templates[0].items[0].prescription_id == revised.id
    assert next_week.weekly_plan.status is WeeklyPlanStatus.FEASIBLE
    assert {item.environment_id for item in next_week.weekly_plan.sessions} == {
        travel_environment.id
    }
    assert next_week.weekly_plan.block_plan_id == block.id
    assert block.allocations[0].stimulus_requirement_id == requirement.id

    session.expire_all()
    assert repository.get_session_prescription(source_prescription.id) == source_prescription
    assert repository.get_exercise_resolution(original_resolution.id) == original_resolution
    assert repository.get_session_prescription(revised.id) == revised
    assert repository.get_latest_session_prescription_revision(source_prescription.id) == revised


def test_session_template_lineage_rejects_unrelated_prescription(
    session: Session,
) -> None:
    (
        repository,
        _,
        _,
        _,
        _,
        _,
        _,
        prescription,
        source_template,
        _,
        _,
        _,
    ) = build_and_persist_weekly_chain(session)
    unrelated = prescription.model_copy(
        update={
            "id": uuid4(),
            "prescribed_at": prescription.prescribed_at + timedelta(minutes=1),
            "rule_version": "fixture-unrelated-prescription@1.0.0",
        }
    )
    repository.add_session_prescription(unrelated)
    session.flush()
    invalid_template = source_template.model_copy(
        update={
            "id": uuid4(),
            "items": (
                source_template.items[0].model_copy(update={"prescription_id": unrelated.id}),
            ),
            "created_for_block_at": source_template.created_for_block_at + timedelta(minutes=2),
            "rule_version": "fixture-invalid-template-lineage@1.0.0",
            "previous_template_id": source_template.id,
        }
    )

    with pytest.raises(DomainIntegrityError, match="must follow prescription lineage"):
        repository.add_session_template(invalid_template)
    session.rollback()
    assert repository.get_session_template(source_template.id) == source_template
    assert repository.get_session_prescription(unrelated.id) is None


def test_session_safety_endpoint_fails_closed_without_a_reviewed_assignment(
    session: Session,
) -> None:
    (
        repository,
        strategy,
        _,
        _,
        _,
        _,
        _,
        _,
        _,
        _,
        _,
        weekly_plan,
    ) = build_and_persist_weekly_chain(session)
    planned_session = weekly_plan.sessions[0]
    policy = SessionSafetyPolicy(
        allowed_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        limited_readiness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        unusual_soreness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        sleep_disruption_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        schedule_limitation_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic unassigned API safety policy.",
        policy_version="fixture-unassigned-safety@1.0.0",
    )
    repository.add_session_safety_policy(policy)
    session.commit()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    try:
        response = TestClient(app).post(
            f"/v1/weekly-plans/{weekly_plan.id}/sessions/{planned_session.id}/safety-checks",
            json={
                "timing": "pre_session",
                "readiness": "ready",
                "reported_at": (planned_session.starts_at - timedelta(minutes=10)).isoformat(),
                "decided_at": (planned_session.starts_at - timedelta(minutes=9)).isoformat(),
                "reliability": "moderate",
                "provenance": {
                    "recorded_by": "automated-test",
                    "source_system": "pytest",
                    "ingestion_method": "api-fixture",
                },
            },
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert response.status_code == 404
    assert response.json() == {
        "detail": "athlete does not have a reviewed safety-policy assignment"
    }


def test_session_endpoints_enforce_latest_safety_and_persist_feedback_atomically(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    (
        repository,
        strategy,
        _,
        _,
        _,
        _,
        _,
        prescription,
        _,
        _,
        _,
        weekly_plan,
    ) = build_and_persist_weekly_chain(session)
    planned_session = weekly_plan.sessions[0]
    policy = SessionSafetyPolicy(
        allowed_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        limited_readiness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        unusual_soreness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        sleep_disruption_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        schedule_limitation_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic API safety policy.",
        policy_version="fixture-api-safety@1.0.0",
    )
    repository.add_session_safety_policy(policy)
    session.flush()
    repository.add_athlete_safety_policy_assignment(
        AthleteSafetyPolicyAssignment(
            athlete_id=weekly_plan.athlete_id,
            safety_policy_id=policy.id,
            sequence_number=1,
            assigned_at=NOW,
            assigned_by="automated-test",
            applicability_rationale="Synthetic API assignment for transaction coverage.",
            rule_version="fixture-safety-assignment@1.0.0",
        )
    )
    session.commit()
    provenance = {
        "recorded_by": "automated-test",
        "source_system": "pytest",
        "ingestion_method": "api-fixture",
    }
    safety_path = f"/v1/weekly-plans/{weekly_plan.id}/sessions/{planned_session.id}/safety-checks"

    def safety_body(*, readiness: str, minute_offset: int) -> dict[str, object]:
        reported_at = planned_session.starts_at - timedelta(minutes=minute_offset)
        return {
            "timing": "pre_session",
            "readiness": readiness,
            "reported_at": reported_at.isoformat(),
            "decided_at": (reported_at + timedelta(minutes=1)).isoformat(),
            "reliability": "high",
            "provenance": provenance,
        }

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    try:
        first_safety_response = TestClient(app).post(
            safety_path, json=safety_body(readiness="ready", minute_offset=20)
        )
        hold_response = TestClient(app).post(
            safety_path, json=safety_body(readiness="not_ready", minute_offset=15)
        )
        first_safety = SessionSafetyCreationResult.model_validate(first_safety_response.json())
        assignment = repository.get_current_athlete_safety_policy_assignment(weekly_plan.athlete_id)
        assert assignment is not None
        assert first_safety.decision.safety_policy_assignment_id == assignment.id
        assert (
            repository.get_session_safety_decision(first_safety.decision.id)
            == first_safety.decision
        )
        assert hold_response.status_code == 201

        performances = [
            {
                "set_index": index,
                "performed": True,
                "target_completed": True,
                "actual_repetitions": 5,
                "load_value": 20,
                "load_unit": "kg",
                "effort_rpe": 7,
                "technique_constraint_met": True,
            }
            for index in range(1, 4)
        ]
        execution_body: dict[str, object] = {
            "pre_session_safety_decision_id": str(first_safety.decision.id),
            "status": "completed",
            "started_at": planned_session.starts_at.isoformat(),
            "ended_at": planned_session.ends_at.isoformat(),
            "items": [
                {
                    "prescription_id": str(prescription.id),
                    "status": "completed",
                    "performances": performances,
                    "item_rpe": 7,
                }
            ],
            "session_rpe": 7,
            "logged_at": (planned_session.ends_at + timedelta(minutes=2)).isoformat(),
            "adherence_calculated_at": (planned_session.ends_at + timedelta(minutes=3)).isoformat(),
            "reliability": "high",
            "provenance": provenance,
        }
        execution_path = (
            f"/v1/weekly-plans/{weekly_plan.id}/sessions/{planned_session.id}/executions"
        )
        stale_decision_response = TestClient(app).post(execution_path, json=execution_body)

        final_safety_response = TestClient(app).post(
            safety_path, json=safety_body(readiness="ready", minute_offset=10)
        )
        final_safety = SessionSafetyCreationResult.model_validate(final_safety_response.json())
        execution_body["pre_session_safety_decision_id"] = str(final_safety.decision.id)
        late_authorization_response = TestClient(app).post(
            execution_path,
            json={
                **execution_body,
                "started_at": (final_safety.decision.decided_at - timedelta(minutes=1)).isoformat(),
            },
        )

        record_types = (ObservationRecord, SessionExecutionRecord, SessionAdherenceRecord)
        counts_before_failure = tuple(
            session.scalar(select(func.count()).select_from(record_type))
            for record_type in record_types
        )

        def reject_adherence(_repository: DomainRepository, _adherence: object) -> None:
            raise DomainIntegrityError("synthetic late adherence failure")

        with monkeypatch.context() as context:
            context.setattr(DomainRepository, "add_session_adherence", reject_adherence)
            late_failure_response = TestClient(app).post(execution_path, json=execution_body)
        counts_after_failure = tuple(
            session.scalar(select(func.count()).select_from(record_type))
            for record_type in record_types
        )
        execution_response = TestClient(app).post(execution_path, json=execution_body)
        execution_result = SessionExecutionCreationResult.model_validate(execution_response.json())
        post_safety_response = TestClient(app).post(
            safety_path,
            json={
                "timing": "post_session",
                "related_session_execution_id": str(execution_result.execution.id),
                "signals": [
                    {
                        "tag": "fixture_preclassified_escalation",
                        "classification": "escalate",
                    }
                ],
                "reported_at": (
                    execution_result.execution.logged_at + timedelta(minutes=1)
                ).isoformat(),
                "decided_at": (
                    execution_result.execution.logged_at + timedelta(minutes=2)
                ).isoformat(),
                "reliability": "high",
                "provenance": provenance,
            },
        )
        duplicate_response = TestClient(app).post(execution_path, json=execution_body)
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert first_safety_response.status_code == 201
    assert first_safety.decision.outcome is SafetyGateOutcome.PROCEED
    assert stale_decision_response.status_code == 409
    assert final_safety_response.status_code == 201
    assert late_authorization_response.status_code == 422
    assert counts_after_failure == counts_before_failure
    assert late_failure_response.status_code == 422
    assert execution_response.status_code == 201
    result = execution_result
    assert result.observation.source is ObservationSource.WORKOUT_RESULT
    assert result.execution.performance_observation_id == result.observation.id
    assert result.execution.pre_session_safety_decision_id == final_safety.decision.id
    assert len(result.adherence) == 1
    assert result.adherence[0].kind == "derived"
    assert result.adherence[0].source_observation_ids == (result.observation.id,)
    assert repository.get_session_execution(result.execution.id) == result.execution
    assert (
        repository.get_session_execution_by_planned_session(planned_session.id) == result.execution
    )
    assert repository.get_session_adherence(result.adherence[0].id) == result.adherence[0]
    assert post_safety_response.status_code == 201
    post_safety = SessionSafetyCreationResult.model_validate(post_safety_response.json())
    assert post_safety.decision.outcome is SafetyGateOutcome.STOP_AND_ESCALATE
    assert post_safety.decision.related_session_execution_id == result.execution.id
    assert duplicate_response.status_code == 409
    assert session.scalar(select(func.count()).select_from(SessionSafetyDecisionRecord)) == 4


def test_progression_service_applies_governed_exposure_and_revision_atomically(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    (
        repository,
        strategy,
        _,
        _,
        _,
        _,
        _,
        prescription,
        session_template,
        _,
        _,
        weekly_plan,
    ) = build_and_persist_weekly_chain(session)
    claim_ids = strategy.evidence_claim_ids
    safety_policy = SessionSafetyPolicy(
        allowed_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        limited_readiness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        unusual_soreness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        sleep_disruption_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        schedule_limitation_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        evidence_claim_ids=claim_ids,
        rationale="Synthetic progression API safety policy.",
        policy_version="fixture-progression-api-safety@1.0.0",
    )
    exposure_definition = ExposureDefinition(
        exercise_id=prescription.exercise_id,
        exposure_type=ExposureType.JUMPING,
        dose_unit="repetitions",
        evidence_claim_ids=claim_ids,
        rationale="Synthetic exposure classification.",
        definition_version="fixture-progression-api@1.0.0",
    )
    exposure_policy = ExposureProgressionPolicy(
        exposure_type=ExposureType.JUMPING,
        dose_unit="repetitions",
        lookback_days=14,
        minimum_recent_entries=1,
        maximum_initial_dose=10,
        maximum_relative_increase=0.2,
        maximum_absolute_increase=5,
        evidence_claim_ids=claim_ids,
        rationale="Synthetic exposure cap.",
        policy_version="fixture-progression-api@1.0.0",
    )
    progression_policy = ProgressionPolicy(
        reference=prescription.progression_rule_reference,
        minimum_set_completion_ratio=1,
        minimum_dose_completion_ratio=1,
        maximum_session_rpe=8,
        adjustment=PrescriptionAdjustment(
            dimension=ProgressionDimension.REPETITIONS,
            amount=1,
            unit="repetitions_per_set",
            description="add one repetition per set",
        ),
        exposure_type=ExposureType.JUMPING,
        evidence_claim_ids=claim_ids,
        rationale="Synthetic progression threshold.",
        policy_version="fixture-progression-api@1.0.0",
    )
    non_exposure_policy = progression_policy.model_copy(
        update={"id": uuid4(), "exposure_type": None, "policy_version": "fixture-no-exposure@1.0.0"}
    )
    repository.add_session_safety_policy(safety_policy)
    repository.add_exposure_definition(exposure_definition)
    repository.add_exposure_progression_policy(exposure_policy)
    repository.add_progression_policy(progression_policy)
    session.commit()
    provenance = Provenance(
        recorded_by="automated-test",
        source_system="pytest",
        ingestion_method="progression-api-fixture",
    )
    execution, _ = build_and_persist_execution_for_planned_session(
        session,
        repository,
        athlete_id=strategy.athlete_id,
        weekly_plan=weekly_plan,
        planned_session_index=0,
        session_template=session_template,
        prescription=prescription,
        safety_policy=safety_policy,
        provenance=provenance,
    )
    path = f"/v1/session-executions/{execution.id}/prescriptions/{prescription.id}/progression"
    target_time = execution.logged_at + timedelta(minutes=5)
    request_body = {
        "progression_policy_id": str(progression_policy.id),
        "exposure": {
            "exposure_definition_id": str(exposure_definition.id),
            "exposure_progression_policy_id": str(exposure_policy.id),
            "proposed_dose": 16,
            "proposed_for": target_time.isoformat(),
        },
        "decided_at": target_time.isoformat(),
        "revision_prescribed_at": (target_time + timedelta(minutes=1)).isoformat(),
    }
    command = CreateProgressionDecisionCommand.model_validate(request_body)

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    try:
        athlete_policy_choice_response = TestClient(app).post(path, json=request_body)
        with pytest.raises(ProgressionValidationError, match="post-session safety"):
            PersistedProgressionService(session).execute(execution.id, prescription.id, command)
        post_decision = persist_post_session_safety(
            session,
            repository,
            weekly_plan=weekly_plan,
            execution=execution,
            safety_policy=safety_policy,
            provenance=provenance,
        )
        automatic_exposure_response = TestClient(app).post(
            path,
            json={"decided_at": target_time.isoformat()},
        )
        repository.add_progression_policy(non_exposure_policy)
        session.commit()
        ambiguous_policy_response = TestClient(app).post(
            path,
            json={"decided_at": target_time.isoformat()},
        )
        record_types = (
            ExposureEntryRecord,
            ExposureValidationDecisionRecord,
            ProgressionDecisionRecord,
            SessionPrescriptionRecord,
        )
        counts_before_failure = tuple(
            session.scalar(select(func.count()).select_from(record_type))
            for record_type in record_types
        )

        def reject_revision(
            _repository: DomainRepository, _prescription: SessionPrescription
        ) -> None:
            raise DomainIntegrityError("synthetic late prescription revision failure")

        with monkeypatch.context() as patch_context:
            patch_context.setattr(DomainRepository, "add_session_prescription", reject_revision)
            with pytest.raises(ProgressionValidationError, match="late prescription revision"):
                PersistedProgressionService(session).execute(execution.id, prescription.id, command)
        counts_after_failure = tuple(
            session.scalar(select(func.count()).select_from(record_type))
            for record_type in record_types
        )
        result = PersistedProgressionService(session).execute(
            execution.id, prescription.id, command
        )
        with pytest.raises(ProgressionConflictError, match="already have a progression"):
            PersistedProgressionService(session).execute(execution.id, prescription.id, command)

        second_execution, _ = build_and_persist_execution_for_planned_session(
            session,
            repository,
            athlete_id=strategy.athlete_id,
            weekly_plan=weekly_plan,
            planned_session_index=1,
            session_template=session_template,
            prescription=prescription,
            safety_policy=safety_policy,
            provenance=provenance,
        )
        second_proceed = persist_post_session_safety(
            session,
            repository,
            weekly_plan=weekly_plan,
            execution=second_execution,
            safety_policy=safety_policy,
            provenance=provenance,
        )
        escalation = persist_post_session_safety(
            session,
            repository,
            weekly_plan=weekly_plan,
            execution=second_execution,
            safety_policy=safety_policy,
            provenance=provenance,
            signals=(
                SafetySignal(
                    tag="fixture_preclassified_escalation",
                    classification=SafetySignalClass.ESCALATE,
                ),
            ),
            reported_after_minutes=4,
        )
        review_command = CreateProgressionDecisionCommand.model_validate(
            {
                "progression_policy_id": str(non_exposure_policy.id),
                "decided_at": (escalation.decided_at + timedelta(minutes=1)).isoformat(),
            }
        )
        review_result = PersistedProgressionService(session).execute(
            second_execution.id,
            prescription.id,
            review_command,
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert athlete_policy_choice_response.status_code == 422
    assert automatic_exposure_response.status_code == 422
    assert automatic_exposure_response.json() == {
        "detail": "exposure-sensitive progression requires governed configuration"
    }
    assert ambiguous_policy_response.status_code == 422
    assert ambiguous_policy_response.json() == {
        "detail": "multiple progression policies match the prescription rule reference"
    }
    assert post_decision.outcome is SafetyGateOutcome.PROCEED
    assert counts_after_failure == counts_before_failure
    assert result.exposure_entry is not None
    assert result.exposure_entry.dose_value == 15
    assert result.exposure_validation is not None
    assert result.exposure_validation.outcome.value == "approved"
    assert result.progression_decision.outcome.value == "progress"
    assert result.progression_decision.post_session_safety_decision_ids == (post_decision.id,)
    assert result.revised_prescription is not None
    assert result.revised_prescription.repetitions_per_set == 6
    assert result.revised_prescription.supersedes_prescription_id == prescription.id
    assert result.revised_prescription.progression_decision_id == result.progression_decision.id
    session.expire_all()
    assert repository.get_exposure_entry(result.exposure_entry.id) == result.exposure_entry
    assert (
        repository.get_exposure_validation_decision(result.exposure_validation.id)
        == result.exposure_validation
    )
    assert (
        repository.get_progression_decision(result.progression_decision.id)
        == result.progression_decision
    )
    assert (
        repository.get_session_prescription(result.revised_prescription.id)
        == result.revised_prescription
    )
    assert review_result.progression_decision.outcome.value == "review_required"
    assert review_result.revised_prescription is None
    assert review_result.progression_decision.post_session_safety_decision_ids == (
        second_proceed.id,
        escalation.id,
    )


def test_safety_execution_and_adherence_round_trip_preserves_provenance(
    session: Session,
) -> None:
    (
        repository,
        strategy,
        _,
        _,
        _,
        _,
        _,
        prescription,
        session_template,
        _,
        _,
        weekly_plan,
    ) = build_and_persist_weekly_chain(session)
    planned_session = weekly_plan.sessions[0]
    policy = SessionSafetyPolicy(
        allowed_modifications=(
            PrescriptionModification.REDUCE_VOLUME,
            PrescriptionModification.REDUCE_INTENSITY,
            PrescriptionModification.SHORTEN_SESSION,
        ),
        limited_readiness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        unusual_soreness_modifications=(PrescriptionModification.REDUCE_INTENSITY,),
        sleep_disruption_modifications=(PrescriptionModification.REDUCE_INTENSITY,),
        schedule_limitation_modifications=(PrescriptionModification.SHORTEN_SESSION,),
        evidence_claim_ids=strategy.evidence_claim_ids,
        rationale="Synthetic deterministic safety-gate persistence fixture.",
        policy_version="fixture-safety@1.0.0",
    )
    provenance = Provenance(
        recorded_by="automated-test",
        source_system="pytest",
        ingestion_method="fixture",
    )
    pre_check = SessionSafetyCheckInput(
        athlete_id=strategy.athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned_session.id,
        timing=SafetyGateTiming.PRE_SESSION,
        readiness=ReadinessLevel.READY,
        reported_at=planned_session.starts_at - timedelta(minutes=15),
        reliability=Confidence.HIGH,
        provenance=provenance,
    )
    pre_observation, pre_decision = SessionSafetyGate().evaluate(
        check=pre_check,
        weekly_plan=weekly_plan,
        planned_session=planned_session,
        policy=policy,
        decided_at=planned_session.starts_at - timedelta(minutes=10),
    )
    assert pre_decision.outcome is SafetyGateOutcome.PROCEED

    repository.add_session_safety_policy(policy)
    repository.add_observation(pre_observation)
    session.flush()
    repository.add_session_safety_decision(pre_decision)
    session.flush()

    performances = tuple(
        SetPerformance(
            set_index=set_index,
            performed=True,
            target_completed=True,
            actual_repetitions=5,
            load_value=20,
            load_unit="kg",
            effort_rpe=7,
            technique_constraint_met=True,
        )
        for set_index in range(1, 4)
    )
    execution_input = SessionExecutionInput(
        athlete_id=strategy.athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned_session.id,
        pre_session_safety_decision_id=pre_decision.id,
        status=SessionExecutionStatus.COMPLETED,
        started_at=planned_session.starts_at,
        ended_at=planned_session.ends_at,
        items=(
            SessionItemExecutionInput(
                prescription_id=prescription.id,
                status=SessionExecutionStatus.COMPLETED,
                performances=performances,
                item_rpe=7,
            ),
        ),
        session_rpe=7,
        logged_at=planned_session.ends_at + timedelta(minutes=2),
        reliability=Confidence.HIGH,
        provenance=provenance,
    )
    performance_observation, execution = SessionExecutionRecorder().record(
        execution_input=execution_input,
        weekly_plan=weekly_plan,
        planned_session=planned_session,
        session_template=session_template,
        prescriptions=(prescription,),
        pre_session_decision=pre_decision,
    )
    repository.add_observation(performance_observation)
    session.flush()
    repository.add_session_execution(execution)
    session.flush()

    adherence = SessionAdherenceCalculator().calculate(
        execution=execution,
        planned_session=planned_session,
        prescription=prescription,
        calculated_at=execution.logged_at + timedelta(minutes=1),
    )
    repository.add_session_adherence(adherence)
    session.flush()

    post_check = SessionSafetyCheckInput(
        athlete_id=strategy.athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned_session.id,
        related_session_execution_id=execution.id,
        timing=SafetyGateTiming.POST_SESSION,
        signals=(
            SafetySignal(
                tag="fixture_preclassified_escalation",
                classification=SafetySignalClass.ESCALATE,
            ),
        ),
        reported_at=adherence.calculated_at + timedelta(minutes=1),
        reliability=Confidence.HIGH,
        provenance=provenance,
    )
    post_observation, post_decision = SessionSafetyGate().evaluate(
        check=post_check,
        weekly_plan=weekly_plan,
        planned_session=planned_session,
        policy=policy,
        decided_at=post_check.reported_at + timedelta(minutes=1),
        related_execution=execution,
    )
    assert post_decision.outcome is SafetyGateOutcome.STOP_AND_ESCALATE
    repository.add_observation(post_observation)
    session.flush()
    repository.add_session_safety_decision(post_decision)
    session.commit()
    session.expire_all()

    assert repository.get_session_safety_policy(policy.id) == policy
    assert repository.get_session_safety_decision(pre_decision.id) == pre_decision
    assert repository.get_session_execution(execution.id) == execution
    assert repository.get_session_adherence(adherence.id) == adherence
    assert repository.get_session_safety_decision(post_decision.id) == post_decision
    assert performance_observation.source is ObservationSource.WORKOUT_RESULT
    assert adherence.kind == "derived"
    assert adherence.source_observation_ids == (performance_observation.id,)
    assert post_decision.related_session_execution_id == execution.id

    execution_record = session.get(SessionExecutionRecord, execution.id)
    assert execution_record is not None
    execution_record.status = SessionExecutionStatus.PARTIAL.value
    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.flush()
    session.rollback()

    adherence_record = session.get(SessionAdherenceRecord, adherence.id)
    assert adherence_record is not None
    adherence_record.actual_dose_total = 0
    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.flush()


def test_progression_exposure_and_revised_prescription_round_trip(
    session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (
        repository,
        strategy,
        requirement,
        resolution,
        first_demand,
        allocation_policy,
        block,
        prescription,
        session_template,
        _,
        _,
        weekly_plan,
    ) = build_and_persist_weekly_chain(session)
    planned = weekly_plan.sessions[0]
    claim_ids = strategy.evidence_claim_ids
    provenance = Provenance(
        recorded_by="automated-test", source_system="pytest", ingestion_method="fixture"
    )
    safety_policy = SessionSafetyPolicy(
        allowed_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        limited_readiness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        unusual_soreness_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        sleep_disruption_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        schedule_limitation_modifications=(PrescriptionModification.REDUCE_VOLUME,),
        evidence_claim_ids=claim_ids,
        rationale="fixture",
        policy_version="fixture@1.0.0",
    )
    check = SessionSafetyCheckInput(
        athlete_id=strategy.athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned.id,
        timing=SafetyGateTiming.PRE_SESSION,
        readiness=ReadinessLevel.READY,
        reported_at=planned.starts_at - timedelta(minutes=2),
        reliability=Confidence.HIGH,
        provenance=provenance,
    )
    safety_observation, safety_decision = SessionSafetyGate().evaluate(
        check=check,
        weekly_plan=weekly_plan,
        planned_session=planned,
        policy=safety_policy,
        decided_at=planned.starts_at - timedelta(minutes=1),
    )
    repository.add_session_safety_policy(safety_policy)
    repository.add_observation(safety_observation)
    session.flush()
    repository.add_session_safety_decision(safety_decision)
    session.flush()
    execution_input = SessionExecutionInput(
        athlete_id=strategy.athlete_id,
        weekly_plan_id=weekly_plan.id,
        planned_session_id=planned.id,
        pre_session_safety_decision_id=safety_decision.id,
        status=SessionExecutionStatus.COMPLETED,
        started_at=planned.starts_at,
        ended_at=planned.ends_at,
        items=(
            SessionItemExecutionInput(
                prescription_id=prescription.id,
                status=SessionExecutionStatus.COMPLETED,
                performances=tuple(
                    SetPerformance(
                        set_index=index,
                        performed=True,
                        target_completed=True,
                        actual_repetitions=5,
                        effort_rpe=7,
                        technique_constraint_met=True,
                    )
                    for index in range(1, 4)
                ),
                item_rpe=7,
            ),
        ),
        session_rpe=7,
        logged_at=planned.ends_at + timedelta(minutes=1),
        reliability=Confidence.HIGH,
        provenance=provenance,
    )
    performance_observation, execution = SessionExecutionRecorder().record(
        execution_input=execution_input,
        weekly_plan=weekly_plan,
        planned_session=planned,
        session_template=session_template,
        prescriptions=(prescription,),
        pre_session_decision=safety_decision,
    )
    repository.add_observation(performance_observation)
    session.flush()
    repository.add_session_execution(execution)
    session.flush()
    adherence = SessionAdherenceCalculator().calculate(
        execution=execution,
        planned_session=planned,
        prescription=prescription,
        calculated_at=execution.logged_at + timedelta(minutes=1),
    )
    repository.add_session_adherence(adherence)
    definition = ExposureDefinition(
        exercise_id=prescription.exercise_id,
        exposure_type=ExposureType.JUMPING,
        dose_unit="repetitions",
        evidence_claim_ids=claim_ids,
        rationale="fixture",
        definition_version="fixture@1.0.0",
    )
    repository.add_exposure_definition(definition)
    session.flush()
    entry = ExposureEntryCalculator().calculate(
        execution=execution, prescription=prescription, definition=definition
    )
    repository.add_exposure_entry(entry)
    exposure_policy = ExposureProgressionPolicy(
        exposure_type=ExposureType.JUMPING,
        dose_unit="repetitions",
        lookback_days=14,
        minimum_recent_entries=1,
        maximum_initial_dose=10,
        maximum_relative_increase=0.2,
        maximum_absolute_increase=5,
        evidence_claim_ids=claim_ids,
        rationale="fixture",
        policy_version="fixture@1.0.0",
    )
    repository.add_exposure_progression_policy(exposure_policy)
    session.flush()
    target = ExposureTarget(
        athlete_id=strategy.athlete_id,
        prescription_id=prescription.id,
        exposure_type=ExposureType.JUMPING,
        proposed_dose=16,
        dose_unit="repetitions",
        proposed_for=planned.starts_at + timedelta(days=7),
    )
    exposure_decision = ExposureProgressionValidator().validate(
        target=target, policy=exposure_policy, entries=(entry,), decided_at=target.proposed_for
    )
    repository.add_exposure_validation_decision(exposure_decision)
    progression_policy = ProgressionPolicy(
        reference=prescription.progression_rule_reference,
        minimum_set_completion_ratio=1,
        minimum_dose_completion_ratio=1,
        maximum_session_rpe=8,
        adjustment=PrescriptionAdjustment(
            dimension=ProgressionDimension.REPETITIONS,
            amount=1,
            unit="repetitions_per_set",
            description="add one repetition per set",
        ),
        exposure_type=ExposureType.JUMPING,
        evidence_claim_ids=claim_ids,
        rationale="fixture",
        policy_version="fixture@1.0.0",
    )
    repository.add_progression_policy(progression_policy)
    session.flush()
    progression = ProgressionEngine().decide(
        prescription=prescription,
        execution=execution,
        adherence=adherence,
        policy=progression_policy,
        exposure_validation=exposure_decision,
        decided_at=target.proposed_for,
    )
    repository.add_progression_decision(progression)
    session.flush()
    revised = PrescriptionProgressionApplicator().apply(
        prescription=prescription,
        decision=progression,
        policy=progression_policy,
        prescribed_at=target.proposed_for + timedelta(minutes=1),
    )
    repository.add_session_prescription(revised)
    session.commit()
    session.expire_all()

    assert repository.get_exposure_definition(definition.id) == definition
    assert repository.get_exposure_entry(entry.id) == entry
    assert repository.get_exposure_progression_policy(exposure_policy.id) == exposure_policy
    assert repository.get_exposure_validation_decision(exposure_decision.id) == exposure_decision
    assert repository.get_progression_policy(progression_policy.id) == progression_policy
    assert repository.get_progression_decision(progression.id) == progression
    assert repository.get_session_prescription(revised.id) == revised

    baseline = repository.get_capability_estimate(strategy.source_capability_estimate_ids[0])
    assert baseline is not None
    review_time = datetime(2026, 9, 21, 14, 0, tzinfo=UTC)
    followup_observation = Observation(
        athlete_id=strategy.athlete_id,
        observed_at=review_time - timedelta(hours=1),
        observation_type="fixture_strength_test",
        measurement=110,
        unit="fixture_unit",
        source=ObservationSource.TEST_RESULT,
        reliability=Confidence.MODERATE,
        provenance=provenance,
    )
    repository.add_observation(followup_observation)
    session.flush()
    followup = CapabilityEstimate(
        athlete_id=strategy.athlete_id,
        domain=baseline.domain,
        estimate=110,
        unit_or_scale=baseline.unit_or_scale,
        estimate_scope=baseline.estimate_scope,
        confidence=Confidence.MODERATE,
        calculation_method="fixture follow-up",
        source_observation_ids=(followup_observation.id,),
        estimated_at=review_time,
        valid_until=review_time + timedelta(days=30),
        rule_version="fixture@1.0.0",
    )
    repository.add_capability_estimate(followup)
    session.flush()
    response = TrainingResponseCalculator().calculate(
        block=block,
        adaptation_id=prescription.adaptation_id,
        prescriptions=(prescription,),
        executions=(execution,),
        adherences=(adherence,),
        baseline=baseline,
        followup=followup,
        intervention_summary="Synthetic completed strength prescription.",
        measurement_uncertainty="Software fixture; no operational measurement claim.",
        contextual_factors=("synthetic fixture",),
        calculated_at=review_time + timedelta(minutes=1),
    )
    review_policy = BlockReviewPolicy(
        minimum_adherence_ratio=0.8,
        minimum_response_confidence=Confidence.LOW,
        evidence_claim_ids=claim_ids,
        rationale="Software fixture only.",
        policy_version="fixture@1.0.0",
    )
    review = BlockReviewEngine().review(
        block=block,
        responses=(response,),
        targets=(
            ResponseEvaluationTarget(
                training_response_id=response.id,
                comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
                minimum_meaningful_change=5,
            ),
        ),
        safety_decisions=(),
        policy=review_policy,
        reviewed_at=review_time + timedelta(minutes=2),
    )
    assert review.outcome is BlockReviewOutcome.SUPPORTED
    low_delivery_response = response.model_copy(update={"adherence_ratio": 0.5})
    low_delivery_review = BlockReviewEngine().review(
        block=block,
        responses=(low_delivery_response,),
        targets=(
            ResponseEvaluationTarget(
                training_response_id=low_delivery_response.id,
                comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
                minimum_meaningful_change=5,
            ),
        ),
        safety_decisions=(),
        policy=review_policy,
        reviewed_at=review_time + timedelta(minutes=2),
    )
    assert low_delivery_review.outcome is BlockReviewOutcome.INCONCLUSIVE
    assert low_delivery_review.response_evaluations[0].threshold_met is None
    repository.add_training_response(response)
    repository.add_block_review_policy(review_policy)
    session.flush()
    repository.add_block_review(review)
    session.commit()
    session.expire_all()
    assert repository.get_training_response(response.id) == response
    assert repository.get_block_review_policy(review_policy.id) == review_policy
    assert repository.get_block_review(review.id) == review

    adaptation = repository.get_adaptation(prescription.adaptation_id)
    floor = repository.get_competency_floor(strategy.competency_floor_ids[0])
    assert adaptation is not None
    assert floor is not None
    context = ReplanningCandidateContext(
        adaptation_id=adaptation.id,
        competency_floor_id=floor.id,
        capability_estimate_id=followup.id,
        general_relevance=0.9,
        goal_relevance=0.8,
        prerequisite_value=0.7,
        expected_trainability=0.7,
        transfer_value=0.8,
        fatigue_cost=0.3,
        time_cost=0.3,
        interference_cost=0.2,
        evidence_claim_ids=claim_ids,
    )
    replanning_preparation = ReplanningPreparationProjector(session).project(
        review.id, projected_at=review.reviewed_at + timedelta(seconds=30)
    )
    assert replanning_preparation.status == "ready_for_explicit_replanning"
    assert replanning_preparation.issues == ()
    assert replanning_preparation.training_responses == (response,)
    assert len(replanning_preparation.adaptation_options) == 1
    assert replanning_preparation.adaptation_options[0].training_response == response
    assert replanning_preparation.adaptation_options[0].estimate_options == (followup,)
    assert floor in replanning_preparation.adaptation_options[0].compatible_competency_floors
    assert followup_observation in replanning_preparation.source_observations
    assert followup.valid_until is not None
    stale_replanning_preparation = ReplanningPreparationProjector(session).project(
        review.id, projected_at=followup.valid_until + timedelta(seconds=1)
    )
    assert stale_replanning_preparation.status == "blocked"
    assert stale_replanning_preparation.adaptation_options[0].estimate_options == ()

    request_body = {
        "candidate_contexts": [context.model_dump(mode="json")],
        "generated_at": (review.reviewed_at + timedelta(minutes=1)).isoformat(),
        "review_after_days": 42,
        "reviewed_by": "fixture replanning operator",
        "applicability_rationale": "Revise the strategy from reviewed post-block state.",
        "uncertainty": "Software fixture only; observed change does not establish causality.",
    }
    with pytest.raises(ValueError, match="operator review metadata"):
        PostBlockReplanningCommand.model_validate({**request_body, "uncertainty": "   "})
    replanning_command = PostBlockReplanningCommand.model_validate(request_body)
    replanning_input_path = tmp_path / "reviewed-replanning.json"
    replanning_input_path.write_text(
        json.dumps(replanning_command.model_dump(mode="json")),
        encoding="utf-8",
    )
    assert load_replanning_command(replanning_input_path) == replanning_command
    invalid_context = context.model_copy(update={"evidence_claim_ids": (uuid4(),)})
    invalid_command = replanning_command.model_copy(
        update={"candidate_contexts": (invalid_context,)}
    )
    replanning_record_types = (
        CapabilityNeedRecord,
        LongRangeStrategyRecord,
        DecisionRecordRecord,
    )
    counts_before_replanning = tuple(
        session.scalar(select(func.count()).select_from(record_type))
        for record_type in replanning_record_types
    )
    with pytest.raises(ReplanningValidationError, match="evidence claim"):
        PersistedReplanningService(session).execute(review.id, invalid_command)
    counts_after_invalid = tuple(
        session.scalar(select(func.count()).select_from(record_type))
        for record_type in replanning_record_types
    )
    assert counts_after_invalid == counts_before_replanning

    def reject_replanning_decision(_repository: DomainRepository, _decision: object) -> None:
        raise DomainIntegrityError("synthetic replanning decision-audit failure")

    with monkeypatch.context() as patch_context:
        patch_context.setattr(
            DomainRepository,
            "add_decision_record",
            reject_replanning_decision,
        )
        with pytest.raises(ReplanningValidationError, match="decision-audit"):
            PersistedReplanningService(session).execute(review.id, replanning_command)
    counts_after_audit_failure = tuple(
        session.scalar(select(func.count()).select_from(record_type))
        for record_type in replanning_record_types
    )
    assert counts_after_audit_failure == counts_before_replanning
    with pytest.raises(ReplanningValidationError, match="review authority assignment"):
        PersistedReplanningService(session).execute(
            review.id,
            replanning_command.model_copy(update={"review_authority_assignment_id": uuid4()}),
        )

    replanner, assignment, _, _ = set_account_role(
        session,
        issuer="urn:agas:development",
        subject="authenticated-post-block-replanner",
        role=AccountRole.PLANNING_REVIEWER,
        status=AccountRoleStatus.ACTIVE,
        assigned_at=review.reviewed_at - timedelta(days=1),
        rationale="Exercise authenticated post-block replanning.",
    )
    authority = AuthorizedRole(
        account_id=replanner.id,
        assignment_id=assignment.id,
        role=assignment.role,
        assigned_at=assignment.assigned_at,
    )
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        OperatorReplanningRequest.model_validate(request_body)
    operator_request = OperatorReplanningRequest.model_validate(
        {key: value for key, value in request_body.items() if key != "reviewed_by"}
    )
    replanning_result = execute_operator_replanning(session, review.id, operator_request, authority)
    with pytest.raises(ReplanningConflictError, match="already has a strategy revision"):
        PersistedReplanningService(session).execute(review.id, replanning_command)
    session.expire_all()
    assert (
        repository.get_long_range_strategy(replanning_result.strategy.id)
        == replanning_result.strategy
    )
    assert repository.get_long_range_strategy(strategy.id) == strategy
    assert replanning_result.decision_record.reason.startswith(
        f"Reviewed by account:{replanner.id}."
    )
    assert f"block_review:{review.id}" in replanning_result.decision_record.evidence
    assert f"account_role_assignment:{assignment.id}" in (
        replanning_result.decision_record.evidence
    )
    assert f"long_range_strategy:{replanning_result.strategy.id}" in (
        replanning_result.decision_record.evidence
    )
    assert session.get(DecisionRecordRecord, replanning_result.decision_record.id) is not None
    revised_priority = replanning_result.strategy.priorities[0]
    assert block.allocations[0].priority_state.value == "develop"
    assert revised_priority.state.value == "maintain"
    completed_replanning_preparation = ReplanningPreparationProjector(session).project(
        review.id, projected_at=replanning_command.generated_at + timedelta(minutes=1)
    )
    assert completed_replanning_preparation.status == "already_replanned"
    assert (
        completed_replanning_preparation.existing_successor_strategy == replanning_result.strategy
    )
    completed_queue = PostBlockReviewQueueProjector(session).project(
        replanning_command.generated_at + timedelta(minutes=1)
    )
    assert completed_queue.items == ()

    next_generated_at = review.reviewed_at + timedelta(minutes=3)
    next_requirement = StimulusRequirement.model_validate(
        {
            **requirement.model_dump(),
            "id": uuid4(),
            "long_range_strategy_id": replanning_result.strategy.id,
            "adaptation_priority_id": revised_priority.id,
            "priority_state": revised_priority.state,
            "source_observation_ids": replanning_result.strategy.source_observation_ids,
            "generated_at": next_generated_at,
        }
    )
    next_resolution = ExerciseResolution(
        stimulus_requirement_id=next_requirement.id,
        environment_id=resolution.environment_id,
        resolver_policy_id=resolution.resolver_policy_id,
        status=resolution.status,
        selected_exercise_id=resolution.selected_exercise_id,
        ranked_matches=tuple(
            item.model_copy(update={"id": uuid4()}) for item in resolution.ranked_matches
        ),
        unresolved_issues=resolution.unresolved_issues,
        source_availability_ids=resolution.source_availability_ids,
        rationale="Re-resolved persisted fixture stimulus for the revised strategy.",
        resolved_at=next_generated_at,
        rule_version="fixture-re-resolution@1.0.0",
    )
    next_demand = AdaptationResourceDemand(
        long_range_strategy_id=replanning_result.strategy.id,
        adaptation_priority_id=revised_priority.id,
        adaptation_id=revised_priority.adaptation_id,
        priority_state=revised_priority.state,
        stimulus_requirement_id=next_requirement.id,
        exercise_resolution_id=next_resolution.id,
        minimum_weekly_minutes=30,
        target_weekly_minutes=30,
        sessions_per_week=1,
        source_observation_ids=replanning_result.strategy.source_observation_ids,
        evidence_claim_ids=replanning_result.strategy.evidence_claim_ids,
        rationale="Synthetic maintained-capability demand for the dependent second block.",
        demand_version="fixture-next-block@1.0.0",
    )
    repository.add_stimulus_requirement(next_requirement)
    session.flush()
    repository.add_exercise_resolution(next_resolution)
    session.flush()
    repository.add_adaptation_resource_demand(next_demand)
    session.commit()

    block_request = {
        "resource_demand_ids": [str(next_demand.id)],
        "resource_allocation_policy_id": str(allocation_policy.id),
        "weekly_budget_minutes": 30,
        "starts_on": "2026-09-21",
        "duration_weeks": 4,
        "constraints": ["Synthetic dependent second-block fixture"],
        "generated_at": next_generated_at.isoformat(),
        "reviewed_by": "fixture block reviewer",
        "applicability_rationale": "Create the dependent block from the reviewed successor state.",
        "uncertainty": "Software fixture only; no operational training claim is made.",
    }
    with pytest.raises(ValueError, match="operator review metadata"):
        CreateBlockPlanCommand.model_validate({**block_request, "uncertainty": "   "})
    block_command = CreateBlockPlanCommand.model_validate(block_request)
    block_input_path = tmp_path / "reviewed-block-plan.json"
    block_input_path.write_text(
        json.dumps(block_command.model_dump(mode="json")),
        encoding="utf-8",
    )
    assert load_block_plan_command(block_input_path) == block_command
    record_types = (BlockPlanRecord, DecisionRecordRecord)
    counts_before_invalid = tuple(
        session.scalar(select(func.count()).select_from(record_type))
        for record_type in record_types
    )
    with pytest.raises(BlockCreationNotFoundError, match="resource demand"):
        PersistedBlockCreationService(session).execute(
            replanning_result.strategy.id,
            block_command.model_copy(update={"resource_demand_ids": (uuid4(),)}),
        )
    with pytest.raises(BlockCreationValidationError, match="strategy priority"):
        PersistedBlockCreationService(session).execute(
            replanning_result.strategy.id,
            block_command.model_copy(update={"resource_demand_ids": (first_demand.id,)}),
        )

    def reject_block_decision(_repository: DomainRepository, _decision: object) -> None:
        raise DomainIntegrityError("synthetic block decision-audit failure")

    with monkeypatch.context() as patch_context:
        patch_context.setattr(DomainRepository, "add_decision_record", reject_block_decision)
        with pytest.raises(BlockCreationValidationError, match="decision-audit"):
            PersistedBlockCreationService(session).execute(
                replanning_result.strategy.id,
                block_command,
            )
    counts_after_invalid = tuple(
        session.scalar(select(func.count()).select_from(record_type))
        for record_type in record_types
    )
    assert counts_after_invalid == counts_before_invalid

    block_result = PersistedBlockCreationService(session).execute(
        replanning_result.strategy.id,
        block_command,
    )
    second_block = block_result.block_plan
    assert block_result.decision_record.reason.startswith("Reviewed by fixture block reviewer.")
    assert f"block_plan:{second_block.id}" in block_result.decision_record.evidence
    assert f"adaptation_resource_demand:{next_demand.id}" in (block_result.decision_record.evidence)
    session.expire_all()
    assert repository.get_block_plan(second_block.id) == second_block
    assert session.get(DecisionRecordRecord, block_result.decision_record.id) is not None
    assert second_block.long_range_strategy_id == replanning_result.strategy.id
    assert second_block.long_range_strategy_id != block.long_range_strategy_id
    assert second_block.allocations[0].adaptation_priority_id == revised_priority.id
    assert second_block.allocations[0].priority_state.value == "maintain"
    assert followup_observation.id in second_block.source_observation_ids

    invalid_revision = replanning_result.strategy.model_copy(
        update={"id": uuid4(), "triggering_block_review_id": uuid4()}
    )
    with pytest.raises(DomainIntegrityError, match="triggering review belongs"):
        repository.add_long_range_strategy(invalid_revision)

    response_record = session.get(TrainingResponseRecord, response.id)
    assert response_record is not None
    response_record.actual_dose_total = 0
    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.flush()
    session.rollback()

    review_record = session.get(BlockReviewRecord, review.id)
    assert review_record is not None
    review_record.outcome = BlockReviewOutcome.INCONCLUSIVE.value
    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.flush()
