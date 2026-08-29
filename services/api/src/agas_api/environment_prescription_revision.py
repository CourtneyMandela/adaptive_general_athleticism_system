from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from agas_domain import (
    AbsoluteLoadTarget,
    AccountRoleStatus,
    AssessmentReviewDecision,
    BodyweightTarget,
    CostLevel,
    DecisionRecord,
    EffortRpeTarget,
    HeartRateZoneTarget,
    PaceTarget,
    RelativeLoadTarget,
    RepetitionsInReserveTarget,
    ResolutionStatus,
    SessionPrescription,
    SessionTemplate,
    TechniqueTarget,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agas_api.current_week import CurrentWeekProjectionError, CurrentWeekProjector

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


class EnvironmentPrescriptionRevisionDraft(BaseModel):
    """A complete reviewed replacement dose for one source-plan prescription."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_prescription_id: UUID
    exercise_resolution_id: UUID
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
    rule_version: NonEmptyText

    @model_validator(mode="after")
    def validate_draft(self) -> EnvironmentPrescriptionRevisionDraft:
        if (self.repetitions_per_set is None) == (self.duration_seconds is None):
            raise ValueError("replacement prescription requires exactly one dose form")
        target_kinds = tuple(item.kind for item in self.intensity_targets)
        if len(set(target_kinds)) != len(target_kinds):
            raise ValueError("replacement intensity target kinds must not contain duplicates")
        return self


class CreateEnvironmentPrescriptionRevisionsCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    revisions: Annotated[tuple[EnvironmentPrescriptionRevisionDraft, ...], Field(min_length=1)]
    prepared_at: datetime
    reviewed_by: NonEmptyText
    review_authority_assignment_id: UUID | None = None
    applicability_rationale: NonEmptyText
    uncertainty: NonEmptyText

    @field_validator("prepared_at")
    @classmethod
    def require_aware_prepared_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("prepared_at must include a timezone")
        return value

    @field_validator("reviewed_by", "applicability_rationale", "uncertainty")
    @classmethod
    def require_meaningful_review_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("operator review metadata must not be blank")
        return normalized

    @model_validator(mode="after")
    def reject_duplicate_sources(self) -> CreateEnvironmentPrescriptionRevisionsCommand:
        source_ids = tuple(item.source_prescription_id for item in self.revisions)
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("revision drafts must have unique source prescriptions")
        return self


class EnvironmentPrescriptionRevisionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    revised_prescriptions: Annotated[tuple[SessionPrescription, ...], Field(min_length=1)]
    decision_record: DecisionRecord


class EnvironmentPrescriptionRevisionUseCaseError(RuntimeError):
    """Base error for reviewed environment prescription revisions."""


class EnvironmentPrescriptionRevisionNotFoundError(EnvironmentPrescriptionRevisionUseCaseError):
    pass


class EnvironmentPrescriptionRevisionConflictError(EnvironmentPrescriptionRevisionUseCaseError):
    pass


class EnvironmentPrescriptionRevisionValidationError(EnvironmentPrescriptionRevisionUseCaseError):
    pass


class PersistedEnvironmentPrescriptionRevisionService:
    """Append reviewed exercise-and-dose successors for a closed source week."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(
        self,
        source_weekly_plan_id: UUID,
        command: CreateEnvironmentPrescriptionRevisionsCommand,
    ) -> EnvironmentPrescriptionRevisionResult:
        try:
            result = self._build(source_weekly_plan_id, command)
            self.repository.add_decision_record(result.decision_record)
            self.session.flush()
            for prescription in result.revised_prescriptions:
                self.repository.add_session_prescription(prescription)
            self.session.commit()
            return result
        except EnvironmentPrescriptionRevisionUseCaseError:
            self.session.rollback()
            raise
        except (CurrentWeekProjectionError, DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise EnvironmentPrescriptionRevisionValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise EnvironmentPrescriptionRevisionConflictError(
                "environment prescription revision conflicts with persisted lineage"
            ) from error

    def _build(
        self,
        source_weekly_plan_id: UUID,
        command: CreateEnvironmentPrescriptionRevisionsCommand,
    ) -> EnvironmentPrescriptionRevisionResult:
        self._validate_review_authority(command)
        source_plan = self.repository.get_weekly_plan(source_weekly_plan_id)
        if source_plan is None:
            raise EnvironmentPrescriptionRevisionNotFoundError("source weekly plan does not exist")
        source_review = CurrentWeekProjector(self.session).project_week(source_plan).review
        if source_review.status != "environment_revision_required":
            raise EnvironmentPrescriptionRevisionValidationError(
                "source weekly plan is not ready for prescription revision: "
                f"{source_review.status}: {source_review.reason}"
            )
        confirmed_availability = self.repository.get_weekly_availability_by_source_plan(
            source_plan.id
        )
        if confirmed_availability is None:
            raise EnvironmentPrescriptionRevisionNotFoundError(
                "confirmed next-week availability does not exist"
            )
        if confirmed_availability.recorded_at > command.prepared_at:
            raise EnvironmentPrescriptionRevisionValidationError(
                "prescription revision cannot predate availability confirmation"
            )
        confirmed_environment_ids = {item.environment_id for item in confirmed_availability.windows}

        block = self.repository.get_block_plan(source_plan.block_plan_id)
        if block is None:
            raise EnvironmentPrescriptionRevisionNotFoundError("source block does not exist")
        policy = self.repository.get_weekly_scheduling_policy(source_plan.scheduling_policy_id)
        if policy is None:
            raise EnvironmentPrescriptionRevisionNotFoundError(
                "weekly scheduling policy does not exist"
            )
        if source_plan.scheduling_policy_review_id is None:
            raise EnvironmentPrescriptionRevisionValidationError(
                "source weekly plan predates governed scheduling policy review"
            )
        policy_review = self.repository.get_weekly_scheduling_policy_review(
            source_plan.scheduling_policy_review_id
        )
        current_policy_review = self.repository.get_current_weekly_scheduling_policy_review(
            policy.id
        )
        if policy_review is None:
            raise EnvironmentPrescriptionRevisionNotFoundError(
                "weekly scheduling policy review does not exist"
            )
        if (
            policy_review.weekly_scheduling_policy_id != policy.id
            or current_policy_review is None
            or current_policy_review.id != policy_review.id
            or policy_review.decision is not AssessmentReviewDecision.APPROVED
            or policy_review.reviewed_at > command.prepared_at
        ):
            raise EnvironmentPrescriptionRevisionValidationError(
                "prescription revision requires the source plan's current approved scheduling "
                "policy review"
            )

        template_ids = {
            *(item.session_template_id for item in source_plan.sessions),
            *(item.session_template_id for item in source_plan.issues),
        }
        if not template_ids:
            raise EnvironmentPrescriptionRevisionValidationError(
                "source weekly plan does not retain session-template lineage"
            )
        templates = []
        source_prescription_ids: set[UUID] = set()
        for template_id in sorted(template_ids, key=str):
            template = self.repository.get_session_template(template_id)
            if template is None:
                raise EnvironmentPrescriptionRevisionNotFoundError(
                    f"source session template {template_id} does not exist"
                )
            templates.append(template)
            source_prescription_ids.update(item.prescription_id for item in template.items)

        allocation_by_id = {item.id: item for item in block.allocations}
        decision_id = uuid4()
        revised_by_source: dict[UUID, SessionPrescription] = {}
        availability_source_ids: list[UUID] = []
        immediate_predecessor_ids: list[UUID] = []
        for draft in command.revisions:
            if draft.source_prescription_id not in source_prescription_ids:
                raise EnvironmentPrescriptionRevisionValidationError(
                    "revision source prescription does not belong to the source weekly plan"
                )
            source = self.repository.get_session_prescription(draft.source_prescription_id)
            if source is None:
                raise EnvironmentPrescriptionRevisionNotFoundError(
                    f"source prescription {draft.source_prescription_id} does not exist"
                )
            predecessor = self.repository.get_latest_session_prescription_revision(
                source.id,
                at_or_before=command.prepared_at,
            )
            if predecessor is None:
                raise EnvironmentPrescriptionRevisionNotFoundError(
                    f"prescription lineage {source.id} does not exist"
                )
            if predecessor.id != source.id and predecessor.planning_decision_record_id is not None:
                raise EnvironmentPrescriptionRevisionConflictError(
                    f"source prescription {source.id} already has an environment revision"
                )
            if predecessor.prescribed_at > command.prepared_at:
                raise EnvironmentPrescriptionRevisionValidationError(
                    "replacement prescription cannot predate its immediate predecessor"
                )

            allocation = allocation_by_id.get(source.resource_allocation_id)
            if allocation is None:
                raise EnvironmentPrescriptionRevisionValidationError(
                    "source prescription allocation does not belong to its block"
                )
            if (
                draft.planned_duration_minutes * allocation.sessions_per_week
                != allocation.allocated_weekly_minutes
            ):
                raise EnvironmentPrescriptionRevisionValidationError(
                    "replacement duration and frequency must preserve allocated weekly minutes"
                )
            resolution = self.repository.get_exercise_resolution(draft.exercise_resolution_id)
            if resolution is None:
                raise EnvironmentPrescriptionRevisionNotFoundError(
                    f"exercise resolution {draft.exercise_resolution_id} does not exist"
                )
            if resolution.id == predecessor.exercise_resolution_id:
                raise EnvironmentPrescriptionRevisionValidationError(
                    "environment revision requires a different exercise resolution"
                )
            if resolution.resolved_at > command.prepared_at:
                raise EnvironmentPrescriptionRevisionValidationError(
                    "replacement prescription cannot predate its exercise resolution"
                )
            if resolution.stimulus_requirement_id != allocation.stimulus_requirement_id:
                raise EnvironmentPrescriptionRevisionValidationError(
                    "replacement resolution targets another stimulus"
                )
            if resolution.status is ResolutionStatus.INFEASIBLE:
                raise EnvironmentPrescriptionRevisionValidationError(
                    "an infeasible resolution cannot produce a replacement prescription"
                )
            if (
                resolution.status is ResolutionStatus.PARTIAL
                and not policy.allow_partial_exercise_resolution
            ):
                raise EnvironmentPrescriptionRevisionValidationError(
                    "partial exercise re-resolution is disabled by weekly scheduling policy"
                )
            if resolution.selected_exercise_id is None:
                raise EnvironmentPrescriptionRevisionValidationError(
                    "replacement resolution has no selected exercise"
                )

            requirement = self.repository.get_stimulus_requirement(
                resolution.stimulus_requirement_id
            )
            if requirement is None:
                raise EnvironmentPrescriptionRevisionNotFoundError(
                    "replacement stimulus requirement does not exist"
                )
            availability_history = self.repository.list_equipment_availability(
                resolution.environment_id
            )
            availability_by_id = {item.id: item for item in availability_history}
            if not set(resolution.source_availability_ids).issubset(availability_by_id):
                raise EnvironmentPrescriptionRevisionValidationError(
                    "replacement resolution availability lineage is incomplete"
                )
            resolution_observation_ids = tuple(
                source_observation_id
                for item in resolution.source_availability_ids
                if (source_observation_id := availability_by_id[item].source_observation_id)
                is not None
            )
            availability_source_ids.extend(resolution.source_availability_ids)
            immediate_predecessor_ids.append(predecessor.id)
            revised_by_source[source.id] = SessionPrescription(
                athlete_id=source_plan.athlete_id,
                block_plan_id=block.id,
                resource_allocation_id=allocation.id,
                exercise_resolution_id=resolution.id,
                exercise_id=resolution.selected_exercise_id,
                adaptation_id=allocation.adaptation_id,
                reason_for_inclusion=draft.reason_for_inclusion,
                sets=draft.sets,
                repetitions_per_set=draft.repetitions_per_set,
                duration_seconds=draft.duration_seconds,
                intensity_targets=draft.intensity_targets,
                rest_seconds=draft.rest_seconds,
                progression_rule_reference=draft.progression_rule_reference,
                substitution_class=draft.substitution_class,
                planned_duration_minutes=draft.planned_duration_minutes,
                fatigue_cost=draft.fatigue_cost,
                source_observation_ids=self._ordered_union(
                    predecessor.source_observation_ids,
                    requirement.source_observation_ids,
                    resolution_observation_ids,
                    confirmed_availability.source_observation_ids,
                ),
                evidence_claim_ids=self._ordered_union(
                    predecessor.evidence_claim_ids,
                    requirement.evidence_claim_ids,
                ),
                prescribed_at=command.prepared_at,
                rule_version=draft.rule_version,
                supersedes_prescription_id=predecessor.id,
                planning_decision_record_id=decision_id,
            )

        self._validate_template_environments(
            templates,
            revised_by_source,
            command.prepared_at,
            confirmed_environment_ids,
        )
        revised = tuple(
            revised_by_source[item.source_prescription_id] for item in command.revisions
        )
        decision = DecisionRecord(
            id=decision_id,
            decision=(
                f"Append {len(revised)} environment-driven prescription revision(s) for source "
                f"weekly plan {source_plan.id}."
            ),
            reason=f"Reviewed by {command.reviewed_by}. {command.applicability_rationale}",
            alternatives_considered=(
                "Retain the existing prescription lineage and defer next-week roll-forward until "
                "the available environment can reproduce the planned exercise means.",
            ),
            evidence=self._decision_evidence(
                source_plan_id=source_plan.id,
                athlete_id=source_plan.athlete_id,
                block_id=block.id,
                scheduling_policy_id=policy.id,
                scheduling_policy_review_id=policy_review.id,
                weekly_availability_id=confirmed_availability.id,
                source_prescription_ids=tuple(
                    item.source_prescription_id for item in command.revisions
                ),
                immediate_predecessor_ids=tuple(immediate_predecessor_ids),
                revised_prescriptions=revised,
                availability_source_ids=tuple(availability_source_ids),
                observation_ids=self._ordered_union(
                    *(item.source_observation_ids for item in revised)
                ),
                evidence_claim_ids=self._ordered_union(
                    policy_review.evidence_claim_ids,
                    *(item.evidence_claim_ids for item in revised),
                ),
                review_authority_assignment_id=command.review_authority_assignment_id,
            ),
            uncertainty=command.uncertainty,
            decision_version="environment-prescription-revision@1.0.0",
            decided_on=command.prepared_at.date(),
        )
        return EnvironmentPrescriptionRevisionResult(
            revised_prescriptions=revised,
            decision_record=decision,
        )

    def _validate_review_authority(
        self, command: CreateEnvironmentPrescriptionRevisionsCommand
    ) -> None:
        assignment_id = command.review_authority_assignment_id
        if assignment_id is None:
            return
        assignment = self.repository.get_account_role_assignment(assignment_id)
        if assignment is None:
            raise EnvironmentPrescriptionRevisionValidationError(
                "review authority assignment does not exist"
            )
        current = self.repository.get_current_account_role_assignment(
            assignment.account_id, assignment.role
        )
        if (
            assignment.status is not AccountRoleStatus.ACTIVE
            or current is None
            or current.id != assignment.id
        ):
            raise EnvironmentPrescriptionRevisionValidationError(
                "review authority assignment is not currently active"
            )
        if command.reviewed_by != f"account:{assignment.account_id}":
            raise EnvironmentPrescriptionRevisionValidationError(
                "reviewed_by does not match the review authority account"
            )
        if command.prepared_at < assignment.assigned_at:
            raise EnvironmentPrescriptionRevisionValidationError(
                "prescription revision cannot predate the reviewer role assignment"
            )

    def _validate_template_environments(
        self,
        templates: Iterable[SessionTemplate],
        revised_by_source: dict[UUID, SessionPrescription],
        prepared_at: datetime,
        allowed_environment_ids: set[UUID],
    ) -> None:
        for template in templates:
            item_prescription_ids = tuple(item.prescription_id for item in template.items)
            environment_ids = set()
            for source_id in item_prescription_ids:
                prescription = revised_by_source.get(source_id)
                if prescription is None:
                    prescription = self.repository.get_latest_session_prescription_revision(
                        source_id,
                        at_or_before=prepared_at,
                    )
                if prescription is None:
                    raise EnvironmentPrescriptionRevisionNotFoundError(
                        f"template prescription {source_id} does not exist"
                    )
                resolution = self.repository.get_exercise_resolution(
                    prescription.exercise_resolution_id
                )
                if resolution is None:
                    raise EnvironmentPrescriptionRevisionNotFoundError(
                        f"exercise resolution {prescription.exercise_resolution_id} does not exist"
                    )
                environment_ids.add(resolution.environment_id)
            if len(environment_ids) != 1:
                raise EnvironmentPrescriptionRevisionValidationError(
                    "all prescriptions in an affected session template must resolve to one "
                    "environment"
                )
            if not environment_ids.issubset(allowed_environment_ids):
                raise EnvironmentPrescriptionRevisionValidationError(
                    "session-template environment is absent from confirmed next-week availability"
                )

    @staticmethod
    def _decision_evidence(
        *,
        source_plan_id: UUID,
        athlete_id: UUID,
        block_id: UUID,
        scheduling_policy_id: UUID,
        scheduling_policy_review_id: UUID,
        weekly_availability_id: UUID,
        source_prescription_ids: tuple[UUID, ...],
        immediate_predecessor_ids: tuple[UUID, ...],
        revised_prescriptions: tuple[SessionPrescription, ...],
        availability_source_ids: tuple[UUID, ...],
        observation_ids: tuple[UUID, ...],
        evidence_claim_ids: tuple[UUID, ...],
        review_authority_assignment_id: UUID | None,
    ) -> tuple[str, ...]:
        values = (
            f"athlete:{athlete_id}",
            f"weekly_plan:{source_plan_id}",
            f"block_plan:{block_id}",
            f"weekly_scheduling_policy:{scheduling_policy_id}",
            f"weekly_scheduling_policy_review:{scheduling_policy_review_id}",
            f"weekly_availability:{weekly_availability_id}",
            *(f"session_prescription:{item}" for item in source_prescription_ids),
            *(f"session_prescription:{item}" for item in immediate_predecessor_ids),
            *(
                f"resource_allocation:{item.resource_allocation_id}"
                for item in revised_prescriptions
            ),
            *(
                f"exercise_resolution:{item.exercise_resolution_id}"
                for item in revised_prescriptions
            ),
            *(f"exercise:{item.exercise_id}" for item in revised_prescriptions),
            *(f"adaptation:{item.adaptation_id}" for item in revised_prescriptions),
            *(f"equipment_availability:{item}" for item in availability_source_ids),
            *(f"observation:{item}" for item in observation_ids),
            *(f"evidence_claim:{item}" for item in evidence_claim_ids),
            *(f"session_prescription:{item.id}" for item in revised_prescriptions),
            *(
                (f"account_role_assignment:{review_authority_assignment_id}",)
                if review_authority_assignment_id is not None
                else ()
            ),
        )
        return tuple(dict.fromkeys(values))

    @staticmethod
    def _ordered_union(*groups: Iterable[UUID]) -> tuple[UUID, ...]:
        return tuple(dict.fromkeys(item for group in groups for item in group))
