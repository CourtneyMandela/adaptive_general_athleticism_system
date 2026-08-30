from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from agas_domain import (
    AbsoluteLoadTarget,
    AccountRole,
    AccountRoleStatus,
    AssessmentReviewDecision,
    AvailabilityWindow,
    BlockPlan,
    BodyweightTarget,
    CostLevel,
    DecisionRecord,
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
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
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
    scheduling_policy_review_id: UUID
    prepared_at: datetime
    reviewed_by: NonEmptyText
    review_authority_assignment_id: UUID | None = None
    applicability_rationale: NonEmptyText
    uncertainty: NonEmptyText

    @field_validator("reviewed_by", "applicability_rationale", "uncertainty")
    @classmethod
    def require_meaningful_review_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("operator review metadata must not be blank")
        return normalized

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
    decision_record: DecisionRecord


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
            self.repository.add_decision_record(result.decision_record)
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
        self._validate_review_authority(command)
        block = self.repository.get_block_plan(block_id)
        if block is None:
            raise WeeklyPlanNotFoundError("block plan does not exist")
        if command.availability.week_start != block.starts_on:
            raise WeeklyPlanValidationError(
                "initial weekly-plan authoring requires block week one; later weeks use "
                "the roll-forward boundary"
            )
        policy = self.repository.get_weekly_scheduling_policy(command.scheduling_policy_id)
        if policy is None:
            raise WeeklyPlanNotFoundError("weekly scheduling policy does not exist")
        policy_review = self.repository.get_weekly_scheduling_policy_review(
            command.scheduling_policy_review_id
        )
        if policy_review is None:
            raise WeeklyPlanNotFoundError("weekly scheduling policy review does not exist")
        current_policy_review = self.repository.get_current_weekly_scheduling_policy_review(
            policy.id
        )
        if (
            policy_review.weekly_scheduling_policy_id != policy.id
            or current_policy_review is None
            or current_policy_review.id != policy_review.id
            or policy_review.decision is not AssessmentReviewDecision.APPROVED
            or policy_review.reviewed_at > command.prepared_at
        ):
            raise WeeklyPlanValidationError(
                "weekly plan requires the exact current approved scheduling policy review"
            )

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
        scheduled = WeeklyScheduler().schedule(
            block=block,
            availability=availability,
            prescriptions=prescriptions,
            session_templates=templates,
            resolutions=resolutions_by_id.values(),
            policy=policy,
            generated_at=command.prepared_at,
        )
        plan = scheduled.model_copy(update={"scheduling_policy_review_id": policy_review.id})
        decision_record = DecisionRecord(
            decision=(
                f"Create block week {plan.block_week} weekly plan {plan.id} for block {block.id}."
            ),
            reason=f"Reviewed by {command.reviewed_by}. {command.applicability_rationale}",
            alternatives_considered=(
                "Defer weekly-plan creation until different reviewed prescriptions, session "
                "composition, availability, or scheduling policy are available.",
            ),
            evidence=self._decision_evidence(
                block=block,
                prescriptions=tuple(prescriptions),
                templates=tuple(templates),
                availability=availability,
                scheduling_policy_id=policy.id,
                scheduling_policy_review_id=policy_review.id,
                weekly_plan=plan,
                review_authority_assignment_id=command.review_authority_assignment_id,
            ),
            uncertainty=command.uncertainty,
            decision_version=(f"first-week-operator-review@1.0.0;scheduler={plan.rule_version}"),
            decided_on=command.prepared_at.date(),
        )
        return WeeklyPlanCreationResult(
            prescriptions=tuple(prescriptions),
            session_templates=tuple(templates),
            availability=availability,
            weekly_plan=plan,
            decision_record=decision_record,
        )

    def _validate_review_authority(self, command: CreateWeeklyPlanCommand) -> None:
        assignment_id = command.review_authority_assignment_id
        if assignment_id is None:
            return
        assignment = self.repository.get_account_role_assignment(assignment_id)
        if assignment is None:
            raise WeeklyPlanValidationError("review authority assignment does not exist")
        current = self.repository.get_current_account_role_assignment(
            assignment.account_id, AccountRole.PLANNING_REVIEWER
        )
        if (
            assignment.role is not AccountRole.PLANNING_REVIEWER
            or assignment.status is not AccountRoleStatus.ACTIVE
            or current is None
            or current.id != assignment.id
        ):
            raise WeeklyPlanValidationError(
                "review authority assignment is not a current planning-reviewer grant"
            )
        if command.reviewed_by != f"account:{assignment.account_id}":
            raise WeeklyPlanValidationError(
                "reviewed_by does not match the review authority account"
            )
        if command.prepared_at < assignment.assigned_at:
            raise WeeklyPlanValidationError(
                "weekly-plan creation cannot predate the reviewer role assignment"
            )

    @staticmethod
    def _decision_evidence(
        *,
        block: BlockPlan,
        prescriptions: tuple[SessionPrescription, ...],
        templates: tuple[SessionTemplate, ...],
        availability: WeeklyAvailability,
        scheduling_policy_id: UUID,
        scheduling_policy_review_id: UUID,
        weekly_plan: WeeklyPlan,
        review_authority_assignment_id: UUID | None,
    ) -> tuple[str, ...]:
        allocation_ids = tuple(item.resource_allocation_id for item in prescriptions)
        values = [
            f"long_range_strategy:{block.long_range_strategy_id}",
            f"block_plan:{block.id}",
            *(f"resource_allocation:{item}" for item in allocation_ids),
            *(f"exercise_resolution:{item.exercise_resolution_id}" for item in prescriptions),
            *(f"exercise:{item.exercise_id}" for item in prescriptions),
            *(f"adaptation:{item.adaptation_id}" for item in prescriptions),
            *(f"observation:{item}" for item in availability.source_observation_ids),
            *(
                f"observation:{item}"
                for prescription in prescriptions
                for item in prescription.source_observation_ids
            ),
            *(
                f"observation:{item}"
                for template in templates
                for item in template.source_observation_ids
            ),
            *(
                f"evidence_claim:{item}"
                for prescription in prescriptions
                for item in prescription.evidence_claim_ids
            ),
            *(
                f"evidence_claim:{item}"
                for template in templates
                for item in template.evidence_claim_ids
            ),
            *(f"session_prescription:{item.id}" for item in prescriptions),
            *(f"session_template:{item.id}" for item in templates),
            f"weekly_availability:{availability.id}",
            f"weekly_scheduling_policy:{scheduling_policy_id}",
            f"weekly_scheduling_policy_review:{scheduling_policy_review_id}",
            f"weekly_plan:{weekly_plan.id}",
        ]
        if review_authority_assignment_id is not None:
            values.append(f"account_role_assignment:{review_authority_assignment_id}")
        return tuple(dict.fromkeys(values))
