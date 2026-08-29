from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from agas_domain import (
    AvailabilityWindow,
    Confidence,
    Observation,
    ObservationSource,
    Provenance,
    WeeklyAvailability,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agas_api.current_week import CurrentWeekProjectionError, CurrentWeekProjector
from agas_api.weekly_planning import AvailabilityWindowDraft


class ConfirmWeeklyAvailabilityCommand(BaseModel):
    """Athlete-authored next-week availability with server-owned lineage metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    windows: tuple[AvailabilityWindowDraft, ...] = ()
    confirmed_at: datetime
    reliability: Confidence
    provenance: Provenance

    @field_validator("confirmed_at")
    @classmethod
    def require_aware_confirmation_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("confirmed_at must include a timezone")
        return value


class WeeklyAvailabilityConfirmationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    availability_observation: Observation
    availability: WeeklyAvailability


class WeeklyAvailabilityConfirmationError(RuntimeError):
    """Base error for persisted next-week availability confirmation."""


class WeeklyAvailabilityConfirmationNotFoundError(WeeklyAvailabilityConfirmationError):
    pass


class WeeklyAvailabilityConfirmationConflictError(WeeklyAvailabilityConfirmationError):
    pass


class WeeklyAvailabilityConfirmationValidationError(WeeklyAvailabilityConfirmationError):
    pass


class PersistedWeeklyAvailabilityConfirmationService:
    """Append observed next-week availability without creating planning state."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(
        self,
        source_weekly_plan_id: UUID,
        command: ConfirmWeeklyAvailabilityCommand,
    ) -> WeeklyAvailabilityConfirmationResult:
        try:
            if (
                self.repository.get_weekly_availability_by_source_plan(source_weekly_plan_id)
                is not None
            ):
                raise WeeklyAvailabilityConfirmationConflictError(
                    "next-week availability is already confirmed for this weekly plan"
                )
            if self.repository.get_weekly_plan_successor(source_weekly_plan_id) is not None:
                raise WeeklyAvailabilityConfirmationConflictError(
                    "weekly plan already has a successor"
                )
            result = self._build(source_weekly_plan_id, command)
            self.repository.add_observation(result.availability_observation)
            self.session.flush()
            self.repository.add_weekly_availability(result.availability)
            self.session.commit()
            return result
        except WeeklyAvailabilityConfirmationError:
            self.session.rollback()
            raise
        except (CurrentWeekProjectionError, DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise WeeklyAvailabilityConfirmationValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise WeeklyAvailabilityConfirmationConflictError(
                "availability confirmation conflicts with persisted weekly lineage"
            ) from error

    def _build(
        self,
        source_weekly_plan_id: UUID,
        command: ConfirmWeeklyAvailabilityCommand,
    ) -> WeeklyAvailabilityConfirmationResult:
        source_plan = self.repository.get_weekly_plan(source_weekly_plan_id)
        if source_plan is None:
            raise WeeklyAvailabilityConfirmationNotFoundError("source weekly plan does not exist")
        source_availability = self.repository.get_weekly_availability(
            source_plan.weekly_availability_id
        )
        if source_availability is None:
            raise WeeklyAvailabilityConfirmationNotFoundError(
                "source weekly availability does not exist"
            )
        source_projection = CurrentWeekProjector(self.session).project_week(source_plan)
        review = source_projection.review
        if review.status != "ready_to_prepare_next_week":
            raise WeeklyAvailabilityConfirmationValidationError(
                "source weekly plan cannot accept availability confirmation: "
                f"{review.status}: {review.reason}"
            )
        closure_times = [source_plan.generated_at, source_availability.recorded_at]
        for planned_session in source_projection.sessions:
            if planned_session.pre_session_safety is not None:
                closure_times.append(planned_session.pre_session_safety.decided_at)
            if planned_session.execution is not None:
                closure_times.append(planned_session.execution.logged_at)
            closure_times.extend(
                item.progression.decided_at
                for item in planned_session.prescriptions
                if item.progression is not None
            )
            execution = self.repository.get_session_execution_by_planned_session(
                planned_session.planned_session_id
            )
            if execution is not None:
                closure_times.extend(
                    item.decided_at
                    for item in self.repository.list_post_session_safety_decisions(execution.id)
                )
        if command.confirmed_at < max(closure_times):
            raise WeeklyAvailabilityConfirmationValidationError(
                "availability confirmation cannot predate source-week closure records"
            )

        next_week_start = source_plan.week_start + timedelta(days=7)
        observation = Observation(
            athlete_id=source_plan.athlete_id,
            observed_at=command.confirmed_at,
            observation_type="weekly_availability_confirmation",
            measurement={
                "week_start": next_week_start.isoformat(),
                "windows": [
                    {
                        "environment_id": str(item.environment_id),
                        "starts_at": item.starts_at.isoformat(),
                        "ends_at": item.ends_at.isoformat(),
                    }
                    for item in command.windows
                ],
            },
            source=ObservationSource.USER_REPORT,
            reliability=command.reliability,
            context={
                "source_weekly_plan_id": str(source_plan.id),
                "source_weekly_availability_id": str(source_availability.id),
            },
            provenance=command.provenance,
        )
        availability = WeeklyAvailability(
            athlete_id=source_plan.athlete_id,
            source_weekly_plan_id=source_plan.id,
            week_start=next_week_start,
            windows=tuple(
                AvailabilityWindow(
                    environment_id=item.environment_id,
                    starts_at=item.starts_at,
                    ends_at=item.ends_at,
                )
                for item in command.windows
            ),
            source_observation_ids=(observation.id,),
            recorded_at=command.confirmed_at,
            rule_version="weekly-availability-confirmation@1.0.0",
        )
        return WeeklyAvailabilityConfirmationResult(
            availability_observation=observation,
            availability=availability,
        )
