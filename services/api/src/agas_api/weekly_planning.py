from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from agas_domain import (
    AbsoluteLoadTarget,
    AvailabilityWindow,
    BodyweightTarget,
    CostLevel,
    EffortRpeTarget,
    HeartRateZoneTarget,
    PaceTarget,
    RelativeLoadTarget,
    RepetitionsInReserveTarget,
    SessionPrescription,
    SessionSection,
    SessionTemplate,
    SessionTemplateItem,
    TechniqueTarget,
    WeeklyAvailability,
    WeeklyPlan,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import BlockPlanningError, WeeklyScheduler
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

NonEmptyText = Annotated[str, Field(min_length=1)]
PrescriptionIntensityTarget = Annotated[
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


class SessionPrescriptionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    resource_allocation_id: UUID
    reason_for_inclusion: NonEmptyText
    sets: int = Field(ge=1)
    repetitions_per_set: int | None = Field(default=None, ge=1)
    duration_seconds: int | None = Field(default=None, ge=1)
    intensity_targets: Annotated[tuple[PrescriptionIntensityTarget, ...], Field(min_length=1)]
    rest_seconds: int = Field(ge=0)
    progression_rule_reference: NonEmptyText
    substitution_class: NonEmptyText
    planned_duration_minutes: int = Field(gt=0)
    fatigue_cost: CostLevel
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    rule_version: NonEmptyText

    @model_validator(mode="after")
    def validate_draft(self) -> SessionPrescriptionDraft:
        if (self.repetitions_per_set is None) == (self.duration_seconds is None):
            raise ValueError("prescription draft requires exactly one of repetitions or duration")
        for field_name in ("source_observation_ids", "evidence_claim_ids"):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        target_kinds = [item.kind for item in self.intensity_targets]
        if len(set(target_kinds)) != len(target_kinds):
            raise ValueError("intensity target kinds must not contain duplicates")
        return self


class SessionTemplateItemDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    resource_allocation_id: UUID
    order_index: int = Field(ge=1)
    section: SessionSection


class SessionTemplateDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: NonEmptyText
    items: Annotated[tuple[SessionTemplateItemDraft, ...], Field(min_length=1)]
    sessions_per_week: int = Field(ge=1)
    planned_duration_minutes: int = Field(gt=0)
    fatigue_cost: CostLevel
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    evidence_claim_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    rule_version: NonEmptyText

    @model_validator(mode="after")
    def validate_draft(self) -> SessionTemplateDraft:
        order = tuple(item.order_index for item in self.items)
        if order != tuple(range(1, len(self.items) + 1)):
            raise ValueError("session template item order must be contiguous and start at one")
        allocation_ids = tuple(item.resource_allocation_id for item in self.items)
        if len(set(allocation_ids)) != len(allocation_ids):
            raise ValueError("session template allocations must not contain duplicates")
        for field_name in ("source_observation_ids", "evidence_claim_ids"):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        return self


class AvailabilityWindowDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    environment_id: UUID
    starts_at: datetime
    ends_at: datetime


class WeeklyAvailabilityDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    week_start: date
    windows: tuple[AvailabilityWindowDraft, ...] = ()
    source_observation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    rule_version: NonEmptyText


class CreateWeeklyPlanCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prescriptions: Annotated[tuple[SessionPrescriptionDraft, ...], Field(min_length=1)]
    session_templates: Annotated[tuple[SessionTemplateDraft, ...], Field(min_length=1)]
    availability: WeeklyAvailabilityDraft
    scheduling_policy_id: UUID
    prepared_at: datetime

    @model_validator(mode="after")
    def validate_command(self) -> CreateWeeklyPlanCommand:
        allocation_ids = tuple(item.resource_allocation_id for item in self.prescriptions)
        if len(set(allocation_ids)) != len(allocation_ids):
            raise ValueError("prescription drafts must have unique resource allocations")
        if self.prepared_at.tzinfo is None or self.prepared_at.utcoffset() is None:
            raise ValueError("prepared_at must include a timezone")
        return self


class WeeklyPlanCreationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prescriptions: Annotated[tuple[SessionPrescription, ...], Field(min_length=1)]
    session_templates: Annotated[tuple[SessionTemplate, ...], Field(min_length=1)]
    availability: WeeklyAvailability
    weekly_plan: WeeklyPlan


class WeeklyPlanUseCaseError(RuntimeError):
    """Base error for the persisted weekly-plan use case."""


class WeeklyPlanNotFoundError(WeeklyPlanUseCaseError):
    pass


class WeeklyPlanConflictError(WeeklyPlanUseCaseError):
    pass


class WeeklyPlanValidationError(WeeklyPlanUseCaseError):
    pass


class PersistedWeeklyPlanService:
    """Build and append explicit prescriptions, session containers, and one week atomically."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(self, block_id: UUID, command: CreateWeeklyPlanCommand) -> WeeklyPlanCreationResult:
        try:
            result = self._build(block_id, command)
            for prescription in result.prescriptions:
                self.repository.add_session_prescription(prescription)
            self.session.flush()
            for template in result.session_templates:
                self.repository.add_session_template(template)
            self.repository.add_weekly_availability(result.availability)
            self.session.flush()
            self.repository.add_weekly_plan(result.weekly_plan)
            self.session.commit()
            return result
        except WeeklyPlanUseCaseError:
            self.session.rollback()
            raise
        except (BlockPlanningError, DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise WeeklyPlanValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise WeeklyPlanConflictError(
                "weekly-plan preparation conflicts with persisted planning state"
            ) from error

    def _build(self, block_id: UUID, command: CreateWeeklyPlanCommand) -> WeeklyPlanCreationResult:
        block = self.repository.get_block_plan(block_id)
        if block is None:
            raise WeeklyPlanNotFoundError("block plan does not exist")
        policy = self.repository.get_weekly_scheduling_policy(command.scheduling_policy_id)
        if policy is None:
            raise WeeklyPlanNotFoundError("weekly scheduling policy does not exist")

        allocation_by_id = {item.id: item for item in block.allocations}
        prescriptions = []
        resolutions_by_id = {}
        for prescription_draft in command.prescriptions:
            allocation = allocation_by_id.get(prescription_draft.resource_allocation_id)
            if allocation is None:
                raise WeeklyPlanValidationError(
                    "prescription allocation does not belong to the block"
                )
            if allocation.allocated_weekly_minutes == 0:
                raise WeeklyPlanValidationError(
                    "a zero-resource allocation cannot receive a prescription"
                )
            resolution_id = allocation.exercise_resolution_id
            if resolution_id is None:
                raise WeeklyPlanValidationError("active allocation has no exercise resolution")
            resolution = self.repository.get_exercise_resolution(resolution_id)
            if resolution is None:
                raise WeeklyPlanNotFoundError(f"exercise resolution {resolution_id} does not exist")
            if resolution.selected_exercise_id is None:
                raise WeeklyPlanValidationError(
                    "an infeasible exercise resolution cannot receive a prescription"
                )
            resolutions_by_id[resolution.id] = resolution
            prescriptions.append(
                SessionPrescription(
                    athlete_id=block.athlete_id,
                    block_plan_id=block.id,
                    resource_allocation_id=allocation.id,
                    exercise_resolution_id=resolution.id,
                    exercise_id=resolution.selected_exercise_id,
                    adaptation_id=allocation.adaptation_id,
                    reason_for_inclusion=prescription_draft.reason_for_inclusion,
                    sets=prescription_draft.sets,
                    repetitions_per_set=prescription_draft.repetitions_per_set,
                    duration_seconds=prescription_draft.duration_seconds,
                    intensity_targets=prescription_draft.intensity_targets,
                    rest_seconds=prescription_draft.rest_seconds,
                    progression_rule_reference=prescription_draft.progression_rule_reference,
                    substitution_class=prescription_draft.substitution_class,
                    planned_duration_minutes=prescription_draft.planned_duration_minutes,
                    fatigue_cost=prescription_draft.fatigue_cost,
                    source_observation_ids=prescription_draft.source_observation_ids,
                    evidence_claim_ids=prescription_draft.evidence_claim_ids,
                    prescribed_at=command.prepared_at,
                    rule_version=prescription_draft.rule_version,
                )
            )

        prescription_by_allocation = {item.resource_allocation_id: item for item in prescriptions}
        templates = []
        for template_draft in command.session_templates:
            items = []
            for item_draft in template_draft.items:
                prescription = prescription_by_allocation.get(item_draft.resource_allocation_id)
                if prescription is None:
                    raise WeeklyPlanValidationError(
                        "session template references an unknown prescription allocation"
                    )
                items.append(
                    SessionTemplateItem(
                        prescription_id=prescription.id,
                        order_index=item_draft.order_index,
                        section=item_draft.section,
                    )
                )
            templates.append(
                SessionTemplate(
                    athlete_id=block.athlete_id,
                    block_plan_id=block.id,
                    name=template_draft.name,
                    items=tuple(items),
                    sessions_per_week=template_draft.sessions_per_week,
                    planned_duration_minutes=template_draft.planned_duration_minutes,
                    fatigue_cost=template_draft.fatigue_cost,
                    source_observation_ids=template_draft.source_observation_ids,
                    evidence_claim_ids=template_draft.evidence_claim_ids,
                    created_for_block_at=command.prepared_at,
                    rule_version=template_draft.rule_version,
                )
            )

        availability = WeeklyAvailability(
            athlete_id=block.athlete_id,
            week_start=command.availability.week_start,
            windows=tuple(
                AvailabilityWindow(
                    environment_id=item.environment_id,
                    starts_at=item.starts_at,
                    ends_at=item.ends_at,
                )
                for item in command.availability.windows
            ),
            source_observation_ids=command.availability.source_observation_ids,
            recorded_at=command.prepared_at,
            rule_version=command.availability.rule_version,
        )
        plan = WeeklyScheduler().schedule(
            block=block,
            availability=availability,
            prescriptions=prescriptions,
            session_templates=templates,
            resolutions=resolutions_by_id.values(),
            policy=policy,
            generated_at=command.prepared_at,
        )
        return WeeklyPlanCreationResult(
            prescriptions=tuple(prescriptions),
            session_templates=tuple(templates),
            availability=availability,
            weekly_plan=plan,
        )
