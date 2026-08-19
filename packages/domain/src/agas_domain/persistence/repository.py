from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import InstrumentedAttribute

from agas_domain.models import (
    Adaptation,
    AdaptationPriority,
    AdaptationRelationship,
    AdaptationResourceDemand,
    AssessmentDefinition,
    AssessmentSelection,
    Athlete,
    AvailabilityWindow,
    BlockIssue,
    BlockPlan,
    BlockReview,
    BlockReviewPolicy,
    CapabilityEstimate,
    CapabilityNeed,
    CompetencyFloor,
    DecisionRecord,
    Environment,
    Equipment,
    EquipmentAvailability,
    EvidenceClaim,
    EvidenceSourceIdentifier,
    Exercise,
    ExerciseMatch,
    ExerciseResolution,
    ExerciseResolverPolicy,
    ExposureDefinition,
    ExposureEntry,
    ExposureProgressionPolicy,
    ExposureValidationDecision,
    LongRangeStrategy,
    Observation,
    PlannedSession,
    PriorityPolicy,
    ProgressionDecision,
    ProgressionPolicy,
    Provenance,
    ResolutionIssue,
    ResourceAllocation,
    ResourceAllocationPolicy,
    ResponseEvaluation,
    RoadmapItem,
    SchedulingIssue,
    SessionAdherence,
    SessionExecution,
    SessionPrescription,
    SessionSafetyDecision,
    SessionSafetyPolicy,
    SetPerformance,
    StimulusRequirement,
    TrainingResponse,
    WeeklyAvailability,
    WeeklyPlan,
    WeeklySchedulingPolicy,
)
from agas_domain.persistence.models import (
    AdaptationEvidenceClaimRecord,
    AdaptationPriorityRecord,
    AdaptationRecord,
    AdaptationRelationshipEvidenceRecord,
    AdaptationRelationshipRecord,
    AdaptationResourceDemandRecord,
    AssessmentDefinitionRecord,
    AssessmentSelectionObservationRecord,
    AssessmentSelectionRecord,
    AthleteRecord,
    AvailabilityWindowRecord,
    BlockPlanEvidenceClaimRecord,
    BlockPlanObservationRecord,
    BlockPlanRecord,
    BlockResourceAllocationRecord,
    BlockReviewEvidenceRecord,
    BlockReviewObservationRecord,
    BlockReviewPolicyEvidenceRecord,
    BlockReviewPolicyRecord,
    BlockReviewRecord,
    BlockReviewResponseRecord,
    BlockReviewSafetyRecord,
    CapabilityEstimateObservationRecord,
    CapabilityEstimateRecord,
    CapabilityNeedEvidenceClaimRecord,
    CapabilityNeedRecord,
    CompetencyFloorEvidenceClaimRecord,
    CompetencyFloorRecord,
    DecisionRecordRecord,
    EnvironmentRecord,
    EquipmentAvailabilityRecord,
    EquipmentRecord,
    EvidenceClaimRecord,
    ExerciseAdaptationRecord,
    ExerciseEquipmentRequirementRecord,
    ExerciseMatchRecord,
    ExerciseRecord,
    ExerciseRelationshipRecord,
    ExerciseResolutionAvailabilityRecord,
    ExerciseResolutionRecord,
    ExerciseResolverPolicyRecord,
    ExposureDefinitionEvidenceRecord,
    ExposureDefinitionRecord,
    ExposureEntryObservationRecord,
    ExposureEntryRecord,
    ExposureProgressionPolicyEvidenceRecord,
    ExposureProgressionPolicyRecord,
    ExposureValidationDecisionRecord,
    ExposureValidationEntryRecord,
    LongRangeStrategyRecord,
    ObservationRecord,
    PlannedSessionRecord,
    PriorityPolicyRecord,
    ProgressionDecisionObservationRecord,
    ProgressionDecisionRecord,
    ProgressionDecisionSafetyRecord,
    ProgressionPolicyEvidenceRecord,
    ProgressionPolicyRecord,
    ResourceAllocationPolicyRecord,
    ResourceDemandEvidenceClaimRecord,
    ResourceDemandObservationRecord,
    RoadmapItemPrerequisiteRecord,
    RoadmapItemRecord,
    SessionAdherenceObservationRecord,
    SessionAdherenceRecord,
    SessionExecutionRecord,
    SessionPrescriptionEvidenceClaimRecord,
    SessionPrescriptionObservationRecord,
    SessionPrescriptionRecord,
    SessionPrescriptionRevisionRecord,
    SessionSafetyDecisionObservationRecord,
    SessionSafetyDecisionRecord,
    SessionSafetyPolicyEvidenceClaimRecord,
    SessionSafetyPolicyRecord,
    SetPerformanceRecord,
    StimulusRequirementEvidenceClaimRecord,
    StimulusRequirementObservationRecord,
    StimulusRequirementRecord,
    StrategyCapabilityEstimateRecord,
    StrategyCompetencyFloorRecord,
    StrategyEvidenceClaimRecord,
    StrategyObservationRecord,
    TrainingResponseAdherenceRecord,
    TrainingResponseExecutionRecord,
    TrainingResponseObservationRecord,
    TrainingResponsePrescriptionRecord,
    TrainingResponseRecord,
    WeeklyAvailabilityObservationRecord,
    WeeklyAvailabilityRecord,
    WeeklyPlanRecord,
    WeeklySchedulingPolicyRecord,
)


class DomainIntegrityError(ValueError):
    """Raised when persistence would break a domain invariant."""


class DomainRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_athlete(self, athlete: Athlete) -> None:
        self.session.add(
            AthleteRecord(
                id=athlete.id,
                schema_version=athlete.schema_version,
                created_at=athlete.created_at,
                display_name=athlete.display_name,
                date_of_birth=athlete.date_of_birth,
                preferences=athlete.preferences,
                goals=list(athlete.goals),
            )
        )

    def add_observation(self, observation: Observation) -> None:
        self._require_athlete(observation.athlete_id)
        self.session.add(
            ObservationRecord(
                id=observation.id,
                schema_version=observation.schema_version,
                created_at=observation.created_at,
                athlete_id=observation.athlete_id,
                observed_at=observation.observed_at,
                observation_type=observation.observation_type,
                measurement=observation.measurement,
                unit=observation.unit,
                source=observation.source.value,
                reliability=observation.reliability.value,
                context=observation.context,
                provenance=observation.provenance.model_dump(mode="json"),
            )
        )

    def add_capability_estimate(self, estimate: CapabilityEstimate) -> None:
        self._require_athlete(estimate.athlete_id)
        observations = self._observations_by_id(estimate.source_observation_ids)
        found_ids = {item.id for item in observations}
        missing = set(estimate.source_observation_ids) - found_ids
        if missing:
            raise DomainIntegrityError(f"unknown source observations: {sorted(map(str, missing))}")
        if any(item.athlete_id != estimate.athlete_id for item in observations):
            raise DomainIntegrityError(
                "all source observations must belong to the same athlete as the estimate"
            )

        record = CapabilityEstimateRecord(
            id=estimate.id,
            schema_version=estimate.schema_version,
            created_at=estimate.created_at,
            kind=estimate.kind,
            athlete_id=estimate.athlete_id,
            domain=estimate.domain.value,
            estimate=estimate.estimate,
            unit_or_scale=estimate.unit_or_scale,
            estimate_scope=estimate.estimate_scope,
            confidence=estimate.confidence.value,
            calculation_method=estimate.calculation_method,
            estimated_at=estimate.estimated_at,
            valid_until=estimate.valid_until,
            rule_version=estimate.rule_version,
        )
        record.source_links = [
            CapabilityEstimateObservationRecord(
                estimate_id=estimate.id,
                observation_id=observation_id,
                source_order=source_order,
            )
            for source_order, observation_id in enumerate(estimate.source_observation_ids)
        ]
        self.session.add(record)

    def add_environment(self, environment: Environment) -> None:
        self._require_athlete(environment.athlete_id)
        self.session.add(
            EnvironmentRecord(
                id=environment.id,
                schema_version=environment.schema_version,
                created_at=environment.created_at,
                athlete_id=environment.athlete_id,
                name=environment.name,
                space_constraints=environment.space_constraints,
                noise_constraints=environment.noise_constraints,
                max_noise_level=environment.max_noise_level.value,
                outdoor_access=environment.outdoor_access,
            )
        )

    def add_equipment(self, equipment: Equipment) -> None:
        self.session.add(
            EquipmentRecord(
                id=equipment.id,
                schema_version=equipment.schema_version,
                created_at=equipment.created_at,
                name=equipment.name,
                category=equipment.category,
                capabilities=equipment.capabilities,
            )
        )

    def add_equipment_availability(self, availability: EquipmentAvailability) -> None:
        if self.session.get(EnvironmentRecord, availability.environment_id) is None:
            raise DomainIntegrityError("environment does not exist")
        if self.session.get(EquipmentRecord, availability.equipment_id) is None:
            raise DomainIntegrityError("equipment does not exist")
        self.session.add(
            EquipmentAvailabilityRecord(
                id=availability.id,
                schema_version=availability.schema_version,
                created_at=availability.created_at,
                environment_id=availability.environment_id,
                equipment_id=availability.equipment_id,
                is_available=availability.is_available,
                effective_from=availability.effective_from,
                effective_until=availability.effective_until,
                capabilities=availability.capabilities,
                load_limits=availability.load_limits,
                reason=availability.reason,
            )
        )

    def add_exercise(self, exercise: Exercise) -> None:
        self._require_ids_exist(
            AdaptationRecord.id,
            (*exercise.primary_adaptation_ids, *exercise.secondary_adaptation_ids),
            "adaptations",
        )
        self._require_ids_exist(EquipmentRecord.id, exercise.equipment_requirement_ids, "equipment")
        self._require_ids_exist(
            ExerciseRecord.id,
            (*exercise.progression_exercise_ids, *exercise.regression_exercise_ids),
            "exercises",
        )

        record = ExerciseRecord(
            id=exercise.id,
            schema_version=exercise.schema_version,
            created_at=exercise.created_at,
            name=exercise.name,
            movement_patterns=list(exercise.movement_patterns),
            joint_demands=list(exercise.joint_demands),
            loading_type=exercise.loading_type,
            loadability=exercise.loadability.value,
            skill_complexity=exercise.skill_complexity.value,
            impact_level=exercise.impact_level.value,
            velocity_characteristics=list(exercise.velocity_characteristics),
            stability_demand=exercise.stability_demand.value,
            fatigue_cost=exercise.fatigue_cost.value,
            soreness_cost=exercise.soreness_cost.value,
            requires_outdoor_access=exercise.requires_outdoor_access,
            minimum_floor_area_m2=exercise.minimum_floor_area_m2,
            noise_level=exercise.noise_level.value,
            contraindication_tags=list(exercise.contraindication_tags),
            measurement_methods=list(exercise.measurement_methods),
        )
        record.adaptation_links = [
            ExerciseAdaptationRecord(
                exercise_id=exercise.id,
                adaptation_id=adaptation_id,
                role=role,
                position=position,
            )
            for role, adaptation_ids in (
                ("primary", exercise.primary_adaptation_ids),
                ("secondary", exercise.secondary_adaptation_ids),
            )
            for position, adaptation_id in enumerate(adaptation_ids)
        ]
        record.equipment_links = [
            ExerciseEquipmentRequirementRecord(
                exercise_id=exercise.id,
                equipment_id=equipment_id,
                position=position,
            )
            for position, equipment_id in enumerate(exercise.equipment_requirement_ids)
        ]
        record.exercise_links = [
            ExerciseRelationshipRecord(
                source_exercise_id=exercise.id,
                target_exercise_id=target_id,
                relationship=relationship,
                position=position,
            )
            for relationship, target_ids in (
                ("progression", exercise.progression_exercise_ids),
                ("regression", exercise.regression_exercise_ids),
            )
            for position, target_id in enumerate(target_ids)
        ]
        self.session.add(record)

    def add_adaptation(self, adaptation: Adaptation) -> None:
        relationship_target_ids = tuple(
            item.target_adaptation_id for item in adaptation.relationships
        )
        relationship_evidence_ids = tuple(
            evidence_id
            for item in adaptation.relationships
            for evidence_id in item.evidence_claim_ids
        )
        self._require_ids_exist(
            AdaptationRecord.id, relationship_target_ids, "relationship target adaptations"
        )
        self._require_ids_exist(
            EvidenceClaimRecord.id,
            (*adaptation.evidence_claim_ids, *relationship_evidence_ids),
            "evidence claims",
        )

        record = AdaptationRecord(
            id=adaptation.id,
            schema_version=adaptation.schema_version,
            created_at=adaptation.created_at,
            name=adaptation.name,
            domain=adaptation.domain.value,
            preferred_stimuli=list(adaptation.preferred_stimuli),
            valid_modalities=list(adaptation.valid_modalities),
            dose_dimensions=list(adaptation.dose_dimensions),
            fatigue_characteristics=adaptation.fatigue_characteristics,
            typical_measurement_methods=list(adaptation.typical_measurement_methods),
            maintenance_requirements=adaptation.maintenance_requirements,
        )
        record.evidence_links = [
            AdaptationEvidenceClaimRecord(
                adaptation_id=adaptation.id,
                evidence_claim_id=evidence_claim_id,
                position=position,
            )
            for position, evidence_claim_id in enumerate(adaptation.evidence_claim_ids)
        ]
        record.relationship_links = []
        for position, relationship in enumerate(adaptation.relationships):
            relationship_record = AdaptationRelationshipRecord(
                id=relationship.id,
                schema_version=relationship.schema_version,
                created_at=relationship.created_at,
                source_adaptation_id=adaptation.id,
                target_adaptation_id=relationship.target_adaptation_id,
                relationship_type=relationship.relationship.value,
                strength=relationship.strength.value,
                confidence=relationship.confidence.value,
                population=relationship.population,
                notes=relationship.notes,
                position=position,
            )
            relationship_record.evidence_links = [
                AdaptationRelationshipEvidenceRecord(
                    relationship_id=relationship.id,
                    evidence_claim_id=evidence_claim_id,
                    position=evidence_position,
                )
                for evidence_position, evidence_claim_id in enumerate(
                    relationship.evidence_claim_ids
                )
            ]
            record.relationship_links.append(relationship_record)
        self.session.add(record)

    def add_evidence_claim(self, claim: EvidenceClaim) -> None:
        self.session.add(
            EvidenceClaimRecord(
                id=claim.id,
                schema_version=claim.schema_version,
                created_at=claim.created_at,
                claim=claim.claim,
                domain=claim.domain,
                population=claim.population,
                intervention=claim.intervention,
                comparator=claim.comparator,
                outcome=claim.outcome,
                study_design=claim.study_design,
                sample_size=claim.sample_size,
                duration=claim.duration,
                effect_direction=claim.effect_direction,
                uncertainty=claim.uncertainty,
                limitations=list(claim.limitations),
                evidence_strength=claim.evidence_strength.value,
                athlete_applicability=claim.athlete_applicability.value,
                applicability_notes=claim.applicability_notes,
                source_identifiers=[
                    item.model_dump(mode="json") for item in claim.source_identifiers
                ],
                reviewer=claim.reviewer,
                claim_version=claim.claim_version,
            )
        )

    def add_decision_record(self, decision: DecisionRecord) -> None:
        self.session.add(
            DecisionRecordRecord(
                id=decision.id,
                schema_version=decision.schema_version,
                created_at=decision.created_at,
                decision=decision.decision,
                reason=decision.reason,
                alternatives_considered=list(decision.alternatives_considered),
                evidence=list(decision.evidence),
                uncertainty=decision.uncertainty,
                decision_version=decision.decision_version,
                decided_on=decision.decided_on,
            )
        )

    def add_competency_floor(self, floor: CompetencyFloor) -> None:
        self._require_ids_exist(
            EvidenceClaimRecord.id, floor.evidence_claim_ids, "competency-floor evidence claims"
        )
        record = CompetencyFloorRecord(
            id=floor.id,
            schema_version=floor.schema_version,
            created_at=floor.created_at,
            domain=floor.domain.value,
            estimate_scope=floor.estimate_scope,
            unit_or_scale=floor.unit_or_scale,
            threshold=floor.threshold,
            comparison_direction=floor.comparison_direction.value,
            population=floor.population,
            applicability_notes=floor.applicability_notes,
            uncertainty=floor.uncertainty,
            floor_version=floor.floor_version,
        )
        record.evidence_links = [
            CompetencyFloorEvidenceClaimRecord(
                competency_floor_id=floor.id,
                evidence_claim_id=evidence_claim_id,
                position=position,
            )
            for position, evidence_claim_id in enumerate(floor.evidence_claim_ids)
        ]
        self.session.add(record)

    def add_capability_need(self, need: CapabilityNeed) -> None:
        self._require_athlete(need.athlete_id)
        if self.session.get(CompetencyFloorRecord, need.competency_floor_id) is None:
            raise DomainIntegrityError("competency floor does not exist")
        if need.capability_estimate_id is not None:
            estimate = self.session.get(CapabilityEstimateRecord, need.capability_estimate_id)
            if estimate is None:
                raise DomainIntegrityError("capability estimate does not exist")
            if estimate.athlete_id != need.athlete_id:
                raise DomainIntegrityError("capability estimate belongs to a different athlete")
        self._require_ids_exist(
            EvidenceClaimRecord.id, need.evidence_claim_ids, "capability-need evidence claims"
        )
        record = CapabilityNeedRecord(
            id=need.id,
            schema_version=need.schema_version,
            created_at=need.created_at,
            athlete_id=need.athlete_id,
            domain=need.domain.value,
            competency_floor_id=need.competency_floor_id,
            capability_estimate_id=need.capability_estimate_id,
            status=need.status.value,
            observed_value=need.observed_value,
            floor_value=need.floor_value,
            unit_or_scale=need.unit_or_scale,
            gap_from_floor=need.gap_from_floor,
            normalized_deficit=need.normalized_deficit,
            confidence=need.confidence.value,
            rationale=need.rationale,
            identified_at=need.identified_at,
            rule_version=need.rule_version,
        )
        record.evidence_links = [
            CapabilityNeedEvidenceClaimRecord(
                capability_need_id=need.id,
                evidence_claim_id=evidence_claim_id,
                position=position,
            )
            for position, evidence_claim_id in enumerate(need.evidence_claim_ids)
        ]
        self.session.add(record)

    def add_priority_policy(self, policy: PriorityPolicy) -> None:
        self.session.add(
            PriorityPolicyRecord(
                id=policy.id,
                schema_version=policy.schema_version,
                created_at=policy.created_at,
                deficit_weight=policy.deficit_weight,
                general_relevance_weight=policy.general_relevance_weight,
                goal_relevance_weight=policy.goal_relevance_weight,
                prerequisite_value_weight=policy.prerequisite_value_weight,
                expected_trainability_weight=policy.expected_trainability_weight,
                transfer_value_weight=policy.transfer_value_weight,
                fatigue_cost_weight=policy.fatigue_cost_weight,
                time_cost_weight=policy.time_cost_weight,
                interference_cost_weight=policy.interference_cost_weight,
                cost_penalty=policy.cost_penalty,
                confidence_multipliers={
                    confidence.value: multiplier
                    for confidence, multiplier in policy.confidence_multipliers.items()
                },
                develop_score_threshold=policy.develop_score_threshold,
                comparative_advantage_threshold=policy.comparative_advantage_threshold,
                severe_deficit_threshold=policy.severe_deficit_threshold,
                max_develop_adaptations=policy.max_develop_adaptations,
                policy_version=policy.policy_version,
            )
        )

    def add_long_range_strategy(self, strategy: LongRangeStrategy) -> None:
        self._require_athlete(strategy.athlete_id)
        if self.session.get(PriorityPolicyRecord, strategy.priority_policy_id) is None:
            raise DomainIntegrityError("priority policy does not exist")
        observations = self._observations_by_id(strategy.source_observation_ids)
        if {item.id for item in observations} != set(strategy.source_observation_ids):
            raise DomainIntegrityError("one or more strategy source observations do not exist")
        if any(item.athlete_id != strategy.athlete_id for item in observations):
            raise DomainIntegrityError("strategy observations belong to a different athlete")
        estimates = list(
            self.session.scalars(
                select(CapabilityEstimateRecord).where(
                    CapabilityEstimateRecord.id.in_(strategy.source_capability_estimate_ids)
                )
            )
        )
        if {item.id for item in estimates} != set(strategy.source_capability_estimate_ids):
            raise DomainIntegrityError("one or more strategy capability estimates do not exist")
        if any(item.athlete_id != strategy.athlete_id for item in estimates):
            raise DomainIntegrityError("strategy estimates belong to a different athlete")
        estimate_source_ids = {
            link.observation_id for estimate in estimates for link in estimate.source_links
        }
        if not estimate_source_ids.issubset(set(strategy.source_observation_ids)):
            raise DomainIntegrityError(
                "strategy observations must include every capability-estimate source"
            )
        self._require_ids_exist(
            CompetencyFloorRecord.id, strategy.competency_floor_ids, "strategy competency floors"
        )
        self._require_ids_exist(
            EvidenceClaimRecord.id, strategy.evidence_claim_ids, "strategy evidence claims"
        )
        adaptation_ids = tuple(item.adaptation_id for item in strategy.priorities)
        prerequisite_ids = tuple(
            prerequisite_id
            for item in strategy.roadmap
            for prerequisite_id in item.prerequisite_adaptation_ids
        )
        self._require_ids_exist(
            AdaptationRecord.id, (*adaptation_ids, *prerequisite_ids), "strategy adaptations"
        )
        need_ids = tuple(item.capability_need_id for item in strategy.priorities)
        self._require_ids_exist(CapabilityNeedRecord.id, need_ids, "strategy capability needs")
        needs = list(
            self.session.scalars(
                select(CapabilityNeedRecord).where(CapabilityNeedRecord.id.in_(need_ids))
            )
        )
        if any(item.athlete_id != strategy.athlete_id for item in needs):
            raise DomainIntegrityError("strategy capability needs belong to a different athlete")
        needs_by_id = {item.id: item for item in needs}
        adaptations = list(
            self.session.scalars(
                select(AdaptationRecord).where(AdaptationRecord.id.in_(adaptation_ids))
            )
        )
        adaptations_by_id = {item.id: item for item in adaptations}
        for priority in strategy.priorities:
            need = needs_by_id[priority.capability_need_id]
            adaptation = adaptations_by_id[priority.adaptation_id]
            if need.domain != adaptation.domain:
                raise DomainIntegrityError("strategy adaptation and need domains must match")
            if need.competency_floor_id not in strategy.competency_floor_ids:
                raise DomainIntegrityError("strategy omits a competency floor used by a need")
            if (
                need.capability_estimate_id is not None
                and need.capability_estimate_id not in strategy.source_capability_estimate_ids
            ):
                raise DomainIntegrityError("strategy omits a capability estimate used by a need")
            need_evidence_ids = {item.evidence_claim_id for item in need.evidence_links}
            if not need_evidence_ids.issubset(set(strategy.evidence_claim_ids)):
                raise DomainIntegrityError("strategy omits evidence used by a capability need")

        record = LongRangeStrategyRecord(
            id=strategy.id,
            schema_version=strategy.schema_version,
            created_at=strategy.created_at,
            athlete_id=strategy.athlete_id,
            priority_policy_id=strategy.priority_policy_id,
            horizon_months=strategy.horizon_months,
            block_hypothesis=strategy.block_hypothesis,
            generated_at=strategy.generated_at,
            next_review_at=strategy.next_review_at,
            rule_version=strategy.rule_version,
        )
        record.priority_links = [
            AdaptationPriorityRecord(
                id=item.id,
                schema_version=item.schema_version,
                created_at=item.created_at,
                strategy_id=strategy.id,
                adaptation_id=item.adaptation_id,
                capability_need_id=item.capability_need_id,
                state=item.state.value,
                score=item.score,
                rank=item.rank,
                development_allocation=item.development_allocation,
                score_components=item.score_components,
                reason_codes=[reason.value for reason in item.reason_codes],
                rationale=list(item.rationale),
                position=position,
            )
            for position, item in enumerate(strategy.priorities)
        ]
        record.roadmap_links = []
        for position, item in enumerate(strategy.roadmap):
            roadmap_record = RoadmapItemRecord(
                id=item.id,
                schema_version=item.schema_version,
                created_at=item.created_at,
                strategy_id=strategy.id,
                adaptation_id=item.adaptation_id,
                current_state=item.current_state.value,
                sequence_group=item.sequence_group,
                rationale=item.rationale,
                review_trigger=item.review_trigger,
                position=position,
            )
            roadmap_record.prerequisite_links = [
                RoadmapItemPrerequisiteRecord(
                    roadmap_item_id=item.id,
                    adaptation_id=adaptation_id,
                    position=prerequisite_position,
                )
                for prerequisite_position, adaptation_id in enumerate(
                    item.prerequisite_adaptation_ids
                )
            ]
            record.roadmap_links.append(roadmap_record)
        record.observation_links = [
            StrategyObservationRecord(
                strategy_id=strategy.id, observation_id=item_id, position=position
            )
            for position, item_id in enumerate(strategy.source_observation_ids)
        ]
        record.estimate_links = [
            StrategyCapabilityEstimateRecord(
                strategy_id=strategy.id, capability_estimate_id=item_id, position=position
            )
            for position, item_id in enumerate(strategy.source_capability_estimate_ids)
        ]
        record.floor_links = [
            StrategyCompetencyFloorRecord(
                strategy_id=strategy.id, competency_floor_id=item_id, position=position
            )
            for position, item_id in enumerate(strategy.competency_floor_ids)
        ]
        record.evidence_links = [
            StrategyEvidenceClaimRecord(
                strategy_id=strategy.id, evidence_claim_id=item_id, position=position
            )
            for position, item_id in enumerate(strategy.evidence_claim_ids)
        ]
        self.session.add(record)

    def add_stimulus_requirement(self, requirement: StimulusRequirement) -> None:
        self._require_athlete(requirement.athlete_id)
        strategy = self.session.get(LongRangeStrategyRecord, requirement.long_range_strategy_id)
        if strategy is None:
            raise DomainIntegrityError("long-range strategy does not exist")
        if strategy.athlete_id != requirement.athlete_id:
            raise DomainIntegrityError("stimulus strategy belongs to a different athlete")
        priority = self.session.get(AdaptationPriorityRecord, requirement.adaptation_priority_id)
        if priority is None:
            raise DomainIntegrityError("adaptation priority does not exist")
        if priority.strategy_id != strategy.id:
            raise DomainIntegrityError("adaptation priority belongs to a different strategy")
        if priority.adaptation_id != requirement.adaptation_id:
            raise DomainIntegrityError("stimulus adaptation differs from its priority")
        if priority.state != requirement.priority_state.value:
            raise DomainIntegrityError("stimulus priority state differs from persisted priority")
        observations = self._observations_by_id(requirement.source_observation_ids)
        if {item.id for item in observations} != set(requirement.source_observation_ids):
            raise DomainIntegrityError("one or more stimulus source observations do not exist")
        if any(item.athlete_id != requirement.athlete_id for item in observations):
            raise DomainIntegrityError("stimulus observations belong to a different athlete")
        self._require_ids_exist(
            EvidenceClaimRecord.id,
            requirement.evidence_claim_ids,
            "stimulus evidence claims",
        )

        record = StimulusRequirementRecord(
            id=requirement.id,
            schema_version=requirement.schema_version,
            created_at=requirement.created_at,
            athlete_id=requirement.athlete_id,
            long_range_strategy_id=requirement.long_range_strategy_id,
            adaptation_priority_id=requirement.adaptation_priority_id,
            adaptation_id=requirement.adaptation_id,
            priority_state=requirement.priority_state.value,
            movement_patterns=list(requirement.movement_patterns),
            allowed_loading_types=list(requirement.allowed_loading_types),
            minimum_loadability=requirement.minimum_loadability.value,
            required_velocity_characteristics=list(requirement.required_velocity_characteristics),
            maximum_skill_complexity=requirement.maximum_skill_complexity.value,
            maximum_impact_level=requirement.maximum_impact_level.value,
            maximum_stability_demand=requirement.maximum_stability_demand.value,
            maximum_fatigue_cost=requirement.maximum_fatigue_cost.value,
            maximum_soreness_cost=requirement.maximum_soreness_cost.value,
            requires_outdoor_access=requirement.requires_outdoor_access,
            minimum_floor_area_m2=requirement.minimum_floor_area_m2,
            contraindication_tags=list(requirement.contraindication_tags),
            rationale=requirement.rationale,
            generated_at=requirement.generated_at,
            rule_version=requirement.rule_version,
        )
        record.observation_links = [
            StimulusRequirementObservationRecord(
                stimulus_requirement_id=requirement.id,
                observation_id=observation_id,
                position=position,
            )
            for position, observation_id in enumerate(requirement.source_observation_ids)
        ]
        record.evidence_links = [
            StimulusRequirementEvidenceClaimRecord(
                stimulus_requirement_id=requirement.id,
                evidence_claim_id=evidence_claim_id,
                position=position,
            )
            for position, evidence_claim_id in enumerate(requirement.evidence_claim_ids)
        ]
        self.session.add(record)

    def add_exercise_resolver_policy(self, policy: ExerciseResolverPolicy) -> None:
        self.session.add(
            ExerciseResolverPolicyRecord(
                id=policy.id,
                schema_version=policy.schema_version,
                created_at=policy.created_at,
                adaptation_role_weight=policy.adaptation_role_weight,
                movement_pattern_weight=policy.movement_pattern_weight,
                loading_type_weight=policy.loading_type_weight,
                loadability_weight=policy.loadability_weight,
                velocity_weight=policy.velocity_weight,
                secondary_adaptation_credit=policy.secondary_adaptation_credit,
                partial_match_threshold=policy.partial_match_threshold,
                full_match_threshold=policy.full_match_threshold,
                max_ranked_candidates=policy.max_ranked_candidates,
                policy_version=policy.policy_version,
            )
        )

    def add_exercise_resolution(self, resolution: ExerciseResolution) -> None:
        requirement = self.session.get(
            StimulusRequirementRecord, resolution.stimulus_requirement_id
        )
        if requirement is None:
            raise DomainIntegrityError("stimulus requirement does not exist")
        environment = self.session.get(EnvironmentRecord, resolution.environment_id)
        if environment is None:
            raise DomainIntegrityError("resolution environment does not exist")
        if environment.athlete_id != requirement.athlete_id:
            raise DomainIntegrityError("resolution environment belongs to a different athlete")
        if self.session.get(ExerciseResolverPolicyRecord, resolution.resolver_policy_id) is None:
            raise DomainIntegrityError("exercise resolver policy does not exist")
        match_exercise_ids = tuple(item.exercise_id for item in resolution.ranked_matches)
        selected_ids = (
            () if resolution.selected_exercise_id is None else (resolution.selected_exercise_id,)
        )
        self._require_ids_exist(
            ExerciseRecord.id,
            (*match_exercise_ids, *selected_ids),
            "resolution exercises",
        )
        availability_records = list(
            self.session.scalars(
                select(EquipmentAvailabilityRecord).where(
                    EquipmentAvailabilityRecord.id.in_(resolution.source_availability_ids)
                )
            )
        )
        if {item.id for item in availability_records} != set(resolution.source_availability_ids):
            raise DomainIntegrityError("one or more availability sources do not exist")
        if any(item.environment_id != resolution.environment_id for item in availability_records):
            raise DomainIntegrityError("availability source belongs to a different environment")

        record = ExerciseResolutionRecord(
            id=resolution.id,
            schema_version=resolution.schema_version,
            created_at=resolution.created_at,
            stimulus_requirement_id=resolution.stimulus_requirement_id,
            environment_id=resolution.environment_id,
            resolver_policy_id=resolution.resolver_policy_id,
            status=resolution.status.value,
            selected_exercise_id=resolution.selected_exercise_id,
            unresolved_issues=[
                item.model_dump(mode="json") for item in resolution.unresolved_issues
            ],
            rationale=resolution.rationale,
            resolved_at=resolution.resolved_at,
            rule_version=resolution.rule_version,
        )
        record.match_links = [
            ExerciseMatchRecord(
                id=item.id,
                schema_version=item.schema_version,
                created_at=item.created_at,
                resolution_id=resolution.id,
                exercise_id=item.exercise_id,
                quality=item.quality.value,
                score=item.score,
                score_components=item.score_components,
                issues=[issue.model_dump(mode="json") for issue in item.issues],
                position=position,
            )
            for position, item in enumerate(resolution.ranked_matches)
        ]
        record.availability_links = [
            ExerciseResolutionAvailabilityRecord(
                resolution_id=resolution.id,
                equipment_availability_id=availability_id,
                position=position,
            )
            for position, availability_id in enumerate(resolution.source_availability_ids)
        ]
        self.session.add(record)

    def get_stimulus_requirement(self, requirement_id: UUID) -> StimulusRequirement | None:
        record = self.session.get(StimulusRequirementRecord, requirement_id)
        if record is None:
            return None
        return StimulusRequirement(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            athlete_id=record.athlete_id,
            long_range_strategy_id=record.long_range_strategy_id,
            adaptation_priority_id=record.adaptation_priority_id,
            adaptation_id=record.adaptation_id,
            priority_state=record.priority_state,
            movement_patterns=tuple(record.movement_patterns),
            allowed_loading_types=tuple(record.allowed_loading_types),
            minimum_loadability=record.minimum_loadability,
            required_velocity_characteristics=tuple(record.required_velocity_characteristics),
            maximum_skill_complexity=record.maximum_skill_complexity,
            maximum_impact_level=record.maximum_impact_level,
            maximum_stability_demand=record.maximum_stability_demand,
            maximum_fatigue_cost=record.maximum_fatigue_cost,
            maximum_soreness_cost=record.maximum_soreness_cost,
            requires_outdoor_access=record.requires_outdoor_access,
            minimum_floor_area_m2=record.minimum_floor_area_m2,
            contraindication_tags=tuple(record.contraindication_tags),
            source_observation_ids=tuple(item.observation_id for item in record.observation_links),
            evidence_claim_ids=tuple(item.evidence_claim_id for item in record.evidence_links),
            rationale=record.rationale,
            generated_at=record.generated_at,
            rule_version=record.rule_version,
        )

    def get_exercise_resolver_policy(self, policy_id: UUID) -> ExerciseResolverPolicy | None:
        record = self.session.get(ExerciseResolverPolicyRecord, policy_id)
        if record is None:
            return None
        return ExerciseResolverPolicy(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            adaptation_role_weight=record.adaptation_role_weight,
            movement_pattern_weight=record.movement_pattern_weight,
            loading_type_weight=record.loading_type_weight,
            loadability_weight=record.loadability_weight,
            velocity_weight=record.velocity_weight,
            secondary_adaptation_credit=record.secondary_adaptation_credit,
            partial_match_threshold=record.partial_match_threshold,
            full_match_threshold=record.full_match_threshold,
            max_ranked_candidates=record.max_ranked_candidates,
            policy_version=record.policy_version,
        )

    def get_exercise_resolution(self, resolution_id: UUID) -> ExerciseResolution | None:
        record = self.session.get(ExerciseResolutionRecord, resolution_id)
        if record is None:
            return None
        return ExerciseResolution(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            stimulus_requirement_id=record.stimulus_requirement_id,
            environment_id=record.environment_id,
            resolver_policy_id=record.resolver_policy_id,
            status=record.status,
            selected_exercise_id=record.selected_exercise_id,
            ranked_matches=tuple(
                ExerciseMatch(
                    id=item.id,
                    schema_version=item.schema_version,
                    created_at=item.created_at,
                    exercise_id=item.exercise_id,
                    quality=item.quality,
                    score=item.score,
                    score_components=item.score_components,
                    issues=tuple(ResolutionIssue.model_validate(issue) for issue in item.issues),
                )
                for item in record.match_links
            ),
            unresolved_issues=tuple(
                ResolutionIssue.model_validate(issue) for issue in record.unresolved_issues
            ),
            source_availability_ids=tuple(
                item.equipment_availability_id for item in record.availability_links
            ),
            rationale=record.rationale,
            resolved_at=record.resolved_at,
            rule_version=record.rule_version,
        )

    def add_adaptation_resource_demand(self, demand: AdaptationResourceDemand) -> None:
        strategy = self.session.get(LongRangeStrategyRecord, demand.long_range_strategy_id)
        if strategy is None:
            raise DomainIntegrityError("resource-demand strategy does not exist")
        priority = self.session.get(AdaptationPriorityRecord, demand.adaptation_priority_id)
        if priority is None or priority.strategy_id != strategy.id:
            raise DomainIntegrityError("resource-demand priority does not belong to its strategy")
        if (
            priority.adaptation_id != demand.adaptation_id
            or priority.state != demand.priority_state
        ):
            raise DomainIntegrityError("resource demand differs from its persisted priority")
        if demand.stimulus_requirement_id is not None:
            stimulus = self.session.get(StimulusRequirementRecord, demand.stimulus_requirement_id)
            if (
                stimulus is None
                or stimulus.long_range_strategy_id != strategy.id
                or stimulus.adaptation_priority_id != priority.id
            ):
                raise DomainIntegrityError("resource-demand stimulus does not match its priority")
        if demand.exercise_resolution_id is not None:
            resolution = self.session.get(ExerciseResolutionRecord, demand.exercise_resolution_id)
            if resolution is None or resolution.stimulus_requirement_id != (
                demand.stimulus_requirement_id
            ):
                raise DomainIntegrityError("resource-demand resolution does not match its stimulus")
        observations = self._observations_by_id(demand.source_observation_ids)
        if {item.id for item in observations} != set(demand.source_observation_ids):
            raise DomainIntegrityError("one or more resource-demand observations do not exist")
        if any(item.athlete_id != strategy.athlete_id for item in observations):
            raise DomainIntegrityError("resource-demand observations belong to another athlete")
        self._require_ids_exist(
            EvidenceClaimRecord.id,
            demand.evidence_claim_ids,
            "resource-demand evidence claims",
        )
        record = AdaptationResourceDemandRecord(
            id=demand.id,
            schema_version=demand.schema_version,
            created_at=demand.created_at,
            long_range_strategy_id=demand.long_range_strategy_id,
            adaptation_priority_id=demand.adaptation_priority_id,
            adaptation_id=demand.adaptation_id,
            priority_state=demand.priority_state.value,
            stimulus_requirement_id=demand.stimulus_requirement_id,
            exercise_resolution_id=demand.exercise_resolution_id,
            minimum_weekly_minutes=demand.minimum_weekly_minutes,
            target_weekly_minutes=demand.target_weekly_minutes,
            sessions_per_week=demand.sessions_per_week,
            rationale=demand.rationale,
            demand_version=demand.demand_version,
        )
        record.observation_links = [
            ResourceDemandObservationRecord(
                resource_demand_id=demand.id,
                observation_id=item_id,
                position=position,
            )
            for position, item_id in enumerate(demand.source_observation_ids)
        ]
        record.evidence_links = [
            ResourceDemandEvidenceClaimRecord(
                resource_demand_id=demand.id,
                evidence_claim_id=item_id,
                position=position,
            )
            for position, item_id in enumerate(demand.evidence_claim_ids)
        ]
        self.session.add(record)

    def get_adaptation_resource_demand(self, demand_id: UUID) -> AdaptationResourceDemand | None:
        record = self.session.get(AdaptationResourceDemandRecord, demand_id)
        if record is None:
            return None
        return AdaptationResourceDemand(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            long_range_strategy_id=record.long_range_strategy_id,
            adaptation_priority_id=record.adaptation_priority_id,
            adaptation_id=record.adaptation_id,
            priority_state=record.priority_state,
            stimulus_requirement_id=record.stimulus_requirement_id,
            exercise_resolution_id=record.exercise_resolution_id,
            minimum_weekly_minutes=record.minimum_weekly_minutes,
            target_weekly_minutes=record.target_weekly_minutes,
            sessions_per_week=record.sessions_per_week,
            source_observation_ids=tuple(item.observation_id for item in record.observation_links),
            evidence_claim_ids=tuple(item.evidence_claim_id for item in record.evidence_links),
            rationale=record.rationale,
            demand_version=record.demand_version,
        )

    def add_resource_allocation_policy(self, policy: ResourceAllocationPolicy) -> None:
        self.session.add(
            ResourceAllocationPolicyRecord(
                id=policy.id,
                schema_version=policy.schema_version,
                created_at=policy.created_at,
                develop_weight=policy.develop_weight,
                maintain_weight=policy.maintain_weight,
                expose_weight=policy.expose_weight,
                allow_partial_exercise_resolution=policy.allow_partial_exercise_resolution,
                policy_version=policy.policy_version,
            )
        )

    def get_resource_allocation_policy(self, policy_id: UUID) -> ResourceAllocationPolicy | None:
        record = self.session.get(ResourceAllocationPolicyRecord, policy_id)
        if record is None:
            return None
        return ResourceAllocationPolicy(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            develop_weight=record.develop_weight,
            maintain_weight=record.maintain_weight,
            expose_weight=record.expose_weight,
            allow_partial_exercise_resolution=record.allow_partial_exercise_resolution,
            policy_version=record.policy_version,
        )

    def add_block_plan(self, block: BlockPlan) -> None:
        self._require_athlete(block.athlete_id)
        strategy = self.session.get(LongRangeStrategyRecord, block.long_range_strategy_id)
        if strategy is None or strategy.athlete_id != block.athlete_id:
            raise DomainIntegrityError("block strategy belongs to a different athlete")
        if (
            self.session.get(ResourceAllocationPolicyRecord, block.resource_allocation_policy_id)
            is None
        ):
            raise DomainIntegrityError("block resource-allocation policy does not exist")
        demand_records = {
            item.id: item
            for item in self.session.scalars(
                select(AdaptationResourceDemandRecord).where(
                    AdaptationResourceDemandRecord.id.in_(
                        item.resource_demand_id for item in block.allocations
                    )
                )
            )
        }
        if len(demand_records) != len(block.allocations):
            raise DomainIntegrityError("one or more block resource demands do not exist")
        for allocation in block.allocations:
            demand = demand_records[allocation.resource_demand_id]
            if demand.long_range_strategy_id != strategy.id:
                raise DomainIntegrityError("block demand belongs to a different strategy")
            expected = (
                demand.adaptation_priority_id,
                demand.adaptation_id,
                demand.priority_state,
                demand.stimulus_requirement_id,
                demand.exercise_resolution_id,
                demand.minimum_weekly_minutes,
                demand.target_weekly_minutes,
                demand.sessions_per_week,
            )
            actual = (
                allocation.adaptation_priority_id,
                allocation.adaptation_id,
                allocation.priority_state.value,
                allocation.stimulus_requirement_id,
                allocation.exercise_resolution_id,
                allocation.minimum_weekly_minutes,
                allocation.target_weekly_minutes,
                allocation.sessions_per_week,
            )
            if actual != expected:
                raise DomainIntegrityError("block allocation differs from its resource demand")
        observations = self._observations_by_id(block.source_observation_ids)
        if {item.id for item in observations} != set(block.source_observation_ids):
            raise DomainIntegrityError("one or more block observations do not exist")
        if any(item.athlete_id != block.athlete_id for item in observations):
            raise DomainIntegrityError("block observations belong to another athlete")
        self._require_ids_exist(
            EvidenceClaimRecord.id,
            block.evidence_claim_ids,
            "block evidence claims",
        )
        record = BlockPlanRecord(
            id=block.id,
            schema_version=block.schema_version,
            created_at=block.created_at,
            athlete_id=block.athlete_id,
            long_range_strategy_id=block.long_range_strategy_id,
            resource_allocation_policy_id=block.resource_allocation_policy_id,
            starts_on=block.starts_on,
            ends_on=block.ends_on,
            duration_weeks=block.duration_weeks,
            weekly_budget_minutes=block.weekly_budget_minutes,
            status=block.status.value,
            hypothesis=block.hypothesis,
            constraints=list(block.constraints),
            generated_at=block.generated_at,
            rule_version=block.rule_version,
        )
        record.allocation_links = [
            BlockResourceAllocationRecord(
                id=item.id,
                schema_version=item.schema_version,
                created_at=item.created_at,
                block_plan_id=block.id,
                resource_demand_id=item.resource_demand_id,
                adaptation_priority_id=item.adaptation_priority_id,
                adaptation_id=item.adaptation_id,
                priority_state=item.priority_state.value,
                stimulus_requirement_id=item.stimulus_requirement_id,
                exercise_resolution_id=item.exercise_resolution_id,
                minimum_weekly_minutes=item.minimum_weekly_minutes,
                target_weekly_minutes=item.target_weekly_minutes,
                allocated_weekly_minutes=item.allocated_weekly_minutes,
                sessions_per_week=item.sessions_per_week,
                status=item.status.value,
                issues=[issue.model_dump(mode="json") for issue in item.issues],
                position=position,
            )
            for position, item in enumerate(block.allocations)
        ]
        record.observation_links = [
            BlockPlanObservationRecord(
                block_plan_id=block.id,
                observation_id=item_id,
                position=position,
            )
            for position, item_id in enumerate(block.source_observation_ids)
        ]
        record.evidence_links = [
            BlockPlanEvidenceClaimRecord(
                block_plan_id=block.id,
                evidence_claim_id=item_id,
                position=position,
            )
            for position, item_id in enumerate(block.evidence_claim_ids)
        ]
        self.session.add(record)

    def get_block_plan(self, block_id: UUID) -> BlockPlan | None:
        record = self.session.get(BlockPlanRecord, block_id)
        if record is None:
            return None
        return BlockPlan(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            athlete_id=record.athlete_id,
            long_range_strategy_id=record.long_range_strategy_id,
            resource_allocation_policy_id=record.resource_allocation_policy_id,
            starts_on=record.starts_on,
            ends_on=record.ends_on,
            duration_weeks=record.duration_weeks,
            weekly_budget_minutes=record.weekly_budget_minutes,
            status=record.status,
            hypothesis=record.hypothesis,
            allocations=tuple(
                ResourceAllocation(
                    id=item.id,
                    schema_version=item.schema_version,
                    created_at=item.created_at,
                    resource_demand_id=item.resource_demand_id,
                    adaptation_priority_id=item.adaptation_priority_id,
                    adaptation_id=item.adaptation_id,
                    priority_state=item.priority_state,
                    stimulus_requirement_id=item.stimulus_requirement_id,
                    exercise_resolution_id=item.exercise_resolution_id,
                    minimum_weekly_minutes=item.minimum_weekly_minutes,
                    target_weekly_minutes=item.target_weekly_minutes,
                    allocated_weekly_minutes=item.allocated_weekly_minutes,
                    sessions_per_week=item.sessions_per_week,
                    status=item.status,
                    issues=tuple(BlockIssue.model_validate(issue) for issue in item.issues),
                )
                for item in record.allocation_links
            ),
            constraints=tuple(record.constraints),
            source_observation_ids=tuple(item.observation_id for item in record.observation_links),
            evidence_claim_ids=tuple(item.evidence_claim_id for item in record.evidence_links),
            generated_at=record.generated_at,
            rule_version=record.rule_version,
        )

    def add_session_prescription(self, prescription: SessionPrescription) -> None:
        block = self.session.get(BlockPlanRecord, prescription.block_plan_id)
        if block is None or block.athlete_id != prescription.athlete_id:
            raise DomainIntegrityError("prescription block belongs to a different athlete")
        allocation = self.session.get(
            BlockResourceAllocationRecord, prescription.resource_allocation_id
        )
        if allocation is None or allocation.block_plan_id != block.id:
            raise DomainIntegrityError("prescription allocation does not belong to its block")
        if (
            allocation.adaptation_id != prescription.adaptation_id
            or allocation.exercise_resolution_id != prescription.exercise_resolution_id
        ):
            raise DomainIntegrityError("prescription differs from its block allocation")
        resolution = self.session.get(ExerciseResolutionRecord, prescription.exercise_resolution_id)
        if resolution is None or resolution.selected_exercise_id != prescription.exercise_id:
            raise DomainIntegrityError("prescription does not use the selected exercise")
        observations = self._observations_by_id(prescription.source_observation_ids)
        if {item.id for item in observations} != set(prescription.source_observation_ids):
            raise DomainIntegrityError("one or more prescription observations do not exist")
        if any(item.athlete_id != prescription.athlete_id for item in observations):
            raise DomainIntegrityError("prescription observations belong to another athlete")
        self._require_ids_exist(
            EvidenceClaimRecord.id,
            prescription.evidence_claim_ids,
            "prescription evidence claims",
        )
        if prescription.supersedes_prescription_id is not None:
            previous = self.session.get(
                SessionPrescriptionRecord, prescription.supersedes_prescription_id
            )
            decision = self.session.get(
                ProgressionDecisionRecord, prescription.progression_decision_id
            )
            if previous is None or decision is None or decision.prescription_id != previous.id:
                raise DomainIntegrityError("prescription revision provenance is invalid")
            if decision.outcome != "progress" or decision.athlete_id != prescription.athlete_id:
                raise DomainIntegrityError("progression decision cannot authorize this revision")
        record = SessionPrescriptionRecord(
            id=prescription.id,
            schema_version=prescription.schema_version,
            created_at=prescription.created_at,
            athlete_id=prescription.athlete_id,
            block_plan_id=prescription.block_plan_id,
            resource_allocation_id=prescription.resource_allocation_id,
            exercise_resolution_id=prescription.exercise_resolution_id,
            exercise_id=prescription.exercise_id,
            adaptation_id=prescription.adaptation_id,
            reason_for_inclusion=prescription.reason_for_inclusion,
            sets=prescription.sets,
            repetitions_per_set=prescription.repetitions_per_set,
            duration_seconds=prescription.duration_seconds,
            intensity_target=prescription.intensity_target,
            rest_seconds=prescription.rest_seconds,
            progression_rule_reference=prescription.progression_rule_reference,
            substitution_class=prescription.substitution_class,
            planned_duration_minutes=prescription.planned_duration_minutes,
            fatigue_cost=prescription.fatigue_cost.value,
            prescribed_at=prescription.prescribed_at,
            rule_version=prescription.rule_version,
        )
        record.observation_links = [
            SessionPrescriptionObservationRecord(
                prescription_id=prescription.id,
                observation_id=item_id,
                position=position,
            )
            for position, item_id in enumerate(prescription.source_observation_ids)
        ]
        record.evidence_links = [
            SessionPrescriptionEvidenceClaimRecord(
                prescription_id=prescription.id,
                evidence_claim_id=item_id,
                position=position,
            )
            for position, item_id in enumerate(prescription.evidence_claim_ids)
        ]
        self.session.add(record)
        if prescription.supersedes_prescription_id is not None:
            self.session.add(
                SessionPrescriptionRevisionRecord(
                    revised_prescription_id=prescription.id,
                    superseded_prescription_id=prescription.supersedes_prescription_id,
                    progression_decision_id=prescription.progression_decision_id,
                )
            )

    def get_session_prescription(self, prescription_id: UUID) -> SessionPrescription | None:
        record = self.session.get(SessionPrescriptionRecord, prescription_id)
        if record is None:
            return None
        revision = self.session.scalar(
            select(SessionPrescriptionRevisionRecord).where(
                SessionPrescriptionRevisionRecord.revised_prescription_id == prescription_id
            )
        )
        return SessionPrescription(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            athlete_id=record.athlete_id,
            block_plan_id=record.block_plan_id,
            resource_allocation_id=record.resource_allocation_id,
            exercise_resolution_id=record.exercise_resolution_id,
            exercise_id=record.exercise_id,
            adaptation_id=record.adaptation_id,
            reason_for_inclusion=record.reason_for_inclusion,
            sets=record.sets,
            repetitions_per_set=record.repetitions_per_set,
            duration_seconds=record.duration_seconds,
            intensity_target=record.intensity_target,
            rest_seconds=record.rest_seconds,
            progression_rule_reference=record.progression_rule_reference,
            substitution_class=record.substitution_class,
            planned_duration_minutes=record.planned_duration_minutes,
            fatigue_cost=record.fatigue_cost,
            source_observation_ids=tuple(item.observation_id for item in record.observation_links),
            evidence_claim_ids=tuple(item.evidence_claim_id for item in record.evidence_links),
            prescribed_at=record.prescribed_at,
            rule_version=record.rule_version,
            supersedes_prescription_id=(revision.superseded_prescription_id if revision else None),
            progression_decision_id=(revision.progression_decision_id if revision else None),
        )

    def add_weekly_availability(self, availability: WeeklyAvailability) -> None:
        self._require_athlete(availability.athlete_id)
        environment_ids = tuple(item.environment_id for item in availability.windows)
        environments = list(
            self.session.scalars(
                select(EnvironmentRecord).where(EnvironmentRecord.id.in_(environment_ids))
            )
        )
        if {item.id for item in environments} != set(environment_ids):
            raise DomainIntegrityError("one or more availability environments do not exist")
        if any(item.athlete_id != availability.athlete_id for item in environments):
            raise DomainIntegrityError("availability environment belongs to another athlete")
        observations = self._observations_by_id(availability.source_observation_ids)
        if {item.id for item in observations} != set(availability.source_observation_ids):
            raise DomainIntegrityError("one or more availability observations do not exist")
        if any(item.athlete_id != availability.athlete_id for item in observations):
            raise DomainIntegrityError("availability observations belong to another athlete")
        record = WeeklyAvailabilityRecord(
            id=availability.id,
            schema_version=availability.schema_version,
            created_at=availability.created_at,
            athlete_id=availability.athlete_id,
            week_start=availability.week_start,
            recorded_at=availability.recorded_at,
            rule_version=availability.rule_version,
        )
        record.windows = [
            AvailabilityWindowRecord(
                id=item.id,
                schema_version=item.schema_version,
                created_at=item.created_at,
                weekly_availability_id=availability.id,
                environment_id=item.environment_id,
                starts_at=item.starts_at,
                ends_at=item.ends_at,
                position=position,
            )
            for position, item in enumerate(availability.windows)
        ]
        record.observation_links = [
            WeeklyAvailabilityObservationRecord(
                weekly_availability_id=availability.id,
                observation_id=item_id,
                position=position,
            )
            for position, item_id in enumerate(availability.source_observation_ids)
        ]
        self.session.add(record)

    def get_weekly_availability(self, availability_id: UUID) -> WeeklyAvailability | None:
        record = self.session.get(WeeklyAvailabilityRecord, availability_id)
        if record is None:
            return None
        return WeeklyAvailability(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            athlete_id=record.athlete_id,
            week_start=record.week_start,
            windows=tuple(
                AvailabilityWindow(
                    id=item.id,
                    schema_version=item.schema_version,
                    created_at=item.created_at,
                    environment_id=item.environment_id,
                    starts_at=item.starts_at,
                    ends_at=item.ends_at,
                )
                for item in record.windows
            ),
            source_observation_ids=tuple(item.observation_id for item in record.observation_links),
            recorded_at=record.recorded_at,
            rule_version=record.rule_version,
        )

    def add_weekly_scheduling_policy(self, policy: WeeklySchedulingPolicy) -> None:
        self.session.add(
            WeeklySchedulingPolicyRecord(
                id=policy.id,
                schema_version=policy.schema_version,
                created_at=policy.created_at,
                minimum_high_fatigue_recovery_hours=(policy.minimum_high_fatigue_recovery_hours),
                maximum_sessions_per_day=policy.maximum_sessions_per_day,
                maximum_high_fatigue_sessions_per_day=(
                    policy.maximum_high_fatigue_sessions_per_day
                ),
                policy_version=policy.policy_version,
            )
        )

    def get_weekly_scheduling_policy(self, policy_id: UUID) -> WeeklySchedulingPolicy | None:
        record = self.session.get(WeeklySchedulingPolicyRecord, policy_id)
        if record is None:
            return None
        return WeeklySchedulingPolicy(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            minimum_high_fatigue_recovery_hours=(record.minimum_high_fatigue_recovery_hours),
            maximum_sessions_per_day=record.maximum_sessions_per_day,
            maximum_high_fatigue_sessions_per_day=(record.maximum_high_fatigue_sessions_per_day),
            policy_version=record.policy_version,
        )

    def add_weekly_plan(self, plan: WeeklyPlan) -> None:
        self._require_athlete(plan.athlete_id)
        block = self.session.get(BlockPlanRecord, plan.block_plan_id)
        availability = self.session.get(WeeklyAvailabilityRecord, plan.weekly_availability_id)
        if block is None or block.athlete_id != plan.athlete_id:
            raise DomainIntegrityError("weekly plan block belongs to another athlete")
        if availability is None or availability.athlete_id != plan.athlete_id:
            raise DomainIntegrityError("weekly plan availability belongs to another athlete")
        if availability.week_start != plan.week_start:
            raise DomainIntegrityError("weekly plan date differs from its availability")
        if self.session.get(WeeklySchedulingPolicyRecord, plan.scheduling_policy_id) is None:
            raise DomainIntegrityError("weekly scheduling policy does not exist")
        window_by_id = {item.id: item for item in availability.windows}
        for session in plan.sessions:
            prescription = self.session.get(SessionPrescriptionRecord, session.prescription_id)
            allocation = self.session.get(
                BlockResourceAllocationRecord, session.resource_allocation_id
            )
            window = window_by_id.get(session.availability_window_id)
            if prescription is None or prescription.block_plan_id != block.id:
                raise DomainIntegrityError("planned session prescription belongs to another block")
            if allocation is None or allocation.block_plan_id != block.id:
                raise DomainIntegrityError("planned session allocation belongs to another block")
            if prescription.resource_allocation_id != allocation.id:
                raise DomainIntegrityError("planned session prescription and allocation differ")
            if window is None or window.environment_id != session.environment_id:
                raise DomainIntegrityError("planned session availability window is invalid")
            if session.starts_at < window.starts_at or session.ends_at > window.ends_at:
                raise DomainIntegrityError("planned session falls outside its availability window")
        record = WeeklyPlanRecord(
            id=plan.id,
            schema_version=plan.schema_version,
            created_at=plan.created_at,
            athlete_id=plan.athlete_id,
            block_plan_id=plan.block_plan_id,
            weekly_availability_id=plan.weekly_availability_id,
            scheduling_policy_id=plan.scheduling_policy_id,
            week_start=plan.week_start,
            block_week=plan.block_week,
            status=plan.status.value,
            issues=[item.model_dump(mode="json") for item in plan.issues],
            generated_at=plan.generated_at,
            rule_version=plan.rule_version,
        )
        record.sessions = [
            PlannedSessionRecord(
                id=item.id,
                schema_version=item.schema_version,
                created_at=item.created_at,
                weekly_plan_id=plan.id,
                prescription_id=item.prescription_id,
                resource_allocation_id=item.resource_allocation_id,
                occurrence_index=item.occurrence_index,
                availability_window_id=item.availability_window_id,
                environment_id=item.environment_id,
                starts_at=item.starts_at,
                ends_at=item.ends_at,
                planned_duration_minutes=item.planned_duration_minutes,
                fatigue_cost=item.fatigue_cost.value,
                position=position,
            )
            for position, item in enumerate(plan.sessions)
        ]
        self.session.add(record)

    def get_weekly_plan(self, plan_id: UUID) -> WeeklyPlan | None:
        record = self.session.get(WeeklyPlanRecord, plan_id)
        if record is None:
            return None
        return WeeklyPlan(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            athlete_id=record.athlete_id,
            block_plan_id=record.block_plan_id,
            weekly_availability_id=record.weekly_availability_id,
            scheduling_policy_id=record.scheduling_policy_id,
            week_start=record.week_start,
            block_week=record.block_week,
            status=record.status,
            sessions=tuple(
                PlannedSession(
                    id=item.id,
                    schema_version=item.schema_version,
                    created_at=item.created_at,
                    prescription_id=item.prescription_id,
                    resource_allocation_id=item.resource_allocation_id,
                    occurrence_index=item.occurrence_index,
                    availability_window_id=item.availability_window_id,
                    environment_id=item.environment_id,
                    starts_at=item.starts_at,
                    ends_at=item.ends_at,
                    planned_duration_minutes=item.planned_duration_minutes,
                    fatigue_cost=item.fatigue_cost,
                )
                for item in record.sessions
            ),
            issues=tuple(SchedulingIssue.model_validate(item) for item in record.issues),
            generated_at=record.generated_at,
            rule_version=record.rule_version,
        )

    def add_session_safety_policy(self, policy: SessionSafetyPolicy) -> None:
        self._require_ids_exist(
            EvidenceClaimRecord.id,
            policy.evidence_claim_ids,
            "session safety policy evidence claims",
        )
        record = SessionSafetyPolicyRecord(
            id=policy.id,
            schema_version=policy.schema_version,
            created_at=policy.created_at,
            allowed_modifications=[item.value for item in policy.allowed_modifications],
            limited_readiness_modifications=[
                item.value for item in policy.limited_readiness_modifications
            ],
            unusual_soreness_modifications=[
                item.value for item in policy.unusual_soreness_modifications
            ],
            sleep_disruption_modifications=[
                item.value for item in policy.sleep_disruption_modifications
            ],
            schedule_limitation_modifications=[
                item.value for item in policy.schedule_limitation_modifications
            ],
            rationale=policy.rationale,
            policy_version=policy.policy_version,
        )
        record.evidence_links = [
            SessionSafetyPolicyEvidenceClaimRecord(
                safety_policy_id=policy.id,
                evidence_claim_id=claim_id,
                position=position,
            )
            for position, claim_id in enumerate(policy.evidence_claim_ids)
        ]
        self.session.add(record)

    def get_session_safety_policy(self, policy_id: UUID) -> SessionSafetyPolicy | None:
        record = self.session.get(SessionSafetyPolicyRecord, policy_id)
        if record is None:
            return None
        return SessionSafetyPolicy(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            allowed_modifications=tuple(record.allowed_modifications),
            limited_readiness_modifications=tuple(record.limited_readiness_modifications),
            unusual_soreness_modifications=tuple(record.unusual_soreness_modifications),
            sleep_disruption_modifications=tuple(record.sleep_disruption_modifications),
            schedule_limitation_modifications=tuple(record.schedule_limitation_modifications),
            evidence_claim_ids=tuple(link.evidence_claim_id for link in record.evidence_links),
            rationale=record.rationale,
            policy_version=record.policy_version,
        )

    def add_session_safety_decision(self, decision: SessionSafetyDecision) -> None:
        self._require_athlete(decision.athlete_id)
        plan = self.session.get(WeeklyPlanRecord, decision.weekly_plan_id)
        planned_session = self.session.get(PlannedSessionRecord, decision.planned_session_id)
        if plan is None or plan.athlete_id != decision.athlete_id:
            raise DomainIntegrityError("safety decision weekly plan belongs to another athlete")
        if planned_session is None or planned_session.weekly_plan_id != plan.id:
            raise DomainIntegrityError("safety decision session does not belong to its weekly plan")
        if self.session.get(SessionSafetyPolicyRecord, decision.safety_policy_id) is None:
            raise DomainIntegrityError("session safety policy does not exist")
        if decision.related_session_execution_id is not None:
            execution = self.session.get(
                SessionExecutionRecord, decision.related_session_execution_id
            )
            if execution is None:
                raise DomainIntegrityError("related session execution does not exist")
            if (
                execution.athlete_id != decision.athlete_id
                or execution.weekly_plan_id != decision.weekly_plan_id
                or execution.planned_session_id != decision.planned_session_id
            ):
                raise DomainIntegrityError(
                    "related execution does not match the safety decision session"
                )
        observations = self._observations_by_id(decision.source_observation_ids)
        if {item.id for item in observations} != set(decision.source_observation_ids):
            raise DomainIntegrityError("one or more safety decision observations do not exist")
        if any(item.athlete_id != decision.athlete_id for item in observations):
            raise DomainIntegrityError("safety decision observations belong to another athlete")
        expected_observation_type = f"session_safety_{decision.timing.value}"
        if any(
            item.source != "user_report" or item.observation_type != expected_observation_type
            for item in observations
        ):
            raise DomainIntegrityError(
                "safety decision requires its structured user-report observation"
            )
        expected_context = {
            "weekly_plan_id": str(decision.weekly_plan_id),
            "planned_session_id": str(decision.planned_session_id),
            "related_session_execution_id": (
                str(decision.related_session_execution_id)
                if decision.related_session_execution_id is not None
                else None
            ),
            "timing": decision.timing.value,
        }
        if any(
            any(item.context.get(key) != value for key, value in expected_context.items())
            for item in observations
        ):
            raise DomainIntegrityError(
                "safety observation context does not match the safety decision"
            )

        record = SessionSafetyDecisionRecord(
            id=decision.id,
            schema_version=decision.schema_version,
            created_at=decision.created_at,
            athlete_id=decision.athlete_id,
            weekly_plan_id=decision.weekly_plan_id,
            planned_session_id=decision.planned_session_id,
            related_session_execution_id=decision.related_session_execution_id,
            safety_policy_id=decision.safety_policy_id,
            timing=decision.timing.value,
            outcome=decision.outcome.value,
            required_modifications=[item.value for item in decision.required_modifications],
            rationale=list(decision.rationale),
            decided_at=decision.decided_at,
            rule_version=decision.rule_version,
        )
        record.observation_links = [
            SessionSafetyDecisionObservationRecord(
                safety_decision_id=decision.id,
                observation_id=observation_id,
                position=position,
            )
            for position, observation_id in enumerate(decision.source_observation_ids)
        ]
        self.session.add(record)

    def get_session_safety_decision(self, decision_id: UUID) -> SessionSafetyDecision | None:
        record = self.session.get(SessionSafetyDecisionRecord, decision_id)
        if record is None:
            return None
        return SessionSafetyDecision(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            athlete_id=record.athlete_id,
            weekly_plan_id=record.weekly_plan_id,
            planned_session_id=record.planned_session_id,
            related_session_execution_id=record.related_session_execution_id,
            safety_policy_id=record.safety_policy_id,
            timing=record.timing,
            outcome=record.outcome,
            required_modifications=tuple(record.required_modifications),
            source_observation_ids=tuple(link.observation_id for link in record.observation_links),
            rationale=tuple(record.rationale),
            decided_at=record.decided_at,
            rule_version=record.rule_version,
        )

    def add_session_execution(self, execution: SessionExecution) -> None:
        self._require_athlete(execution.athlete_id)
        plan = self.session.get(WeeklyPlanRecord, execution.weekly_plan_id)
        planned_session = self.session.get(PlannedSessionRecord, execution.planned_session_id)
        prescription = self.session.get(SessionPrescriptionRecord, execution.prescription_id)
        safety_decision = self.session.get(
            SessionSafetyDecisionRecord, execution.pre_session_safety_decision_id
        )
        if plan is None or plan.athlete_id != execution.athlete_id:
            raise DomainIntegrityError("session execution weekly plan belongs to another athlete")
        if planned_session is None or planned_session.weekly_plan_id != plan.id:
            raise DomainIntegrityError("executed session does not belong to its weekly plan")
        if (
            prescription is None
            or prescription.id != planned_session.prescription_id
            or prescription.athlete_id != execution.athlete_id
        ):
            raise DomainIntegrityError("session execution prescription does not match its plan")
        if safety_decision is None:
            raise DomainIntegrityError("pre-session safety decision does not exist")
        if (
            safety_decision.timing != "pre_session"
            or safety_decision.athlete_id != execution.athlete_id
            or safety_decision.weekly_plan_id != execution.weekly_plan_id
            or safety_decision.planned_session_id != execution.planned_session_id
        ):
            raise DomainIntegrityError("safety decision does not authorize this session")
        if safety_decision.outcome not in {"proceed", "modify"}:
            raise DomainIntegrityError("blocking safety decision cannot authorize execution")
        if set(safety_decision.required_modifications) != {
            item.value for item in execution.applied_modifications
        }:
            raise DomainIntegrityError("execution does not acknowledge required modifications")
        observation = self.session.get(ObservationRecord, execution.performance_observation_id)
        if observation is None or observation.athlete_id != execution.athlete_id:
            raise DomainIntegrityError("performance observation is missing or belongs elsewhere")
        if (
            observation.source != "workout_result"
            or observation.observation_type != "session_execution"
        ):
            raise DomainIntegrityError(
                "session execution requires a direct workout-result observation"
            )
        expected_context = {
            "weekly_plan_id": str(execution.weekly_plan_id),
            "planned_session_id": str(execution.planned_session_id),
            "prescription_id": str(execution.prescription_id),
            "pre_session_safety_decision_id": str(execution.pre_session_safety_decision_id),
        }
        if any(observation.context.get(key) != value for key, value in expected_context.items()):
            raise DomainIntegrityError(
                "performance observation context does not match the session execution"
            )

        record = SessionExecutionRecord(
            id=execution.id,
            schema_version=execution.schema_version,
            created_at=execution.created_at,
            athlete_id=execution.athlete_id,
            weekly_plan_id=execution.weekly_plan_id,
            planned_session_id=execution.planned_session_id,
            prescription_id=execution.prescription_id,
            pre_session_safety_decision_id=execution.pre_session_safety_decision_id,
            status=execution.status.value,
            started_at=execution.started_at,
            ended_at=execution.ended_at,
            applied_modifications=[item.value for item in execution.applied_modifications],
            session_rpe=execution.session_rpe,
            note=execution.note,
            performance_observation_id=execution.performance_observation_id,
            logged_at=execution.logged_at,
            rule_version=execution.rule_version,
        )
        record.performances = [
            SetPerformanceRecord(
                id=item.id,
                schema_version=item.schema_version,
                created_at=item.created_at,
                session_execution_id=execution.id,
                set_index=item.set_index,
                performed=item.performed,
                target_completed=item.target_completed,
                actual_repetitions=item.actual_repetitions,
                actual_duration_seconds=item.actual_duration_seconds,
                load_value=item.load_value,
                load_unit=item.load_unit,
                effort_rpe=item.effort_rpe,
                technique_constraint_met=item.technique_constraint_met,
            )
            for item in execution.performances
        ]
        self.session.add(record)

    def get_session_execution(self, execution_id: UUID) -> SessionExecution | None:
        record = self.session.get(SessionExecutionRecord, execution_id)
        if record is None:
            return None
        return SessionExecution(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            athlete_id=record.athlete_id,
            weekly_plan_id=record.weekly_plan_id,
            planned_session_id=record.planned_session_id,
            prescription_id=record.prescription_id,
            pre_session_safety_decision_id=record.pre_session_safety_decision_id,
            status=record.status,
            started_at=record.started_at,
            ended_at=record.ended_at,
            performances=tuple(
                SetPerformance(
                    id=item.id,
                    schema_version=item.schema_version,
                    created_at=item.created_at,
                    set_index=item.set_index,
                    performed=item.performed,
                    target_completed=item.target_completed,
                    actual_repetitions=item.actual_repetitions,
                    actual_duration_seconds=item.actual_duration_seconds,
                    load_value=item.load_value,
                    load_unit=item.load_unit,
                    effort_rpe=item.effort_rpe,
                    technique_constraint_met=item.technique_constraint_met,
                )
                for item in record.performances
            ),
            applied_modifications=tuple(record.applied_modifications),
            session_rpe=record.session_rpe,
            note=record.note,
            performance_observation_id=record.performance_observation_id,
            logged_at=record.logged_at,
            rule_version=record.rule_version,
        )

    def add_session_adherence(self, adherence: SessionAdherence) -> None:
        execution = self.session.get(SessionExecutionRecord, adherence.session_execution_id)
        planned_session = self.session.get(PlannedSessionRecord, adherence.planned_session_id)
        if execution is None or execution.athlete_id != adherence.athlete_id:
            raise DomainIntegrityError("adherence execution is missing or belongs elsewhere")
        if (
            planned_session is None
            or planned_session.id != execution.planned_session_id
            or adherence.prescription_id != execution.prescription_id
            or adherence.prescription_id != planned_session.prescription_id
        ):
            raise DomainIntegrityError("adherence does not match the executed prescription")
        observations = self._observations_by_id(adherence.source_observation_ids)
        if {item.id for item in observations} != set(adherence.source_observation_ids):
            raise DomainIntegrityError("one or more adherence observations do not exist")
        if any(item.athlete_id != adherence.athlete_id for item in observations):
            raise DomainIntegrityError("adherence observations belong to another athlete")
        if execution.performance_observation_id not in adherence.source_observation_ids:
            raise DomainIntegrityError("adherence must reference the performance observation")

        record = SessionAdherenceRecord(
            id=adherence.id,
            schema_version=adherence.schema_version,
            created_at=adherence.created_at,
            kind=adherence.kind,
            athlete_id=adherence.athlete_id,
            session_execution_id=adherence.session_execution_id,
            planned_session_id=adherence.planned_session_id,
            prescription_id=adherence.prescription_id,
            prescribed_sets=adherence.prescribed_sets,
            performed_sets=adherence.performed_sets,
            target_completed_sets=adherence.target_completed_sets,
            prescribed_dose_total=adherence.prescribed_dose_total,
            actual_dose_total=adherence.actual_dose_total,
            dose_unit=adherence.dose_unit,
            set_completion_ratio=adherence.set_completion_ratio,
            dose_completion_ratio=adherence.dose_completion_ratio,
            calculated_at=adherence.calculated_at,
            calculation_method=adherence.calculation_method,
            rule_version=adherence.rule_version,
        )
        record.observation_links = [
            SessionAdherenceObservationRecord(
                session_adherence_id=adherence.id,
                observation_id=observation_id,
                position=position,
            )
            for position, observation_id in enumerate(adherence.source_observation_ids)
        ]
        self.session.add(record)

    def get_session_adherence(self, adherence_id: UUID) -> SessionAdherence | None:
        record = self.session.get(SessionAdherenceRecord, adherence_id)
        if record is None:
            return None
        return SessionAdherence(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            kind=record.kind,
            athlete_id=record.athlete_id,
            session_execution_id=record.session_execution_id,
            planned_session_id=record.planned_session_id,
            prescription_id=record.prescription_id,
            prescribed_sets=record.prescribed_sets,
            performed_sets=record.performed_sets,
            target_completed_sets=record.target_completed_sets,
            prescribed_dose_total=record.prescribed_dose_total,
            actual_dose_total=record.actual_dose_total,
            dose_unit=record.dose_unit,
            set_completion_ratio=record.set_completion_ratio,
            dose_completion_ratio=record.dose_completion_ratio,
            source_observation_ids=tuple(link.observation_id for link in record.observation_links),
            calculated_at=record.calculated_at,
            calculation_method=record.calculation_method,
            rule_version=record.rule_version,
        )

    def add_progression_policy(self, policy: ProgressionPolicy) -> None:
        self._require_ids_exist(
            EvidenceClaimRecord.id, policy.evidence_claim_ids, "progression evidence"
        )
        record = ProgressionPolicyRecord(
            id=policy.id,
            schema_version=policy.schema_version,
            created_at=policy.created_at,
            reference=policy.reference,
            minimum_set_completion_ratio=policy.minimum_set_completion_ratio,
            minimum_dose_completion_ratio=policy.minimum_dose_completion_ratio,
            maximum_session_rpe=policy.maximum_session_rpe,
            require_technique_constraint=policy.require_technique_constraint,
            adjustment=policy.adjustment.model_dump(mode="json"),
            exposure_type=policy.exposure_type.value if policy.exposure_type else None,
            rationale=policy.rationale,
            policy_version=policy.policy_version,
        )
        record.evidence_links = [
            ProgressionPolicyEvidenceRecord(
                progression_policy_id=policy.id, evidence_claim_id=item, position=position
            )
            for position, item in enumerate(policy.evidence_claim_ids)
        ]
        self.session.add(record)

    def get_progression_policy(self, record_id: UUID) -> ProgressionPolicy | None:
        record = self.session.get(ProgressionPolicyRecord, record_id)
        return (
            None
            if record is None
            else ProgressionPolicy(
                id=record.id,
                schema_version=record.schema_version,
                created_at=record.created_at,
                reference=record.reference,
                minimum_set_completion_ratio=record.minimum_set_completion_ratio,
                minimum_dose_completion_ratio=record.minimum_dose_completion_ratio,
                maximum_session_rpe=record.maximum_session_rpe,
                require_technique_constraint=record.require_technique_constraint,
                adjustment=record.adjustment,
                exposure_type=record.exposure_type,
                evidence_claim_ids=tuple(item.evidence_claim_id for item in record.evidence_links),
                rationale=record.rationale,
                policy_version=record.policy_version,
            )
        )

    def add_exposure_definition(self, definition: ExposureDefinition) -> None:
        self._require_ids_exist(
            EvidenceClaimRecord.id, definition.evidence_claim_ids, "exposure evidence"
        )
        if self.session.get(ExerciseRecord, definition.exercise_id) is None:
            raise DomainIntegrityError("exposure definition exercise does not exist")
        record = ExposureDefinitionRecord(
            id=definition.id,
            schema_version=definition.schema_version,
            created_at=definition.created_at,
            exercise_id=definition.exercise_id,
            exposure_type=definition.exposure_type.value,
            dose_unit=definition.dose_unit,
            rationale=definition.rationale,
            definition_version=definition.definition_version,
        )
        record.evidence_links = [
            ExposureDefinitionEvidenceRecord(
                exposure_definition_id=definition.id, evidence_claim_id=item, position=position
            )
            for position, item in enumerate(definition.evidence_claim_ids)
        ]
        self.session.add(record)

    def get_exposure_definition(self, record_id: UUID) -> ExposureDefinition | None:
        record = self.session.get(ExposureDefinitionRecord, record_id)
        return (
            None
            if record is None
            else ExposureDefinition(
                id=record.id,
                schema_version=record.schema_version,
                created_at=record.created_at,
                exercise_id=record.exercise_id,
                exposure_type=record.exposure_type,
                dose_unit=record.dose_unit,
                evidence_claim_ids=tuple(item.evidence_claim_id for item in record.evidence_links),
                rationale=record.rationale,
                definition_version=record.definition_version,
            )
        )

    def add_exposure_entry(self, entry: ExposureEntry) -> None:
        execution = self.session.get(SessionExecutionRecord, entry.session_execution_id)
        definition = self.session.get(ExposureDefinitionRecord, entry.exposure_definition_id)
        if execution is None or execution.athlete_id != entry.athlete_id:
            raise DomainIntegrityError("exposure entry execution is missing or belongs elsewhere")
        if (
            definition is None
            or execution.prescription_id != entry.prescription_id
            or execution.planned_session_id != entry.planned_session_id
            or definition.exposure_type != entry.exposure_type.value
            or definition.dose_unit != entry.dose_unit
            or execution.performance_observation_id not in entry.source_observation_ids
        ):
            raise DomainIntegrityError("exposure entry does not match its execution or definition")
        self._require_ids_exist(
            ObservationRecord.id, entry.source_observation_ids, "exposure observations"
        )
        record = ExposureEntryRecord(
            id=entry.id,
            schema_version=entry.schema_version,
            created_at=entry.created_at,
            kind=entry.kind,
            athlete_id=entry.athlete_id,
            session_execution_id=entry.session_execution_id,
            planned_session_id=entry.planned_session_id,
            prescription_id=entry.prescription_id,
            exposure_definition_id=entry.exposure_definition_id,
            exposure_type=entry.exposure_type.value,
            dose_value=entry.dose_value,
            dose_unit=entry.dose_unit,
            occurred_at=entry.occurred_at,
            calculation_method=entry.calculation_method,
            rule_version=entry.rule_version,
        )
        record.observation_links = [
            ExposureEntryObservationRecord(
                exposure_entry_id=entry.id, observation_id=item, position=position
            )
            for position, item in enumerate(entry.source_observation_ids)
        ]
        self.session.add(record)

    def get_exposure_entry(self, record_id: UUID) -> ExposureEntry | None:
        record = self.session.get(ExposureEntryRecord, record_id)
        return (
            None
            if record is None
            else ExposureEntry(
                id=record.id,
                schema_version=record.schema_version,
                created_at=record.created_at,
                kind=record.kind,
                athlete_id=record.athlete_id,
                session_execution_id=record.session_execution_id,
                planned_session_id=record.planned_session_id,
                prescription_id=record.prescription_id,
                exposure_definition_id=record.exposure_definition_id,
                exposure_type=record.exposure_type,
                dose_value=record.dose_value,
                dose_unit=record.dose_unit,
                source_observation_ids=tuple(
                    item.observation_id for item in record.observation_links
                ),
                occurred_at=record.occurred_at,
                calculation_method=record.calculation_method,
                rule_version=record.rule_version,
            )
        )

    def add_exposure_progression_policy(self, policy: ExposureProgressionPolicy) -> None:
        self._require_ids_exist(
            EvidenceClaimRecord.id, policy.evidence_claim_ids, "exposure policy evidence"
        )
        record = ExposureProgressionPolicyRecord(
            id=policy.id,
            schema_version=policy.schema_version,
            created_at=policy.created_at,
            exposure_type=policy.exposure_type.value,
            dose_unit=policy.dose_unit,
            lookback_days=policy.lookback_days,
            minimum_recent_entries=policy.minimum_recent_entries,
            maximum_initial_dose=policy.maximum_initial_dose,
            maximum_relative_increase=policy.maximum_relative_increase,
            maximum_absolute_increase=policy.maximum_absolute_increase,
            rationale=policy.rationale,
            policy_version=policy.policy_version,
        )
        record.evidence_links = [
            ExposureProgressionPolicyEvidenceRecord(
                exposure_policy_id=policy.id, evidence_claim_id=item, position=position
            )
            for position, item in enumerate(policy.evidence_claim_ids)
        ]
        self.session.add(record)

    def add_exposure_validation_decision(self, decision: ExposureValidationDecision) -> None:
        self._require_ids_exist(
            ExposureEntryRecord.id, decision.source_exposure_entry_ids, "exposure entries"
        )
        if self.session.get(ExposureProgressionPolicyRecord, decision.exposure_policy_id) is None:
            raise DomainIntegrityError("exposure progression policy does not exist")
        record = ExposureValidationDecisionRecord(
            id=decision.id,
            schema_version=decision.schema_version,
            created_at=decision.created_at,
            athlete_id=decision.athlete_id,
            prescription_id=decision.prescription_id,
            exposure_policy_id=decision.exposure_policy_id,
            exposure_type=decision.exposure_type.value,
            proposed_dose=decision.proposed_dose,
            dose_unit=decision.dose_unit,
            baseline_dose=decision.baseline_dose,
            maximum_allowed_dose=decision.maximum_allowed_dose,
            outcome=decision.outcome.value,
            rationale=list(decision.rationale),
            decided_at=decision.decided_at,
            rule_version=decision.rule_version,
        )
        record.entry_links = [
            ExposureValidationEntryRecord(
                exposure_validation_decision_id=decision.id,
                exposure_entry_id=item,
                position=position,
            )
            for position, item in enumerate(decision.source_exposure_entry_ids)
        ]
        self.session.add(record)

    def add_progression_decision(self, decision: ProgressionDecision) -> None:
        self._require_ids_exist(
            ObservationRecord.id, decision.source_observation_ids, "progression observations"
        )
        execution = self.session.get(SessionExecutionRecord, decision.session_execution_id)
        adherence = self.session.get(SessionAdherenceRecord, decision.session_adherence_id)
        if (
            execution is None
            or adherence is None
            or execution.athlete_id != decision.athlete_id
            or execution.prescription_id != decision.prescription_id
            or adherence.session_execution_id != execution.id
        ):
            raise DomainIntegrityError("progression decision execution chain is invalid")
        if self.session.get(ProgressionPolicyRecord, decision.progression_policy_id) is None:
            raise DomainIntegrityError("progression policy does not exist")
        self._require_ids_exist(
            SessionSafetyDecisionRecord.id,
            decision.post_session_safety_decision_ids,
            "post-session safety decisions",
        )
        if (
            decision.exposure_validation_decision_id is not None
            and self.session.get(
                ExposureValidationDecisionRecord, decision.exposure_validation_decision_id
            )
            is None
        ):
            raise DomainIntegrityError("exposure validation decision does not exist")
        record = ProgressionDecisionRecord(
            id=decision.id,
            schema_version=decision.schema_version,
            created_at=decision.created_at,
            athlete_id=decision.athlete_id,
            weekly_plan_id=decision.weekly_plan_id,
            planned_session_id=decision.planned_session_id,
            prescription_id=decision.prescription_id,
            session_execution_id=decision.session_execution_id,
            session_adherence_id=decision.session_adherence_id,
            progression_policy_id=decision.progression_policy_id,
            exposure_validation_decision_id=decision.exposure_validation_decision_id,
            outcome=decision.outcome.value,
            adjustment=decision.adjustment.model_dump(mode="json") if decision.adjustment else None,
            rationale=list(decision.rationale),
            decided_at=decision.decided_at,
            rule_version=decision.rule_version,
        )
        record.safety_links = [
            ProgressionDecisionSafetyRecord(
                progression_decision_id=decision.id, safety_decision_id=item, position=position
            )
            for position, item in enumerate(decision.post_session_safety_decision_ids)
        ]
        record.observation_links = [
            ProgressionDecisionObservationRecord(
                progression_decision_id=decision.id, observation_id=item, position=position
            )
            for position, item in enumerate(decision.source_observation_ids)
        ]
        self.session.add(record)

    def get_exposure_progression_policy(self, record_id: UUID) -> ExposureProgressionPolicy | None:
        record = self.session.get(ExposureProgressionPolicyRecord, record_id)
        if record is None:
            return None
        return ExposureProgressionPolicy(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            exposure_type=record.exposure_type,
            dose_unit=record.dose_unit,
            lookback_days=record.lookback_days,
            minimum_recent_entries=record.minimum_recent_entries,
            maximum_initial_dose=record.maximum_initial_dose,
            maximum_relative_increase=record.maximum_relative_increase,
            maximum_absolute_increase=record.maximum_absolute_increase,
            evidence_claim_ids=tuple(item.evidence_claim_id for item in record.evidence_links),
            rationale=record.rationale,
            policy_version=record.policy_version,
        )

    def get_exposure_validation_decision(
        self, record_id: UUID
    ) -> ExposureValidationDecision | None:
        record = self.session.get(ExposureValidationDecisionRecord, record_id)
        if record is None:
            return None
        return ExposureValidationDecision(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            athlete_id=record.athlete_id,
            prescription_id=record.prescription_id,
            exposure_policy_id=record.exposure_policy_id,
            exposure_type=record.exposure_type,
            proposed_dose=record.proposed_dose,
            dose_unit=record.dose_unit,
            baseline_dose=record.baseline_dose,
            maximum_allowed_dose=record.maximum_allowed_dose,
            source_exposure_entry_ids=tuple(item.exposure_entry_id for item in record.entry_links),
            outcome=record.outcome,
            rationale=tuple(record.rationale),
            decided_at=record.decided_at,
            rule_version=record.rule_version,
        )

    def get_progression_decision(self, record_id: UUID) -> ProgressionDecision | None:
        record = self.session.get(ProgressionDecisionRecord, record_id)
        if record is None:
            return None
        return ProgressionDecision(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            athlete_id=record.athlete_id,
            weekly_plan_id=record.weekly_plan_id,
            planned_session_id=record.planned_session_id,
            prescription_id=record.prescription_id,
            session_execution_id=record.session_execution_id,
            session_adherence_id=record.session_adherence_id,
            progression_policy_id=record.progression_policy_id,
            post_session_safety_decision_ids=tuple(
                item.safety_decision_id for item in record.safety_links
            ),
            exposure_validation_decision_id=record.exposure_validation_decision_id,
            outcome=record.outcome,
            adjustment=record.adjustment,
            source_observation_ids=tuple(item.observation_id for item in record.observation_links),
            rationale=tuple(record.rationale),
            decided_at=record.decided_at,
            rule_version=record.rule_version,
        )

    def add_training_response(self, response: TrainingResponse) -> None:
        block = self.session.get(BlockPlanRecord, response.block_plan_id)
        baseline = self.session.get(
            CapabilityEstimateRecord, response.baseline_capability_estimate_id
        )
        followup = self.session.get(
            CapabilityEstimateRecord, response.followup_capability_estimate_id
        )
        if block is None or block.athlete_id != response.athlete_id:
            raise DomainIntegrityError("training response block belongs to another athlete")
        if (
            baseline is None
            or followup is None
            or baseline.athlete_id != response.athlete_id
            or followup.athlete_id != response.athlete_id
        ):
            raise DomainIntegrityError("training response estimates belong to another athlete")
        self._require_ids_exist(
            SessionPrescriptionRecord.id, response.prescription_ids, "response prescriptions"
        )
        self._require_ids_exist(
            SessionExecutionRecord.id, response.session_execution_ids, "response executions"
        )
        self._require_ids_exist(
            SessionAdherenceRecord.id, response.session_adherence_ids, "response adherence"
        )
        self._require_ids_exist(
            ObservationRecord.id, response.source_observation_ids, "response observations"
        )
        record = TrainingResponseRecord(
            id=response.id,
            schema_version=response.schema_version,
            created_at=response.created_at,
            kind=response.kind,
            athlete_id=response.athlete_id,
            block_plan_id=response.block_plan_id,
            adaptation_id=response.adaptation_id,
            intervention_summary=response.intervention_summary,
            prescribed_sessions=response.prescribed_sessions,
            completed_sessions=response.completed_sessions,
            prescribed_dose_total=response.prescribed_dose_total,
            actual_dose_total=response.actual_dose_total,
            dose_unit=response.dose_unit,
            adherence_ratio=response.adherence_ratio,
            baseline_capability_estimate_id=response.baseline_capability_estimate_id,
            followup_capability_estimate_id=response.followup_capability_estimate_id,
            baseline_value=response.baseline_value,
            followup_value=response.followup_value,
            observed_change=response.observed_change,
            measurement_uncertainty=response.measurement_uncertainty,
            contextual_factors=list(response.contextual_factors),
            confidence=response.confidence.value,
            calculated_at=response.calculated_at,
            calculation_method=response.calculation_method,
            rule_version=response.rule_version,
        )
        record.prescription_links = [
            TrainingResponsePrescriptionRecord(
                training_response_id=response.id, prescription_id=item, position=position
            )
            for position, item in enumerate(response.prescription_ids)
        ]
        record.execution_links = [
            TrainingResponseExecutionRecord(
                training_response_id=response.id, execution_id=item, position=position
            )
            for position, item in enumerate(response.session_execution_ids)
        ]
        record.adherence_links = [
            TrainingResponseAdherenceRecord(
                training_response_id=response.id, adherence_id=item, position=position
            )
            for position, item in enumerate(response.session_adherence_ids)
        ]
        record.observation_links = [
            TrainingResponseObservationRecord(
                training_response_id=response.id, observation_id=item, position=position
            )
            for position, item in enumerate(response.source_observation_ids)
        ]
        self.session.add(record)

    def get_training_response(self, record_id: UUID) -> TrainingResponse | None:
        record = self.session.get(TrainingResponseRecord, record_id)
        if record is None:
            return None
        return TrainingResponse(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            kind=record.kind,
            athlete_id=record.athlete_id,
            block_plan_id=record.block_plan_id,
            adaptation_id=record.adaptation_id,
            intervention_summary=record.intervention_summary,
            prescription_ids=tuple(item.prescription_id for item in record.prescription_links),
            session_execution_ids=tuple(item.execution_id for item in record.execution_links),
            session_adherence_ids=tuple(item.adherence_id for item in record.adherence_links),
            prescribed_sessions=record.prescribed_sessions,
            completed_sessions=record.completed_sessions,
            prescribed_dose_total=record.prescribed_dose_total,
            actual_dose_total=record.actual_dose_total,
            dose_unit=record.dose_unit,
            adherence_ratio=record.adherence_ratio,
            baseline_capability_estimate_id=record.baseline_capability_estimate_id,
            followup_capability_estimate_id=record.followup_capability_estimate_id,
            baseline_value=record.baseline_value,
            followup_value=record.followup_value,
            observed_change=record.observed_change,
            measurement_uncertainty=record.measurement_uncertainty,
            contextual_factors=tuple(record.contextual_factors),
            confidence=record.confidence,
            source_observation_ids=tuple(item.observation_id for item in record.observation_links),
            calculated_at=record.calculated_at,
            calculation_method=record.calculation_method,
            rule_version=record.rule_version,
        )

    def add_block_review_policy(self, policy: BlockReviewPolicy) -> None:
        self._require_ids_exist(
            EvidenceClaimRecord.id, policy.evidence_claim_ids, "block review evidence"
        )
        record = BlockReviewPolicyRecord(
            id=policy.id,
            schema_version=policy.schema_version,
            created_at=policy.created_at,
            minimum_adherence_ratio=policy.minimum_adherence_ratio,
            minimum_response_confidence=policy.minimum_response_confidence.value,
            rationale=policy.rationale,
            policy_version=policy.policy_version,
        )
        record.evidence_links = [
            BlockReviewPolicyEvidenceRecord(
                block_review_policy_id=policy.id, evidence_claim_id=item, position=position
            )
            for position, item in enumerate(policy.evidence_claim_ids)
        ]
        self.session.add(record)

    def get_block_review_policy(self, record_id: UUID) -> BlockReviewPolicy | None:
        record = self.session.get(BlockReviewPolicyRecord, record_id)
        if record is None:
            return None
        return BlockReviewPolicy(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            minimum_adherence_ratio=record.minimum_adherence_ratio,
            minimum_response_confidence=record.minimum_response_confidence,
            evidence_claim_ids=tuple(item.evidence_claim_id for item in record.evidence_links),
            rationale=record.rationale,
            policy_version=record.policy_version,
        )

    def add_block_review(self, review: BlockReview) -> None:
        block = self.session.get(BlockPlanRecord, review.block_plan_id)
        if (
            block is None
            or block.athlete_id != review.athlete_id
            or block.hypothesis != review.block_hypothesis
        ):
            raise DomainIntegrityError("block review does not match its immutable block")
        if self.session.get(BlockReviewPolicyRecord, review.block_review_policy_id) is None:
            raise DomainIntegrityError("block review policy does not exist")
        self._require_ids_exist(
            TrainingResponseRecord.id, review.training_response_ids, "training responses"
        )
        self._require_ids_exist(
            SessionSafetyDecisionRecord.id,
            review.post_session_safety_decision_ids,
            "review safety decisions",
        )
        self._require_ids_exist(
            ObservationRecord.id, review.source_observation_ids, "review observations"
        )
        self._require_ids_exist(
            EvidenceClaimRecord.id, review.evidence_claim_ids, "review evidence"
        )
        record = BlockReviewRecord(
            id=review.id,
            schema_version=review.schema_version,
            created_at=review.created_at,
            kind=review.kind,
            athlete_id=review.athlete_id,
            block_plan_id=review.block_plan_id,
            block_hypothesis=review.block_hypothesis,
            block_review_policy_id=review.block_review_policy_id,
            prescribed_sessions=review.prescribed_sessions,
            completed_sessions=review.completed_sessions,
            aggregate_adherence_ratio=review.aggregate_adherence_ratio,
            outcome=review.outcome.value,
            rationale=list(review.rationale),
            reviewed_at=review.reviewed_at,
            rule_version=review.rule_version,
        )
        record.response_links = [
            BlockReviewResponseRecord(
                block_review_id=review.id,
                training_response_id=item.training_response_id,
                comparison_direction=item.comparison_direction.value,
                minimum_meaningful_change=item.minimum_meaningful_change,
                threshold_met=item.threshold_met,
                evaluation_rationale=item.rationale,
                position=position,
            )
            for position, item in enumerate(review.response_evaluations)
        ]
        record.safety_links = [
            BlockReviewSafetyRecord(
                block_review_id=review.id, safety_decision_id=item, position=position
            )
            for position, item in enumerate(review.post_session_safety_decision_ids)
        ]
        record.observation_links = [
            BlockReviewObservationRecord(
                block_review_id=review.id, observation_id=item, position=position
            )
            for position, item in enumerate(review.source_observation_ids)
        ]
        record.evidence_links = [
            BlockReviewEvidenceRecord(
                block_review_id=review.id, evidence_claim_id=item, position=position
            )
            for position, item in enumerate(review.evidence_claim_ids)
        ]
        self.session.add(record)

    def get_block_review(self, record_id: UUID) -> BlockReview | None:
        record = self.session.get(BlockReviewRecord, record_id)
        if record is None:
            return None
        evaluations = tuple(
            ResponseEvaluation(
                training_response_id=item.training_response_id,
                comparison_direction=item.comparison_direction,
                minimum_meaningful_change=item.minimum_meaningful_change,
                threshold_met=item.threshold_met,
                rationale=item.evaluation_rationale,
            )
            for item in record.response_links
        )
        return BlockReview(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            kind=record.kind,
            athlete_id=record.athlete_id,
            block_plan_id=record.block_plan_id,
            block_hypothesis=record.block_hypothesis,
            block_review_policy_id=record.block_review_policy_id,
            training_response_ids=tuple(
                item.training_response_id for item in record.response_links
            ),
            response_evaluations=evaluations,
            post_session_safety_decision_ids=tuple(
                item.safety_decision_id for item in record.safety_links
            ),
            prescribed_sessions=record.prescribed_sessions,
            completed_sessions=record.completed_sessions,
            aggregate_adherence_ratio=record.aggregate_adherence_ratio,
            outcome=record.outcome,
            source_observation_ids=tuple(item.observation_id for item in record.observation_links),
            evidence_claim_ids=tuple(item.evidence_claim_id for item in record.evidence_links),
            rationale=tuple(record.rationale),
            reviewed_at=record.reviewed_at,
            rule_version=record.rule_version,
        )

    def get_competency_floor(self, floor_id: UUID) -> CompetencyFloor | None:
        record = self.session.get(CompetencyFloorRecord, floor_id)
        if record is None:
            return None
        return CompetencyFloor(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            domain=record.domain,
            estimate_scope=record.estimate_scope,
            unit_or_scale=record.unit_or_scale,
            threshold=record.threshold,
            comparison_direction=record.comparison_direction,
            population=record.population,
            applicability_notes=record.applicability_notes,
            uncertainty=record.uncertainty,
            evidence_claim_ids=tuple(item.evidence_claim_id for item in record.evidence_links),
            floor_version=record.floor_version,
        )

    def get_capability_need(self, need_id: UUID) -> CapabilityNeed | None:
        record = self.session.get(CapabilityNeedRecord, need_id)
        if record is None:
            return None
        return CapabilityNeed(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            athlete_id=record.athlete_id,
            domain=record.domain,
            competency_floor_id=record.competency_floor_id,
            capability_estimate_id=record.capability_estimate_id,
            status=record.status,
            observed_value=record.observed_value,
            floor_value=record.floor_value,
            unit_or_scale=record.unit_or_scale,
            gap_from_floor=record.gap_from_floor,
            normalized_deficit=record.normalized_deficit,
            confidence=record.confidence,
            rationale=record.rationale,
            evidence_claim_ids=tuple(item.evidence_claim_id for item in record.evidence_links),
            identified_at=record.identified_at,
            rule_version=record.rule_version,
        )

    def get_priority_policy(self, policy_id: UUID) -> PriorityPolicy | None:
        record = self.session.get(PriorityPolicyRecord, policy_id)
        if record is None:
            return None
        return PriorityPolicy(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            deficit_weight=record.deficit_weight,
            general_relevance_weight=record.general_relevance_weight,
            goal_relevance_weight=record.goal_relevance_weight,
            prerequisite_value_weight=record.prerequisite_value_weight,
            expected_trainability_weight=record.expected_trainability_weight,
            transfer_value_weight=record.transfer_value_weight,
            fatigue_cost_weight=record.fatigue_cost_weight,
            time_cost_weight=record.time_cost_weight,
            interference_cost_weight=record.interference_cost_weight,
            cost_penalty=record.cost_penalty,
            confidence_multipliers=record.confidence_multipliers,
            develop_score_threshold=record.develop_score_threshold,
            comparative_advantage_threshold=record.comparative_advantage_threshold,
            severe_deficit_threshold=record.severe_deficit_threshold,
            max_develop_adaptations=record.max_develop_adaptations,
            policy_version=record.policy_version,
        )

    def get_long_range_strategy(self, strategy_id: UUID) -> LongRangeStrategy | None:
        record = self.session.get(LongRangeStrategyRecord, strategy_id)
        if record is None:
            return None
        priorities = tuple(
            AdaptationPriority(
                id=item.id,
                schema_version=item.schema_version,
                created_at=item.created_at,
                adaptation_id=item.adaptation_id,
                capability_need_id=item.capability_need_id,
                state=item.state,
                score=item.score,
                rank=item.rank,
                development_allocation=item.development_allocation,
                score_components=item.score_components,
                reason_codes=tuple(item.reason_codes),
                rationale=tuple(item.rationale),
            )
            for item in record.priority_links
        )
        roadmap = tuple(
            RoadmapItem(
                id=item.id,
                schema_version=item.schema_version,
                created_at=item.created_at,
                adaptation_id=item.adaptation_id,
                current_state=item.current_state,
                sequence_group=item.sequence_group,
                prerequisite_adaptation_ids=tuple(
                    link.adaptation_id for link in item.prerequisite_links
                ),
                rationale=item.rationale,
                review_trigger=item.review_trigger,
            )
            for item in record.roadmap_links
        )
        return LongRangeStrategy(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            athlete_id=record.athlete_id,
            priority_policy_id=record.priority_policy_id,
            horizon_months=record.horizon_months,
            priorities=priorities,
            roadmap=roadmap,
            block_hypothesis=record.block_hypothesis,
            source_observation_ids=tuple(item.observation_id for item in record.observation_links),
            source_capability_estimate_ids=tuple(
                item.capability_estimate_id for item in record.estimate_links
            ),
            competency_floor_ids=tuple(item.competency_floor_id for item in record.floor_links),
            evidence_claim_ids=tuple(item.evidence_claim_id for item in record.evidence_links),
            generated_at=record.generated_at,
            next_review_at=record.next_review_at,
            rule_version=record.rule_version,
        )

    def add_assessment_definition(self, definition: AssessmentDefinition) -> None:
        self.session.add(
            AssessmentDefinitionRecord(
                id=definition.id,
                schema_version=definition.schema_version,
                created_at=definition.created_at,
                slug=definition.slug,
                name=definition.name,
                domain=definition.domain.value,
                observation_type=definition.observation_type,
                intensity=definition.intensity.value,
                unit_or_scale=definition.unit_or_scale,
                protocol_version=definition.protocol_version,
                requires_body_mass=definition.requires_body_mass,
                required_equipment_categories=list(definition.required_equipment_categories),
                min_training_age_months=definition.min_training_age_months,
                required_skill_tags=list(definition.required_skill_tags),
                required_recent_exposure_tags=list(definition.required_recent_exposure_tags),
                blocked_by_symptom_flags=list(definition.blocked_by_symptom_flags),
                blocked_by_injury_flags=list(definition.blocked_by_injury_flags),
                blocked_by_health_screening_flags=list(
                    definition.blocked_by_health_screening_flags
                ),
            )
        )

    def add_assessment_selection(self, selection: AssessmentSelection) -> None:
        self._require_athlete(selection.athlete_id)
        if self.session.get(AssessmentDefinitionRecord, selection.assessment_definition_id) is None:
            raise DomainIntegrityError("assessment definition does not exist")
        observations = self._observations_by_id(selection.source_observation_ids)
        found_ids = {item.id for item in observations}
        missing = set(selection.source_observation_ids) - found_ids
        if missing:
            raise DomainIntegrityError(f"unknown source observations: {sorted(map(str, missing))}")
        if any(item.athlete_id != selection.athlete_id for item in observations):
            raise DomainIntegrityError(
                "all source observations must belong to the same athlete as the selection"
            )

        record = AssessmentSelectionRecord(
            id=selection.id,
            schema_version=selection.schema_version,
            created_at=selection.created_at,
            athlete_id=selection.athlete_id,
            assessment_definition_id=selection.assessment_definition_id,
            decision=selection.decision.value,
            reason_codes=[item.value for item in selection.reason_codes],
            rationale=list(selection.rationale),
            evaluated_at=selection.evaluated_at,
            rule_version=selection.rule_version,
        )
        record.source_links = [
            AssessmentSelectionObservationRecord(
                selection_id=selection.id,
                observation_id=observation_id,
                source_order=source_order,
            )
            for source_order, observation_id in enumerate(selection.source_observation_ids)
        ]
        self.session.add(record)

    def get_assessment_definition(self, definition_id: UUID) -> AssessmentDefinition | None:
        record = self.session.get(AssessmentDefinitionRecord, definition_id)
        if record is None:
            return None
        return AssessmentDefinition(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            slug=record.slug,
            name=record.name,
            domain=record.domain,
            observation_type=record.observation_type,
            intensity=record.intensity,
            unit_or_scale=record.unit_or_scale,
            protocol_version=record.protocol_version,
            requires_body_mass=record.requires_body_mass,
            required_equipment_categories=tuple(record.required_equipment_categories),
            min_training_age_months=record.min_training_age_months,
            required_skill_tags=tuple(record.required_skill_tags),
            required_recent_exposure_tags=tuple(record.required_recent_exposure_tags),
            blocked_by_symptom_flags=tuple(record.blocked_by_symptom_flags),
            blocked_by_injury_flags=tuple(record.blocked_by_injury_flags),
            blocked_by_health_screening_flags=tuple(record.blocked_by_health_screening_flags),
        )

    def get_assessment_selection(self, selection_id: UUID) -> AssessmentSelection | None:
        record = self.session.get(AssessmentSelectionRecord, selection_id)
        if record is None:
            return None
        return AssessmentSelection(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            athlete_id=record.athlete_id,
            assessment_definition_id=record.assessment_definition_id,
            decision=record.decision,
            reason_codes=tuple(record.reason_codes),
            rationale=tuple(record.rationale),
            source_observation_ids=tuple(link.observation_id for link in record.source_links),
            evaluated_at=record.evaluated_at,
            rule_version=record.rule_version,
        )

    def get_observation(self, observation_id: UUID) -> Observation | None:
        record = self.session.get(ObservationRecord, observation_id)
        if record is None:
            return None
        return Observation(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            athlete_id=record.athlete_id,
            observed_at=record.observed_at,
            observation_type=record.observation_type,
            measurement=record.measurement,
            unit=record.unit,
            source=record.source,
            reliability=record.reliability,
            context=record.context,
            provenance=Provenance.model_validate(record.provenance),
        )

    def get_capability_estimate(self, estimate_id: UUID) -> CapabilityEstimate | None:
        record = self.session.get(CapabilityEstimateRecord, estimate_id)
        if record is None:
            return None
        return CapabilityEstimate(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            kind="derived",
            athlete_id=record.athlete_id,
            domain=record.domain,
            estimate=record.estimate,
            unit_or_scale=record.unit_or_scale,
            estimate_scope=record.estimate_scope,
            confidence=record.confidence,
            calculation_method=record.calculation_method,
            source_observation_ids=tuple(link.observation_id for link in record.source_links),
            estimated_at=record.estimated_at,
            valid_until=record.valid_until,
            rule_version=record.rule_version,
        )

    def get_evidence_claim(self, claim_id: UUID) -> EvidenceClaim | None:
        record = self.session.get(EvidenceClaimRecord, claim_id)
        if record is None:
            return None
        return EvidenceClaim(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            claim=record.claim,
            domain=record.domain,
            population=record.population,
            intervention=record.intervention,
            comparator=record.comparator,
            outcome=record.outcome,
            study_design=record.study_design,
            sample_size=record.sample_size,
            duration=record.duration,
            effect_direction=record.effect_direction,
            uncertainty=record.uncertainty,
            limitations=tuple(record.limitations),
            evidence_strength=record.evidence_strength,
            athlete_applicability=record.athlete_applicability,
            applicability_notes=record.applicability_notes,
            source_identifiers=tuple(
                EvidenceSourceIdentifier.model_validate(item) for item in record.source_identifiers
            ),
            reviewer=record.reviewer,
            claim_version=record.claim_version,
        )

    def get_exercise(self, exercise_id: UUID) -> Exercise | None:
        record = self.session.get(ExerciseRecord, exercise_id)
        if record is None:
            return None
        return Exercise(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            name=record.name,
            movement_patterns=tuple(record.movement_patterns),
            primary_adaptation_ids=tuple(
                link.adaptation_id for link in record.adaptation_links if link.role == "primary"
            ),
            secondary_adaptation_ids=tuple(
                link.adaptation_id for link in record.adaptation_links if link.role == "secondary"
            ),
            joint_demands=tuple(record.joint_demands),
            equipment_requirement_ids=tuple(link.equipment_id for link in record.equipment_links),
            loading_type=record.loading_type,
            loadability=record.loadability,
            skill_complexity=record.skill_complexity,
            impact_level=record.impact_level,
            velocity_characteristics=tuple(record.velocity_characteristics),
            stability_demand=record.stability_demand,
            fatigue_cost=record.fatigue_cost,
            soreness_cost=record.soreness_cost,
            requires_outdoor_access=record.requires_outdoor_access,
            minimum_floor_area_m2=record.minimum_floor_area_m2,
            noise_level=record.noise_level,
            progression_exercise_ids=tuple(
                link.target_exercise_id
                for link in record.exercise_links
                if link.relationship == "progression"
            ),
            regression_exercise_ids=tuple(
                link.target_exercise_id
                for link in record.exercise_links
                if link.relationship == "regression"
            ),
            contraindication_tags=tuple(record.contraindication_tags),
            measurement_methods=tuple(record.measurement_methods),
        )

    def get_adaptation(self, adaptation_id: UUID) -> Adaptation | None:
        record = self.session.get(AdaptationRecord, adaptation_id)
        if record is None:
            return None
        return Adaptation(
            id=record.id,
            schema_version=record.schema_version,
            created_at=record.created_at,
            name=record.name,
            domain=record.domain,
            preferred_stimuli=tuple(record.preferred_stimuli),
            valid_modalities=tuple(record.valid_modalities),
            dose_dimensions=tuple(record.dose_dimensions),
            fatigue_characteristics=record.fatigue_characteristics,
            typical_measurement_methods=tuple(record.typical_measurement_methods),
            maintenance_requirements=record.maintenance_requirements,
            relationships=tuple(
                AdaptationRelationship(
                    id=link.id,
                    schema_version=link.schema_version,
                    created_at=link.created_at,
                    target_adaptation_id=link.target_adaptation_id,
                    relationship=link.relationship_type,
                    strength=link.strength,
                    confidence=link.confidence,
                    population=link.population,
                    evidence_claim_ids=tuple(
                        evidence.evidence_claim_id for evidence in link.evidence_links
                    ),
                    notes=link.notes,
                )
                for link in record.relationship_links
            ),
            evidence_claim_ids=tuple(
                evidence.evidence_claim_id for evidence in record.evidence_links
            ),
        )

    def equipment_history(self, environment_id: UUID) -> list[EquipmentAvailabilityRecord]:
        statement = (
            select(EquipmentAvailabilityRecord)
            .where(EquipmentAvailabilityRecord.environment_id == environment_id)
            .order_by(
                EquipmentAvailabilityRecord.effective_from,
                EquipmentAvailabilityRecord.created_at,
            )
        )
        return list(self.session.scalars(statement))

    def _require_athlete(self, athlete_id: UUID) -> None:
        if self.session.get(AthleteRecord, athlete_id) is None:
            raise DomainIntegrityError(f"athlete {athlete_id} does not exist")

    def _observations_by_id(self, ids: Iterable[UUID]) -> list[ObservationRecord]:
        return list(
            self.session.scalars(select(ObservationRecord).where(ObservationRecord.id.in_(ids)))
        )

    def _require_ids_exist(
        self,
        id_column: InstrumentedAttribute[UUID],
        ids: Iterable[UUID],
        label: str,
    ) -> None:
        requested = set(ids)
        if not requested:
            return
        found = set(self.session.scalars(select(id_column).where(id_column.in_(requested))))
        missing = requested - found
        if missing:
            raise DomainIntegrityError(f"unknown {label}: {sorted(map(str, missing))}")
