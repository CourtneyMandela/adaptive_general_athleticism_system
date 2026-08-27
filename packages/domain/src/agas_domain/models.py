from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from agas_domain.enums import (
    AdaptationRelationshipType,
    Applicability,
    AssessmentDecision,
    AssessmentEligibilityOutcome,
    AssessmentIntensity,
    AssessmentMeasurementType,
    AssessmentReason,
    AssessmentReviewDecision,
    BlockIssueCode,
    BlockPlanStatus,
    BlockReviewOutcome,
    CapabilityDomain,
    ComparisonDirection,
    CompetencyStatus,
    Confidence,
    CostLevel,
    DoseDimension,
    EvidenceStrength,
    ExposureType,
    ExposureValidationOutcome,
    ImpactLevel,
    JointRegion,
    Laterality,
    Loadability,
    LoadingType,
    MovementPattern,
    ObservationSource,
    PlanningReason,
    PrescriptionModification,
    ProgressionDimension,
    ProgressionOutcome,
    ReadinessLevel,
    ResolutionIssueCode,
    ResolutionStatus,
    SafetyGateOutcome,
    SafetyGateTiming,
    SafetySignalClass,
    SchedulingIssueCode,
    SessionExecutionStatus,
    SessionSection,
    StimulusType,
    TrainingModality,
    TrainingPriorityState,
    VelocityCharacteristic,
    WeeklyPlanStatus,
)

SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+].+)?$")
NonEmptyText = Annotated[str, Field(min_length=1)]
UnitInterval = Annotated[float, Field(ge=0, le=1)]


def utc_now() -> datetime:
    return datetime.now(UTC)


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


class VersionedRecord(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    schema_version: str = "1.0.0"
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        if not SEMVER_PATTERN.fullmatch(value):
            raise ValueError("schema_version must be a semantic version")
        return value

    @field_validator("created_at")
    @classmethod
    def require_aware_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must include a timezone")
        return value


class Provenance(DomainModel):
    recorded_by: NonEmptyText
    source_system: NonEmptyText
    ingestion_method: NonEmptyText
    external_reference: str | None = None
    raw_record_hash: str | None = None


class Account(VersionedRecord):
    issuer: Annotated[str, Field(min_length=1, max_length=300)]
    subject: Annotated[str, Field(min_length=1, max_length=255)]

    @field_validator("issuer", "subject")
    @classmethod
    def normalize_identity_value(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("account identity values must not be blank")
        return normalized


class Athlete(VersionedRecord):
    display_name: Annotated[str, Field(min_length=1, max_length=120)]
    date_of_birth: date | None = None
    preferences: dict[str, JsonValue] = Field(default_factory=dict)
    goals: tuple[NonEmptyText, ...] = ()


class AthleteOwnership(VersionedRecord):
    account_id: UUID
    athlete_id: UUID
    granted_at: datetime
    grant_method: NonEmptyText
    rule_version: NonEmptyText

    @field_validator("granted_at")
    @classmethod
    def require_aware_granted_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("ownership grant time must include a timezone")
        return value


class Observation(VersionedRecord):
    athlete_id: UUID
    observed_at: datetime
    observation_type: NonEmptyText
    measurement: JsonValue
    unit: str | None = None
    source: ObservationSource
    reliability: Confidence
    context: dict[str, JsonValue] = Field(default_factory=dict)
    provenance: Provenance

    @field_validator("observed_at")
    @classmethod
    def require_aware_observed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return value


class CapabilityEstimate(VersionedRecord):
    kind: Literal["derived"] = "derived"
    athlete_id: UUID
    domain: CapabilityDomain
    estimate: JsonValue
    unit_or_scale: NonEmptyText
    estimate_scope: NonEmptyText = "domain"
    confidence: Confidence
    calculation_method: NonEmptyText
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    estimated_at: datetime
    valid_until: datetime | None = None
    rule_version: NonEmptyText

    @field_validator("estimated_at", "valid_until")
    @classmethod
    def require_aware_estimate_times(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("estimate timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_estimate(self) -> CapabilityEstimate:
        if len(set(self.source_observation_ids)) != len(self.source_observation_ids):
            raise ValueError("source_observation_ids must not contain duplicates")
        if self.valid_until is not None and self.valid_until <= self.estimated_at:
            raise ValueError("valid_until must be later than estimated_at")
        return self


class Environment(VersionedRecord):
    athlete_id: UUID
    name: Annotated[str, Field(min_length=1, max_length=120)]
    space_constraints: dict[str, JsonValue] = Field(default_factory=dict)
    noise_constraints: str | None = None
    max_noise_level: CostLevel = CostLevel.HIGH
    outdoor_access: bool = False


class Equipment(VersionedRecord):
    name: Annotated[str, Field(min_length=1, max_length=160)]
    category: NonEmptyText
    capabilities: dict[str, JsonValue] = Field(default_factory=dict)


class EquipmentAvailability(VersionedRecord):
    environment_id: UUID
    equipment_id: UUID
    is_available: bool
    effective_from: datetime
    effective_until: datetime | None = None
    capabilities: dict[str, JsonValue] = Field(default_factory=dict)
    load_limits: dict[str, JsonValue] = Field(default_factory=dict)
    reason: str | None = None

    @field_validator("effective_from", "effective_until")
    @classmethod
    def require_aware_effective_times(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("availability timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_window(self) -> EquipmentAvailability:
        if self.effective_until is not None and self.effective_until <= self.effective_from:
            raise ValueError("effective_until must be later than effective_from")
        return self


class Exercise(VersionedRecord):
    name: Annotated[str, Field(min_length=1, max_length=180)]
    movement_patterns: Annotated[tuple[MovementPattern, ...], Field(min_length=1)]
    primary_adaptation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    secondary_adaptation_ids: tuple[UUID, ...] = ()
    joint_demands: tuple[JointRegion, ...] = ()
    equipment_requirement_ids: tuple[UUID, ...] = ()
    loading_type: LoadingType
    laterality: Laterality
    loadability: Loadability
    skill_complexity: CostLevel
    impact_level: ImpactLevel
    velocity_characteristics: tuple[VelocityCharacteristic, ...] = ()
    stability_demand: CostLevel
    fatigue_cost: CostLevel
    soreness_cost: CostLevel
    requires_outdoor_access: bool = False
    minimum_floor_area_m2: float | None = Field(default=None, gt=0)
    noise_level: CostLevel = CostLevel.LOW
    progression_exercise_ids: tuple[UUID, ...] = ()
    regression_exercise_ids: tuple[UUID, ...] = ()
    contraindication_tags: tuple[NonEmptyText, ...] = ()
    measurement_methods: tuple[NonEmptyText, ...] = ()

    @model_validator(mode="after")
    def validate_relationships(self) -> Exercise:
        self._require_unique_ids("primary_adaptation_ids", self.primary_adaptation_ids)
        self._require_unique_ids("secondary_adaptation_ids", self.secondary_adaptation_ids)
        self._require_unique_ids("equipment_requirement_ids", self.equipment_requirement_ids)
        self._require_unique_ids("progression_exercise_ids", self.progression_exercise_ids)
        self._require_unique_ids("regression_exercise_ids", self.regression_exercise_ids)
        if set(self.primary_adaptation_ids) & set(self.secondary_adaptation_ids):
            raise ValueError("an adaptation cannot be both primary and secondary")
        if set(self.progression_exercise_ids) & set(self.regression_exercise_ids):
            raise ValueError("an exercise cannot be both a progression and regression")
        return self

    @staticmethod
    def _require_unique_ids(field_name: str, values: tuple[UUID, ...]) -> None:
        if len(set(values)) != len(values):
            raise ValueError(f"{field_name} must not contain duplicates")


class AdaptationRelationship(VersionedRecord):
    target_adaptation_id: UUID
    relationship: AdaptationRelationshipType
    strength: Confidence
    confidence: Confidence
    population: NonEmptyText
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    notes: str | None = None

    @model_validator(mode="after")
    def validate_evidence_ids(self) -> AdaptationRelationship:
        if len(set(self.evidence_claim_ids)) != len(self.evidence_claim_ids):
            raise ValueError("evidence_claim_ids must not contain duplicates")
        return self


class Adaptation(VersionedRecord):
    name: Annotated[str, Field(min_length=1, max_length=180)]
    domain: CapabilityDomain
    preferred_stimuli: tuple[StimulusType, ...] = ()
    valid_modalities: tuple[TrainingModality, ...] = ()
    dose_dimensions: tuple[DoseDimension, ...] = ()
    fatigue_characteristics: dict[str, JsonValue] = Field(default_factory=dict)
    typical_measurement_methods: tuple[NonEmptyText, ...] = ()
    maintenance_requirements: dict[str, JsonValue] = Field(default_factory=dict)
    relationships: tuple[AdaptationRelationship, ...] = ()
    evidence_claim_ids: tuple[UUID, ...] = ()

    @model_validator(mode="after")
    def validate_relationships(self) -> Adaptation:
        if len(set(self.evidence_claim_ids)) != len(self.evidence_claim_ids):
            raise ValueError("evidence_claim_ids must not contain duplicates")
        relationship_ids = [item.id for item in self.relationships]
        if len(set(relationship_ids)) != len(relationship_ids):
            raise ValueError("relationship ids must not contain duplicates")
        if any(item.target_adaptation_id == self.id for item in self.relationships):
            raise ValueError("an adaptation cannot relate to itself")
        return self


class EvidenceSourceIdentifier(DomainModel):
    scheme: Literal["doi", "pmid", "openalex", "other"]
    value: NonEmptyText


class EvidenceClaim(VersionedRecord):
    claim: NonEmptyText
    domain: NonEmptyText
    population: NonEmptyText
    intervention: NonEmptyText
    comparator: str | None = None
    outcome: NonEmptyText
    study_design: NonEmptyText
    sample_size: int | None = Field(default=None, ge=1)
    duration: str | None = None
    effect_direction: str | None = None
    uncertainty: NonEmptyText
    limitations: tuple[NonEmptyText, ...] = ()
    evidence_strength: EvidenceStrength
    athlete_applicability: Applicability
    applicability_notes: NonEmptyText
    source_identifiers: Annotated[tuple[EvidenceSourceIdentifier, ...], Field(min_length=1)]
    reviewer: NonEmptyText
    claim_version: NonEmptyText


class DecisionRecord(VersionedRecord):
    decision: NonEmptyText
    reason: NonEmptyText
    alternatives_considered: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    evidence: tuple[NonEmptyText, ...] = ()
    uncertainty: NonEmptyText
    decision_version: NonEmptyText
    decided_on: date


class CatalogImport(VersionedRecord):
    catalog_version: Annotated[str, Field(pattern=r"^\d+\.\d+\.\d+$")]
    review_status: NonEmptyText
    reviewed_by: NonEmptyText
    reviewed_at: date
    scope: NonEmptyText
    notes: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    evidence_claim_ids: tuple[UUID, ...] = ()
    adaptation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    equipment_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    exercise_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    imported_at: datetime
    importer_version: NonEmptyText

    @field_validator("imported_at")
    @classmethod
    def require_aware_imported_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("imported_at must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_catalog_ids(self) -> CatalogImport:
        for field_name in (
            "evidence_claim_ids",
            "adaptation_ids",
            "equipment_ids",
            "exercise_ids",
        ):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        return self


class AssessmentContext(DomainModel):
    athlete_id: UUID
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    body_mass_kg: float | None = Field(default=None, gt=0)
    health_screening_completed: bool = False
    training_age_months_by_domain: dict[str, Annotated[int, Field(ge=0)]] = Field(
        default_factory=dict
    )
    current_symptom_flags: tuple[NonEmptyText, ...] = ()
    current_injury_flags: tuple[NonEmptyText, ...] = ()
    health_screening_flags: tuple[NonEmptyText, ...] = ()
    exercise_skill_tags: tuple[NonEmptyText, ...] = ()
    recent_exposure_tags: tuple[NonEmptyText, ...] = ()
    available_equipment_categories: tuple[NonEmptyText, ...] = ()
    evaluated_at: datetime = Field(default_factory=utc_now)

    @field_validator("evaluated_at")
    @classmethod
    def require_aware_evaluated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluated_at must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_context_sets(self) -> AssessmentContext:
        for field_name in (
            "source_observation_ids",
            "current_symptom_flags",
            "current_injury_flags",
            "health_screening_flags",
            "exercise_skill_tags",
            "recent_exposure_tags",
            "available_equipment_categories",
        ):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        return self


class AssessmentDefinition(VersionedRecord):
    slug: Annotated[str, Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")]
    name: Annotated[str, Field(min_length=1, max_length=180)]
    domain: CapabilityDomain
    observation_type: NonEmptyText
    intensity: AssessmentIntensity
    unit_or_scale: NonEmptyText
    protocol_version: NonEmptyText
    requires_body_mass: bool = False
    required_equipment_categories: tuple[NonEmptyText, ...] = ()
    min_training_age_months: int = Field(default=0, ge=0)
    required_skill_tags: tuple[NonEmptyText, ...] = ()
    required_recent_exposure_tags: tuple[NonEmptyText, ...] = ()
    blocked_by_symptom_flags: tuple[NonEmptyText, ...] = ()
    blocked_by_injury_flags: tuple[NonEmptyText, ...] = ()
    blocked_by_health_screening_flags: tuple[NonEmptyText, ...] = ()


class AssessmentMeasurementSchema(DomainModel):
    measurement_type: AssessmentMeasurementType
    label: NonEmptyText
    minimum: float | None = Field(default=None, allow_inf_nan=False)
    maximum: float | None = Field(default=None, allow_inf_nan=False)
    step: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    allowed_values: tuple[NonEmptyText, ...] = ()
    measurement_schema_version: NonEmptyText

    @model_validator(mode="after")
    def validate_measurement_contract(self) -> AssessmentMeasurementSchema:
        if self.minimum is not None and self.maximum is not None and self.maximum < self.minimum:
            raise ValueError("measurement maximum cannot be below minimum")
        if self.measurement_type is AssessmentMeasurementType.CATEGORY:
            if not self.allowed_values:
                raise ValueError("categorical measurements require allowed values")
            if self.minimum is not None or self.maximum is not None or self.step is not None:
                raise ValueError("categorical measurements cannot define numeric constraints")
        elif self.allowed_values:
            raise ValueError("numeric measurements cannot define categorical values")
        if self.measurement_type is AssessmentMeasurementType.INTEGER:
            constraints = (self.minimum, self.maximum, self.step)
            if any(
                value is not None and Decimal(str(value)) % Decimal(1) != 0 for value in constraints
            ):
                raise ValueError("integer measurement constraints must use whole numbers")
        if len(set(self.allowed_values)) != len(self.allowed_values):
            raise ValueError("measurement allowed values must not contain duplicates")
        return self

    def validate_measurement(self, value: JsonValue) -> None:
        if self.measurement_type is AssessmentMeasurementType.CATEGORY:
            if not isinstance(value, str) or value not in self.allowed_values:
                raise ValueError("measurement is not an allowed category")
            return
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("measurement must be numeric")
        if self.measurement_type is AssessmentMeasurementType.INTEGER and type(value) is not int:
            raise ValueError("measurement must be an integer")
        numeric = Decimal(str(value))
        if not numeric.is_finite():
            raise ValueError("measurement must be finite")
        if self.minimum is not None and numeric < Decimal(str(self.minimum)):
            raise ValueError("measurement is below the reviewed minimum")
        if self.maximum is not None and numeric > Decimal(str(self.maximum)):
            raise ValueError("measurement is above the reviewed maximum")
        if self.step is not None:
            origin = self.minimum if self.minimum is not None else 0
            if (numeric - Decimal(str(origin))) % Decimal(str(self.step)) != 0:
                raise ValueError("measurement does not match the reviewed step")


class AssessmentDefinitionReview(VersionedRecord):
    assessment_definition_id: UUID
    decision: AssessmentReviewDecision
    sequence_number: Annotated[int, Field(ge=1)]
    supersedes_review_id: UUID | None = None
    protocol_instructions: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    result_entry_instructions: NonEmptyText
    measurement_schema: AssessmentMeasurementSchema | None = None
    recommended_reassessment_days: Annotated[int, Field(ge=1)] | None = None
    self_administered: bool = False
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    reviewed_at: datetime
    reviewer: NonEmptyText
    applicability_notes: NonEmptyText
    uncertainty: NonEmptyText
    review_version: NonEmptyText

    @field_validator("reviewed_at")
    @classmethod
    def require_aware_reviewed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("assessment review time must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_review(self) -> AssessmentDefinitionReview:
        if len(set(self.protocol_instructions)) != len(self.protocol_instructions):
            raise ValueError("protocol_instructions must not contain duplicates")
        if len(set(self.evidence_claim_ids)) != len(self.evidence_claim_ids):
            raise ValueError("evidence_claim_ids must not contain duplicates")
        if self.sequence_number == 1 and self.supersedes_review_id is not None:
            raise ValueError("the first assessment review cannot supersede another record")
        if self.sequence_number > 1 and self.supersedes_review_id is None:
            raise ValueError("later assessment reviews must reference their predecessor")
        if self.supersedes_review_id == self.id:
            raise ValueError("an assessment review cannot supersede itself")
        if (
            self.decision is AssessmentReviewDecision.APPROVED
            and self.recommended_reassessment_days is None
        ):
            raise ValueError("approved assessments require a reassessment interval")
        return self


class AssessmentEligibilityReview(VersionedRecord):
    athlete_id: UUID
    outcome: AssessmentEligibilityOutcome
    sequence_number: Annotated[int, Field(ge=1)]
    supersedes_review_id: UUID | None = None
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    reviewed_at: datetime
    valid_until: datetime
    reviewed_by: NonEmptyText
    screening_process_reference: NonEmptyText
    rationale: NonEmptyText
    uncertainty: NonEmptyText
    rule_version: NonEmptyText

    @field_validator("reviewed_at", "valid_until")
    @classmethod
    def require_aware_eligibility_times(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("assessment eligibility timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_eligibility_review(self) -> AssessmentEligibilityReview:
        if len(set(self.source_observation_ids)) != len(self.source_observation_ids):
            raise ValueError("source_observation_ids must not contain duplicates")
        if self.valid_until <= self.reviewed_at:
            raise ValueError("eligibility valid_until must be later than reviewed_at")
        if self.sequence_number == 1 and self.supersedes_review_id is not None:
            raise ValueError("the first eligibility review cannot supersede another record")
        if self.sequence_number > 1 and self.supersedes_review_id is None:
            raise ValueError("later eligibility reviews must reference their predecessor")
        if self.supersedes_review_id == self.id:
            raise ValueError("an eligibility review cannot supersede itself")
        return self


class AssessmentSelection(VersionedRecord):
    athlete_id: UUID
    assessment_definition_id: UUID
    assessment_definition_review_id: UUID | None = None
    assessment_eligibility_review_id: UUID | None = None
    decision: AssessmentDecision
    reason_codes: Annotated[tuple[AssessmentReason, ...], Field(min_length=1)]
    rationale: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    evaluated_at: datetime
    rule_version: NonEmptyText

    @field_validator("evaluated_at")
    @classmethod
    def require_aware_selection_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluated_at must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_selection(self) -> AssessmentSelection:
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise ValueError("reason_codes must not contain duplicates")
        if len(set(self.source_observation_ids)) != len(self.source_observation_ids):
            raise ValueError("source_observation_ids must not contain duplicates")
        if len(self.reason_codes) != len(self.rationale):
            raise ValueError("each reason code must have one rationale")
        if self.decision is AssessmentDecision.SELECTED and self.reason_codes != (
            AssessmentReason.ELIGIBLE,
        ):
            raise ValueError("selected assessments must use the eligible reason")
        return self


class AssessmentSelectionRun(VersionedRecord):
    athlete_id: UUID
    assessment_eligibility_review_id: UUID
    environment_id: UUID
    context_observation_id: UUID
    selection_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    evaluated_at: datetime
    rule_version: NonEmptyText

    @field_validator("evaluated_at")
    @classmethod
    def require_aware_run_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("assessment run time must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_selection_ids(self) -> AssessmentSelectionRun:
        if len(set(self.selection_ids)) != len(self.selection_ids):
            raise ValueError("selection_ids must not contain duplicates")
        return self


class AssessmentPerformance(VersionedRecord):
    athlete_id: UUID
    assessment_selection_run_id: UUID
    assessment_selection_id: UUID
    assessment_definition_id: UUID
    assessment_definition_review_id: UUID
    assessment_eligibility_review_id: UUID
    result_observation_id: UUID
    performed_at: datetime
    rule_version: NonEmptyText

    @field_validator("performed_at")
    @classmethod
    def require_aware_performed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("assessment performance time must include a timezone")
        return value


class AssessmentResultInput(DomainModel):
    athlete_id: UUID
    assessment_definition_id: UUID
    performed_at: datetime
    measurement: JsonValue
    unit: NonEmptyText
    reliability: Confidence
    context: dict[str, JsonValue] = Field(default_factory=dict)
    provenance: Provenance

    @field_validator("performed_at")
    @classmethod
    def require_aware_performed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("performed_at must include a timezone")
        return value


class CapabilityEstimationPolicy(VersionedRecord):
    domain: CapabilityDomain
    observation_type: NonEmptyText
    unit_or_scale: NonEmptyText
    calculation_method: NonEmptyText
    valid_for_days: int = Field(ge=1)
    multi_observation_window_days: int = Field(default=90, ge=1)
    rule_version: NonEmptyText


class CompetencyFloor(VersionedRecord):
    domain: CapabilityDomain
    estimate_scope: NonEmptyText
    unit_or_scale: NonEmptyText
    threshold: float = Field(gt=0)
    comparison_direction: ComparisonDirection
    population: NonEmptyText
    applicability_notes: NonEmptyText
    uncertainty: NonEmptyText
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    floor_version: NonEmptyText

    @model_validator(mode="after")
    def validate_evidence(self) -> CompetencyFloor:
        if len(set(self.evidence_claim_ids)) != len(self.evidence_claim_ids):
            raise ValueError("evidence_claim_ids must not contain duplicates")
        return self


class CapabilityNeed(VersionedRecord):
    athlete_id: UUID
    domain: CapabilityDomain
    competency_floor_id: UUID
    capability_estimate_id: UUID | None = None
    status: CompetencyStatus
    observed_value: float | None = None
    floor_value: float
    unit_or_scale: NonEmptyText
    gap_from_floor: float | None = None
    normalized_deficit: UnitInterval | None = None
    confidence: Confidence
    rationale: NonEmptyText
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    identified_at: datetime
    rule_version: NonEmptyText

    @field_validator("identified_at")
    @classmethod
    def require_aware_identified_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("identified_at must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_need(self) -> CapabilityNeed:
        if len(set(self.evidence_claim_ids)) != len(self.evidence_claim_ids):
            raise ValueError("evidence_claim_ids must not contain duplicates")
        if self.status is CompetencyStatus.BELOW_FLOOR:
            if self.gap_from_floor is None or self.gap_from_floor <= 0:
                raise ValueError("below-floor needs require a positive gap_from_floor")
            if self.normalized_deficit is None or self.normalized_deficit <= 0:
                raise ValueError("below-floor needs require a positive normalized_deficit")
        elif self.normalized_deficit not in (None, 0):
            raise ValueError("only below-floor needs may have normalized deficit")
        if self.status in {
            CompetencyStatus.BELOW_FLOOR,
            CompetencyStatus.MEETS_FLOOR,
            CompetencyStatus.ABOVE_FLOOR,
        } and (self.capability_estimate_id is None or self.observed_value is None):
            raise ValueError("comparable needs require an estimate and numeric observed value")
        return self


class PriorityPolicy(VersionedRecord):
    deficit_weight: float = Field(ge=0)
    general_relevance_weight: float = Field(ge=0)
    goal_relevance_weight: float = Field(ge=0)
    prerequisite_value_weight: float = Field(ge=0)
    expected_trainability_weight: float = Field(ge=0)
    transfer_value_weight: float = Field(ge=0)
    fatigue_cost_weight: float = Field(ge=0)
    time_cost_weight: float = Field(ge=0)
    interference_cost_weight: float = Field(ge=0)
    cost_penalty: UnitInterval
    confidence_multipliers: dict[Confidence, UnitInterval]
    develop_score_threshold: UnitInterval
    comparative_advantage_threshold: UnitInterval
    severe_deficit_threshold: UnitInterval
    max_develop_adaptations: int = Field(ge=1)
    policy_version: NonEmptyText

    @model_validator(mode="after")
    def validate_policy(self) -> PriorityPolicy:
        benefit_weights = (
            self.deficit_weight,
            self.general_relevance_weight,
            self.goal_relevance_weight,
            self.prerequisite_value_weight,
            self.expected_trainability_weight,
            self.transfer_value_weight,
        )
        if sum(benefit_weights) <= 0:
            raise ValueError("at least one benefit weight must be positive")
        required_confidence = set(Confidence)
        if set(self.confidence_multipliers) != required_confidence:
            raise ValueError("confidence_multipliers must define every confidence level")
        return self


class AdaptationPlanningCandidate(DomainModel):
    adaptation_id: UUID
    capability_need_id: UUID
    general_relevance: UnitInterval
    goal_relevance: UnitInterval
    prerequisite_value: UnitInterval
    expected_trainability: UnitInterval
    transfer_value: UnitInterval
    fatigue_cost: UnitInterval
    time_cost: UnitInterval
    interference_cost: UnitInterval
    safe_to_train: bool = True
    introductory_exposure_needed: bool = False
    prerequisites_met: bool = True
    prerequisite_adaptation_ids: tuple[UUID, ...] = ()
    cultivate_comparative_advantage: bool = False
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_candidate(self) -> AdaptationPlanningCandidate:
        for field_name in (
            "prerequisite_adaptation_ids",
            "source_observation_ids",
            "evidence_claim_ids",
        ):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        if self.adaptation_id in self.prerequisite_adaptation_ids:
            raise ValueError("an adaptation cannot be its own prerequisite")
        return self


class ReplanningCandidateContext(DomainModel):
    adaptation_id: UUID
    competency_floor_id: UUID
    capability_estimate_id: UUID
    general_relevance: UnitInterval
    goal_relevance: UnitInterval
    prerequisite_value: UnitInterval
    expected_trainability: UnitInterval
    transfer_value: UnitInterval
    fatigue_cost: UnitInterval
    time_cost: UnitInterval
    interference_cost: UnitInterval
    safe_to_train: bool = True
    introductory_exposure_needed: bool = False
    prerequisites_met: bool = True
    prerequisite_adaptation_ids: tuple[UUID, ...] = ()
    cultivate_comparative_advantage: bool = False
    source_observation_ids: tuple[UUID, ...] = ()
    evidence_claim_ids: tuple[UUID, ...] = ()

    @model_validator(mode="after")
    def validate_context(self) -> ReplanningCandidateContext:
        for field_name in (
            "prerequisite_adaptation_ids",
            "source_observation_ids",
            "evidence_claim_ids",
        ):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        if self.adaptation_id in self.prerequisite_adaptation_ids:
            raise ValueError("an adaptation cannot be its own prerequisite")
        return self


class AdaptationPriority(VersionedRecord):
    adaptation_id: UUID
    capability_need_id: UUID
    state: TrainingPriorityState
    score: UnitInterval
    rank: int = Field(ge=1)
    development_allocation: UnitInterval = 0
    score_components: dict[str, UnitInterval]
    reason_codes: Annotated[tuple[PlanningReason, ...], Field(min_length=1)]
    rationale: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_priority(self) -> AdaptationPriority:
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise ValueError("reason_codes must not contain duplicates")
        if len(self.reason_codes) != len(self.rationale):
            raise ValueError("each reason code must have one rationale")
        if self.state is not TrainingPriorityState.DEVELOP and self.development_allocation != 0:
            raise ValueError("only DEVELOP priorities may receive development allocation")
        return self


class RoadmapItem(VersionedRecord):
    adaptation_id: UUID
    current_state: TrainingPriorityState
    sequence_group: int = Field(ge=1)
    prerequisite_adaptation_ids: tuple[UUID, ...] = ()
    rationale: NonEmptyText
    review_trigger: NonEmptyText


class LongRangeStrategy(VersionedRecord):
    athlete_id: UUID
    priority_policy_id: UUID
    horizon_months: int = Field(ge=6, le=24)
    priorities: Annotated[tuple[AdaptationPriority, ...], Field(min_length=1)]
    roadmap: Annotated[tuple[RoadmapItem, ...], Field(min_length=1)]
    block_hypothesis: NonEmptyText
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    source_capability_estimate_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    competency_floor_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    generated_at: datetime
    next_review_at: datetime
    rule_version: NonEmptyText
    supersedes_strategy_id: UUID | None = None
    triggering_block_review_id: UUID | None = None

    @field_validator("generated_at", "next_review_at")
    @classmethod
    def require_aware_strategy_times(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("strategy timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_strategy(self) -> LongRangeStrategy:
        if self.next_review_at <= self.generated_at:
            raise ValueError("next_review_at must be later than generated_at")
        for field_name in (
            "source_observation_ids",
            "source_capability_estimate_ids",
            "competency_floor_ids",
            "evidence_claim_ids",
        ):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        priority_adaptations = [item.adaptation_id for item in self.priorities]
        roadmap_adaptations = [item.adaptation_id for item in self.roadmap]
        if len(set(priority_adaptations)) != len(priority_adaptations):
            raise ValueError("priorities must contain each adaptation once")
        if set(priority_adaptations) != set(roadmap_adaptations):
            raise ValueError("roadmap and priorities must cover the same adaptations")
        allocation = sum(item.development_allocation for item in self.priorities)
        has_development = any(
            item.state is TrainingPriorityState.DEVELOP for item in self.priorities
        )
        if has_development and abs(allocation - 1.0) > 1e-6:
            raise ValueError("DEVELOP allocation must sum to one")
        if not has_development and allocation != 0:
            raise ValueError("allocation must be zero when nothing is in DEVELOP")
        if (self.supersedes_strategy_id is None) != (self.triggering_block_review_id is None):
            raise ValueError(
                "strategy revisions require both superseded strategy and triggering review ids"
            )
        if self.supersedes_strategy_id == self.id:
            raise ValueError("a strategy cannot supersede itself")
        return self


class ClosedLoopReplanningResult(DomainModel):
    capability_needs: Annotated[tuple[CapabilityNeed, ...], Field(min_length=1)]
    strategy: LongRangeStrategy

    @model_validator(mode="after")
    def validate_result(self) -> ClosedLoopReplanningResult:
        need_ids = tuple(item.id for item in self.capability_needs)
        if len(set(need_ids)) != len(need_ids):
            raise ValueError("closed-loop replanning needs must have unique ids")
        if {item.capability_need_id for item in self.strategy.priorities} != set(need_ids):
            raise ValueError("replanned strategy priorities must use the returned capability needs")
        return self


class AvailableEquipmentSnapshot(DomainModel):
    equipment_id: UUID
    category: NonEmptyText
    capabilities: dict[str, JsonValue] = Field(default_factory=dict)
    load_limits: dict[str, JsonValue] = Field(default_factory=dict)


class EnvironmentSnapshot(DomainModel):
    athlete_id: UUID
    environment_id: UUID
    captured_at: datetime
    available_equipment: tuple[AvailableEquipmentSnapshot, ...] = ()
    source_availability_ids: tuple[UUID, ...] = ()
    floor_area_m2: float | None = Field(default=None, gt=0)
    max_noise_level: CostLevel
    outdoor_access: bool

    @field_validator("captured_at")
    @classmethod
    def require_aware_captured_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_snapshot(self) -> EnvironmentSnapshot:
        equipment_ids = [item.equipment_id for item in self.available_equipment]
        if len(set(equipment_ids)) != len(equipment_ids):
            raise ValueError("available_equipment must not contain duplicate equipment")
        if len(set(self.source_availability_ids)) != len(self.source_availability_ids):
            raise ValueError("source_availability_ids must not contain duplicates")
        return self


class StimulusSpecification(DomainModel):
    movement_patterns: Annotated[tuple[MovementPattern, ...], Field(min_length=1)]
    allowed_loading_types: Annotated[tuple[LoadingType, ...], Field(min_length=1)]
    allowed_lateralities: Annotated[tuple[Laterality, ...], Field(min_length=1)]
    minimum_loadability: Loadability
    required_velocity_characteristics: tuple[VelocityCharacteristic, ...] = ()
    maximum_skill_complexity: CostLevel
    maximum_impact_level: ImpactLevel
    maximum_stability_demand: CostLevel
    maximum_fatigue_cost: CostLevel
    maximum_soreness_cost: CostLevel
    requires_outdoor_access: bool = False
    minimum_floor_area_m2: float | None = Field(default=None, gt=0)
    contraindication_tags: tuple[NonEmptyText, ...] = ()
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    rationale: NonEmptyText

    @model_validator(mode="after")
    def validate_specification(self) -> StimulusSpecification:
        for field_name in (
            "movement_patterns",
            "allowed_loading_types",
            "allowed_lateralities",
            "required_velocity_characteristics",
            "contraindication_tags",
            "source_observation_ids",
            "evidence_claim_ids",
        ):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        return self


class StimulusRequirement(VersionedRecord):
    athlete_id: UUID
    long_range_strategy_id: UUID
    adaptation_priority_id: UUID
    adaptation_id: UUID
    priority_state: TrainingPriorityState
    movement_patterns: Annotated[tuple[MovementPattern, ...], Field(min_length=1)]
    allowed_loading_types: Annotated[tuple[LoadingType, ...], Field(min_length=1)]
    allowed_lateralities: Annotated[tuple[Laterality, ...], Field(min_length=1)]
    minimum_loadability: Loadability
    required_velocity_characteristics: tuple[VelocityCharacteristic, ...] = ()
    maximum_skill_complexity: CostLevel
    maximum_impact_level: ImpactLevel
    maximum_stability_demand: CostLevel
    maximum_fatigue_cost: CostLevel
    maximum_soreness_cost: CostLevel
    requires_outdoor_access: bool = False
    minimum_floor_area_m2: float | None = Field(default=None, gt=0)
    contraindication_tags: tuple[NonEmptyText, ...] = ()
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    rationale: NonEmptyText
    generated_at: datetime
    rule_version: NonEmptyText

    @field_validator("generated_at")
    @classmethod
    def require_aware_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_requirement(self) -> StimulusRequirement:
        if self.priority_state is TrainingPriorityState.DEFER:
            raise ValueError("a deferred adaptation cannot produce a current stimulus requirement")
        for field_name in (
            "movement_patterns",
            "allowed_loading_types",
            "allowed_lateralities",
            "required_velocity_characteristics",
            "contraindication_tags",
            "source_observation_ids",
            "evidence_claim_ids",
        ):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        return self


class ExerciseResolverPolicy(VersionedRecord):
    adaptation_role_weight: float = Field(ge=0)
    movement_pattern_weight: float = Field(ge=0)
    loading_type_weight: float = Field(ge=0)
    loadability_weight: float = Field(ge=0)
    velocity_weight: float = Field(ge=0)
    laterality_weight: float = Field(ge=0)
    secondary_adaptation_credit: UnitInterval
    partial_match_threshold: UnitInterval
    full_match_threshold: UnitInterval
    max_ranked_candidates: int = Field(ge=1)
    policy_version: NonEmptyText

    @model_validator(mode="after")
    def validate_resolver_policy(self) -> ExerciseResolverPolicy:
        if (
            self.adaptation_role_weight
            + self.movement_pattern_weight
            + self.loading_type_weight
            + self.loadability_weight
            + self.velocity_weight
            + self.laterality_weight
            <= 0
        ):
            raise ValueError("at least one resolver weight must be positive")
        if self.full_match_threshold < self.partial_match_threshold:
            raise ValueError("full_match_threshold must be at least partial_match_threshold")
        return self


class ResolutionIssue(DomainModel):
    code: ResolutionIssueCode
    detail: NonEmptyText


class ExerciseMatch(VersionedRecord):
    exercise_id: UUID
    quality: ResolutionStatus
    score: UnitInterval
    score_components: dict[str, UnitInterval]
    issues: tuple[ResolutionIssue, ...] = ()

    @model_validator(mode="after")
    def validate_match(self) -> ExerciseMatch:
        if self.quality is ResolutionStatus.INFEASIBLE:
            raise ValueError("ranked exercise matches cannot have infeasible quality")
        if self.quality is ResolutionStatus.FULL and self.issues:
            raise ValueError("full matches cannot retain unresolved issues")
        if self.quality is ResolutionStatus.PARTIAL and not self.issues:
            raise ValueError("partial matches require at least one explicit issue")
        return self


class ExerciseResolution(VersionedRecord):
    stimulus_requirement_id: UUID
    environment_id: UUID
    resolver_policy_id: UUID
    status: ResolutionStatus
    selected_exercise_id: UUID | None = None
    ranked_matches: tuple[ExerciseMatch, ...] = ()
    unresolved_issues: tuple[ResolutionIssue, ...] = ()
    source_availability_ids: tuple[UUID, ...] = ()
    rationale: NonEmptyText
    resolved_at: datetime
    rule_version: NonEmptyText

    @field_validator("resolved_at")
    @classmethod
    def require_aware_resolved_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("resolved_at must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_resolution(self) -> ExerciseResolution:
        if len(set(self.source_availability_ids)) != len(self.source_availability_ids):
            raise ValueError("source_availability_ids must not contain duplicates")
        match_ids = [item.exercise_id for item in self.ranked_matches]
        if len(set(match_ids)) != len(match_ids):
            raise ValueError("ranked_matches must not contain duplicate exercises")
        if self.status is ResolutionStatus.INFEASIBLE:
            if self.selected_exercise_id is not None:
                raise ValueError("infeasible resolution cannot select an exercise")
            if self.ranked_matches:
                raise ValueError("infeasible resolution cannot retain ranked matches")
            if not self.unresolved_issues:
                raise ValueError("infeasible resolution requires unresolved issues")
        else:
            if self.selected_exercise_id is None:
                raise ValueError("full and partial resolutions require a selected exercise")
            if (
                not self.ranked_matches
                or self.ranked_matches[0].exercise_id != self.selected_exercise_id
            ):
                raise ValueError("selected exercise must be the first ranked match")
            if self.ranked_matches[0].quality is not self.status:
                raise ValueError("resolution status must match the selected candidate quality")
            if self.unresolved_issues != self.ranked_matches[0].issues:
                raise ValueError("resolution issues must match the selected candidate issues")
        return self


class AdaptationResourceDemand(VersionedRecord):
    long_range_strategy_id: UUID
    adaptation_priority_id: UUID
    adaptation_id: UUID
    priority_state: TrainingPriorityState
    stimulus_requirement_id: UUID | None = None
    exercise_resolution_id: UUID | None = None
    minimum_weekly_minutes: int = Field(ge=0)
    target_weekly_minutes: int = Field(ge=0)
    sessions_per_week: int = Field(ge=0)
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    rationale: NonEmptyText
    demand_version: NonEmptyText

    @model_validator(mode="after")
    def validate_demand(self) -> AdaptationResourceDemand:
        if self.target_weekly_minutes < self.minimum_weekly_minutes:
            raise ValueError("target weekly minutes cannot be below the minimum")
        if self.priority_state is TrainingPriorityState.DEFER:
            if any(
                (
                    self.minimum_weekly_minutes,
                    self.target_weekly_minutes,
                    self.sessions_per_week,
                )
            ):
                raise ValueError("deferred demands cannot request training resources")
            if self.stimulus_requirement_id is not None or self.exercise_resolution_id is not None:
                raise ValueError("deferred demands cannot reference an active stimulus")
        else:
            if self.minimum_weekly_minutes <= 0 or self.sessions_per_week <= 0:
                raise ValueError("active demands require positive minimum time and frequency")
            if self.stimulus_requirement_id is None or self.exercise_resolution_id is None:
                raise ValueError("active demands require a stimulus and exercise resolution")
            if self.minimum_weekly_minutes % self.sessions_per_week != 0:
                raise ValueError("minimum minutes must divide evenly across weekly sessions")
            if self.target_weekly_minutes % self.sessions_per_week != 0:
                raise ValueError("target minutes must divide evenly across weekly sessions")
        for field_name in ("source_observation_ids", "evidence_claim_ids"):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        return self


class ResourceAllocationPolicy(VersionedRecord):
    develop_weight: float = Field(gt=0)
    maintain_weight: float = Field(ge=0)
    expose_weight: float = Field(ge=0)
    allow_partial_exercise_resolution: bool
    policy_version: NonEmptyText

    @model_validator(mode="after")
    def validate_allocation_policy(self) -> ResourceAllocationPolicy:
        if self.maintain_weight == 0 and self.expose_weight == 0 and self.develop_weight == 0:
            raise ValueError("at least one allocation weight must be positive")
        return self


class BlockIssue(DomainModel):
    code: BlockIssueCode
    detail: NonEmptyText


class ResourceAllocation(VersionedRecord):
    resource_demand_id: UUID
    adaptation_priority_id: UUID
    adaptation_id: UUID
    priority_state: TrainingPriorityState
    stimulus_requirement_id: UUID | None = None
    exercise_resolution_id: UUID | None = None
    minimum_weekly_minutes: int = Field(ge=0)
    target_weekly_minutes: int = Field(ge=0)
    allocated_weekly_minutes: int = Field(ge=0)
    sessions_per_week: int = Field(ge=0)
    status: BlockPlanStatus
    issues: tuple[BlockIssue, ...] = ()

    @model_validator(mode="after")
    def validate_resource_allocation(self) -> ResourceAllocation:
        if self.target_weekly_minutes < self.minimum_weekly_minutes:
            raise ValueError("allocation target cannot be below its minimum")
        if self.allocated_weekly_minutes > self.target_weekly_minutes:
            raise ValueError("allocated minutes cannot exceed the target")
        if self.priority_state is TrainingPriorityState.DEFER:
            if any(
                (
                    self.minimum_weekly_minutes,
                    self.target_weekly_minutes,
                    self.allocated_weekly_minutes,
                    self.sessions_per_week,
                )
            ):
                raise ValueError("deferred allocations must remain zero")
        elif self.status is not BlockPlanStatus.INFEASIBLE:
            if self.allocated_weekly_minutes < self.minimum_weekly_minutes:
                raise ValueError("feasible allocations cannot fall below their minimum")
            if self.sessions_per_week <= 0:
                raise ValueError("active allocations require weekly sessions")
            if self.allocated_weekly_minutes % self.sessions_per_week != 0:
                raise ValueError("allocated minutes must divide evenly across weekly sessions")
        if self.status is BlockPlanStatus.FULL:
            if self.allocated_weekly_minutes != self.target_weekly_minutes or self.issues:
                raise ValueError("full allocations must reach target without issues")
        elif not self.issues:
            raise ValueError("partial and infeasible allocations require explicit issues")
        return self


class BlockPlan(VersionedRecord):
    athlete_id: UUID
    long_range_strategy_id: UUID
    resource_allocation_policy_id: UUID
    starts_on: date
    ends_on: date
    duration_weeks: int = Field(ge=4, le=6)
    weekly_budget_minutes: int = Field(gt=0)
    status: BlockPlanStatus
    hypothesis: NonEmptyText
    allocations: Annotated[tuple[ResourceAllocation, ...], Field(min_length=1)]
    constraints: tuple[NonEmptyText, ...] = ()
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    generated_at: datetime
    rule_version: NonEmptyText

    @field_validator("generated_at")
    @classmethod
    def require_aware_block_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("block timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_block(self) -> BlockPlan:
        expected_end = self.starts_on + timedelta(days=self.duration_weeks * 7 - 1)
        if self.ends_on != expected_end:
            raise ValueError("block end date must match its duration")
        if sum(item.allocated_weekly_minutes for item in self.allocations) > (
            self.weekly_budget_minutes
        ):
            raise ValueError("block allocations cannot exceed the weekly budget")
        for field_name in (
            "constraints",
            "source_observation_ids",
            "evidence_claim_ids",
        ):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        for values, label in (
            ([item.resource_demand_id for item in self.allocations], "resource demands"),
            ([item.adaptation_priority_id for item in self.allocations], "priorities"),
            ([item.adaptation_id for item in self.allocations], "adaptations"),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"block allocations must contain unique {label}")
        statuses = {item.status for item in self.allocations}
        if self.status is BlockPlanStatus.FULL and statuses != {BlockPlanStatus.FULL}:
            raise ValueError("full blocks require every allocation to be full")
        if self.status is BlockPlanStatus.PARTIAL and (
            BlockPlanStatus.PARTIAL not in statuses or BlockPlanStatus.INFEASIBLE in statuses
        ):
            raise ValueError("partial blocks require a partial and no infeasible allocation")
        if self.status is BlockPlanStatus.INFEASIBLE and (
            BlockPlanStatus.INFEASIBLE not in statuses
        ):
            raise ValueError("infeasible blocks require an infeasible allocation")
        return self


class AbsoluteLoadTarget(DomainModel):
    kind: Literal["absolute_load"] = "absolute_load"
    value: float = Field(gt=0)
    unit: NonEmptyText


class RelativeLoadTarget(DomainModel):
    kind: Literal["relative_load"] = "relative_load"
    percentage: float = Field(gt=0, le=200)
    reference: NonEmptyText


class BodyweightTarget(DomainModel):
    kind: Literal["bodyweight"] = "bodyweight"


class EffortRpeTarget(DomainModel):
    kind: Literal["effort_rpe"] = "effort_rpe"
    minimum: float = Field(ge=0, le=10)
    maximum: float = Field(ge=0, le=10)

    @model_validator(mode="after")
    def validate_range(self) -> EffortRpeTarget:
        if self.maximum < self.minimum:
            raise ValueError("RPE maximum cannot be lower than minimum")
        return self


class RepetitionsInReserveTarget(DomainModel):
    kind: Literal["repetitions_in_reserve"] = "repetitions_in_reserve"
    minimum: float = Field(ge=0, le=10)
    maximum: float = Field(ge=0, le=10)

    @model_validator(mode="after")
    def validate_range(self) -> RepetitionsInReserveTarget:
        if self.maximum < self.minimum:
            raise ValueError("RIR maximum cannot be lower than minimum")
        return self


class HeartRateZoneTarget(DomainModel):
    kind: Literal["heart_rate_zone"] = "heart_rate_zone"
    zone: int = Field(ge=1, le=5)


class PaceTarget(DomainModel):
    kind: Literal["pace"] = "pace"
    value: float = Field(gt=0)
    unit: NonEmptyText


class TechniqueTarget(DomainModel):
    kind: Literal["technique"] = "technique"
    constraints: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_constraints(self) -> TechniqueTarget:
        if len(set(self.constraints)) != len(self.constraints):
            raise ValueError("technique constraints must not contain duplicates")
        return self


IntensityTarget = Annotated[
    AbsoluteLoadTarget
    | RelativeLoadTarget
    | BodyweightTarget
    | EffortRpeTarget
    | RepetitionsInReserveTarget
    | HeartRateZoneTarget
    | PaceTarget
    | TechniqueTarget,
    Field(discriminator="kind"),
]


class SessionPrescription(VersionedRecord):
    athlete_id: UUID
    block_plan_id: UUID
    resource_allocation_id: UUID
    exercise_resolution_id: UUID
    exercise_id: UUID
    adaptation_id: UUID
    reason_for_inclusion: NonEmptyText
    sets: int = Field(ge=1)
    repetitions_per_set: int | None = Field(default=None, ge=1)
    duration_seconds: int | None = Field(default=None, ge=1)
    intensity_targets: Annotated[tuple[IntensityTarget, ...], Field(min_length=1)]
    rest_seconds: int = Field(ge=0)
    progression_rule_reference: NonEmptyText
    substitution_class: NonEmptyText
    planned_duration_minutes: int = Field(gt=0)
    fatigue_cost: CostLevel
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    prescribed_at: datetime
    rule_version: NonEmptyText
    supersedes_prescription_id: UUID | None = None
    progression_decision_id: UUID | None = None

    @field_validator("prescribed_at")
    @classmethod
    def require_aware_prescribed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("prescription timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_prescription(self) -> SessionPrescription:
        if (self.repetitions_per_set is None) == (self.duration_seconds is None):
            raise ValueError("prescription requires exactly one of repetitions or duration")
        for field_name in ("source_observation_ids", "evidence_claim_ids"):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        if (self.supersedes_prescription_id is None) != (self.progression_decision_id is None):
            raise ValueError("prescription revisions require both superseded and decision ids")
        if self.supersedes_prescription_id == self.id:
            raise ValueError("a prescription cannot supersede itself")
        target_kinds = [item.kind for item in self.intensity_targets]
        if len(set(target_kinds)) != len(target_kinds):
            raise ValueError("intensity target kinds must not contain duplicates")
        load_kinds = {"absolute_load", "relative_load", "bodyweight"}
        if len(load_kinds & set(target_kinds)) > 1:
            raise ValueError("a prescription may contain only one load target")
        return self


class SessionTemplateItem(DomainModel):
    prescription_id: UUID
    order_index: int = Field(ge=1)
    section: SessionSection


class SessionTemplate(VersionedRecord):
    athlete_id: UUID
    block_plan_id: UUID
    name: NonEmptyText
    items: Annotated[tuple[SessionTemplateItem, ...], Field(min_length=1)]
    sessions_per_week: int = Field(ge=1)
    planned_duration_minutes: int = Field(gt=0)
    fatigue_cost: CostLevel
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    created_for_block_at: datetime
    rule_version: NonEmptyText
    previous_template_id: UUID | None = None

    @field_validator("created_for_block_at")
    @classmethod
    def require_aware_template_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("session template timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_template(self) -> SessionTemplate:
        order = tuple(item.order_index for item in self.items)
        if order != tuple(range(1, len(self.items) + 1)):
            raise ValueError("session template item order must be contiguous and start at one")
        if len({item.prescription_id for item in self.items}) != len(self.items):
            raise ValueError("session template prescriptions must not contain duplicates")
        for field_name in ("source_observation_ids", "evidence_claim_ids"):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        if self.previous_template_id == self.id:
            raise ValueError("a session template cannot follow itself")
        return self


class AvailabilityWindow(VersionedRecord):
    environment_id: UUID
    starts_at: datetime
    ends_at: datetime

    @field_validator("starts_at", "ends_at")
    @classmethod
    def require_aware_window_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("availability timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_window(self) -> AvailabilityWindow:
        if self.ends_at <= self.starts_at:
            raise ValueError("availability window must have positive duration")
        return self


class WeeklyAvailability(VersionedRecord):
    athlete_id: UUID
    week_start: date
    windows: tuple[AvailabilityWindow, ...] = ()
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    recorded_at: datetime
    rule_version: NonEmptyText

    @field_validator("recorded_at")
    @classmethod
    def require_aware_availability_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("availability timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_availability(self) -> WeeklyAvailability:
        if len(set(self.source_observation_ids)) != len(self.source_observation_ids):
            raise ValueError("source_observation_ids must not contain duplicates")
        if len({item.id for item in self.windows}) != len(self.windows):
            raise ValueError("availability windows must have unique ids")
        week_end = self.week_start + timedelta(days=7)
        for window in self.windows:
            if not (self.week_start <= window.starts_at.date() < week_end):
                raise ValueError("availability window must start within its week")
            if window.ends_at.date() > week_end or (
                window.ends_at.date() == week_end and window.ends_at.time() != datetime.min.time()
            ):
                raise ValueError("availability window must end within its week")
        ordered = sorted(self.windows, key=lambda item: item.starts_at)
        if any(current.starts_at < previous.ends_at for previous, current in pairwise(ordered)):
            raise ValueError("availability windows must not overlap")
        return self


class WeeklySchedulingPolicy(VersionedRecord):
    minimum_high_fatigue_recovery_hours: int = Field(ge=0)
    maximum_sessions_per_day: int = Field(ge=1)
    maximum_high_fatigue_sessions_per_day: int = Field(ge=1)
    allow_partial_exercise_resolution: bool
    policy_version: NonEmptyText


class SchedulingIssue(DomainModel):
    code: SchedulingIssueCode
    detail: NonEmptyText
    session_template_id: UUID
    occurrence_index: int = Field(ge=1)


class PlannedSession(VersionedRecord):
    session_template_id: UUID
    occurrence_index: int = Field(ge=1)
    availability_window_id: UUID
    environment_id: UUID
    starts_at: datetime
    ends_at: datetime
    planned_duration_minutes: int = Field(gt=0)
    fatigue_cost: CostLevel

    @field_validator("starts_at", "ends_at")
    @classmethod
    def require_aware_session_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("session timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_planned_session(self) -> PlannedSession:
        if self.ends_at <= self.starts_at:
            raise ValueError("planned session must have positive duration")
        if self.ends_at - self.starts_at != timedelta(minutes=self.planned_duration_minutes):
            raise ValueError("planned duration must match session timestamps")
        return self


class WeeklyPlan(VersionedRecord):
    athlete_id: UUID
    block_plan_id: UUID
    weekly_availability_id: UUID
    scheduling_policy_id: UUID
    week_start: date
    block_week: int = Field(ge=1, le=6)
    status: WeeklyPlanStatus
    sessions: tuple[PlannedSession, ...] = ()
    issues: tuple[SchedulingIssue, ...] = ()
    generated_at: datetime
    rule_version: NonEmptyText
    previous_weekly_plan_id: UUID | None = None

    @field_validator("generated_at")
    @classmethod
    def require_aware_weekly_plan_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("weekly plan timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_weekly_plan(self) -> WeeklyPlan:
        if self.previous_weekly_plan_id == self.id:
            raise ValueError("a weekly plan cannot follow itself")
        occurrence_keys = [
            (item.session_template_id, item.occurrence_index) for item in self.sessions
        ]
        if len(set(occurrence_keys)) != len(occurrence_keys):
            raise ValueError("weekly sessions must contain unique template occurrences")
        ordered = sorted(self.sessions, key=lambda item: item.starts_at)
        if any(current.starts_at < previous.ends_at for previous, current in pairwise(ordered)):
            raise ValueError("weekly sessions must not overlap")
        if self.status is WeeklyPlanStatus.FEASIBLE and self.issues:
            raise ValueError("feasible weekly plans cannot retain scheduling issues")
        if self.status is WeeklyPlanStatus.INFEASIBLE and not self.issues:
            raise ValueError("infeasible weekly plans require explicit issues")
        return self


class SafetySignal(DomainModel):
    tag: NonEmptyText
    classification: SafetySignalClass
    required_modifications: tuple[PrescriptionModification, ...] = ()

    @model_validator(mode="after")
    def validate_signal(self) -> SafetySignal:
        if len(set(self.required_modifications)) != len(self.required_modifications):
            raise ValueError("signal modifications must not contain duplicates")
        if self.classification is SafetySignalClass.MODIFY and not self.required_modifications:
            raise ValueError("modification-class signals require explicit modifications")
        if self.classification is SafetySignalClass.ESCALATE and self.required_modifications:
            raise ValueError("escalation-class signals cannot be reduced to modifications")
        return self


class SessionSafetyCheckInput(DomainModel):
    athlete_id: UUID
    weekly_plan_id: UUID
    planned_session_id: UUID
    related_session_execution_id: UUID | None = None
    timing: SafetyGateTiming
    readiness: ReadinessLevel | None = None
    unusual_soreness: bool = False
    major_sleep_disruption: bool = False
    major_schedule_limitation: bool = False
    signals: tuple[SafetySignal, ...] = ()
    note: str | None = None
    reported_at: datetime
    reliability: Confidence
    provenance: Provenance

    @field_validator("reported_at")
    @classmethod
    def require_aware_safety_report_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("safety report timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_safety_check(self) -> SessionSafetyCheckInput:
        keys = [(item.tag, item.classification) for item in self.signals]
        if len(set(keys)) != len(keys):
            raise ValueError("safety signals must not contain duplicates")
        if self.timing is SafetyGateTiming.PRE_SESSION:
            if self.readiness is None:
                raise ValueError("pre-session checks require readiness")
            if self.related_session_execution_id is not None:
                raise ValueError("pre-session checks cannot reference an execution")
        elif self.related_session_execution_id is None:
            raise ValueError("post-session checks require a related execution")
        return self


class SessionSafetyPolicy(VersionedRecord):
    allowed_modifications: Annotated[tuple[PrescriptionModification, ...], Field(min_length=1)]
    limited_readiness_modifications: Annotated[
        tuple[PrescriptionModification, ...], Field(min_length=1)
    ]
    unusual_soreness_modifications: Annotated[
        tuple[PrescriptionModification, ...], Field(min_length=1)
    ]
    sleep_disruption_modifications: Annotated[
        tuple[PrescriptionModification, ...], Field(min_length=1)
    ]
    schedule_limitation_modifications: Annotated[
        tuple[PrescriptionModification, ...], Field(min_length=1)
    ]
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    rationale: NonEmptyText
    policy_version: NonEmptyText

    @model_validator(mode="after")
    def validate_safety_policy(self) -> SessionSafetyPolicy:
        if len(set(self.allowed_modifications)) != len(self.allowed_modifications):
            raise ValueError("allowed modifications must not contain duplicates")
        allowed = set(self.allowed_modifications)
        for field_name in (
            "limited_readiness_modifications",
            "unusual_soreness_modifications",
            "sleep_disruption_modifications",
            "schedule_limitation_modifications",
            "evidence_claim_ids",
        ):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
            if field_name != "evidence_claim_ids" and not set(values) <= allowed:
                raise ValueError(f"{field_name} contains a modification not allowed by policy")
        return self


class AthleteSafetyPolicyAssignment(VersionedRecord):
    athlete_id: UUID
    safety_policy_id: UUID
    sequence_number: Annotated[int, Field(ge=1)]
    supersedes_assignment_id: UUID | None = None
    assigned_at: datetime
    assigned_by: NonEmptyText
    applicability_rationale: NonEmptyText
    rule_version: NonEmptyText

    @field_validator("assigned_at")
    @classmethod
    def require_aware_assignment_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("safety-policy assignment time must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_assignment_chain(self) -> AthleteSafetyPolicyAssignment:
        if self.sequence_number == 1 and self.supersedes_assignment_id is not None:
            raise ValueError("the first safety-policy assignment cannot supersede another record")
        if self.sequence_number > 1 and self.supersedes_assignment_id is None:
            raise ValueError("later safety-policy assignments must reference their predecessor")
        if self.supersedes_assignment_id == self.id:
            raise ValueError("a safety-policy assignment cannot supersede itself")
        return self


class SessionSafetyDecision(VersionedRecord):
    athlete_id: UUID
    weekly_plan_id: UUID
    planned_session_id: UUID
    related_session_execution_id: UUID | None = None
    safety_policy_id: UUID
    safety_policy_assignment_id: UUID | None = None
    timing: SafetyGateTiming
    outcome: SafetyGateOutcome
    required_modifications: tuple[PrescriptionModification, ...] = ()
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    rationale: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    decided_at: datetime
    rule_version: NonEmptyText

    @field_validator("decided_at")
    @classmethod
    def require_aware_safety_decision_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("safety decision timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_safety_decision(self) -> SessionSafetyDecision:
        for field_name in (
            "required_modifications",
            "source_observation_ids",
            "rationale",
        ):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        if self.outcome is SafetyGateOutcome.MODIFY:
            if not self.required_modifications:
                raise ValueError("modify decisions require explicit modifications")
        elif self.required_modifications:
            raise ValueError("only modify decisions may require modifications")
        if self.timing is SafetyGateTiming.PRE_SESSION:
            if self.related_session_execution_id is not None:
                raise ValueError("pre-session decisions cannot reference an execution")
        elif self.related_session_execution_id is None:
            raise ValueError("post-session decisions require a related execution")
        return self


class SetPerformance(VersionedRecord):
    set_index: int = Field(ge=1)
    performed: bool
    target_completed: bool
    actual_repetitions: int | None = Field(default=None, ge=0)
    actual_duration_seconds: int | None = Field(default=None, ge=0)
    load_value: float | None = Field(default=None, ge=0)
    load_unit: str | None = None
    effort_rpe: float | None = Field(default=None, ge=0, le=10)
    technique_constraint_met: bool | None = None

    @model_validator(mode="after")
    def validate_set_performance(self) -> SetPerformance:
        if self.target_completed and not self.performed:
            raise ValueError("an unperformed set cannot complete its target")
        dose_values = (self.actual_repetitions, self.actual_duration_seconds)
        if self.performed and sum(value is not None for value in dose_values) != 1:
            raise ValueError("performed sets require exactly one repetitions-or-duration value")
        if not self.performed and any(value is not None for value in dose_values):
            raise ValueError("unperformed sets cannot contain an actual dose")
        if (self.load_value is None) != (self.load_unit is None):
            raise ValueError("load value and unit must be supplied together")
        if not self.performed and any(
            value is not None
            for value in (self.load_value, self.effort_rpe, self.technique_constraint_met)
        ):
            raise ValueError("unperformed sets cannot contain performance details")
        return self


class SessionItemExecutionInput(DomainModel):
    prescription_id: UUID
    status: SessionExecutionStatus
    performances: tuple[SetPerformance, ...] = ()
    item_rpe: float | None = Field(default=None, ge=0, le=10)
    note: str | None = None

    @model_validator(mode="after")
    def validate_item_execution_input(self) -> SessionItemExecutionInput:
        if len({item.set_index for item in self.performances}) != len(self.performances):
            raise ValueError("set performance indices must be unique within an item")
        if self.status is SessionExecutionStatus.NOT_STARTED:
            if self.performances or self.item_rpe is not None:
                raise ValueError("not-started items cannot contain performed work or effort")
        elif not self.performances:
            raise ValueError("started items require set performance records")
        return self


class SessionExecutionInput(DomainModel):
    athlete_id: UUID
    weekly_plan_id: UUID
    planned_session_id: UUID
    pre_session_safety_decision_id: UUID
    status: SessionExecutionStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None
    items: Annotated[tuple[SessionItemExecutionInput, ...], Field(min_length=1)]
    applied_modifications: tuple[PrescriptionModification, ...] = ()
    session_rpe: float | None = Field(default=None, ge=0, le=10)
    note: str | None = None
    logged_at: datetime
    reliability: Confidence
    provenance: Provenance

    @field_validator("started_at", "ended_at", "logged_at")
    @classmethod
    def require_aware_execution_input_times(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("execution timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_execution_input(self) -> SessionExecutionInput:
        if len({item.prescription_id for item in self.items}) != len(self.items):
            raise ValueError("session execution items must use unique prescriptions")
        if len(set(self.applied_modifications)) != len(self.applied_modifications):
            raise ValueError("applied modifications must not contain duplicates")
        if self.status is SessionExecutionStatus.NOT_STARTED:
            if self.started_at is not None or self.ended_at is not None:
                raise ValueError("not-started execution cannot contain a time interval")
            if any(item.status is not SessionExecutionStatus.NOT_STARTED for item in self.items):
                raise ValueError("not-started sessions require every item to be not started")
            if self.session_rpe is not None:
                raise ValueError("not-started execution cannot contain session effort")
        else:
            if self.started_at is None or self.ended_at is None:
                raise ValueError("started execution requires start and end timestamps")
            if self.ended_at <= self.started_at:
                raise ValueError("execution end must be later than its start")
            if self.logged_at < self.ended_at:
                raise ValueError("execution cannot be logged before it ends")
            item_statuses = {item.status for item in self.items}
            if self.status is SessionExecutionStatus.COMPLETED and item_statuses != {
                SessionExecutionStatus.COMPLETED
            }:
                raise ValueError("completed sessions require every item to be completed")
            if self.status is SessionExecutionStatus.PARTIAL and (
                item_statuses == {SessionExecutionStatus.COMPLETED}
                or item_statuses == {SessionExecutionStatus.NOT_STARTED}
            ):
                raise ValueError("partial sessions require a mixture of completed and limited work")
        return self


class SessionItemExecution(VersionedRecord):
    prescription_id: UUID
    status: SessionExecutionStatus
    performances: tuple[SetPerformance, ...] = ()
    item_rpe: float | None = Field(default=None, ge=0, le=10)
    note: str | None = None

    @model_validator(mode="after")
    def validate_item_execution(self) -> SessionItemExecution:
        if len({item.set_index for item in self.performances}) != len(self.performances):
            raise ValueError("set performance indices must be unique within an item")
        if self.status is SessionExecutionStatus.NOT_STARTED:
            if self.performances or self.item_rpe is not None:
                raise ValueError("not-started items cannot contain performed work or effort")
        elif not self.performances:
            raise ValueError("started items require set performance records")
        return self


class SessionExecution(VersionedRecord):
    athlete_id: UUID
    weekly_plan_id: UUID
    planned_session_id: UUID
    session_template_id: UUID
    pre_session_safety_decision_id: UUID
    status: SessionExecutionStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None
    items: Annotated[tuple[SessionItemExecution, ...], Field(min_length=1)]
    applied_modifications: tuple[PrescriptionModification, ...] = ()
    session_rpe: float | None = Field(default=None, ge=0, le=10)
    note: str | None = None
    performance_observation_id: UUID
    logged_at: datetime
    rule_version: NonEmptyText

    @field_validator("started_at", "ended_at", "logged_at")
    @classmethod
    def require_aware_execution_times(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("execution timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_execution(self) -> SessionExecution:
        if len({item.prescription_id for item in self.items}) != len(self.items):
            raise ValueError("session execution items must use unique prescriptions")
        if len(set(self.applied_modifications)) != len(self.applied_modifications):
            raise ValueError("applied modifications must not contain duplicates")
        if self.status is SessionExecutionStatus.NOT_STARTED:
            if self.started_at is not None or self.ended_at is not None:
                raise ValueError("not-started execution cannot contain a time interval")
            if any(item.status is not SessionExecutionStatus.NOT_STARTED for item in self.items):
                raise ValueError("not-started sessions require every item to be not started")
        elif self.started_at is None or self.ended_at is None or self.ended_at <= self.started_at:
            raise ValueError("started execution requires a valid time interval")
        elif self.status is SessionExecutionStatus.COMPLETED and any(
            item.status is not SessionExecutionStatus.COMPLETED for item in self.items
        ):
            raise ValueError("completed sessions require every item to be completed")
        return self


class SessionAdherence(VersionedRecord):
    kind: Literal["derived"] = "derived"
    athlete_id: UUID
    session_execution_id: UUID
    planned_session_id: UUID
    prescription_id: UUID
    prescribed_sets: int = Field(ge=1)
    performed_sets: int = Field(ge=0)
    target_completed_sets: int = Field(ge=0)
    prescribed_dose_total: int = Field(ge=1)
    actual_dose_total: int = Field(ge=0)
    dose_unit: Literal["repetitions", "seconds"]
    set_completion_ratio: UnitInterval
    dose_completion_ratio: UnitInterval
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    calculated_at: datetime
    calculation_method: NonEmptyText
    rule_version: NonEmptyText

    @field_validator("calculated_at")
    @classmethod
    def require_aware_adherence_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("adherence timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_adherence(self) -> SessionAdherence:
        if self.performed_sets > self.prescribed_sets:
            raise ValueError("performed sets cannot exceed prescribed sets")
        if self.target_completed_sets > self.performed_sets:
            raise ValueError("target-completed sets cannot exceed performed sets")
        if len(set(self.source_observation_ids)) != len(self.source_observation_ids):
            raise ValueError("source_observation_ids must not contain duplicates")
        return self


class PrescriptionAdjustment(DomainModel):
    dimension: ProgressionDimension
    amount: float = Field(gt=0)
    unit: NonEmptyText
    description: NonEmptyText


class ProgressionPolicy(VersionedRecord):
    reference: NonEmptyText
    minimum_set_completion_ratio: UnitInterval
    minimum_dose_completion_ratio: UnitInterval
    maximum_session_rpe: float = Field(ge=0, le=10)
    require_technique_constraint: bool = True
    adjustment: PrescriptionAdjustment
    exposure_type: ExposureType | None = None
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    rationale: NonEmptyText
    policy_version: NonEmptyText

    @model_validator(mode="after")
    def validate_progression_policy(self) -> ProgressionPolicy:
        if len(set(self.evidence_claim_ids)) != len(self.evidence_claim_ids):
            raise ValueError("evidence_claim_ids must not contain duplicates")
        return self


class ExposureDefinition(VersionedRecord):
    exercise_id: UUID
    exposure_type: ExposureType
    dose_unit: Literal["repetitions", "seconds"]
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    rationale: NonEmptyText
    definition_version: NonEmptyText


class ExposureEntry(VersionedRecord):
    kind: Literal["derived"] = "derived"
    athlete_id: UUID
    session_execution_id: UUID
    planned_session_id: UUID
    prescription_id: UUID
    exposure_definition_id: UUID
    exposure_type: ExposureType
    dose_value: float = Field(ge=0)
    dose_unit: Literal["repetitions", "seconds"]
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    occurred_at: datetime
    calculation_method: NonEmptyText
    rule_version: NonEmptyText

    @field_validator("occurred_at")
    @classmethod
    def require_aware_exposure_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("exposure timestamps must include a timezone")
        return value


class ExposureProgressionPolicy(VersionedRecord):
    exposure_type: ExposureType
    dose_unit: Literal["repetitions", "seconds"]
    lookback_days: int = Field(ge=1)
    minimum_recent_entries: int = Field(ge=1)
    maximum_initial_dose: float = Field(gt=0)
    maximum_relative_increase: float = Field(ge=0)
    maximum_absolute_increase: float = Field(ge=0)
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    rationale: NonEmptyText
    policy_version: NonEmptyText


class ExposureTarget(DomainModel):
    athlete_id: UUID
    prescription_id: UUID
    exposure_type: ExposureType
    proposed_dose: float = Field(gt=0)
    dose_unit: Literal["repetitions", "seconds"]
    proposed_for: datetime

    @field_validator("proposed_for")
    @classmethod
    def require_aware_target_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("exposure target timestamps must include a timezone")
        return value


class ExposureValidationDecision(VersionedRecord):
    athlete_id: UUID
    prescription_id: UUID
    exposure_policy_id: UUID
    exposure_type: ExposureType
    proposed_dose: float = Field(gt=0)
    dose_unit: Literal["repetitions", "seconds"]
    baseline_dose: float | None = Field(default=None, ge=0)
    maximum_allowed_dose: float = Field(gt=0)
    source_exposure_entry_ids: tuple[UUID, ...] = ()
    outcome: ExposureValidationOutcome
    rationale: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    decided_at: datetime
    rule_version: NonEmptyText

    @field_validator("decided_at")
    @classmethod
    def require_aware_exposure_decision_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("exposure decision timestamps must include a timezone")
        return value


class ProgressionDecision(VersionedRecord):
    athlete_id: UUID
    weekly_plan_id: UUID
    planned_session_id: UUID
    prescription_id: UUID
    session_execution_id: UUID
    session_adherence_id: UUID
    progression_policy_id: UUID
    post_session_safety_decision_ids: tuple[UUID, ...] = ()
    exposure_validation_decision_id: UUID | None = None
    outcome: ProgressionOutcome
    adjustment: PrescriptionAdjustment | None = None
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    rationale: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    decided_at: datetime
    rule_version: NonEmptyText

    @model_validator(mode="after")
    def validate_progression_decision(self) -> ProgressionDecision:
        if self.outcome is ProgressionOutcome.PROGRESS and self.adjustment is None:
            raise ValueError("progress decisions require an adjustment")
        if self.outcome is not ProgressionOutcome.PROGRESS and self.adjustment is not None:
            raise ValueError("only progress decisions may contain an adjustment")
        return self


class TrainingResponse(VersionedRecord):
    kind: Literal["derived"] = "derived"
    athlete_id: UUID
    block_plan_id: UUID
    adaptation_id: UUID
    intervention_summary: NonEmptyText
    prescription_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    session_execution_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    session_adherence_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    prescribed_sessions: int = Field(ge=1)
    completed_sessions: int = Field(ge=0)
    prescribed_dose_total: float = Field(ge=0)
    actual_dose_total: float = Field(ge=0)
    dose_unit: NonEmptyText
    adherence_ratio: UnitInterval
    baseline_capability_estimate_id: UUID
    followup_capability_estimate_id: UUID
    baseline_value: float
    followup_value: float
    observed_change: float
    measurement_uncertainty: NonEmptyText
    contextual_factors: tuple[NonEmptyText, ...] = ()
    confidence: Confidence
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    calculated_at: datetime
    calculation_method: NonEmptyText
    rule_version: NonEmptyText

    @field_validator("calculated_at")
    @classmethod
    def require_aware_response_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("response timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_training_response(self) -> TrainingResponse:
        if self.completed_sessions > self.prescribed_sessions:
            raise ValueError("completed sessions cannot exceed prescribed sessions")
        for field_name in (
            "prescription_ids",
            "session_execution_ids",
            "session_adherence_ids",
            "contextual_factors",
            "source_observation_ids",
        ):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        if len(self.session_adherence_ids) != self.prescribed_sessions:
            raise ValueError("prescribed sessions must match item-level adherence records")
        if len(self.session_execution_ids) > len(self.session_adherence_ids):
            raise ValueError("each execution requires at least one item-level adherence record")
        return self


class BlockReviewPolicy(VersionedRecord):
    minimum_adherence_ratio: UnitInterval
    minimum_response_confidence: Confidence
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    rationale: NonEmptyText
    policy_version: NonEmptyText

    @model_validator(mode="after")
    def validate_block_review_policy(self) -> BlockReviewPolicy:
        if len(set(self.evidence_claim_ids)) != len(self.evidence_claim_ids):
            raise ValueError("evidence_claim_ids must not contain duplicates")
        return self


class ResponseEvaluation(DomainModel):
    training_response_id: UUID
    comparison_direction: ComparisonDirection
    minimum_meaningful_change: float = Field(ge=0)
    threshold_met: bool | None
    rationale: NonEmptyText


class ResponseEvaluationTarget(DomainModel):
    training_response_id: UUID
    comparison_direction: ComparisonDirection
    minimum_meaningful_change: float = Field(ge=0)


class BlockReview(VersionedRecord):
    kind: Literal["derived"] = "derived"
    athlete_id: UUID
    block_plan_id: UUID
    block_hypothesis: NonEmptyText
    block_review_policy_id: UUID
    training_response_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    response_evaluations: Annotated[tuple[ResponseEvaluation, ...], Field(min_length=1)]
    post_session_safety_decision_ids: tuple[UUID, ...] = ()
    prescribed_sessions: int = Field(ge=1)
    completed_sessions: int = Field(ge=0)
    aggregate_adherence_ratio: UnitInterval
    outcome: BlockReviewOutcome
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    rationale: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    reviewed_at: datetime
    rule_version: NonEmptyText

    @field_validator("reviewed_at")
    @classmethod
    def require_aware_review_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("review timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_review(self) -> BlockReview:
        if self.completed_sessions > self.prescribed_sessions:
            raise ValueError("completed sessions cannot exceed prescribed sessions")
        if (
            tuple(item.training_response_id for item in self.response_evaluations)
            != self.training_response_ids
        ):
            raise ValueError("response evaluations must match ordered training responses")
        for field_name in (
            "training_response_ids",
            "post_session_safety_decision_ids",
            "source_observation_ids",
            "evidence_claim_ids",
            "rationale",
        ):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        return self
