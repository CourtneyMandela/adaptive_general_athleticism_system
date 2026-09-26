from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from agas_domain import (
    AbsoluteLoadTarget,
    Confidence,
    CostLevel,
    EffortRpeTarget,
    ExposureDefinition,
    ExposureNeedStatus,
    ExposureProgressionPolicy,
    ExposureTarget,
    ExposureType,
    ExposureValidationOutcome,
    Observation,
    ObservationSource,
    PrescriptionAdjustment,
    ProgressionDimension,
    ProgressionOutcome,
    ProgressionPolicy,
    Provenance,
    SafetyGateOutcome,
    SafetyGateTiming,
    SessionAdherence,
    SessionExecution,
    SessionExecutionStatus,
    SessionItemExecution,
    SessionPrescription,
    SessionSafetyDecision,
    SetPerformance,
)
from agas_planner import (
    ExposureEntryCalculator,
    ExposureNeedDeriver,
    ExposureProgressionValidator,
    PrescriptionProgressionApplicator,
    ProgressionEngine,
    ProgressionError,
)

NOW = datetime(2026, 8, 19, 14, 0, tzinfo=UTC)


def readiness_observation(answer: str | None) -> Observation:
    return Observation(
        athlete_id=uuid4(),
        observed_at=NOW,
        observation_type="assessment_readiness_self_report",
        measurement={"recent_jump_exposure": answer},
        source=ObservationSource.USER_REPORT,
        reliability=Confidence.MODERATE,
        provenance=Provenance(
            recorded_by="fixture",
            source_system="pytest",
            ingestion_method="fixture",
        ),
    )


@pytest.mark.parametrize(
    ("answer", "expected"),
    (
        ("yes", ExposureNeedStatus.RECENT_EXPOSURE_CONFIRMED),
        ("no", ExposureNeedStatus.INTRODUCTORY_EXPOSURE_NEEDED),
        ("unsure", ExposureNeedStatus.UNKNOWN),
        (None, ExposureNeedStatus.UNKNOWN),
    ),
)
def test_exposure_need_is_derived_without_becoming_a_capability_score(
    answer: str | None,
    expected: ExposureNeedStatus,
) -> None:
    observation = readiness_observation(answer)
    need = ExposureNeedDeriver().derive_from_report(
        observation=observation,
        need_id=uuid4(),
        exposure_type=ExposureType.JUMPING,
        target_scope="assessment:countermovement_jump:maximal",
        response_field="recent_jump_exposure",
        lookback_days=28,
        minimum_exposure_days=2,
        authority_reference="engineering-decision:0124@1.0.0",
        valid_until=NOW + timedelta(hours=24),
    )

    assert need.kind == "derived"
    assert need.status is expected
    assert need.source_observation_ids == (observation.id,)
    assert need.minimum_exposure_days == 2
    assert need.authority_reference == "engineering-decision:0124@1.0.0"
    assert "not a measured count" in need.uncertainty


def test_exposure_need_rejects_unstructured_or_unsupported_source_answers() -> None:
    deriver = ExposureNeedDeriver()
    with pytest.raises(ProgressionError, match="structured report"):
        deriver.derive_from_report(
            observation=readiness_observation("yes").model_copy(update={"measurement": 3}),
            need_id=uuid4(),
            exposure_type=ExposureType.JUMPING,
            target_scope="assessment:countermovement_jump:maximal",
            response_field="recent_jump_exposure",
            lookback_days=28,
            minimum_exposure_days=2,
            authority_reference="engineering-decision:0124@1.0.0",
            valid_until=NOW + timedelta(hours=24),
        )
    with pytest.raises(ProgressionError, match="unsupported answer"):
        deriver.derive_from_report(
            observation=readiness_observation("sometimes"),
            need_id=uuid4(),
            exposure_type=ExposureType.JUMPING,
            target_scope="assessment:countermovement_jump:maximal",
            response_field="recent_jump_exposure",
            lookback_days=28,
            minimum_exposure_days=2,
            authority_reference="engineering-decision:0124@1.0.0",
            valid_until=NOW + timedelta(hours=24),
        )


def chain() -> tuple[SessionPrescription, SessionExecution, SessionAdherence]:
    athlete_id, plan_id, planned_id = uuid4(), uuid4(), uuid4()
    prescription = SessionPrescription(
        athlete_id=athlete_id,
        block_plan_id=uuid4(),
        resource_allocation_id=uuid4(),
        exercise_resolution_id=uuid4(),
        exercise_id=uuid4(),
        adaptation_id=uuid4(),
        reason_for_inclusion="fixture",
        sets=3,
        repetitions_per_set=5,
        intensity_targets=(
            AbsoluteLoadTarget(value=100, unit="kg"),
            EffortRpeTarget(minimum=6, maximum=8),
        ),
        rest_seconds=120,
        progression_rule_reference="fixture-progression@1.0.0",
        substitution_class="fixture",
        planned_duration_minutes=30,
        fatigue_cost=CostLevel.MODERATE,
        source_observation_ids=(uuid4(),),
        evidence_claim_ids=(uuid4(),),
        prescribed_at=NOW,
        rule_version="fixture@1.0.0",
    )
    observation_id = uuid4()
    execution = SessionExecution(
        athlete_id=athlete_id,
        weekly_plan_id=plan_id,
        planned_session_id=planned_id,
        session_template_id=uuid4(),
        pre_session_safety_decision_id=uuid4(),
        status=SessionExecutionStatus.COMPLETED,
        started_at=NOW,
        ended_at=NOW + timedelta(minutes=30),
        items=(
            SessionItemExecution(
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
        performance_observation_id=observation_id,
        logged_at=NOW + timedelta(minutes=31),
        rule_version="fixture@1.0.0",
    )
    adherence = SessionAdherence(
        athlete_id=athlete_id,
        session_execution_id=execution.id,
        planned_session_id=planned_id,
        prescription_id=prescription.id,
        prescribed_sets=3,
        performed_sets=3,
        target_completed_sets=3,
        prescribed_dose_total=15,
        actual_dose_total=15,
        dose_unit="repetitions",
        set_completion_ratio=1,
        dose_completion_ratio=1,
        source_observation_ids=(observation_id,),
        calculated_at=NOW + timedelta(minutes=32),
        calculation_method="fixture",
        rule_version="fixture@1.0.0",
    )
    return prescription, execution, adherence


def progression_policy(exposure_type: ExposureType | None = None) -> ProgressionPolicy:
    return ProgressionPolicy(
        reference="fixture-progression@1.0.0",
        minimum_set_completion_ratio=1,
        minimum_dose_completion_ratio=1,
        maximum_session_rpe=8,
        adjustment=PrescriptionAdjustment(
            dimension=ProgressionDimension.REPETITIONS,
            amount=1,
            unit="repetitions_per_set",
            description="add one repetition per set",
        ),
        exposure_type=exposure_type,
        evidence_claim_ids=(uuid4(),),
        rationale="software fixture",
        policy_version="fixture@1.0.0",
    )


def duration_chain() -> tuple[SessionPrescription, SessionExecution, SessionAdherence]:
    prescription, execution, adherence = chain()
    duration_prescription = prescription.model_copy(
        update={
            "sets": 1,
            "repetitions_per_set": None,
            "duration_seconds": 600,
            "planned_duration_minutes": 12,
        }
    )
    item = execution.items[0].model_copy(
        update={
            "prescription_id": duration_prescription.id,
            "performances": (
                execution.items[0]
                .performances[0]
                .model_copy(
                    update={
                        "actual_repetitions": None,
                        "actual_duration_seconds": 600,
                        "effort_rpe": 5,
                    }
                ),
            ),
            "item_rpe": 5,
        }
    )
    duration_execution = execution.model_copy(update={"items": (item,), "session_rpe": 5})
    duration_adherence = adherence.model_copy(
        update={
            "prescription_id": duration_prescription.id,
            "prescribed_sets": 1,
            "performed_sets": 1,
            "target_completed_sets": 1,
            "prescribed_dose_total": 600,
            "actual_dose_total": 600,
            "dose_unit": "seconds",
        }
    )
    return duration_prescription, duration_execution, duration_adherence


def test_completed_session_progresses_but_post_session_escalation_requires_review() -> None:
    prescription, execution, adherence = chain()
    policy = progression_policy()
    engine = ProgressionEngine()
    progressed = engine.decide(
        prescription=prescription,
        execution=execution,
        adherence=adherence,
        policy=policy,
        decided_at=NOW + timedelta(minutes=35),
    )
    assert progressed.outcome is ProgressionOutcome.PROGRESS
    assert progressed.adjustment == policy.adjustment

    safety_observation_id = uuid4()
    escalation = SessionSafetyDecision(
        athlete_id=execution.athlete_id,
        weekly_plan_id=execution.weekly_plan_id,
        planned_session_id=execution.planned_session_id,
        related_session_execution_id=execution.id,
        safety_policy_id=uuid4(),
        timing=SafetyGateTiming.POST_SESSION,
        outcome=SafetyGateOutcome.STOP_AND_ESCALATE,
        source_observation_ids=(safety_observation_id,),
        rationale=("fixture escalation",),
        decided_at=NOW + timedelta(minutes=33),
        rule_version="fixture@1.0.0",
    )
    reviewed = engine.decide(
        prescription=prescription,
        execution=execution,
        adherence=adherence,
        policy=policy,
        post_session_decisions=(escalation,),
        decided_at=NOW + timedelta(minutes=35),
    )
    assert reviewed.outcome is ProgressionOutcome.REVIEW_REQUIRED
    assert reviewed.adjustment is None
    assert safety_observation_id in reviewed.source_observation_ids


def test_duration_progression_advances_within_ceiling_and_holds_at_ceiling() -> None:
    prescription, execution, adherence = duration_chain()
    policy = ProgressionPolicy(
        reference=prescription.progression_rule_reference,
        minimum_set_completion_ratio=1,
        minimum_dose_completion_ratio=1,
        maximum_session_rpe=6,
        adjustment=PrescriptionAdjustment(
            dimension=ProgressionDimension.DURATION,
            amount=60,
            unit="seconds_per_set",
            description="Add one minute within the reviewed ceiling.",
        ),
        maximum_prescription_value=720,
        maximum_prescription_value_unit="seconds_per_set",
        evidence_claim_ids=(uuid4(),),
        rationale="Synthetic bounded-duration fixture.",
        policy_version="fixture-bounded-duration@1.0.0",
    )
    engine = ProgressionEngine()

    progressed = engine.decide(
        prescription=prescription,
        execution=execution,
        adherence=adherence,
        policy=policy,
        decided_at=NOW + timedelta(minutes=35),
    )
    revised = PrescriptionProgressionApplicator().apply(
        prescription=prescription,
        decision=progressed,
        policy=policy,
        prescribed_at=NOW + timedelta(days=1),
        planned_duration_minutes=12,
    )

    assert progressed.outcome is ProgressionOutcome.PROGRESS
    assert revised.duration_seconds == 660

    capped_prescription = prescription.model_copy(update={"duration_seconds": 720})
    capped_item = execution.items[0].model_copy(update={"prescription_id": capped_prescription.id})
    capped_execution = execution.model_copy(update={"items": (capped_item,)})
    capped_adherence = adherence.model_copy(update={"prescription_id": capped_prescription.id})
    held = engine.decide(
        prescription=capped_prescription,
        execution=capped_execution,
        adherence=capped_adherence,
        policy=policy,
        decided_at=NOW + timedelta(minutes=35),
    )

    assert held.outcome is ProgressionOutcome.HOLD
    assert held.adjustment is None
    assert "configured ceiling" in held.rationale[0]


def test_duration_progression_cannot_exceed_session_envelope() -> None:
    prescription, execution, adherence = duration_chain()
    policy = ProgressionPolicy(
        reference=prescription.progression_rule_reference,
        minimum_set_completion_ratio=1,
        minimum_dose_completion_ratio=1,
        maximum_session_rpe=6,
        adjustment=PrescriptionAdjustment(
            dimension=ProgressionDimension.DURATION,
            amount=180,
            unit="seconds_per_set",
            description="Synthetic oversized increase.",
        ),
        evidence_claim_ids=(uuid4(),),
        rationale="Synthetic session-envelope fixture.",
        policy_version="fixture-duration-envelope@1.0.0",
    )
    decision = ProgressionEngine().decide(
        prescription=prescription,
        execution=execution,
        adherence=adherence,
        policy=policy,
        decided_at=NOW + timedelta(minutes=35),
    )

    with pytest.raises(ProgressionError, match="planned session envelope"):
        PrescriptionProgressionApplicator().apply(
            prescription=prescription,
            decision=decision,
            policy=policy,
            prescribed_at=NOW + timedelta(days=1),
            planned_duration_minutes=12,
        )


def test_exposure_ledger_rejects_unearned_jump_and_blocks_progression() -> None:
    prescription, execution, adherence = chain()
    definition = ExposureDefinition(
        exercise_id=prescription.exercise_id,
        exposure_type=ExposureType.JUMPING,
        dose_unit="repetitions",
        evidence_claim_ids=prescription.evidence_claim_ids,
        rationale="software fixture",
        definition_version="fixture@1.0.0",
    )
    entry = ExposureEntryCalculator().calculate(
        execution=execution, prescription=prescription, definition=definition
    )
    exposure_policy = ExposureProgressionPolicy(
        exposure_type=ExposureType.JUMPING,
        dose_unit="repetitions",
        lookback_days=14,
        minimum_recent_entries=1,
        maximum_initial_dose=10,
        maximum_relative_increase=0.2,
        maximum_absolute_increase=5,
        evidence_claim_ids=prescription.evidence_claim_ids,
        rationale="software fixture; not an operational threshold",
        policy_version="fixture@1.0.0",
    )
    target = ExposureTarget(
        athlete_id=execution.athlete_id,
        prescription_id=prescription.id,
        exposure_type=ExposureType.JUMPING,
        proposed_dose=25,
        dose_unit="repetitions",
        proposed_for=NOW + timedelta(days=7),
    )
    validation = ExposureProgressionValidator().validate(
        target=target,
        policy=exposure_policy,
        entries=(entry,),
        decided_at=target.proposed_for,
    )
    assert entry.kind == "derived"
    assert entry.source_observation_ids == (execution.performance_observation_id,)
    assert validation.maximum_allowed_dose == 18
    assert validation.outcome is ExposureValidationOutcome.REJECTED

    decision = ProgressionEngine().decide(
        prescription=prescription,
        execution=execution,
        adherence=adherence,
        policy=progression_policy(ExposureType.JUMPING),
        exposure_validation=validation,
        decided_at=target.proposed_for,
    )
    assert decision.outcome is ProgressionOutcome.HOLD
    assert decision.adjustment is None


def test_approved_decision_creates_new_immutable_prescription() -> None:
    prescription, execution, adherence = chain()
    policy = progression_policy()
    decision = ProgressionEngine().decide(
        prescription=prescription,
        execution=execution,
        adherence=adherence,
        policy=policy,
        decided_at=NOW + timedelta(minutes=35),
    )
    revised = PrescriptionProgressionApplicator().apply(
        prescription=prescription,
        decision=decision,
        policy=policy,
        prescribed_at=NOW + timedelta(days=1),
    )
    assert revised.id != prescription.id
    assert prescription.repetitions_per_set == 5
    assert revised.repetitions_per_set == 6
    assert revised.supersedes_prescription_id == prescription.id
    assert revised.progression_decision_id == decision.id
    assert revised.source_observation_ids == (
        *prescription.source_observation_ids,
        *decision.source_observation_ids,
    )

    blocked = decision.model_copy(update={"outcome": ProgressionOutcome.HOLD, "adjustment": None})
    with pytest.raises(ProgressionError, match="does not authorize"):
        PrescriptionProgressionApplicator().apply(
            prescription=prescription,
            decision=blocked,
            policy=policy,
            prescribed_at=NOW + timedelta(days=1),
        )


def test_load_progression_updates_the_typed_absolute_load_target() -> None:
    prescription, execution, adherence = chain()
    policy = ProgressionPolicy(
        reference=prescription.progression_rule_reference,
        minimum_set_completion_ratio=1,
        minimum_dose_completion_ratio=1,
        maximum_session_rpe=8,
        adjustment=PrescriptionAdjustment(
            dimension=ProgressionDimension.LOAD,
            amount=2.5,
            unit="kg",
            description="add 2.5 kilograms",
        ),
        evidence_claim_ids=(uuid4(),),
        rationale="software fixture",
        policy_version="fixture@1.0.0",
    )
    decision = ProgressionEngine().decide(
        prescription=prescription,
        execution=execution,
        adherence=adherence,
        policy=policy,
        decided_at=NOW + timedelta(minutes=35),
    )

    revised = PrescriptionProgressionApplicator().apply(
        prescription=prescription,
        decision=decision,
        policy=policy,
        prescribed_at=NOW + timedelta(days=1),
    )

    original_load = next(
        target
        for target in prescription.intensity_targets
        if isinstance(target, AbsoluteLoadTarget)
    )
    revised_load = next(
        target for target in revised.intensity_targets if isinstance(target, AbsoluteLoadTarget)
    )
    assert original_load.value == 100
    assert revised_load.value == 102.5
    assert revised_load.unit == "kg"
