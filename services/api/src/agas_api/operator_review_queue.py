from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from agas_domain.persistence.models import WeeklyPlanRecord
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from agas_api.current_week import CurrentWeekProjectionError, CurrentWeekProjector


class EnvironmentReviewWindowProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    environment_id: UUID
    environment_name: str
    starts_at: datetime
    ends_at: datetime


class UnresolvedEnvironmentPrescriptionProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_prescription_id: UUID
    effective_prescription_id: UUID
    session_template_id: UUID
    session_template_name: str
    resource_allocation_id: UUID
    stimulus_requirement_id: UUID
    exercise_resolution_id: UUID
    resolution_environment_id: UUID
    resolution_environment_name: str
    exercise_id: UUID
    exercise_name: str
    adaptation_id: UUID
    adaptation_name: str
    reason: str


class EnvironmentReviewQueueItemProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_weekly_plan_id: UUID
    athlete_id: UUID
    athlete_display_name: str
    current_week_start: date
    next_week_start: date
    confirmed_weekly_availability_id: UUID
    availability_confirmed_at: datetime
    availability_source_observation_ids: tuple[UUID, ...]
    confirmed_windows: tuple[EnvironmentReviewWindowProjection, ...]
    unresolved_prescriptions: tuple[UnresolvedEnvironmentPrescriptionProjection, ...]


class EnvironmentReviewQueueProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    projected_at: datetime
    items: tuple[EnvironmentReviewQueueItemProjection, ...]


class OperatorReviewQueueProjectionError(RuntimeError):
    pass


class EnvironmentReviewQueueProjector:
    """Derive pending environment reviews without creating mutable task state."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)
        self.current_week_projector = CurrentWeekProjector(session)

    def project(self, projected_at: datetime | None = None) -> EnvironmentReviewQueueProjection:
        instant = projected_at or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("queue projection time must include a timezone")
        plan_ids = self.session.scalars(
            select(WeeklyPlanRecord.id).order_by(
                WeeklyPlanRecord.week_start,
                WeeklyPlanRecord.generated_at,
                WeeklyPlanRecord.id,
            )
        ).all()
        items = []
        try:
            for plan_id in plan_ids:
                plan = self.repository.get_weekly_plan(plan_id)
                if plan is None:
                    raise OperatorReviewQueueProjectionError(
                        "weekly plan disappeared during queue projection"
                    )
                review = self.current_week_projector.project_week(plan).review
                if review.status != "environment_revision_required":
                    continue
                availability = self.repository.get_weekly_availability_by_source_plan(plan.id)
                athlete = self.repository.get_athlete(plan.athlete_id)
                if availability is None or athlete is None:
                    raise OperatorReviewQueueProjectionError(
                        "environment review source metadata is incomplete"
                    )
                allowed_environment_ids = {window.environment_id for window in availability.windows}
                windows = []
                for window in availability.windows:
                    environment = self.repository.get_environment(window.environment_id)
                    if environment is None or environment.athlete_id != plan.athlete_id:
                        raise OperatorReviewQueueProjectionError(
                            "confirmed review environment metadata is incomplete"
                        )
                    windows.append(
                        EnvironmentReviewWindowProjection(
                            environment_id=environment.id,
                            environment_name=environment.name,
                            starts_at=window.starts_at,
                            ends_at=window.ends_at,
                        )
                    )
                unresolved = self._unresolved_prescriptions(
                    plan_id=plan.id,
                    athlete_id=plan.athlete_id,
                    allowed_environment_ids=allowed_environment_ids,
                )
                if len(unresolved) != review.unresolved_environment_prescriptions:
                    raise OperatorReviewQueueProjectionError(
                        "environment review count disagrees with current-week readiness"
                    )
                items.append(
                    EnvironmentReviewQueueItemProjection(
                        source_weekly_plan_id=plan.id,
                        athlete_id=athlete.id,
                        athlete_display_name=athlete.display_name,
                        current_week_start=plan.week_start,
                        next_week_start=availability.week_start,
                        confirmed_weekly_availability_id=availability.id,
                        availability_confirmed_at=availability.recorded_at,
                        availability_source_observation_ids=(availability.source_observation_ids),
                        confirmed_windows=tuple(windows),
                        unresolved_prescriptions=unresolved,
                    )
                )
        except (CurrentWeekProjectionError, DomainIntegrityError, ValueError) as error:
            raise OperatorReviewQueueProjectionError(str(error)) from error
        return EnvironmentReviewQueueProjection(
            projected_at=instant,
            items=tuple(
                sorted(
                    items,
                    key=lambda item: (
                        item.availability_confirmed_at,
                        item.next_week_start,
                        str(item.source_weekly_plan_id),
                    ),
                )
            ),
        )

    def _unresolved_prescriptions(
        self,
        *,
        plan_id: UUID,
        athlete_id: UUID,
        allowed_environment_ids: set[UUID],
    ) -> tuple[UnresolvedEnvironmentPrescriptionProjection, ...]:
        plan = self.repository.get_weekly_plan(plan_id)
        if plan is None:
            raise OperatorReviewQueueProjectionError("source weekly plan does not exist")
        template_ids = {
            *(item.session_template_id for item in plan.sessions),
            *(item.session_template_id for item in plan.issues),
        }
        unresolved = []
        seen: set[tuple[UUID, UUID]] = set()
        for template_id in sorted(template_ids, key=str):
            template = self.repository.get_session_template(template_id)
            if template is None or template.athlete_id != athlete_id:
                raise OperatorReviewQueueProjectionError(
                    "source session template metadata is incomplete"
                )
            for template_item in template.items:
                key = (template.id, template_item.prescription_id)
                if key in seen:
                    continue
                seen.add(key)
                prescription = self.repository.get_latest_session_prescription_revision(
                    template_item.prescription_id
                )
                if prescription is None:
                    raise OperatorReviewQueueProjectionError(
                        "source prescription lineage is incomplete"
                    )
                resolution = self.repository.get_exercise_resolution(
                    prescription.exercise_resolution_id
                )
                if resolution is None:
                    raise OperatorReviewQueueProjectionError(
                        "source exercise resolution does not exist"
                    )
                if resolution.environment_id in allowed_environment_ids:
                    continue
                exercise = self.repository.get_exercise(prescription.exercise_id)
                adaptation = self.repository.get_adaptation(prescription.adaptation_id)
                environment = self.repository.get_environment(resolution.environment_id)
                requirement = self.repository.get_stimulus_requirement(
                    resolution.stimulus_requirement_id
                )
                if any(item is None for item in (exercise, adaptation, environment, requirement)):
                    raise OperatorReviewQueueProjectionError(
                        "unresolved prescription metadata is incomplete"
                    )
                assert exercise is not None
                assert adaptation is not None
                assert environment is not None
                assert requirement is not None
                unresolved.append(
                    UnresolvedEnvironmentPrescriptionProjection(
                        source_prescription_id=template_item.prescription_id,
                        effective_prescription_id=prescription.id,
                        session_template_id=template.id,
                        session_template_name=template.name,
                        resource_allocation_id=prescription.resource_allocation_id,
                        stimulus_requirement_id=requirement.id,
                        exercise_resolution_id=resolution.id,
                        resolution_environment_id=environment.id,
                        resolution_environment_name=environment.name,
                        exercise_id=exercise.id,
                        exercise_name=exercise.name,
                        adaptation_id=adaptation.id,
                        adaptation_name=adaptation.name,
                        reason=(
                            "The effective exercise resolution environment is absent from the "
                            "athlete's confirmed next-week availability."
                        ),
                    )
                )
        return tuple(unresolved)
