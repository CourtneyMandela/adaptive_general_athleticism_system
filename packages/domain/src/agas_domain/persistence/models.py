from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from agas_domain.persistence.types import UTCDateTime

JsonType = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    type_annotation_map: ClassVar[dict[object, object]] = {
        dict[str, Any]: JsonType,
        list[Any]: JsonType,
    }


class VersionedRecordMixin:
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class AccountRecord(VersionedRecordMixin, Base):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("issuer", "subject", name="uq_account_issuer_subject"),)

    issuer: Mapped[str] = mapped_column(String(300), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)


class AccountRoleAssignmentRecord(VersionedRecordMixin, Base):
    __tablename__ = "account_role_assignments"
    __table_args__ = (
        CheckConstraint(
            "role IN ('planning_reviewer', 'assessment_reviewer')",
            name="ck_account_role_assignment_role",
        ),
        CheckConstraint(
            "status IN ('active', 'revoked')",
            name="ck_account_role_assignment_status",
        ),
        CheckConstraint(
            "sequence_number >= 1",
            name="ck_account_role_assignment_sequence_positive",
        ),
        UniqueConstraint(
            "account_id",
            "role",
            "sequence_number",
            name="uq_account_role_assignment_sequence",
        ),
        UniqueConstraint(
            "supersedes_assignment_id",
            name="uq_account_role_assignment_superseded_once",
        ),
    )

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    supersedes_assignment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("account_role_assignments.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    assigned_by: Mapped[str] = mapped_column(String(160), nullable=False)
    rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(120), nullable=False)


class AthleteRecord(VersionedRecordMixin, Base):
    __tablename__ = "athletes"

    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date(), nullable=True)
    preferences: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    goals: Mapped[list[str]] = mapped_column(JsonType, nullable=False, default=list)


class AthleteOwnershipRecord(VersionedRecordMixin, Base):
    __tablename__ = "athlete_ownerships"
    __table_args__ = (UniqueConstraint("athlete_id", name="uq_athlete_owner"),)

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    granted_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    grant_method: Mapped[str] = mapped_column(String(120), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(120), nullable=False)


class ObservationRecord(VersionedRecordMixin, Base):
    __tablename__ = "observations"

    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    observation_type: Mapped[str] = mapped_column(String(120), nullable=False)
    measurement: Mapped[Any] = mapped_column(JsonType, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    reliability: Mapped[str] = mapped_column(String(40), nullable=False)
    context: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    provenance: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)


class CapabilityEstimateRecord(VersionedRecordMixin, Base):
    __tablename__ = "capability_estimates"
    __table_args__ = (
        CheckConstraint("kind = 'derived'", name="ck_estimate_is_derived"),
        CheckConstraint(
            "(capability_estimation_policy_id IS NULL) = "
            "(triggering_assessment_performance_id IS NULL)",
            name="ck_assessment_estimate_lineage_complete",
        ),
        UniqueConstraint(
            "triggering_assessment_performance_id",
            "capability_estimation_policy_id",
            name="uq_assessment_estimate_performance_policy",
        ),
    )

    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="derived")
    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    domain: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    estimate: Mapped[Any] = mapped_column(JsonType, nullable=False)
    unit_or_scale: Mapped[str] = mapped_column(String(80), nullable=False)
    estimate_scope: Mapped[str] = mapped_column(String(160), nullable=False)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False)
    calculation_method: Mapped[str] = mapped_column(String(160), nullable=False)
    estimated_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    rule_version: Mapped[str] = mapped_column(String(80), nullable=False)
    capability_estimation_policy_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("capability_estimation_policies.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    triggering_assessment_performance_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assessment_performances.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )

    source_links: Mapped[list[CapabilityEstimateObservationRecord]] = relationship(
        back_populates="estimate",
        cascade="save-update, merge",
        lazy="selectin",
        order_by="CapabilityEstimateObservationRecord.source_order",
    )


class CapabilityEstimateObservationRecord(Base):
    __tablename__ = "capability_estimate_observations"
    __table_args__ = (
        UniqueConstraint("estimate_id", "source_order", name="uq_estimate_source_order"),
    )

    estimate_id: Mapped[UUID] = mapped_column(
        ForeignKey("capability_estimates.id", ondelete="RESTRICT"), primary_key=True
    )
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), primary_key=True
    )
    source_order: Mapped[int] = mapped_column(Integer(), nullable=False)
    estimate: Mapped[CapabilityEstimateRecord] = relationship(back_populates="source_links")


class EnvironmentRecord(VersionedRecordMixin, Base):
    __tablename__ = "environments"
    __table_args__ = (UniqueConstraint("athlete_id", "name", name="uq_environment_name"),)

    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    space_constraints: Mapped[dict[str, Any]] = mapped_column(
        JsonType, nullable=False, default=dict
    )
    noise_constraints: Mapped[str | None] = mapped_column(Text(), nullable=True)
    max_noise_level: Mapped[str] = mapped_column(String(40), nullable=False)
    outdoor_access: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)


class EquipmentRecord(VersionedRecordMixin, Base):
    __tablename__ = "equipment"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    capabilities: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)


class EquipmentAvailabilityRecord(VersionedRecordMixin, Base):
    __tablename__ = "equipment_availability"

    environment_id: Mapped[UUID] = mapped_column(
        ForeignKey("environments.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    equipment_id: Mapped[UUID] = mapped_column(
        ForeignKey("equipment.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    source_observation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    is_available: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    effective_until: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    capabilities: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    load_limits: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    reason: Mapped[str | None] = mapped_column(Text(), nullable=True)


class ExerciseRecord(VersionedRecordMixin, Base):
    __tablename__ = "exercises"

    name: Mapped[str] = mapped_column(String(180), nullable=False)
    movement_patterns: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    joint_demands: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    loading_type: Mapped[str] = mapped_column(String(100), nullable=False)
    laterality: Mapped[str] = mapped_column(String(40), nullable=False)
    loadability: Mapped[str] = mapped_column(String(40), nullable=False)
    skill_complexity: Mapped[str] = mapped_column(String(40), nullable=False)
    impact_level: Mapped[str] = mapped_column(String(40), nullable=False)
    velocity_characteristics: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    stability_demand: Mapped[str] = mapped_column(String(40), nullable=False)
    fatigue_cost: Mapped[str] = mapped_column(String(40), nullable=False)
    soreness_cost: Mapped[str] = mapped_column(String(40), nullable=False)
    requires_outdoor_access: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    minimum_floor_area_m2: Mapped[float | None] = mapped_column(Float(), nullable=True)
    noise_level: Mapped[str] = mapped_column(String(40), nullable=False)
    contraindication_tags: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    measurement_methods: Mapped[list[str]] = mapped_column(JsonType, nullable=False)

    adaptation_links: Mapped[list[ExerciseAdaptationRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="ExerciseAdaptationRecord.position",
    )
    equipment_links: Mapped[list[ExerciseEquipmentRequirementRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="ExerciseEquipmentRequirementRecord.position",
    )
    exercise_links: Mapped[list[ExerciseRelationshipRecord]] = relationship(
        foreign_keys="ExerciseRelationshipRecord.source_exercise_id",
        cascade="save-update, merge",
        lazy="selectin",
        order_by="ExerciseRelationshipRecord.position",
    )


class AdaptationRecord(VersionedRecordMixin, Base):
    __tablename__ = "adaptations"

    name: Mapped[str] = mapped_column(String(180), nullable=False)
    domain: Mapped[str] = mapped_column(String(80), nullable=False)
    preferred_stimuli: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    valid_modalities: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    dose_dimensions: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    fatigue_characteristics: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    typical_measurement_methods: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    maintenance_requirements: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)

    evidence_links: Mapped[list[AdaptationEvidenceClaimRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="AdaptationEvidenceClaimRecord.position",
    )
    relationship_links: Mapped[list[AdaptationRelationshipRecord]] = relationship(
        foreign_keys="AdaptationRelationshipRecord.source_adaptation_id",
        cascade="save-update, merge",
        lazy="selectin",
        order_by="AdaptationRelationshipRecord.position",
    )


class EvidenceClaimRecord(VersionedRecordMixin, Base):
    __tablename__ = "evidence_claims"

    claim: Mapped[str] = mapped_column(Text(), nullable=False)
    domain: Mapped[str] = mapped_column(String(120), nullable=False)
    population: Mapped[str] = mapped_column(Text(), nullable=False)
    intervention: Mapped[str] = mapped_column(Text(), nullable=False)
    comparator: Mapped[str | None] = mapped_column(Text(), nullable=True)
    outcome: Mapped[str] = mapped_column(Text(), nullable=False)
    study_design: Mapped[str] = mapped_column(String(120), nullable=False)
    sample_size: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(120), nullable=True)
    effect_direction: Mapped[str | None] = mapped_column(String(120), nullable=True)
    uncertainty: Mapped[str] = mapped_column(Text(), nullable=False)
    limitations: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    evidence_strength: Mapped[str] = mapped_column(String(40), nullable=False)
    athlete_applicability: Mapped[str] = mapped_column(String(40), nullable=False)
    applicability_notes: Mapped[str] = mapped_column(Text(), nullable=False)
    source_identifiers: Mapped[list[dict[str, str]]] = mapped_column(JsonType, nullable=False)
    reviewer: Mapped[str] = mapped_column(String(160), nullable=False)
    claim_version: Mapped[str] = mapped_column(String(80), nullable=False)


class AssessmentDefinitionRecord(VersionedRecordMixin, Base):
    __tablename__ = "assessment_definitions"

    slug: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    domain: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    observation_type: Mapped[str] = mapped_column(String(120), nullable=False)
    intensity: Mapped[str] = mapped_column(String(40), nullable=False)
    unit_or_scale: Mapped[str] = mapped_column(String(80), nullable=False)
    protocol_version: Mapped[str] = mapped_column(String(80), nullable=False)
    requires_body_mass: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    required_equipment_categories: Mapped[list[str]] = mapped_column(
        JsonType, nullable=False, default=list
    )
    min_training_age_months: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    required_skill_tags: Mapped[list[str]] = mapped_column(JsonType, nullable=False, default=list)
    required_recent_exposure_tags: Mapped[list[str]] = mapped_column(
        JsonType, nullable=False, default=list
    )
    blocked_by_symptom_flags: Mapped[list[str]] = mapped_column(
        JsonType, nullable=False, default=list
    )
    blocked_by_injury_flags: Mapped[list[str]] = mapped_column(
        JsonType, nullable=False, default=list
    )
    blocked_by_health_screening_flags: Mapped[list[str]] = mapped_column(
        JsonType, nullable=False, default=list
    )


class AssessmentDefinitionReviewRecord(VersionedRecordMixin, Base):
    __tablename__ = "assessment_definition_reviews"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved', 'needs_revision', 'rejected')",
            name="ck_assessment_review_decision",
        ),
        CheckConstraint("sequence_number >= 1", name="ck_assessment_review_sequence_positive"),
        CheckConstraint(
            "recommended_reassessment_days IS NULL OR recommended_reassessment_days >= 1",
            name="ck_assessment_review_reassessment_positive",
        ),
        CheckConstraint(
            "decision != 'approved' OR recommended_reassessment_days IS NOT NULL",
            name="ck_approved_assessment_has_reassessment_interval",
        ),
        UniqueConstraint(
            "assessment_definition_id",
            "sequence_number",
            name="uq_assessment_review_definition_sequence",
        ),
        UniqueConstraint("supersedes_review_id", name="uq_assessment_review_superseded_once"),
    )

    assessment_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessment_definitions.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    supersedes_review_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assessment_definition_reviews.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    protocol_instructions: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    result_entry_instructions: Mapped[str] = mapped_column(Text(), nullable=False)
    measurement_schema: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    recommended_reassessment_days: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    self_administered: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    reviewer: Mapped[str] = mapped_column(String(160), nullable=False)
    applicability_notes: Mapped[str] = mapped_column(Text(), nullable=False)
    uncertainty: Mapped[str] = mapped_column(Text(), nullable=False)
    review_version: Mapped[str] = mapped_column(String(120), nullable=False)

    evidence_links: Mapped[list[AssessmentDefinitionReviewEvidenceClaimRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="AssessmentDefinitionReviewEvidenceClaimRecord.position",
    )


class AssessmentDefinitionReviewEvidenceClaimRecord(Base):
    __tablename__ = "assessment_definition_review_evidence_claims"
    __table_args__ = (
        UniqueConstraint(
            "assessment_review_id",
            "position",
            name="uq_assessment_review_evidence_order",
        ),
    )

    assessment_review_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessment_definition_reviews.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class CapabilityEstimationPolicyRecord(VersionedRecordMixin, Base):
    __tablename__ = "capability_estimation_policies"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved', 'needs_revision', 'rejected')",
            name="ck_capability_estimation_policy_decision",
        ),
        CheckConstraint(
            "sequence_number >= 1", name="ck_capability_estimation_policy_sequence_positive"
        ),
        CheckConstraint("valid_for_days >= 1", name="ck_capability_estimation_validity_positive"),
        CheckConstraint(
            "multi_observation_window_days >= 1",
            name="ck_capability_estimation_window_positive",
        ),
        UniqueConstraint(
            "assessment_definition_id",
            "sequence_number",
            name="uq_capability_estimation_policy_definition_sequence",
        ),
        UniqueConstraint(
            "supersedes_policy_id", name="uq_capability_estimation_policy_superseded_once"
        ),
        Index("ix_cap_estimation_policy_definition", "assessment_definition_id"),
        Index(
            "ix_cap_estimation_policy_definition_review",
            "assessment_definition_review_id",
        ),
        Index("ix_cap_estimation_policy_decision", "decision"),
        Index("ix_cap_estimation_policy_supersedes", "supersedes_policy_id"),
        Index("ix_cap_estimation_policy_domain", "domain"),
        Index("ix_cap_estimation_policy_reviewed_at", "reviewed_at"),
    )

    assessment_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessment_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    assessment_definition_review_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessment_definition_reviews.id", ondelete="RESTRICT"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    supersedes_policy_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("capability_estimation_policies.id", ondelete="RESTRICT"),
        nullable=True,
    )
    domain: Mapped[str] = mapped_column(String(80), nullable=False)
    observation_type: Mapped[str] = mapped_column(String(120), nullable=False)
    unit_or_scale: Mapped[str] = mapped_column(String(80), nullable=False)
    calculation_method: Mapped[str] = mapped_column(String(160), nullable=False)
    valid_for_days: Mapped[int] = mapped_column(Integer(), nullable=False)
    multi_observation_window_days: Mapped[int] = mapped_column(Integer(), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(160), nullable=False)
    applicability_notes: Mapped[str] = mapped_column(Text(), nullable=False)
    uncertainty: Mapped[str] = mapped_column(Text(), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(120), nullable=False)

    evidence_links: Mapped[list[CapabilityEstimationPolicyEvidenceClaimRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="CapabilityEstimationPolicyEvidenceClaimRecord.position",
    )


class CapabilityEstimationPolicyEvidenceClaimRecord(Base):
    __tablename__ = "capability_estimation_policy_evidence_claims"
    __table_args__ = (
        UniqueConstraint(
            "capability_estimation_policy_id",
            "position",
            name="uq_capability_estimation_policy_evidence_order",
        ),
    )

    capability_estimation_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("capability_estimation_policies.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class AssessmentEligibilityReviewRecord(VersionedRecordMixin, Base):
    __tablename__ = "assessment_eligibility_reviews"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('selection_allowed', 'selection_blocked', 'review_required')",
            name="ck_assessment_eligibility_outcome",
        ),
        CheckConstraint("sequence_number >= 1", name="ck_assessment_eligibility_sequence_positive"),
        CheckConstraint("valid_until > reviewed_at", name="ck_assessment_eligibility_valid_window"),
        UniqueConstraint(
            "athlete_id",
            "sequence_number",
            name="uq_assessment_eligibility_athlete_sequence",
        ),
        UniqueConstraint("supersedes_review_id", name="uq_assessment_eligibility_superseded_once"),
    )

    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    outcome: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    supersedes_review_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assessment_eligibility_reviews.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    valid_until: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(160), nullable=False)
    screening_process_reference: Mapped[str] = mapped_column(String(160), nullable=False)
    rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    uncertainty: Mapped[str] = mapped_column(Text(), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(120), nullable=False)

    source_links: Mapped[list[AssessmentEligibilityReviewObservationRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="AssessmentEligibilityReviewObservationRecord.position",
    )


class AssessmentEligibilityReviewObservationRecord(Base):
    __tablename__ = "assessment_eligibility_review_observations"
    __table_args__ = (
        UniqueConstraint(
            "eligibility_review_id",
            "position",
            name="uq_assessment_eligibility_observation_order",
        ),
    )

    eligibility_review_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessment_eligibility_reviews.id", ondelete="RESTRICT"), primary_key=True
    )
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class AssessmentSelectionRecord(VersionedRecordMixin, Base):
    __tablename__ = "assessment_selections"

    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    assessment_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessment_definitions.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    assessment_definition_review_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assessment_definition_reviews.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    assessment_eligibility_review_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assessment_eligibility_reviews.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    rationale: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(80), nullable=False)

    source_links: Mapped[list[AssessmentSelectionObservationRecord]] = relationship(
        back_populates="selection",
        cascade="save-update, merge",
        lazy="selectin",
        order_by="AssessmentSelectionObservationRecord.source_order",
    )


class AssessmentSelectionObservationRecord(Base):
    __tablename__ = "assessment_selection_observations"
    __table_args__ = (
        UniqueConstraint("selection_id", "source_order", name="uq_selection_source_order"),
    )

    selection_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessment_selections.id", ondelete="RESTRICT"), primary_key=True
    )
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), primary_key=True
    )
    source_order: Mapped[int] = mapped_column(Integer(), nullable=False)
    selection: Mapped[AssessmentSelectionRecord] = relationship(back_populates="source_links")


class AssessmentSelectionRunRecord(VersionedRecordMixin, Base):
    __tablename__ = "assessment_selection_runs"
    __table_args__ = (
        UniqueConstraint("context_observation_id", name="uq_assessment_run_context_observation"),
    )

    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    assessment_eligibility_review_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessment_eligibility_reviews.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    environment_id: Mapped[UUID] = mapped_column(
        ForeignKey("environments.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    context_observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    evaluated_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(120), nullable=False)

    selection_links: Mapped[list[AssessmentSelectionRunItemRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="AssessmentSelectionRunItemRecord.position",
    )


class AssessmentSelectionRunItemRecord(Base):
    __tablename__ = "assessment_selection_run_items"
    __table_args__ = (
        UniqueConstraint("assessment_run_id", "position", name="uq_assessment_run_selection_order"),
        UniqueConstraint("selection_id", name="uq_assessment_selection_one_run"),
    )

    assessment_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessment_selection_runs.id", ondelete="RESTRICT"), primary_key=True
    )
    selection_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessment_selections.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class AssessmentPerformanceRecord(VersionedRecordMixin, Base):
    __tablename__ = "assessment_performances"
    __table_args__ = (
        UniqueConstraint("assessment_selection_id", name="uq_assessment_performance_selection"),
        UniqueConstraint("result_observation_id", name="uq_assessment_performance_observation"),
    )

    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    assessment_selection_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessment_selection_runs.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    assessment_selection_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessment_selections.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    assessment_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessment_definitions.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    assessment_definition_review_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessment_definition_reviews.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    assessment_eligibility_review_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessment_eligibility_reviews.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    result_observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    performed_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(120), nullable=False)


class CompetencyFloorRecord(VersionedRecordMixin, Base):
    __tablename__ = "competency_floors"

    domain: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    estimate_scope: Mapped[str] = mapped_column(String(160), nullable=False)
    unit_or_scale: Mapped[str] = mapped_column(String(80), nullable=False)
    threshold: Mapped[float] = mapped_column(Float(), nullable=False)
    comparison_direction: Mapped[str] = mapped_column(String(40), nullable=False)
    population: Mapped[str] = mapped_column(Text(), nullable=False)
    applicability_notes: Mapped[str] = mapped_column(Text(), nullable=False)
    uncertainty: Mapped[str] = mapped_column(Text(), nullable=False)
    floor_version: Mapped[str] = mapped_column(String(80), nullable=False)

    evidence_links: Mapped[list[CompetencyFloorEvidenceClaimRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="CompetencyFloorEvidenceClaimRecord.position",
    )


class CompetencyFloorEvidenceClaimRecord(Base):
    __tablename__ = "competency_floor_evidence_claims"
    __table_args__ = (
        UniqueConstraint("competency_floor_id", "position", name="uq_floor_evidence_order"),
    )

    competency_floor_id: Mapped[UUID] = mapped_column(
        ForeignKey("competency_floors.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class CompetencyFloorReviewRecord(VersionedRecordMixin, Base):
    __tablename__ = "competency_floor_reviews"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved', 'needs_revision', 'rejected')",
            name="ck_competency_floor_review_decision",
        ),
        CheckConstraint(
            "sequence_number >= 1", name="ck_competency_floor_review_sequence_positive"
        ),
        UniqueConstraint(
            "competency_floor_id",
            "sequence_number",
            name="uq_competency_floor_review_floor_sequence",
        ),
        UniqueConstraint("supersedes_review_id", name="uq_competency_floor_review_superseded_once"),
    )

    competency_floor_id: Mapped[UUID] = mapped_column(
        ForeignKey("competency_floors.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    decision: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    supersedes_review_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("competency_floor_reviews.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(160), nullable=False)
    applicability_rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    uncertainty: Mapped[str] = mapped_column(Text(), nullable=False)
    review_version: Mapped[str] = mapped_column(String(120), nullable=False)

    evidence_links: Mapped[list[CompetencyFloorReviewEvidenceClaimRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="CompetencyFloorReviewEvidenceClaimRecord.position",
    )


class CompetencyFloorReviewEvidenceClaimRecord(Base):
    __tablename__ = "competency_floor_review_evidence_claims"
    __table_args__ = (
        UniqueConstraint(
            "competency_floor_review_id",
            "position",
            name="uq_competency_floor_review_evidence_order",
        ),
    )

    competency_floor_review_id: Mapped[UUID] = mapped_column(
        ForeignKey("competency_floor_reviews.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class CapabilityNeedRecord(VersionedRecordMixin, Base):
    __tablename__ = "capability_needs"

    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    domain: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    competency_floor_id: Mapped[UUID] = mapped_column(
        ForeignKey("competency_floors.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    capability_estimate_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("capability_estimates.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    observed_value: Mapped[float | None] = mapped_column(Float(), nullable=True)
    floor_value: Mapped[float] = mapped_column(Float(), nullable=False)
    unit_or_scale: Mapped[str] = mapped_column(String(80), nullable=False)
    gap_from_floor: Mapped[float | None] = mapped_column(Float(), nullable=True)
    normalized_deficit: Mapped[float | None] = mapped_column(Float(), nullable=True)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False)
    rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    identified_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(80), nullable=False)

    evidence_links: Mapped[list[CapabilityNeedEvidenceClaimRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="CapabilityNeedEvidenceClaimRecord.position",
    )


class CapabilityNeedEvidenceClaimRecord(Base):
    __tablename__ = "capability_need_evidence_claims"
    __table_args__ = (
        UniqueConstraint("capability_need_id", "position", name="uq_need_evidence_order"),
    )

    capability_need_id: Mapped[UUID] = mapped_column(
        ForeignKey("capability_needs.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class PriorityPolicyRecord(VersionedRecordMixin, Base):
    __tablename__ = "priority_policies"

    deficit_weight: Mapped[float] = mapped_column(Float(), nullable=False)
    general_relevance_weight: Mapped[float] = mapped_column(Float(), nullable=False)
    goal_relevance_weight: Mapped[float] = mapped_column(Float(), nullable=False)
    prerequisite_value_weight: Mapped[float] = mapped_column(Float(), nullable=False)
    expected_trainability_weight: Mapped[float] = mapped_column(Float(), nullable=False)
    transfer_value_weight: Mapped[float] = mapped_column(Float(), nullable=False)
    fatigue_cost_weight: Mapped[float] = mapped_column(Float(), nullable=False)
    time_cost_weight: Mapped[float] = mapped_column(Float(), nullable=False)
    interference_cost_weight: Mapped[float] = mapped_column(Float(), nullable=False)
    cost_penalty: Mapped[float] = mapped_column(Float(), nullable=False)
    confidence_multipliers: Mapped[dict[str, float]] = mapped_column(JsonType, nullable=False)
    develop_score_threshold: Mapped[float] = mapped_column(Float(), nullable=False)
    comparative_advantage_threshold: Mapped[float] = mapped_column(Float(), nullable=False)
    severe_deficit_threshold: Mapped[float] = mapped_column(Float(), nullable=False)
    max_develop_adaptations: Mapped[int] = mapped_column(Integer(), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)


class PriorityPolicyReviewRecord(VersionedRecordMixin, Base):
    __tablename__ = "priority_policy_reviews"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved', 'needs_revision', 'rejected')",
            name="ck_priority_policy_review_decision",
        ),
        CheckConstraint("sequence_number >= 1", name="ck_priority_policy_review_sequence_positive"),
        UniqueConstraint(
            "priority_policy_id",
            "sequence_number",
            name="uq_priority_policy_review_policy_sequence",
        ),
        UniqueConstraint("supersedes_review_id", name="uq_priority_policy_review_superseded_once"),
    )

    priority_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("priority_policies.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    decision: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    supersedes_review_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("priority_policy_reviews.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(160), nullable=False)
    applicability_rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    uncertainty: Mapped[str] = mapped_column(Text(), nullable=False)
    review_version: Mapped[str] = mapped_column(String(120), nullable=False)

    evidence_links: Mapped[list[PriorityPolicyReviewEvidenceClaimRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="PriorityPolicyReviewEvidenceClaimRecord.position",
    )


class PriorityPolicyReviewEvidenceClaimRecord(Base):
    __tablename__ = "priority_policy_review_evidence_claims"
    __table_args__ = (
        UniqueConstraint(
            "priority_policy_review_id",
            "position",
            name="uq_priority_policy_review_evidence_order",
        ),
    )

    priority_policy_review_id: Mapped[UUID] = mapped_column(
        ForeignKey("priority_policy_reviews.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class InitialPlanningContextDraftRecord(VersionedRecordMixin, Base):
    __tablename__ = "initial_planning_context_drafts"

    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    priority_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("priority_policies.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    priority_policy_review_id: Mapped[UUID] = mapped_column(
        ForeignKey("priority_policy_reviews.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    horizon_months: Mapped[int] = mapped_column(Integer(), nullable=False)
    review_after_days: Mapped[int] = mapped_column(Integer(), nullable=False)
    authored_by_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    author_authority_assignment_id: Mapped[UUID] = mapped_column(
        ForeignKey("account_role_assignments.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    authored_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    applicability_rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    uncertainty: Mapped[str] = mapped_column(Text(), nullable=False)
    draft_version: Mapped[str] = mapped_column(String(120), nullable=False)

    candidate_links: Mapped[list[InitialPlanningCandidateContextRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="InitialPlanningCandidateContextRecord.position",
    )


class InitialPlanningCandidateContextRecord(Base):
    __tablename__ = "initial_planning_candidate_contexts"
    __table_args__ = (
        CheckConstraint(
            "general_relevance >= 0 AND general_relevance <= 1 "
            "AND goal_relevance >= 0 AND goal_relevance <= 1 "
            "AND prerequisite_value >= 0 AND prerequisite_value <= 1 "
            "AND expected_trainability >= 0 AND expected_trainability <= 1 "
            "AND transfer_value >= 0 AND transfer_value <= 1 "
            "AND fatigue_cost >= 0 AND fatigue_cost <= 1 "
            "AND time_cost >= 0 AND time_cost <= 1 "
            "AND interference_cost >= 0 AND interference_cost <= 1",
            name="ck_initial_planning_candidate_unit_intervals",
        ),
        UniqueConstraint("draft_id", "position", name="uq_initial_planning_candidate_order"),
        UniqueConstraint("draft_id", "adaptation_id", name="uq_initial_planning_draft_adaptation"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    draft_id: Mapped[UUID] = mapped_column(
        ForeignKey("initial_planning_context_drafts.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)
    adaptation_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptations.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    competency_floor_id: Mapped[UUID] = mapped_column(
        ForeignKey("competency_floors.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    competency_floor_review_id: Mapped[UUID] = mapped_column(
        ForeignKey("competency_floor_reviews.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    capability_estimate_id: Mapped[UUID] = mapped_column(
        ForeignKey("capability_estimates.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    general_relevance: Mapped[float] = mapped_column(Float(), nullable=False)
    goal_relevance: Mapped[float] = mapped_column(Float(), nullable=False)
    prerequisite_value: Mapped[float] = mapped_column(Float(), nullable=False)
    expected_trainability: Mapped[float] = mapped_column(Float(), nullable=False)
    transfer_value: Mapped[float] = mapped_column(Float(), nullable=False)
    fatigue_cost: Mapped[float] = mapped_column(Float(), nullable=False)
    time_cost: Mapped[float] = mapped_column(Float(), nullable=False)
    interference_cost: Mapped[float] = mapped_column(Float(), nullable=False)
    safe_to_train: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    introductory_exposure_needed: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    prerequisites_met: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    cultivate_comparative_advantage: Mapped[bool] = mapped_column(Boolean(), nullable=False)

    prerequisite_links: Mapped[list[InitialPlanningContextPrerequisiteRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="InitialPlanningContextPrerequisiteRecord.position",
    )
    observation_links: Mapped[list[InitialPlanningContextObservationRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="InitialPlanningContextObservationRecord.position",
    )
    evidence_links: Mapped[list[InitialPlanningContextEvidenceRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="InitialPlanningContextEvidenceRecord.position",
    )


class InitialPlanningContextPrerequisiteRecord(Base):
    __tablename__ = "initial_planning_context_prerequisites"
    __table_args__ = (
        UniqueConstraint(
            "candidate_context_id", "position", name="uq_initial_context_prerequisite_order"
        ),
    )

    candidate_context_id: Mapped[UUID] = mapped_column(
        ForeignKey("initial_planning_candidate_contexts.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    adaptation_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptations.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class InitialPlanningContextObservationRecord(Base):
    __tablename__ = "initial_planning_context_observations"
    __table_args__ = (
        UniqueConstraint(
            "candidate_context_id", "position", name="uq_initial_context_observation_order"
        ),
    )

    candidate_context_id: Mapped[UUID] = mapped_column(
        ForeignKey("initial_planning_candidate_contexts.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class InitialPlanningContextEvidenceRecord(Base):
    __tablename__ = "initial_planning_context_evidence_claims"
    __table_args__ = (
        UniqueConstraint(
            "candidate_context_id", "position", name="uq_initial_context_evidence_order"
        ),
    )

    candidate_context_id: Mapped[UUID] = mapped_column(
        ForeignKey("initial_planning_candidate_contexts.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class InitialPlanningContextReviewRecord(VersionedRecordMixin, Base):
    __tablename__ = "initial_planning_context_reviews"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved', 'needs_revision', 'rejected')",
            name="ck_initial_planning_context_review_decision",
        ),
        UniqueConstraint("draft_id", name="uq_initial_planning_context_review_draft"),
    )

    draft_id: Mapped[UUID] = mapped_column(
        ForeignKey("initial_planning_context_drafts.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    reviewed_by_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    review_authority_assignment_id: Mapped[UUID] = mapped_column(
        ForeignKey("account_role_assignments.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    applicability_rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    uncertainty: Mapped[str] = mapped_column(Text(), nullable=False)
    review_version: Mapped[str] = mapped_column(String(120), nullable=False)


class LongRangeStrategyRecord(VersionedRecordMixin, Base):
    __tablename__ = "long_range_strategies"
    __table_args__ = (
        CheckConstraint(
            "(supersedes_strategy_id IS NULL AND triggering_block_review_id IS NULL) "
            "OR (supersedes_strategy_id IS NOT NULL "
            "AND triggering_block_review_id IS NOT NULL)",
            name="ck_strategy_revision_lineage_pair",
        ),
        UniqueConstraint("triggering_block_review_id", name="uq_strategy_triggering_block_review"),
        Index(
            "uq_initial_strategy_athlete",
            "athlete_id",
            unique=True,
            postgresql_where=text("supersedes_strategy_id IS NULL"),
            sqlite_where=text("supersedes_strategy_id IS NULL"),
        ),
    )

    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    priority_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("priority_policies.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    supersedes_strategy_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "long_range_strategies.id",
            name="fk_strategy_supersedes_strategy",
            ondelete="RESTRICT",
        ),
        index=True,
        nullable=True,
    )
    triggering_block_review_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "block_reviews.id",
            name="fk_strategy_triggering_block_review",
            ondelete="RESTRICT",
            use_alter=True,
        ),
        index=True,
        nullable=True,
    )
    horizon_months: Mapped[int] = mapped_column(Integer(), nullable=False)
    block_hypothesis: Mapped[str] = mapped_column(Text(), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    next_review_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(160), nullable=False)

    priority_links: Mapped[list[AdaptationPriorityRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="AdaptationPriorityRecord.position",
    )
    roadmap_links: Mapped[list[RoadmapItemRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="RoadmapItemRecord.position",
    )
    observation_links: Mapped[list[StrategyObservationRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="StrategyObservationRecord.position",
    )
    estimate_links: Mapped[list[StrategyCapabilityEstimateRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="StrategyCapabilityEstimateRecord.position",
    )
    floor_links: Mapped[list[StrategyCompetencyFloorRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="StrategyCompetencyFloorRecord.position",
    )
    evidence_links: Mapped[list[StrategyEvidenceClaimRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="StrategyEvidenceClaimRecord.position",
    )


class AdaptationPriorityRecord(VersionedRecordMixin, Base):
    __tablename__ = "adaptation_priorities"
    __table_args__ = (
        UniqueConstraint("strategy_id", "position", name="uq_strategy_priority_order"),
        UniqueConstraint("strategy_id", "adaptation_id", name="uq_strategy_adaptation_priority"),
    )

    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("long_range_strategies.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    adaptation_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptations.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    capability_need_id: Mapped[UUID] = mapped_column(
        ForeignKey("capability_needs.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    score: Mapped[float] = mapped_column(Float(), nullable=False)
    rank: Mapped[int] = mapped_column(Integer(), nullable=False)
    development_allocation: Mapped[float] = mapped_column(Float(), nullable=False)
    score_components: Mapped[dict[str, float]] = mapped_column(JsonType, nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    rationale: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class RoadmapItemRecord(VersionedRecordMixin, Base):
    __tablename__ = "roadmap_items"
    __table_args__ = (
        UniqueConstraint("strategy_id", "position", name="uq_strategy_roadmap_order"),
        UniqueConstraint("strategy_id", "adaptation_id", name="uq_strategy_roadmap_adaptation"),
    )

    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("long_range_strategies.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    adaptation_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptations.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    current_state: Mapped[str] = mapped_column(String(40), nullable=False)
    sequence_group: Mapped[int] = mapped_column(Integer(), nullable=False)
    rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    review_trigger: Mapped[str] = mapped_column(Text(), nullable=False)
    position: Mapped[int] = mapped_column(Integer(), nullable=False)

    prerequisite_links: Mapped[list[RoadmapItemPrerequisiteRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="RoadmapItemPrerequisiteRecord.position",
    )


class RoadmapItemPrerequisiteRecord(Base):
    __tablename__ = "roadmap_item_prerequisites"
    __table_args__ = (
        UniqueConstraint("roadmap_item_id", "position", name="uq_roadmap_prerequisite_order"),
    )

    roadmap_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("roadmap_items.id", ondelete="RESTRICT"), primary_key=True
    )
    adaptation_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptations.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class StrategyObservationRecord(Base):
    __tablename__ = "strategy_observations"
    __table_args__ = (UniqueConstraint("strategy_id", "position", name="uq_strategy_obs_order"),)

    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("long_range_strategies.id", ondelete="RESTRICT"), primary_key=True
    )
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class StrategyCapabilityEstimateRecord(Base):
    __tablename__ = "strategy_capability_estimates"
    __table_args__ = (
        UniqueConstraint("strategy_id", "position", name="uq_strategy_estimate_order"),
    )

    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("long_range_strategies.id", ondelete="RESTRICT"), primary_key=True
    )
    capability_estimate_id: Mapped[UUID] = mapped_column(
        ForeignKey("capability_estimates.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class StrategyCompetencyFloorRecord(Base):
    __tablename__ = "strategy_competency_floors"
    __table_args__ = (UniqueConstraint("strategy_id", "position", name="uq_strategy_floor_order"),)

    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("long_range_strategies.id", ondelete="RESTRICT"), primary_key=True
    )
    competency_floor_id: Mapped[UUID] = mapped_column(
        ForeignKey("competency_floors.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class StrategyEvidenceClaimRecord(Base):
    __tablename__ = "strategy_evidence_claims"
    __table_args__ = (
        UniqueConstraint("strategy_id", "position", name="uq_strategy_evidence_order"),
    )

    strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("long_range_strategies.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class StimulusRequirementRecord(VersionedRecordMixin, Base):
    __tablename__ = "stimulus_requirements"

    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    long_range_strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("long_range_strategies.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    adaptation_priority_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptation_priorities.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    adaptation_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptations.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    priority_state: Mapped[str] = mapped_column(String(40), nullable=False)
    movement_patterns: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    allowed_loading_types: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    allowed_lateralities: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    minimum_loadability: Mapped[str] = mapped_column(String(40), nullable=False)
    required_velocity_characteristics: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    maximum_skill_complexity: Mapped[str] = mapped_column(String(40), nullable=False)
    maximum_impact_level: Mapped[str] = mapped_column(String(40), nullable=False)
    maximum_stability_demand: Mapped[str] = mapped_column(String(40), nullable=False)
    maximum_fatigue_cost: Mapped[str] = mapped_column(String(40), nullable=False)
    maximum_soreness_cost: Mapped[str] = mapped_column(String(40), nullable=False)
    requires_outdoor_access: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    minimum_floor_area_m2: Mapped[float | None] = mapped_column(Float(), nullable=True)
    contraindication_tags: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(80), nullable=False)

    observation_links: Mapped[list[StimulusRequirementObservationRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="StimulusRequirementObservationRecord.position",
    )
    evidence_links: Mapped[list[StimulusRequirementEvidenceClaimRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="StimulusRequirementEvidenceClaimRecord.position",
    )


class StimulusRequirementObservationRecord(Base):
    __tablename__ = "stimulus_requirement_observations"
    __table_args__ = (
        UniqueConstraint("stimulus_requirement_id", "position", name="uq_stimulus_obs_order"),
    )

    stimulus_requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("stimulus_requirements.id", ondelete="RESTRICT"), primary_key=True
    )
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class StimulusRequirementEvidenceClaimRecord(Base):
    __tablename__ = "stimulus_requirement_evidence_claims"
    __table_args__ = (
        UniqueConstraint("stimulus_requirement_id", "position", name="uq_stimulus_evidence_order"),
    )

    stimulus_requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("stimulus_requirements.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class ExerciseResolverPolicyRecord(VersionedRecordMixin, Base):
    __tablename__ = "exercise_resolver_policies"

    adaptation_role_weight: Mapped[float] = mapped_column(Float(), nullable=False)
    movement_pattern_weight: Mapped[float] = mapped_column(Float(), nullable=False)
    loading_type_weight: Mapped[float] = mapped_column(Float(), nullable=False)
    loadability_weight: Mapped[float] = mapped_column(Float(), nullable=False)
    velocity_weight: Mapped[float] = mapped_column(Float(), nullable=False)
    laterality_weight: Mapped[float] = mapped_column(Float(), nullable=False)
    secondary_adaptation_credit: Mapped[float] = mapped_column(Float(), nullable=False)
    partial_match_threshold: Mapped[float] = mapped_column(Float(), nullable=False)
    full_match_threshold: Mapped[float] = mapped_column(Float(), nullable=False)
    max_ranked_candidates: Mapped[int] = mapped_column(Integer(), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)


class ExerciseResolutionRecord(VersionedRecordMixin, Base):
    __tablename__ = "exercise_resolutions"

    stimulus_requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("stimulus_requirements.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    environment_id: Mapped[UUID] = mapped_column(
        ForeignKey("environments.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    resolver_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("exercise_resolver_policies.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    selected_exercise_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    unresolved_issues: Mapped[list[dict[str, str]]] = mapped_column(JsonType, nullable=False)
    rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(160), nullable=False)

    match_links: Mapped[list[ExerciseMatchRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="ExerciseMatchRecord.position",
    )
    availability_links: Mapped[list[ExerciseResolutionAvailabilityRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="ExerciseResolutionAvailabilityRecord.position",
    )


class ExerciseMatchRecord(VersionedRecordMixin, Base):
    __tablename__ = "exercise_matches"
    __table_args__ = (
        UniqueConstraint("resolution_id", "position", name="uq_resolution_match_order"),
        UniqueConstraint("resolution_id", "exercise_id", name="uq_resolution_exercise_match"),
    )

    resolution_id: Mapped[UUID] = mapped_column(
        ForeignKey("exercise_resolutions.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    exercise_id: Mapped[UUID] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    quality: Mapped[str] = mapped_column(String(40), nullable=False)
    score: Mapped[float] = mapped_column(Float(), nullable=False)
    score_components: Mapped[dict[str, float]] = mapped_column(JsonType, nullable=False)
    issues: Mapped[list[dict[str, str]]] = mapped_column(JsonType, nullable=False)
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class ExerciseResolutionAvailabilityRecord(Base):
    __tablename__ = "exercise_resolution_availability"
    __table_args__ = (
        UniqueConstraint("resolution_id", "position", name="uq_resolution_availability_order"),
    )

    resolution_id: Mapped[UUID] = mapped_column(
        ForeignKey("exercise_resolutions.id", ondelete="RESTRICT"), primary_key=True
    )
    equipment_availability_id: Mapped[UUID] = mapped_column(
        ForeignKey("equipment_availability.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class AdaptationResourceDemandRecord(VersionedRecordMixin, Base):
    __tablename__ = "adaptation_resource_demands"

    long_range_strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("long_range_strategies.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    adaptation_priority_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptation_priorities.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    adaptation_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptations.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    priority_state: Mapped[str] = mapped_column(String(40), nullable=False)
    stimulus_requirement_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stimulus_requirements.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    exercise_resolution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("exercise_resolutions.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    minimum_weekly_minutes: Mapped[int] = mapped_column(Integer(), nullable=False)
    target_weekly_minutes: Mapped[int] = mapped_column(Integer(), nullable=False)
    sessions_per_week: Mapped[int] = mapped_column(Integer(), nullable=False)
    rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    demand_version: Mapped[str] = mapped_column(String(80), nullable=False)

    observation_links: Mapped[list[ResourceDemandObservationRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="ResourceDemandObservationRecord.position",
    )
    evidence_links: Mapped[list[ResourceDemandEvidenceClaimRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="ResourceDemandEvidenceClaimRecord.position",
    )


class ResourceDemandObservationRecord(Base):
    __tablename__ = "resource_demand_observations"
    __table_args__ = (
        UniqueConstraint("resource_demand_id", "position", name="uq_resource_demand_obs_order"),
    )

    resource_demand_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptation_resource_demands.id", ondelete="RESTRICT"), primary_key=True
    )
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class ResourceDemandEvidenceClaimRecord(Base):
    __tablename__ = "resource_demand_evidence_claims"
    __table_args__ = (
        UniqueConstraint(
            "resource_demand_id", "position", name="uq_resource_demand_evidence_order"
        ),
    )

    resource_demand_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptation_resource_demands.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class ResourceAllocationPolicyRecord(VersionedRecordMixin, Base):
    __tablename__ = "resource_allocation_policies"

    develop_weight: Mapped[float] = mapped_column(Float(), nullable=False)
    maintain_weight: Mapped[float] = mapped_column(Float(), nullable=False)
    expose_weight: Mapped[float] = mapped_column(Float(), nullable=False)
    allow_partial_exercise_resolution: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)


class BlockPlanRecord(VersionedRecordMixin, Base):
    __tablename__ = "block_plans"

    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    long_range_strategy_id: Mapped[UUID] = mapped_column(
        ForeignKey("long_range_strategies.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    resource_allocation_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("resource_allocation_policies.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    starts_on: Mapped[date] = mapped_column(Date(), index=True, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date(), nullable=False)
    duration_weeks: Mapped[int] = mapped_column(Integer(), nullable=False)
    weekly_budget_minutes: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text(), nullable=False)
    constraints: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(160), nullable=False)

    allocation_links: Mapped[list[BlockResourceAllocationRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="BlockResourceAllocationRecord.position",
    )
    observation_links: Mapped[list[BlockPlanObservationRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="BlockPlanObservationRecord.position",
    )
    evidence_links: Mapped[list[BlockPlanEvidenceClaimRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="BlockPlanEvidenceClaimRecord.position",
    )


class BlockResourceAllocationRecord(VersionedRecordMixin, Base):
    __tablename__ = "block_resource_allocations"
    __table_args__ = (
        UniqueConstraint("block_plan_id", "position", name="uq_block_allocation_order"),
        UniqueConstraint(
            "block_plan_id", "adaptation_priority_id", name="uq_block_priority_allocation"
        ),
    )

    block_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("block_plans.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    resource_demand_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptation_resource_demands.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    adaptation_priority_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptation_priorities.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    adaptation_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptations.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    priority_state: Mapped[str] = mapped_column(String(40), nullable=False)
    stimulus_requirement_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stimulus_requirements.id", ondelete="RESTRICT"), nullable=True
    )
    exercise_resolution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("exercise_resolutions.id", ondelete="RESTRICT"), nullable=True
    )
    minimum_weekly_minutes: Mapped[int] = mapped_column(Integer(), nullable=False)
    target_weekly_minutes: Mapped[int] = mapped_column(Integer(), nullable=False)
    allocated_weekly_minutes: Mapped[int] = mapped_column(Integer(), nullable=False)
    sessions_per_week: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    issues: Mapped[list[dict[str, str]]] = mapped_column(JsonType, nullable=False)
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class BlockPlanObservationRecord(Base):
    __tablename__ = "block_plan_observations"
    __table_args__ = (
        UniqueConstraint("block_plan_id", "position", name="uq_block_plan_obs_order"),
    )

    block_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("block_plans.id", ondelete="RESTRICT"), primary_key=True
    )
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class BlockPlanEvidenceClaimRecord(Base):
    __tablename__ = "block_plan_evidence_claims"
    __table_args__ = (
        UniqueConstraint("block_plan_id", "position", name="uq_block_plan_evidence_order"),
    )

    block_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("block_plans.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class SessionPrescriptionRecord(VersionedRecordMixin, Base):
    __tablename__ = "session_prescriptions"

    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    block_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("block_plans.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    resource_allocation_id: Mapped[UUID] = mapped_column(
        ForeignKey("block_resource_allocations.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    exercise_resolution_id: Mapped[UUID] = mapped_column(
        ForeignKey("exercise_resolutions.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    exercise_id: Mapped[UUID] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    adaptation_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptations.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    reason_for_inclusion: Mapped[str] = mapped_column(Text(), nullable=False)
    sets: Mapped[int] = mapped_column(Integer(), nullable=False)
    repetitions_per_set: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    intensity_targets: Mapped[list[dict[str, Any]]] = mapped_column(JsonType, nullable=False)
    rest_seconds: Mapped[int] = mapped_column(Integer(), nullable=False)
    progression_rule_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    substitution_class: Mapped[str] = mapped_column(String(160), nullable=False)
    planned_duration_minutes: Mapped[int] = mapped_column(Integer(), nullable=False)
    fatigue_cost: Mapped[str] = mapped_column(String(40), nullable=False)
    prescribed_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(160), nullable=False)

    observation_links: Mapped[list[SessionPrescriptionObservationRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="SessionPrescriptionObservationRecord.position",
    )
    evidence_links: Mapped[list[SessionPrescriptionEvidenceClaimRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="SessionPrescriptionEvidenceClaimRecord.position",
    )


class SessionPrescriptionObservationRecord(Base):
    __tablename__ = "session_prescription_observations"
    __table_args__ = (
        UniqueConstraint("prescription_id", "position", name="uq_prescription_obs_order"),
    )

    prescription_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_prescriptions.id", ondelete="RESTRICT"), primary_key=True
    )
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class SessionPrescriptionEvidenceClaimRecord(Base):
    __tablename__ = "session_prescription_evidence_claims"
    __table_args__ = (
        UniqueConstraint("prescription_id", "position", name="uq_prescription_evidence_order"),
    )

    prescription_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_prescriptions.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class SessionTemplateRecord(VersionedRecordMixin, Base):
    __tablename__ = "session_templates"

    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    block_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("block_plans.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    previous_template_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("session_templates.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
        unique=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    sessions_per_week: Mapped[int] = mapped_column(Integer(), nullable=False)
    planned_duration_minutes: Mapped[int] = mapped_column(Integer(), nullable=False)
    fatigue_cost: Mapped[str] = mapped_column(String(40), nullable=False)
    created_for_block_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), index=True, nullable=False
    )
    rule_version: Mapped[str] = mapped_column(String(160), nullable=False)
    items: Mapped[list[SessionTemplateItemRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="SessionTemplateItemRecord.order_index",
    )
    observation_links: Mapped[list[SessionTemplateObservationRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="SessionTemplateObservationRecord.position",
    )
    evidence_links: Mapped[list[SessionTemplateEvidenceRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="SessionTemplateEvidenceRecord.position",
    )


class SessionTemplateItemRecord(Base):
    __tablename__ = "session_template_items"
    __table_args__ = (
        UniqueConstraint("session_template_id", "order_index", name="uq_template_item_order"),
    )
    session_template_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_templates.id", ondelete="RESTRICT"), primary_key=True
    )
    prescription_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_prescriptions.id", ondelete="RESTRICT"), primary_key=True
    )
    order_index: Mapped[int] = mapped_column(Integer(), nullable=False)
    section: Mapped[str] = mapped_column(String(40), nullable=False)


class SessionTemplateObservationRecord(Base):
    __tablename__ = "session_template_observations"
    __table_args__ = (
        UniqueConstraint("session_template_id", "position", name="uq_template_obs_order"),
    )
    session_template_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_templates.id", ondelete="RESTRICT"), primary_key=True
    )
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class SessionTemplateEvidenceRecord(Base):
    __tablename__ = "session_template_evidence_claims"
    __table_args__ = (
        UniqueConstraint("session_template_id", "position", name="uq_template_evidence_order"),
    )
    session_template_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_templates.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class WeeklyAvailabilityRecord(VersionedRecordMixin, Base):
    __tablename__ = "weekly_availabilities"
    __table_args__ = (
        UniqueConstraint(
            "source_weekly_plan_id",
            name="uq_weekly_availability_source_plan",
        ),
    )

    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    source_weekly_plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "weekly_plans.id",
            name="fk_weekly_availability_source_plan",
            ondelete="RESTRICT",
            use_alter=True,
        ),
        index=True,
        nullable=True,
    )
    week_start: Mapped[date] = mapped_column(Date(), index=True, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(80), nullable=False)

    windows: Mapped[list[AvailabilityWindowRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="AvailabilityWindowRecord.position",
    )
    observation_links: Mapped[list[WeeklyAvailabilityObservationRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="WeeklyAvailabilityObservationRecord.position",
    )


class AvailabilityWindowRecord(VersionedRecordMixin, Base):
    __tablename__ = "availability_windows"
    __table_args__ = (
        UniqueConstraint("weekly_availability_id", "position", name="uq_availability_window_order"),
    )

    weekly_availability_id: Mapped[UUID] = mapped_column(
        ForeignKey("weekly_availabilities.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    environment_id: Mapped[UUID] = mapped_column(
        ForeignKey("environments.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class WeeklyAvailabilityObservationRecord(Base):
    __tablename__ = "weekly_availability_observations"
    __table_args__ = (
        UniqueConstraint("weekly_availability_id", "position", name="uq_weekly_avail_obs_order"),
    )

    weekly_availability_id: Mapped[UUID] = mapped_column(
        ForeignKey("weekly_availabilities.id", ondelete="RESTRICT"), primary_key=True
    )
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class WeeklySchedulingPolicyRecord(VersionedRecordMixin, Base):
    __tablename__ = "weekly_scheduling_policies"

    minimum_high_fatigue_recovery_hours: Mapped[int] = mapped_column(Integer(), nullable=False)
    maximum_sessions_per_day: Mapped[int] = mapped_column(Integer(), nullable=False)
    maximum_high_fatigue_sessions_per_day: Mapped[int] = mapped_column(Integer(), nullable=False)
    allow_partial_exercise_resolution: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)


class WeeklySchedulingPolicyReviewRecord(VersionedRecordMixin, Base):
    __tablename__ = "weekly_scheduling_policy_reviews"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved', 'needs_revision', 'rejected')",
            name="ck_weekly_scheduling_policy_review_decision",
        ),
        CheckConstraint(
            "sequence_number >= 1",
            name="ck_weekly_scheduling_policy_review_sequence_positive",
        ),
        UniqueConstraint(
            "weekly_scheduling_policy_id",
            "sequence_number",
            name="uq_weekly_scheduling_policy_review_policy_sequence",
        ),
        UniqueConstraint(
            "supersedes_review_id",
            name="uq_weekly_scheduling_policy_review_superseded_once",
        ),
    )

    weekly_scheduling_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("weekly_scheduling_policies.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    supersedes_review_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("weekly_scheduling_policy_reviews.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(160), nullable=False)
    applicability_rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    uncertainty: Mapped[str] = mapped_column(Text(), nullable=False)
    review_version: Mapped[str] = mapped_column(String(120), nullable=False)

    evidence_links: Mapped[list[WeeklySchedulingPolicyReviewEvidenceClaimRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="WeeklySchedulingPolicyReviewEvidenceClaimRecord.position",
    )


class WeeklySchedulingPolicyReviewEvidenceClaimRecord(Base):
    __tablename__ = "weekly_scheduling_policy_review_evidence_claims"
    __table_args__ = (
        UniqueConstraint(
            "weekly_scheduling_policy_review_id",
            "position",
            name="uq_weekly_scheduling_policy_review_evidence_order",
        ),
    )

    weekly_scheduling_policy_review_id: Mapped[UUID] = mapped_column(
        ForeignKey("weekly_scheduling_policy_reviews.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class WeeklyPlanRecord(VersionedRecordMixin, Base):
    __tablename__ = "weekly_plans"

    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    block_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("block_plans.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    previous_weekly_plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("weekly_plans.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
        unique=True,
    )
    weekly_availability_id: Mapped[UUID] = mapped_column(
        ForeignKey("weekly_availabilities.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    scheduling_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("weekly_scheduling_policies.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    scheduling_policy_review_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("weekly_scheduling_policy_reviews.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    week_start: Mapped[date] = mapped_column(Date(), index=True, nullable=False)
    block_week: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JsonType, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(160), nullable=False)

    sessions: Mapped[list[PlannedSessionRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="PlannedSessionRecord.position",
    )


class PlannedSessionRecord(VersionedRecordMixin, Base):
    __tablename__ = "planned_sessions"
    __table_args__ = (
        UniqueConstraint("weekly_plan_id", "position", name="uq_planned_session_order"),
        UniqueConstraint(
            "weekly_plan_id",
            "session_template_id",
            "occurrence_index",
            name="uq_planned_template_occurrence",
        ),
    )

    weekly_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("weekly_plans.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    session_template_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_templates.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    occurrence_index: Mapped[int] = mapped_column(Integer(), nullable=False)
    availability_window_id: Mapped[UUID] = mapped_column(
        ForeignKey("availability_windows.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    environment_id: Mapped[UUID] = mapped_column(
        ForeignKey("environments.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    planned_duration_minutes: Mapped[int] = mapped_column(Integer(), nullable=False)
    fatigue_cost: Mapped[str] = mapped_column(String(40), nullable=False)
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class SessionSafetyPolicyRecord(VersionedRecordMixin, Base):
    __tablename__ = "session_safety_policies"

    allowed_modifications: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    limited_readiness_modifications: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    unusual_soreness_modifications: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    sleep_disruption_modifications: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    schedule_limitation_modifications: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)

    evidence_links: Mapped[list[SessionSafetyPolicyEvidenceClaimRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="SessionSafetyPolicyEvidenceClaimRecord.position",
    )


class SessionSafetyPolicyEvidenceClaimRecord(Base):
    __tablename__ = "session_safety_policy_evidence_claims"
    __table_args__ = (
        UniqueConstraint("safety_policy_id", "position", name="uq_safety_policy_evidence_order"),
    )

    safety_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_safety_policies.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class AthleteSafetyPolicyAssignmentRecord(VersionedRecordMixin, Base):
    __tablename__ = "athlete_safety_policy_assignments"
    __table_args__ = (
        CheckConstraint("sequence_number >= 1", name="ck_safety_assignment_sequence_positive"),
        UniqueConstraint(
            "athlete_id", "sequence_number", name="uq_athlete_safety_assignment_sequence"
        ),
        UniqueConstraint("supersedes_assignment_id", name="uq_safety_assignment_superseded_once"),
    )

    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    safety_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_safety_policies.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    supersedes_assignment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("athlete_safety_policy_assignments.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    assigned_by: Mapped[str] = mapped_column(String(160), nullable=False)
    applicability_rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(120), nullable=False)


class SessionSafetyDecisionRecord(VersionedRecordMixin, Base):
    __tablename__ = "session_safety_decisions"

    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    weekly_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("weekly_plans.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    planned_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("planned_sessions.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    related_session_execution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "session_executions.id",
            ondelete="RESTRICT",
            use_alter=True,
            name="fk_safety_decision_related_execution",
        ),
        index=True,
        nullable=True,
    )
    safety_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_safety_policies.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    safety_policy_assignment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("athlete_safety_policy_assignments.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    timing: Mapped[str] = mapped_column(String(40), nullable=False)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    required_modifications: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    rationale: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(160), nullable=False)

    observation_links: Mapped[list[SessionSafetyDecisionObservationRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="SessionSafetyDecisionObservationRecord.position",
    )


class SessionSafetyDecisionObservationRecord(Base):
    __tablename__ = "session_safety_decision_observations"
    __table_args__ = (
        UniqueConstraint("safety_decision_id", "position", name="uq_safety_decision_obs_order"),
    )

    safety_decision_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_safety_decisions.id", ondelete="RESTRICT"), primary_key=True
    )
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class SessionExecutionRecord(VersionedRecordMixin, Base):
    __tablename__ = "session_executions"
    __table_args__ = (UniqueConstraint("planned_session_id", name="uq_execution_planned_session"),)

    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    weekly_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("weekly_plans.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    planned_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("planned_sessions.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    session_template_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_templates.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    pre_session_safety_decision_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_safety_decisions.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    applied_modifications: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    session_rpe: Mapped[float | None] = mapped_column(Float(), nullable=True)
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    performance_observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    logged_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(160), nullable=False)

    items: Mapped[list[SessionItemExecutionRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="SessionItemExecutionRecord.position",
    )


class SessionItemExecutionRecord(VersionedRecordMixin, Base):
    __tablename__ = "session_item_executions"
    __table_args__ = (
        UniqueConstraint("session_execution_id", "position", name="uq_execution_item_order"),
        UniqueConstraint(
            "session_execution_id", "prescription_id", name="uq_execution_prescription_item"
        ),
    )
    session_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_executions.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    prescription_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_prescriptions.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    item_rpe: Mapped[float | None] = mapped_column(Float(), nullable=True)
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    position: Mapped[int] = mapped_column(Integer(), nullable=False)
    performances: Mapped[list[SetPerformanceRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="SetPerformanceRecord.set_index",
    )


class SetPerformanceRecord(VersionedRecordMixin, Base):
    __tablename__ = "set_performances"
    __table_args__ = (
        UniqueConstraint("session_item_execution_id", "set_index", name="uq_item_set_index"),
    )

    session_item_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_item_executions.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    set_index: Mapped[int] = mapped_column(Integer(), nullable=False)
    performed: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    target_completed: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    actual_repetitions: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    actual_duration_seconds: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    load_value: Mapped[float | None] = mapped_column(Float(), nullable=True)
    load_unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    effort_rpe: Mapped[float | None] = mapped_column(Float(), nullable=True)
    technique_constraint_met: Mapped[bool | None] = mapped_column(Boolean(), nullable=True)


class SessionAdherenceRecord(VersionedRecordMixin, Base):
    __tablename__ = "session_adherence"
    __table_args__ = (
        CheckConstraint("kind = 'derived'", name="ck_adherence_is_derived"),
        UniqueConstraint(
            "session_execution_id",
            "prescription_id",
            name="uq_adherence_execution_prescription",
        ),
    )

    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="derived")
    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    session_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_executions.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    planned_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("planned_sessions.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    prescription_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_prescriptions.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    prescribed_sets: Mapped[int] = mapped_column(Integer(), nullable=False)
    performed_sets: Mapped[int] = mapped_column(Integer(), nullable=False)
    target_completed_sets: Mapped[int] = mapped_column(Integer(), nullable=False)
    prescribed_dose_total: Mapped[int] = mapped_column(Integer(), nullable=False)
    actual_dose_total: Mapped[int] = mapped_column(Integer(), nullable=False)
    dose_unit: Mapped[str] = mapped_column(String(40), nullable=False)
    set_completion_ratio: Mapped[float] = mapped_column(Float(), nullable=False)
    dose_completion_ratio: Mapped[float] = mapped_column(Float(), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    calculation_method: Mapped[str] = mapped_column(String(160), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(160), nullable=False)

    observation_links: Mapped[list[SessionAdherenceObservationRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="SessionAdherenceObservationRecord.position",
    )


class SessionAdherenceObservationRecord(Base):
    __tablename__ = "session_adherence_observations"
    __table_args__ = (
        UniqueConstraint("session_adherence_id", "position", name="uq_adherence_obs_order"),
    )

    session_adherence_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_adherence.id", ondelete="RESTRICT"), primary_key=True
    )
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class ProgressionPolicyRecord(VersionedRecordMixin, Base):
    __tablename__ = "progression_policies"
    reference: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    minimum_set_completion_ratio: Mapped[float] = mapped_column(Float(), nullable=False)
    minimum_dose_completion_ratio: Mapped[float] = mapped_column(Float(), nullable=False)
    maximum_session_rpe: Mapped[float] = mapped_column(Float(), nullable=False)
    require_technique_constraint: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    adjustment: Mapped[dict[str, object]] = mapped_column(JsonType, nullable=False)
    exposure_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)
    evidence_links: Mapped[list[ProgressionPolicyEvidenceRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="ProgressionPolicyEvidenceRecord.position",
    )


class ExposureDefinitionRecord(VersionedRecordMixin, Base):
    __tablename__ = "exposure_definitions"
    exercise_id: Mapped[UUID] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"), index=True
    )
    exposure_type: Mapped[str] = mapped_column(String(60), nullable=False)
    dose_unit: Mapped[str] = mapped_column(String(40), nullable=False)
    rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    definition_version: Mapped[str] = mapped_column(String(80), nullable=False)
    evidence_links: Mapped[list[ExposureDefinitionEvidenceRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="ExposureDefinitionEvidenceRecord.position",
    )


class ExposureEntryRecord(VersionedRecordMixin, Base):
    __tablename__ = "exposure_entries"
    __table_args__ = (
        CheckConstraint("kind = 'derived'", name="ck_exposure_entry_derived"),
        UniqueConstraint(
            "session_execution_id",
            "prescription_id",
            "exposure_definition_id",
            name="uq_exposure_entry_execution_prescription_definition",
        ),
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True
    )
    session_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_executions.id", ondelete="RESTRICT"), index=True
    )
    planned_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("planned_sessions.id", ondelete="RESTRICT"), index=True
    )
    prescription_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_prescriptions.id", ondelete="RESTRICT"), index=True
    )
    exposure_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("exposure_definitions.id", ondelete="RESTRICT"), index=True
    )
    exposure_type: Mapped[str] = mapped_column(String(60), nullable=False)
    dose_value: Mapped[float] = mapped_column(Float(), nullable=False)
    dose_unit: Mapped[str] = mapped_column(String(40), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    calculation_method: Mapped[str] = mapped_column(String(160), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(160), nullable=False)
    observation_links: Mapped[list[ExposureEntryObservationRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="ExposureEntryObservationRecord.position",
    )


class ExposureProgressionPolicyRecord(VersionedRecordMixin, Base):
    __tablename__ = "exposure_progression_policies"
    exposure_type: Mapped[str] = mapped_column(String(60), nullable=False)
    dose_unit: Mapped[str] = mapped_column(String(40), nullable=False)
    lookback_days: Mapped[int] = mapped_column(Integer(), nullable=False)
    minimum_recent_entries: Mapped[int] = mapped_column(Integer(), nullable=False)
    maximum_initial_dose: Mapped[float] = mapped_column(Float(), nullable=False)
    maximum_relative_increase: Mapped[float] = mapped_column(Float(), nullable=False)
    maximum_absolute_increase: Mapped[float] = mapped_column(Float(), nullable=False)
    rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)
    evidence_links: Mapped[list[ExposureProgressionPolicyEvidenceRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="ExposureProgressionPolicyEvidenceRecord.position",
    )


class ExposureValidationDecisionRecord(VersionedRecordMixin, Base):
    __tablename__ = "exposure_validation_decisions"
    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True
    )
    prescription_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_prescriptions.id", ondelete="RESTRICT"), index=True
    )
    exposure_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("exposure_progression_policies.id", ondelete="RESTRICT"), index=True
    )
    exposure_type: Mapped[str] = mapped_column(String(60), nullable=False)
    proposed_dose: Mapped[float] = mapped_column(Float(), nullable=False)
    dose_unit: Mapped[str] = mapped_column(String(40), nullable=False)
    baseline_dose: Mapped[float | None] = mapped_column(Float(), nullable=True)
    maximum_allowed_dose: Mapped[float] = mapped_column(Float(), nullable=False)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    rationale: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    rule_version: Mapped[str] = mapped_column(String(160), nullable=False)
    entry_links: Mapped[list[ExposureValidationEntryRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="ExposureValidationEntryRecord.position",
    )


class ProgressionDecisionRecord(VersionedRecordMixin, Base):
    __tablename__ = "progression_decisions"
    __table_args__ = (
        UniqueConstraint(
            "session_execution_id",
            "prescription_id",
            name="uq_progression_execution_prescription",
        ),
    )
    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True
    )
    weekly_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("weekly_plans.id", ondelete="RESTRICT"), index=True
    )
    planned_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("planned_sessions.id", ondelete="RESTRICT"), index=True
    )
    prescription_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_prescriptions.id", ondelete="RESTRICT"), index=True
    )
    session_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_executions.id", ondelete="RESTRICT"), index=True
    )
    session_adherence_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_adherence.id", ondelete="RESTRICT"), index=True
    )
    progression_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("progression_policies.id", ondelete="RESTRICT"), index=True
    )
    exposure_validation_decision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("exposure_validation_decisions.id", ondelete="RESTRICT"), nullable=True
    )
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    adjustment: Mapped[dict[str, object] | None] = mapped_column(JsonType, nullable=True)
    rationale: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    rule_version: Mapped[str] = mapped_column(String(160), nullable=False)
    safety_links: Mapped[list[ProgressionDecisionSafetyRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="ProgressionDecisionSafetyRecord.position",
    )
    observation_links: Mapped[list[ProgressionDecisionObservationRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="ProgressionDecisionObservationRecord.position",
    )


class ProgressionPolicyEvidenceRecord(Base):
    __tablename__ = "progression_policy_evidence_claims"
    progression_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("progression_policies.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class ExposureDefinitionEvidenceRecord(Base):
    __tablename__ = "exposure_definition_evidence_claims"
    exposure_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("exposure_definitions.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class ExposureEntryObservationRecord(Base):
    __tablename__ = "exposure_entry_observations"
    exposure_entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("exposure_entries.id", ondelete="RESTRICT"), primary_key=True
    )
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class ExposureProgressionPolicyEvidenceRecord(Base):
    __tablename__ = "exposure_progression_policy_evidence_claims"
    exposure_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("exposure_progression_policies.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class ExposureValidationEntryRecord(Base):
    __tablename__ = "exposure_validation_entries"
    exposure_validation_decision_id: Mapped[UUID] = mapped_column(
        ForeignKey("exposure_validation_decisions.id", ondelete="RESTRICT"), primary_key=True
    )
    exposure_entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("exposure_entries.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class ProgressionDecisionSafetyRecord(Base):
    __tablename__ = "progression_decision_safety_decisions"
    progression_decision_id: Mapped[UUID] = mapped_column(
        ForeignKey("progression_decisions.id", ondelete="RESTRICT"), primary_key=True
    )
    safety_decision_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_safety_decisions.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class ProgressionDecisionObservationRecord(Base):
    __tablename__ = "progression_decision_observations"
    progression_decision_id: Mapped[UUID] = mapped_column(
        ForeignKey("progression_decisions.id", ondelete="RESTRICT"), primary_key=True
    )
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class SessionPrescriptionRevisionRecord(Base):
    __tablename__ = "session_prescription_revisions"
    __table_args__ = (
        CheckConstraint(
            "(progression_decision_id IS NOT NULL AND planning_decision_record_id IS NULL) OR "
            "(progression_decision_id IS NULL AND planning_decision_record_id IS NOT NULL)",
            name="ck_prescription_revision_one_authorizer",
        ),
    )
    revised_prescription_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_prescriptions.id", ondelete="RESTRICT"), primary_key=True
    )
    superseded_prescription_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_prescriptions.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    progression_decision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("progression_decisions.id", ondelete="RESTRICT"), nullable=True, unique=True
    )
    planning_decision_record_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("decision_records.id", ondelete="RESTRICT"), nullable=True, index=True
    )


class TrainingResponseRecord(VersionedRecordMixin, Base):
    __tablename__ = "training_responses"
    __table_args__ = (CheckConstraint("kind = 'derived'", name="ck_training_response_derived"),)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True
    )
    block_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("block_plans.id", ondelete="RESTRICT"), index=True
    )
    adaptation_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptations.id", ondelete="RESTRICT"), index=True
    )
    intervention_summary: Mapped[str] = mapped_column(Text(), nullable=False)
    prescribed_sessions: Mapped[int] = mapped_column(Integer(), nullable=False)
    completed_sessions: Mapped[int] = mapped_column(Integer(), nullable=False)
    prescribed_dose_total: Mapped[float] = mapped_column(Float(), nullable=False)
    actual_dose_total: Mapped[float] = mapped_column(Float(), nullable=False)
    dose_unit: Mapped[str] = mapped_column(String(40), nullable=False)
    adherence_ratio: Mapped[float] = mapped_column(Float(), nullable=False)
    baseline_capability_estimate_id: Mapped[UUID] = mapped_column(
        ForeignKey("capability_estimates.id", ondelete="RESTRICT"), index=True
    )
    followup_capability_estimate_id: Mapped[UUID] = mapped_column(
        ForeignKey("capability_estimates.id", ondelete="RESTRICT"), index=True
    )
    baseline_value: Mapped[float] = mapped_column(Float(), nullable=False)
    followup_value: Mapped[float] = mapped_column(Float(), nullable=False)
    observed_change: Mapped[float] = mapped_column(Float(), nullable=False)
    measurement_uncertainty: Mapped[str] = mapped_column(Text(), nullable=False)
    contextual_factors: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    calculation_method: Mapped[str] = mapped_column(String(160), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(160), nullable=False)
    prescription_links: Mapped[list[TrainingResponsePrescriptionRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="TrainingResponsePrescriptionRecord.position",
    )
    execution_links: Mapped[list[TrainingResponseExecutionRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="TrainingResponseExecutionRecord.position",
    )
    adherence_links: Mapped[list[TrainingResponseAdherenceRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="TrainingResponseAdherenceRecord.position",
    )
    observation_links: Mapped[list[TrainingResponseObservationRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="TrainingResponseObservationRecord.position",
    )


class TrainingResponsePrescriptionRecord(Base):
    __tablename__ = "training_response_prescriptions"
    __table_args__ = (
        UniqueConstraint(
            "training_response_id", "position", name="uq_training_response_prescription_order"
        ),
    )
    training_response_id: Mapped[UUID] = mapped_column(
        ForeignKey("training_responses.id", ondelete="RESTRICT"), primary_key=True
    )
    prescription_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_prescriptions.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class TrainingResponseExecutionRecord(Base):
    __tablename__ = "training_response_executions"
    __table_args__ = (
        UniqueConstraint(
            "training_response_id", "position", name="uq_training_response_execution_order"
        ),
    )
    training_response_id: Mapped[UUID] = mapped_column(
        ForeignKey("training_responses.id", ondelete="RESTRICT"), primary_key=True
    )
    execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_executions.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class TrainingResponseAdherenceRecord(Base):
    __tablename__ = "training_response_adherence"
    __table_args__ = (
        UniqueConstraint(
            "training_response_id", "position", name="uq_training_response_adherence_order"
        ),
    )
    training_response_id: Mapped[UUID] = mapped_column(
        ForeignKey("training_responses.id", ondelete="RESTRICT"), primary_key=True
    )
    adherence_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_adherence.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class TrainingResponseObservationRecord(Base):
    __tablename__ = "training_response_observations"
    __table_args__ = (
        UniqueConstraint(
            "training_response_id", "position", name="uq_training_response_observation_order"
        ),
    )
    training_response_id: Mapped[UUID] = mapped_column(
        ForeignKey("training_responses.id", ondelete="RESTRICT"), primary_key=True
    )
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class BlockReviewPolicyRecord(VersionedRecordMixin, Base):
    __tablename__ = "block_review_policies"
    minimum_adherence_ratio: Mapped[float] = mapped_column(Float(), nullable=False)
    minimum_response_confidence: Mapped[str] = mapped_column(String(40), nullable=False)
    rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)
    evidence_links: Mapped[list[BlockReviewPolicyEvidenceRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="BlockReviewPolicyEvidenceRecord.position",
    )


class BlockReviewPolicyEvidenceRecord(Base):
    __tablename__ = "block_review_policy_evidence_claims"
    __table_args__ = (
        UniqueConstraint(
            "block_review_policy_id", "position", name="uq_block_review_policy_evidence_order"
        ),
    )
    block_review_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("block_review_policies.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class BlockReviewRecord(VersionedRecordMixin, Base):
    __tablename__ = "block_reviews"
    __table_args__ = (
        CheckConstraint("kind = 'derived'", name="ck_block_review_derived"),
        UniqueConstraint("block_plan_id", name="uq_block_review_block_plan"),
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    athlete_id: Mapped[UUID] = mapped_column(
        ForeignKey("athletes.id", ondelete="RESTRICT"), index=True
    )
    block_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("block_plans.id", ondelete="RESTRICT"), index=True
    )
    block_hypothesis: Mapped[str] = mapped_column(Text(), nullable=False)
    block_review_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("block_review_policies.id", ondelete="RESTRICT"), index=True
    )
    prescribed_sessions: Mapped[int] = mapped_column(Integer(), nullable=False)
    completed_sessions: Mapped[int] = mapped_column(Integer(), nullable=False)
    aggregate_adherence_ratio: Mapped[float] = mapped_column(Float(), nullable=False)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    rationale: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    rule_version: Mapped[str] = mapped_column(String(160), nullable=False)
    response_links: Mapped[list[BlockReviewResponseRecord]] = relationship(
        cascade="save-update, merge", lazy="selectin", order_by="BlockReviewResponseRecord.position"
    )
    safety_links: Mapped[list[BlockReviewSafetyRecord]] = relationship(
        cascade="save-update, merge", lazy="selectin", order_by="BlockReviewSafetyRecord.position"
    )
    observation_links: Mapped[list[BlockReviewObservationRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="BlockReviewObservationRecord.position",
    )
    evidence_links: Mapped[list[BlockReviewEvidenceRecord]] = relationship(
        cascade="save-update, merge", lazy="selectin", order_by="BlockReviewEvidenceRecord.position"
    )


class BlockReviewResponseRecord(Base):
    __tablename__ = "block_review_responses"
    __table_args__ = (
        UniqueConstraint("block_review_id", "position", name="uq_block_review_response_order"),
    )
    block_review_id: Mapped[UUID] = mapped_column(
        ForeignKey("block_reviews.id", ondelete="RESTRICT"), primary_key=True
    )
    training_response_id: Mapped[UUID] = mapped_column(
        ForeignKey("training_responses.id", ondelete="RESTRICT"), primary_key=True
    )
    comparison_direction: Mapped[str] = mapped_column(String(40), nullable=False)
    minimum_meaningful_change: Mapped[float] = mapped_column(Float(), nullable=False)
    threshold_met: Mapped[bool | None] = mapped_column(Boolean(), nullable=True)
    evaluation_rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class BlockReviewSafetyRecord(Base):
    __tablename__ = "block_review_safety_decisions"
    __table_args__ = (
        UniqueConstraint("block_review_id", "position", name="uq_block_review_safety_order"),
    )
    block_review_id: Mapped[UUID] = mapped_column(
        ForeignKey("block_reviews.id", ondelete="RESTRICT"), primary_key=True
    )
    safety_decision_id: Mapped[UUID] = mapped_column(
        ForeignKey("session_safety_decisions.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class BlockReviewObservationRecord(Base):
    __tablename__ = "block_review_observations"
    __table_args__ = (
        UniqueConstraint("block_review_id", "position", name="uq_block_review_observation_order"),
    )
    block_review_id: Mapped[UUID] = mapped_column(
        ForeignKey("block_reviews.id", ondelete="RESTRICT"), primary_key=True
    )
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class BlockReviewEvidenceRecord(Base):
    __tablename__ = "block_review_evidence_claims"
    __table_args__ = (
        UniqueConstraint("block_review_id", "position", name="uq_block_review_evidence_order"),
    )
    block_review_id: Mapped[UUID] = mapped_column(
        ForeignKey("block_reviews.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class DecisionRecordRecord(VersionedRecordMixin, Base):
    __tablename__ = "decision_records"

    decision: Mapped[str] = mapped_column(Text(), nullable=False)
    reason: Mapped[str] = mapped_column(Text(), nullable=False)
    alternatives_considered: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    uncertainty: Mapped[str] = mapped_column(Text(), nullable=False)
    decision_version: Mapped[str] = mapped_column(String(80), nullable=False)
    decided_on: Mapped[date] = mapped_column(Date(), nullable=False)


class CatalogImportRecord(VersionedRecordMixin, Base):
    __tablename__ = "catalog_imports"

    catalog_version: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    review_status: Mapped[str] = mapped_column(String(80), nullable=False)
    reviewed_by: Mapped[str] = mapped_column(Text(), nullable=False)
    reviewed_at: Mapped[date] = mapped_column(Date(), nullable=False)
    scope: Mapped[str] = mapped_column(Text(), nullable=False)
    notes: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    content_digest: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    importer_version: Mapped[str] = mapped_column(String(80), nullable=False)

    evidence_links: Mapped[list[CatalogImportEvidenceRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="CatalogImportEvidenceRecord.position",
    )
    adaptation_links: Mapped[list[CatalogImportAdaptationRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="CatalogImportAdaptationRecord.position",
    )
    equipment_links: Mapped[list[CatalogImportEquipmentRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="CatalogImportEquipmentRecord.position",
    )
    exercise_links: Mapped[list[CatalogImportExerciseRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="CatalogImportExerciseRecord.position",
    )


class CatalogImportEvidenceRecord(Base):
    __tablename__ = "catalog_import_evidence_claims"
    __table_args__ = (
        UniqueConstraint("catalog_import_id", "position", name="uq_catalog_import_evidence_order"),
    )

    catalog_import_id: Mapped[UUID] = mapped_column(
        ForeignKey("catalog_imports.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class CatalogImportAdaptationRecord(Base):
    __tablename__ = "catalog_import_adaptations"
    __table_args__ = (
        UniqueConstraint(
            "catalog_import_id", "position", name="uq_catalog_import_adaptation_order"
        ),
    )

    catalog_import_id: Mapped[UUID] = mapped_column(
        ForeignKey("catalog_imports.id", ondelete="RESTRICT"), primary_key=True
    )
    adaptation_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptations.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class CatalogImportEquipmentRecord(Base):
    __tablename__ = "catalog_import_equipment"
    __table_args__ = (
        UniqueConstraint("catalog_import_id", "position", name="uq_catalog_import_equipment_order"),
    )

    catalog_import_id: Mapped[UUID] = mapped_column(
        ForeignKey("catalog_imports.id", ondelete="RESTRICT"), primary_key=True
    )
    equipment_id: Mapped[UUID] = mapped_column(
        ForeignKey("equipment.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class CatalogImportExerciseRecord(Base):
    __tablename__ = "catalog_import_exercises"
    __table_args__ = (
        UniqueConstraint("catalog_import_id", "position", name="uq_catalog_import_exercise_order"),
    )

    catalog_import_id: Mapped[UUID] = mapped_column(
        ForeignKey("catalog_imports.id", ondelete="RESTRICT"), primary_key=True
    )
    exercise_id: Mapped[UUID] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class ExerciseAdaptationRecord(Base):
    __tablename__ = "exercise_adaptations"
    __table_args__ = (
        CheckConstraint("role IN ('primary', 'secondary')", name="ck_exercise_adaptation_role"),
        UniqueConstraint("exercise_id", "role", "position", name="uq_exercise_adaptation_order"),
    )

    exercise_id: Mapped[UUID] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"), primary_key=True
    )
    adaptation_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptations.id", ondelete="RESTRICT"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(20), primary_key=True)
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class ExerciseEquipmentRequirementRecord(Base):
    __tablename__ = "exercise_equipment_requirements"
    __table_args__ = (
        UniqueConstraint("exercise_id", "position", name="uq_exercise_equipment_order"),
    )

    exercise_id: Mapped[UUID] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"), primary_key=True
    )
    equipment_id: Mapped[UUID] = mapped_column(
        ForeignKey("equipment.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class ExerciseRelationshipRecord(Base):
    __tablename__ = "exercise_relationships"
    __table_args__ = (
        CheckConstraint(
            "relationship IN ('progression', 'regression')",
            name="ck_exercise_relationship_type",
        ),
        CheckConstraint(
            "source_exercise_id <> target_exercise_id",
            name="ck_exercise_relationship_not_self",
        ),
        UniqueConstraint(
            "source_exercise_id",
            "relationship",
            "position",
            name="uq_exercise_relationship_order",
        ),
    )

    source_exercise_id: Mapped[UUID] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"), primary_key=True
    )
    target_exercise_id: Mapped[UUID] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"), primary_key=True
    )
    relationship: Mapped[str] = mapped_column(String(20), primary_key=True)
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class AdaptationEvidenceClaimRecord(Base):
    __tablename__ = "adaptation_evidence_claims"
    __table_args__ = (
        UniqueConstraint("adaptation_id", "position", name="uq_adaptation_evidence_order"),
    )

    adaptation_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptations.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class AdaptationRelationshipRecord(VersionedRecordMixin, Base):
    __tablename__ = "adaptation_relationships"
    __table_args__ = (
        CheckConstraint(
            "source_adaptation_id <> target_adaptation_id",
            name="ck_adaptation_relationship_not_self",
        ),
        UniqueConstraint(
            "source_adaptation_id",
            "position",
            name="uq_adaptation_relationship_order",
        ),
    )

    source_adaptation_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptations.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    target_adaptation_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptations.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    relationship_type: Mapped[str] = mapped_column("relationship", String(60), nullable=False)
    strength: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False)
    population: Mapped[str] = mapped_column(Text(), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    position: Mapped[int] = mapped_column(Integer(), nullable=False)

    evidence_links: Mapped[list[AdaptationRelationshipEvidenceRecord]] = relationship(
        cascade="save-update, merge",
        lazy="selectin",
        order_by="AdaptationRelationshipEvidenceRecord.position",
    )


class AdaptationRelationshipEvidenceRecord(Base):
    __tablename__ = "adaptation_relationship_evidence"
    __table_args__ = (
        UniqueConstraint("relationship_id", "position", name="uq_relationship_evidence_order"),
    )

    relationship_id: Mapped[UUID] = mapped_column(
        ForeignKey("adaptation_relationships.id", ondelete="RESTRICT"), primary_key=True
    )
    evidence_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_claims.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer(), nullable=False)


class ImmutableHistoricalRecordError(RuntimeError):
    pass


def _reject_mutation(_mapper: object, _connection: object, target: object) -> None:
    raise ImmutableHistoricalRecordError(
        f"{type(target).__name__} is append-only; add a new version instead"
    )


for _record_type in (
    AccountRecord,
    AccountRoleAssignmentRecord,
    AthleteOwnershipRecord,
    ObservationRecord,
    CapabilityEstimateRecord,
    CapabilityEstimateObservationRecord,
    EquipmentAvailabilityRecord,
    EvidenceClaimRecord,
    AssessmentDefinitionRecord,
    AssessmentDefinitionReviewRecord,
    AssessmentDefinitionReviewEvidenceClaimRecord,
    CapabilityEstimationPolicyRecord,
    CapabilityEstimationPolicyEvidenceClaimRecord,
    AssessmentEligibilityReviewRecord,
    AssessmentEligibilityReviewObservationRecord,
    AssessmentSelectionRecord,
    AssessmentSelectionObservationRecord,
    AssessmentSelectionRunRecord,
    AssessmentSelectionRunItemRecord,
    AssessmentPerformanceRecord,
    CompetencyFloorRecord,
    CompetencyFloorEvidenceClaimRecord,
    CompetencyFloorReviewRecord,
    CompetencyFloorReviewEvidenceClaimRecord,
    CapabilityNeedRecord,
    CapabilityNeedEvidenceClaimRecord,
    PriorityPolicyRecord,
    PriorityPolicyReviewRecord,
    PriorityPolicyReviewEvidenceClaimRecord,
    InitialPlanningContextDraftRecord,
    InitialPlanningCandidateContextRecord,
    InitialPlanningContextPrerequisiteRecord,
    InitialPlanningContextObservationRecord,
    InitialPlanningContextEvidenceRecord,
    InitialPlanningContextReviewRecord,
    LongRangeStrategyRecord,
    AdaptationPriorityRecord,
    RoadmapItemRecord,
    RoadmapItemPrerequisiteRecord,
    StrategyObservationRecord,
    StrategyCapabilityEstimateRecord,
    StrategyCompetencyFloorRecord,
    StrategyEvidenceClaimRecord,
    StimulusRequirementRecord,
    StimulusRequirementObservationRecord,
    StimulusRequirementEvidenceClaimRecord,
    ExerciseResolverPolicyRecord,
    ExerciseResolutionRecord,
    ExerciseMatchRecord,
    ExerciseResolutionAvailabilityRecord,
    AdaptationResourceDemandRecord,
    ResourceDemandObservationRecord,
    ResourceDemandEvidenceClaimRecord,
    ResourceAllocationPolicyRecord,
    BlockPlanRecord,
    BlockResourceAllocationRecord,
    BlockPlanObservationRecord,
    BlockPlanEvidenceClaimRecord,
    SessionPrescriptionRecord,
    SessionPrescriptionObservationRecord,
    SessionPrescriptionEvidenceClaimRecord,
    SessionTemplateRecord,
    SessionTemplateItemRecord,
    SessionTemplateObservationRecord,
    SessionTemplateEvidenceRecord,
    WeeklyAvailabilityRecord,
    AvailabilityWindowRecord,
    WeeklyAvailabilityObservationRecord,
    WeeklySchedulingPolicyRecord,
    WeeklyPlanRecord,
    PlannedSessionRecord,
    SessionSafetyPolicyRecord,
    SessionSafetyPolicyEvidenceClaimRecord,
    AthleteSafetyPolicyAssignmentRecord,
    SessionSafetyDecisionRecord,
    SessionSafetyDecisionObservationRecord,
    SessionExecutionRecord,
    SessionItemExecutionRecord,
    SetPerformanceRecord,
    SessionAdherenceRecord,
    SessionAdherenceObservationRecord,
    ProgressionPolicyRecord,
    ExposureDefinitionRecord,
    ExposureEntryRecord,
    ExposureProgressionPolicyRecord,
    ExposureValidationDecisionRecord,
    ProgressionDecisionRecord,
    ProgressionPolicyEvidenceRecord,
    ExposureDefinitionEvidenceRecord,
    ExposureEntryObservationRecord,
    ExposureProgressionPolicyEvidenceRecord,
    ExposureValidationEntryRecord,
    ProgressionDecisionSafetyRecord,
    ProgressionDecisionObservationRecord,
    SessionPrescriptionRevisionRecord,
    TrainingResponseRecord,
    TrainingResponsePrescriptionRecord,
    TrainingResponseExecutionRecord,
    TrainingResponseAdherenceRecord,
    TrainingResponseObservationRecord,
    BlockReviewPolicyRecord,
    BlockReviewPolicyEvidenceRecord,
    BlockReviewRecord,
    BlockReviewResponseRecord,
    BlockReviewSafetyRecord,
    BlockReviewObservationRecord,
    BlockReviewEvidenceRecord,
    DecisionRecordRecord,
    CatalogImportRecord,
    CatalogImportEvidenceRecord,
    CatalogImportAdaptationRecord,
    CatalogImportEquipmentRecord,
    CatalogImportExerciseRecord,
    ExerciseRecord,
    ExerciseAdaptationRecord,
    ExerciseEquipmentRequirementRecord,
    ExerciseRelationshipRecord,
    AdaptationRecord,
    AdaptationEvidenceClaimRecord,
    AdaptationRelationshipRecord,
    AdaptationRelationshipEvidenceRecord,
):
    event.listen(_record_type, "before_update", _reject_mutation)
    event.listen(_record_type, "before_delete", _reject_mutation)
