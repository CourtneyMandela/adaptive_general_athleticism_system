from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from agas_domain import (
    AssessmentReviewDecision,
    CostLevel,
    SessionPrescription,
    SessionTemplate,
    SessionTemplateItem,
    WeeklyAvailability,
    WeeklyPlan,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import BlockPlanningError, WeeklyScheduler
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agas_api.current_week import CurrentWeekProjectionError, CurrentWeekProjector


class RollForwardWeeklyPlanCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    weekly_availability_id: UUID
    prepared_at: datetime

    @model_validator(mode="after")
    def validate_command(self) -> RollForwardWeeklyPlanCommand:
        if self.prepared_at.tzinfo is None or self.prepared_at.utcoffset() is None:
            raise ValueError("prepared_at must include a timezone")
        return self


class WeeklyPlanRollForwardResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prescriptions: Annotated[tuple[SessionPrescription, ...], Field(min_length=1)]
    session_templates: Annotated[tuple[SessionTemplate, ...], Field(min_length=1)]
    created_session_templates: tuple[SessionTemplate, ...]
    availability: WeeklyAvailability
    weekly_plan: WeeklyPlan


class WeeklyPlanRollForwardError(RuntimeError):
    """Base error for transactional weekly plan roll-forward."""


class WeeklyPlanRollForwardNotFoundError(WeeklyPlanRollForwardError):
    pass


class WeeklyPlanRollForwardConflictError(WeeklyPlanRollForwardError):
    pass


class WeeklyPlanRollForwardValidationError(WeeklyPlanRollForwardError):
    pass


class PersistedWeeklyPlanRollForwardService:
    """Append one consecutive week using immutable prescription revision lineage."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(
        self, weekly_plan_id: UUID, command: RollForwardWeeklyPlanCommand
    ) -> WeeklyPlanRollForwardResult:
        try:
            if self.repository.get_weekly_plan_successor(weekly_plan_id) is not None:
                raise WeeklyPlanRollForwardConflictError(
                    "weekly plan already has an automatic successor"
                )
            result = self._build(weekly_plan_id, command)
            for template in result.created_session_templates:
                self.repository.add_session_template(template)
            self.repository.add_weekly_plan(result.weekly_plan)
            self.session.commit()
            return result
        except WeeklyPlanRollForwardError:
            self.session.rollback()
            raise
        except (BlockPlanningError, DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise WeeklyPlanRollForwardValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise WeeklyPlanRollForwardConflictError(
                "weekly roll-forward conflicts with persisted planning lineage"
            ) from error

    def _build(
        self, weekly_plan_id: UUID, command: RollForwardWeeklyPlanCommand
    ) -> WeeklyPlanRollForwardResult:
        source_plan = self.repository.get_weekly_plan(weekly_plan_id)
        if source_plan is None:
            raise WeeklyPlanRollForwardNotFoundError("weekly plan does not exist")
        source_availability = self.repository.get_weekly_availability(
            source_plan.weekly_availability_id
        )
        if source_availability is None:
            raise WeeklyPlanRollForwardNotFoundError("source weekly availability does not exist")
        if (
            source_availability.athlete_id != source_plan.athlete_id
            or source_availability.week_start != source_plan.week_start
        ):
            raise WeeklyPlanRollForwardValidationError(
                "source weekly availability does not match its plan"
            )
        block = self.repository.get_block_plan(source_plan.block_plan_id)
        if block is None:
            raise WeeklyPlanRollForwardNotFoundError("weekly plan block does not exist")
        policy = self.repository.get_weekly_scheduling_policy(source_plan.scheduling_policy_id)
        if policy is None:
            raise WeeklyPlanRollForwardNotFoundError("weekly scheduling policy does not exist")
        if source_plan.scheduling_policy_review_id is None:
            raise WeeklyPlanRollForwardValidationError(
                "source weekly plan predates governed scheduling policy review"
            )
        policy_review = self.repository.get_weekly_scheduling_policy_review(
            source_plan.scheduling_policy_review_id
        )
        if policy_review is None:
            raise WeeklyPlanRollForwardNotFoundError(
                "weekly scheduling policy review does not exist"
            )
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
            raise WeeklyPlanRollForwardValidationError(
                "weekly roll-forward requires the source plan's current approved scheduling "
                "policy review"
            )
        try:
            source_review = CurrentWeekProjector(self.session).project_week(source_plan).review
        except CurrentWeekProjectionError as error:
            raise WeeklyPlanRollForwardValidationError(
                f"source weekly plan review is unavailable: {error}"
            ) from error
        if source_review.status != "ready_to_finalize_next_week":
            raise WeeklyPlanRollForwardValidationError(
                "source weekly plan is not ready for automatic advancement: "
                f"{source_review.status}: {source_review.reason}"
            )
        next_week_start = source_plan.week_start + timedelta(days=7)
        availability = self.repository.get_weekly_availability(command.weekly_availability_id)
        if availability is None:
            raise WeeklyPlanRollForwardNotFoundError(
                "confirmed next-week availability does not exist"
            )
        if (
            availability.source_weekly_plan_id != source_plan.id
            or availability.athlete_id != source_plan.athlete_id
            or availability.week_start != next_week_start
        ):
            raise WeeklyPlanRollForwardValidationError(
                "confirmed availability does not belong to this weekly advancement"
            )
        if availability.recorded_at > command.prepared_at:
            raise WeeklyPlanRollForwardValidationError(
                "weekly plan cannot predate its availability confirmation"
            )

        template_ids = {
            *(item.session_template_id for item in source_plan.sessions),
            *(item.session_template_id for item in source_plan.issues),
        }
        if not template_ids:
            raise WeeklyPlanRollForwardValidationError(
                "source weekly plan does not retain session-template lineage"
            )

        effective_templates = []
        created_templates = []
        prescriptions_by_id: dict[UUID, SessionPrescription] = {}
        for template_id in sorted(template_ids, key=str):
            source_template = self.repository.get_session_template(template_id)
            if source_template is None:
                raise WeeklyPlanRollForwardNotFoundError(
                    f"session template {template_id} does not exist"
                )
            effective_prescriptions = []
            for item in source_template.items:
                prescription = self.repository.get_latest_session_prescription_revision(
                    item.prescription_id,
                    at_or_before=command.prepared_at,
                )
                if prescription is None:
                    raise WeeklyPlanRollForwardNotFoundError(
                        f"session prescription {item.prescription_id} does not exist"
                    )
                effective_prescriptions.append(prescription)
                prescriptions_by_id[prescription.id] = prescription

            effective_template = self._carry_template(
                source_template, tuple(effective_prescriptions), command.prepared_at
            )
            effective_templates.append(effective_template)
            if effective_template.id != source_template.id:
                created_templates.append(effective_template)

        resolutions = []
        for prescription in prescriptions_by_id.values():
            resolution = self.repository.get_exercise_resolution(
                prescription.exercise_resolution_id
            )
            if resolution is None:
                raise WeeklyPlanRollForwardNotFoundError(
                    f"exercise resolution {prescription.exercise_resolution_id} does not exist"
                )
            resolutions.append(resolution)
        allowed_environment_ids = {item.environment_id for item in availability.windows}
        if any(
            resolution.environment_id not in allowed_environment_ids for resolution in resolutions
        ):
            raise WeeklyPlanRollForwardValidationError(
                "effective prescription environments are not represented in confirmed availability"
            )

        scheduled = WeeklyScheduler().schedule(
            block=block,
            availability=availability,
            prescriptions=prescriptions_by_id.values(),
            session_templates=effective_templates,
            resolutions=resolutions,
            policy=policy,
            generated_at=command.prepared_at,
        )
        plan = scheduled.model_copy(
            update={
                "previous_weekly_plan_id": source_plan.id,
                "scheduling_policy_review_id": policy_review.id,
                "rule_version": (f"weekly-roll-forward@2.0.0;scheduler={scheduled.rule_version}"),
            }
        )
        return WeeklyPlanRollForwardResult(
            prescriptions=tuple(prescriptions_by_id.values()),
            session_templates=tuple(effective_templates),
            created_session_templates=tuple(created_templates),
            availability=availability,
            weekly_plan=plan,
        )

    @staticmethod
    def _carry_template(
        source: SessionTemplate,
        prescriptions: tuple[SessionPrescription, ...],
        prepared_at: datetime,
    ) -> SessionTemplate:
        source_ids = tuple(item.prescription_id for item in source.items)
        effective_ids = tuple(item.id for item in prescriptions)
        if effective_ids == source_ids:
            return source
        if len(prescriptions) != len(source.items):
            raise ValueError("template prescriptions do not match source structure")
        fatigue_rank = {CostLevel.LOW: 0, CostLevel.MODERATE: 1, CostLevel.HIGH: 2}
        return SessionTemplate(
            athlete_id=source.athlete_id,
            block_plan_id=source.block_plan_id,
            previous_template_id=source.id,
            name=source.name,
            items=tuple(
                SessionTemplateItem(
                    prescription_id=prescription.id,
                    order_index=source_item.order_index,
                    section=source_item.section,
                )
                for source_item, prescription in zip(source.items, prescriptions, strict=True)
            ),
            sessions_per_week=source.sessions_per_week,
            planned_duration_minutes=sum(item.planned_duration_minutes for item in prescriptions),
            fatigue_cost=max(
                (item.fatigue_cost for item in prescriptions),
                key=lambda item: fatigue_rank[item],
            ),
            source_observation_ids=PersistedWeeklyPlanRollForwardService._ordered_union(
                source.source_observation_ids,
                *(item.source_observation_ids for item in prescriptions),
            ),
            evidence_claim_ids=PersistedWeeklyPlanRollForwardService._ordered_union(
                source.evidence_claim_ids,
                *(item.evidence_claim_ids for item in prescriptions),
            ),
            created_for_block_at=prepared_at,
            rule_version="session-template-roll-forward@1.0.0",
        )

    @staticmethod
    def _ordered_union(*groups: Iterable[UUID]) -> tuple[UUID, ...]:
        return tuple(dict.fromkeys(item for group in groups for item in group))
