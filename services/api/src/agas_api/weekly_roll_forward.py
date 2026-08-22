from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from agas_domain import (
    AvailabilityWindow,
    Confidence,
    CostLevel,
    Observation,
    ObservationSource,
    Provenance,
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

from agas_api.weekly_planning import WeeklyAvailabilityDraft


class RollForwardWeeklyPlanCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    availability: WeeklyAvailabilityDraft
    prepared_at: datetime
    reliability: Confidence
    provenance: Provenance

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
    availability_observation: Observation
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
            self.repository.add_observation(result.availability_observation)
            self.session.flush()
            for template in result.created_session_templates:
                self.repository.add_session_template(template)
            self.repository.add_weekly_availability(result.availability)
            self.session.flush()
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
        block = self.repository.get_block_plan(source_plan.block_plan_id)
        if block is None:
            raise WeeklyPlanRollForwardNotFoundError("weekly plan block does not exist")
        policy = self.repository.get_weekly_scheduling_policy(source_plan.scheduling_policy_id)
        if policy is None:
            raise WeeklyPlanRollForwardNotFoundError("weekly scheduling policy does not exist")
        if command.availability.week_start != source_plan.week_start + timedelta(days=7):
            raise WeeklyPlanRollForwardValidationError(
                "roll-forward availability must describe the immediately following week"
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

        availability_observation = Observation(
            athlete_id=source_plan.athlete_id,
            observed_at=command.prepared_at,
            observation_type="weekly_availability_confirmation",
            measurement={
                "week_start": command.availability.week_start.isoformat(),
                "windows": [
                    {
                        "environment_id": str(item.environment_id),
                        "starts_at": item.starts_at.isoformat(),
                        "ends_at": item.ends_at.isoformat(),
                    }
                    for item in command.availability.windows
                ],
            },
            source=ObservationSource.USER_REPORT,
            reliability=command.reliability,
            context={"source_weekly_plan_id": str(source_plan.id)},
            provenance=command.provenance,
        )
        availability = WeeklyAvailability(
            athlete_id=source_plan.athlete_id,
            week_start=command.availability.week_start,
            windows=tuple(
                AvailabilityWindow(
                    environment_id=item.environment_id,
                    starts_at=item.starts_at,
                    ends_at=item.ends_at,
                )
                for item in command.availability.windows
            ),
            source_observation_ids=self._ordered_union(
                command.availability.source_observation_ids,
                (availability_observation.id,),
            ),
            recorded_at=command.prepared_at,
            rule_version=command.availability.rule_version,
        )
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
                "rule_version": (f"weekly-roll-forward@1.0.0;scheduler={scheduled.rule_version}"),
            }
        )
        return WeeklyPlanRollForwardResult(
            prescriptions=tuple(prescriptions_by_id.values()),
            session_templates=tuple(effective_templates),
            created_session_templates=tuple(created_templates),
            availability_observation=availability_observation,
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
