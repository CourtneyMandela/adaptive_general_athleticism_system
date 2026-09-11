from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from agas_domain import (
    Confidence,
    CostLevel,
    EquipmentAvailability,
    Observation,
    ObservationSource,
    Provenance,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import EnvironmentSnapshotBuilder, ResolutionError
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

NonEmptyText = Annotated[str, Field(min_length=1)]
EquipmentState = Literal["available", "unavailable", "unknown"]


class EquipmentStateChange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    equipment_id: UUID
    is_available: bool
    effective_from: datetime
    effective_until: datetime | None = None
    capabilities: dict[str, JsonValue] = Field(default_factory=dict)
    load_limits: dict[str, JsonValue] = Field(default_factory=dict)
    reason: Annotated[str | None, Field(default=None, max_length=500)]

    @field_validator("effective_from", "effective_until")
    @classmethod
    def require_aware_times(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("equipment state times must include a timezone")
        return value

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        normalized = value.strip() if value is not None else None
        return normalized or None

    @model_validator(mode="after")
    def validate_window(self) -> EquipmentStateChange:
        if self.effective_until is not None and self.effective_until <= self.effective_from:
            raise ValueError("equipment state end must be later than its start")
        return self


class RecordEquipmentStateCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    changes: Annotated[tuple[EquipmentStateChange, ...], Field(min_length=1)]
    reported_at: datetime
    reliability: Confidence
    provenance: Provenance
    report_reason: Annotated[str, Field(min_length=1, max_length=500)]

    @field_validator("reported_at")
    @classmethod
    def require_aware_report_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reported_at must include a timezone")
        return value

    @field_validator("report_reason")
    @classmethod
    def normalize_report_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("report_reason must not be blank")
        return normalized

    @model_validator(mode="after")
    def reject_duplicate_equipment(self) -> RecordEquipmentStateCommand:
        equipment_ids = tuple(item.equipment_id for item in self.changes)
        if len(set(equipment_ids)) != len(equipment_ids):
            raise ValueError("equipment changes must not contain duplicate equipment")
        return self


class EquipmentStateReportResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observation: Observation
    availability_events: Annotated[tuple[EquipmentAvailability, ...], Field(min_length=1)]


class RecordEnvironmentFloorAreaCommand(BaseModel):
    """Append one factual usable-floor-area report without rewriting onboarding history."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    floor_area_m2: float = Field(gt=0, le=100000)
    effective_from: datetime
    reported_at: datetime
    reliability: Confidence
    provenance: Provenance
    report_reason: Annotated[str, Field(min_length=1, max_length=500)]

    @field_validator("effective_from", "reported_at")
    @classmethod
    def require_aware_times(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("environment floor-area times must include a timezone")
        return value

    @field_validator("report_reason")
    @classmethod
    def normalize_report_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("report_reason must not be blank")
        return normalized


class EnvironmentFloorAreaReportResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observation: Observation


class EnvironmentEquipmentProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    equipment_id: UUID
    name: str
    category: str
    state: EquipmentState
    availability_event_id: UUID | None
    source_observation_id: UUID | None
    effective_from: datetime | None
    effective_until: datetime | None
    capabilities: dict[str, JsonValue]
    load_limits: dict[str, JsonValue]
    reason: str | None


class EnvironmentStateProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    environment_id: UUID
    name: str
    floor_area_m2: float | None
    floor_area_source_observation_id: UUID | None = None
    floor_area_effective_from: datetime | None = None
    noise_constraints: str | None
    max_noise_level: CostLevel
    outdoor_access: bool
    equipment: tuple[EnvironmentEquipmentProjection, ...]


class AthleteEnvironmentProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    athlete_id: UUID
    as_of: datetime
    environments: tuple[EnvironmentStateProjection, ...]
    projection_version: str = "athlete-environment-state@1.1.0"


class EnvironmentManagementError(RuntimeError):
    """Base error for athlete-owned environment state reporting."""


class EnvironmentManagementNotFoundError(EnvironmentManagementError):
    pass


class EnvironmentManagementConflictError(EnvironmentManagementError):
    pass


class EnvironmentManagementValidationError(EnvironmentManagementError):
    pass


class PersistedEquipmentStateService:
    rule_version = "equipment-state-reporting@1.0.0"

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(
        self,
        athlete_id: UUID,
        environment_id: UUID,
        command: RecordEquipmentStateCommand,
    ) -> EquipmentStateReportResult:
        try:
            result = self._build(athlete_id, environment_id, command)
            self.repository.add_observation(result.observation)
            self.session.flush()
            for event in result.availability_events:
                self.repository.add_equipment_availability(event)
            self.session.commit()
            return result
        except EnvironmentManagementError:
            self.session.rollback()
            raise
        except (DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise EnvironmentManagementValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise EnvironmentManagementConflictError(
                "equipment report conflicts with persisted environment history"
            ) from error

    def _build(
        self,
        athlete_id: UUID,
        environment_id: UUID,
        command: RecordEquipmentStateCommand,
    ) -> EquipmentStateReportResult:
        athlete = self.repository.get_athlete(athlete_id)
        if athlete is None:
            raise EnvironmentManagementNotFoundError("athlete does not exist")
        environment = self.repository.get_environment(environment_id)
        if environment is None or environment.athlete_id != athlete_id:
            raise EnvironmentManagementNotFoundError("environment does not exist")
        for change in command.changes:
            if self.repository.get_equipment(change.equipment_id) is None:
                raise EnvironmentManagementNotFoundError(
                    f"equipment {change.equipment_id} does not exist"
                )
            if change.effective_from < environment.created_at:
                raise EnvironmentManagementValidationError(
                    "equipment state cannot predate its environment"
                )

        observation = Observation(
            created_at=command.reported_at,
            athlete_id=athlete_id,
            observed_at=command.reported_at,
            observation_type="equipment_environment_state_report",
            measurement={
                "environment_id": str(environment.id),
                "environment_name": environment.name,
                "report_reason": command.report_reason,
                "changes": [item.model_dump(mode="json") for item in command.changes],
            },
            source=ObservationSource.USER_REPORT,
            reliability=command.reliability,
            context={"equipment_state_rule_version": self.rule_version},
            provenance=command.provenance,
        )
        events = tuple(
            EquipmentAvailability(
                created_at=command.reported_at,
                environment_id=environment.id,
                equipment_id=change.equipment_id,
                source_observation_id=observation.id,
                is_available=change.is_available,
                effective_from=change.effective_from,
                effective_until=change.effective_until,
                capabilities=change.capabilities,
                load_limits=change.load_limits,
                reason=change.reason or command.report_reason,
            )
            for change in command.changes
        )
        return EquipmentStateReportResult(observation=observation, availability_events=events)


class PersistedEnvironmentFloorAreaService:
    rule_version = "environment-floor-area-report@1.0.0"

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(
        self,
        athlete_id: UUID,
        environment_id: UUID,
        command: RecordEnvironmentFloorAreaCommand,
    ) -> EnvironmentFloorAreaReportResult:
        athlete = self.repository.get_athlete(athlete_id)
        environment = self.repository.get_environment(environment_id)
        if athlete is None:
            raise EnvironmentManagementNotFoundError("athlete does not exist")
        if environment is None or environment.athlete_id != athlete_id:
            raise EnvironmentManagementNotFoundError("environment does not exist")
        if command.effective_from < environment.created_at:
            raise EnvironmentManagementValidationError(
                "floor-area state cannot predate its environment"
            )
        observation = Observation(
            created_at=command.reported_at,
            athlete_id=athlete_id,
            observed_at=command.reported_at,
            observation_type="environment_floor_area_report",
            measurement={
                "environment_id": str(environment.id),
                "floor_area_m2": command.floor_area_m2,
                "effective_from": command.effective_from.isoformat(),
                "report_reason": command.report_reason,
            },
            source=ObservationSource.USER_REPORT,
            reliability=command.reliability,
            context={"environment_floor_area_rule_version": self.rule_version},
            provenance=command.provenance,
        )
        try:
            self.repository.add_observation(observation)
            self.session.commit()
        except DomainIntegrityError as error:
            self.session.rollback()
            raise EnvironmentManagementValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise EnvironmentManagementConflictError(
                "floor-area report conflicts with persisted environment history"
            ) from error
        return EnvironmentFloorAreaReportResult(observation=observation)


def resolve_environment_floor_area(
    repository: DomainRepository,
    environment_id: UUID,
    athlete_id: UUID,
    as_of: datetime,
    baseline: float | None,
) -> tuple[float | None, UUID | None, datetime | None]:
    """Resolve the latest effective typed observation, falling back to onboarding state."""

    current: tuple[datetime, datetime, str, float, UUID] | None = None
    for observation in repository.list_observations(
        athlete_id, observation_type="environment_floor_area_report"
    ):
        measurement = observation.measurement
        if not isinstance(measurement, dict):
            raise EnvironmentManagementValidationError(
                f"floor-area observation {observation.id} has invalid measurement content"
            )
        reported_environment_id = measurement.get("environment_id")
        if not isinstance(reported_environment_id, str):
            raise EnvironmentManagementValidationError(
                f"floor-area observation {observation.id} has no environment identity"
            )
        if reported_environment_id != str(environment_id):
            continue
        raw_area = measurement.get("floor_area_m2")
        raw_effective = measurement.get("effective_from")
        if (
            isinstance(raw_area, bool)
            or not isinstance(raw_area, int | float)
            or raw_area <= 0
            or not isinstance(raw_effective, str)
        ):
            raise EnvironmentManagementValidationError(
                f"floor-area observation {observation.id} has invalid area or effective time"
            )
        try:
            effective = datetime.fromisoformat(raw_effective.replace("Z", "+00:00"))
        except ValueError:
            raise EnvironmentManagementValidationError(
                f"floor-area observation {observation.id} has an invalid effective time"
            ) from None
        if effective.tzinfo is None:
            raise EnvironmentManagementValidationError(
                f"floor-area observation {observation.id} has a timezone-naive effective time"
            )
        if effective > as_of:
            continue
        candidate = (
            effective,
            observation.observed_at,
            str(observation.id),
            float(raw_area),
            observation.id,
        )
        if current is None or candidate[:3] > current[:3]:
            current = candidate
    return (baseline, None, None) if current is None else (current[3], current[4], current[0])


def get_athlete_environment_projection(
    session: Session, athlete_id: UUID, as_of: datetime | None = None
) -> AthleteEnvironmentProjection:
    repository = DomainRepository(session)
    if repository.get_athlete(athlete_id) is None:
        raise EnvironmentManagementNotFoundError("athlete does not exist")
    instant = as_of or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("environment projection time must include a timezone")

    equipment = repository.list_equipment()
    builder = EnvironmentSnapshotBuilder()
    environment_projections = []
    for environment in repository.list_environments(athlete_id):
        history = repository.list_equipment_availability(environment.id)
        try:
            current = builder.current_availability(environment, equipment, history, instant)
        except ResolutionError as error:
            raise EnvironmentManagementValidationError(str(error)) from error
        items = []
        for item in equipment:
            event = current.get(item.id)
            items.append(
                EnvironmentEquipmentProjection(
                    equipment_id=item.id,
                    name=item.name,
                    category=item.category,
                    state=(
                        "unknown"
                        if event is None
                        else "available"
                        if event.is_available
                        else "unavailable"
                    ),
                    availability_event_id=event.id if event else None,
                    source_observation_id=event.source_observation_id if event else None,
                    effective_from=event.effective_from if event else None,
                    effective_until=event.effective_until if event else None,
                    capabilities=(
                        {**item.capabilities, **event.capabilities}
                        if event and event.is_available
                        else item.capabilities
                    ),
                    load_limits=event.load_limits if event else {},
                    reason=event.reason if event else None,
                )
            )
        floor_area = environment.space_constraints.get("floor_area_m2")
        baseline_floor_area = (
            float(floor_area)
            if isinstance(floor_area, int | float) and not isinstance(floor_area, bool)
            else None
        )
        current_floor_area, floor_source_id, floor_effective_from = resolve_environment_floor_area(
            repository,
            environment.id,
            athlete_id,
            instant,
            baseline_floor_area,
        )
        environment_projections.append(
            EnvironmentStateProjection(
                environment_id=environment.id,
                name=environment.name,
                floor_area_m2=current_floor_area,
                floor_area_source_observation_id=floor_source_id,
                floor_area_effective_from=floor_effective_from,
                noise_constraints=environment.noise_constraints,
                max_noise_level=environment.max_noise_level,
                outdoor_access=environment.outdoor_access,
                equipment=tuple(items),
            )
        )
    return AthleteEnvironmentProjection(
        athlete_id=athlete_id,
        as_of=instant,
        environments=tuple(environment_projections),
    )
