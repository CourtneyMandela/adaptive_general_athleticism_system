from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from agas_domain import (
    Athlete,
    Confidence,
    CostLevel,
    Environment,
    EquipmentAvailability,
    Observation,
    ObservationSource,
    Provenance,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

NonEmptyText = Annotated[str, Field(min_length=1)]


class OnboardingEquipmentSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    equipment_id: UUID
    capabilities: dict[str, JsonValue] = Field(default_factory=dict)
    load_limits: dict[str, JsonValue] = Field(default_factory=dict)


class OnboardingEnvironmentDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: Annotated[str, Field(min_length=1, max_length=120)]
    floor_area_m2: float | None = Field(default=None, gt=0)
    noise_constraints: Annotated[str | None, Field(default=None, max_length=500)]
    max_noise_level: CostLevel = CostLevel.HIGH
    outdoor_access: bool = False
    equipment: tuple[OnboardingEquipmentSelection, ...] = ()

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("environment name must not be blank")
        return normalized

    @field_validator("noise_constraints")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        normalized = value.strip() if value is not None else None
        return normalized or None

    @model_validator(mode="after")
    def reject_duplicate_equipment(self) -> OnboardingEnvironmentDraft:
        equipment_ids = tuple(item.equipment_id for item in self.equipment)
        if len(set(equipment_ids)) != len(equipment_ids):
            raise ValueError("environment equipment selections must not contain duplicates")
        return self


class CreateAthleteOnboardingCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    display_name: Annotated[str, Field(min_length=1, max_length=120)]
    goals: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    preferred_activities: tuple[NonEmptyText, ...] = ()
    disliked_activities: tuple[NonEmptyText, ...] = ()
    environments: Annotated[tuple[OnboardingEnvironmentDraft, ...], Field(min_length=1)]
    reported_at: datetime
    reliability: Confidence
    provenance: Provenance

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("display name must not be blank")
        return normalized

    @field_validator("goals", "preferred_activities", "disliked_activities")
    @classmethod
    def normalize_text_lists(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(value.strip() for value in values)
        if any(not value for value in normalized):
            raise ValueError("profile entries must not be blank")
        if len({value.casefold() for value in normalized}) != len(normalized):
            raise ValueError("profile entries must not contain duplicates")
        return normalized

    @model_validator(mode="after")
    def validate_command(self) -> CreateAthleteOnboardingCommand:
        if self.reported_at.tzinfo is None or self.reported_at.utcoffset() is None:
            raise ValueError("reported_at must include a timezone")
        environment_names = tuple(item.name.casefold() for item in self.environments)
        if len(set(environment_names)) != len(environment_names):
            raise ValueError("environment names must not contain duplicates")
        overlap = {item.casefold() for item in self.preferred_activities} & {
            item.casefold() for item in self.disliked_activities
        }
        if overlap:
            raise ValueError("an activity cannot be both preferred and disliked")
        return self


class OnboardingEquipmentOption(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    equipment_id: UUID
    name: str
    category: str
    capabilities: dict[str, JsonValue]


class AthleteOnboardingResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    athlete: Athlete
    intake_observation: Observation
    environments: tuple[Environment, ...]
    equipment_availability: tuple[EquipmentAvailability, ...]


class AthleteOnboardingError(RuntimeError):
    """Base error for transactional profile and environment onboarding."""


class AthleteOnboardingNotFoundError(AthleteOnboardingError):
    pass


class AthleteOnboardingConflictError(AthleteOnboardingError):
    pass


class AthleteOnboardingValidationError(AthleteOnboardingError):
    pass


class PersistedAthleteOnboardingService:
    """Append one non-sensitive athlete profile and environment snapshot atomically."""

    rule_version = "profile-environment-onboarding@1.0.0"

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(self, command: CreateAthleteOnboardingCommand) -> AthleteOnboardingResult:
        try:
            result = self._build(command)
            self.repository.add_athlete(result.athlete)
            self.session.flush()
            self.repository.add_observation(result.intake_observation)
            self.session.flush()
            for environment in result.environments:
                self.repository.add_environment(environment)
            self.session.flush()
            for availability in result.equipment_availability:
                self.repository.add_equipment_availability(availability)
            self.session.commit()
            return result
        except AthleteOnboardingError:
            self.session.rollback()
            raise
        except (DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise AthleteOnboardingValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise AthleteOnboardingConflictError(
                "athlete onboarding conflicts with persisted profile state"
            ) from error

    def _build(self, command: CreateAthleteOnboardingCommand) -> AthleteOnboardingResult:
        selected_equipment_ids = tuple(
            selection.equipment_id
            for environment in command.environments
            for selection in environment.equipment
        )
        for equipment_id in dict.fromkeys(selected_equipment_ids):
            if self.repository.get_equipment(equipment_id) is None:
                raise AthleteOnboardingNotFoundError(
                    f"equipment selection {equipment_id} does not exist"
                )

        athlete = Athlete(
            created_at=command.reported_at,
            display_name=command.display_name,
            preferences={
                "preferred_activities": list(command.preferred_activities),
                "disliked_activities": list(command.disliked_activities),
            },
            goals=command.goals,
        )
        observation = Observation(
            created_at=command.reported_at,
            athlete_id=athlete.id,
            observed_at=command.reported_at,
            observation_type="onboarding_profile_environment_report",
            measurement={
                "display_name": command.display_name,
                "goals": list(command.goals),
                "preferred_activities": list(command.preferred_activities),
                "disliked_activities": list(command.disliked_activities),
                "environments": [
                    {
                        "name": draft.name,
                        "floor_area_m2": draft.floor_area_m2,
                        "noise_constraints": draft.noise_constraints,
                        "max_noise_level": draft.max_noise_level.value,
                        "outdoor_access": draft.outdoor_access,
                        "equipment": [
                            {
                                "equipment_id": str(selection.equipment_id),
                                "capabilities": selection.capabilities,
                                "load_limits": selection.load_limits,
                            }
                            for selection in draft.equipment
                        ],
                    }
                    for draft in command.environments
                ],
            },
            source=ObservationSource.USER_REPORT,
            reliability=command.reliability,
            context={"onboarding_rule_version": self.rule_version},
            provenance=command.provenance,
        )
        environments = tuple(
            Environment(
                created_at=command.reported_at,
                athlete_id=athlete.id,
                name=draft.name,
                space_constraints=(
                    {"floor_area_m2": draft.floor_area_m2}
                    if draft.floor_area_m2 is not None
                    else {}
                ),
                noise_constraints=draft.noise_constraints,
                max_noise_level=draft.max_noise_level,
                outdoor_access=draft.outdoor_access,
            )
            for draft in command.environments
        )
        availability = tuple(
            EquipmentAvailability(
                created_at=command.reported_at,
                environment_id=environment.id,
                equipment_id=selection.equipment_id,
                is_available=True,
                effective_from=command.reported_at,
                capabilities=selection.capabilities,
                load_limits=selection.load_limits,
                reason=f"confirmed by onboarding observation {observation.id}",
            )
            for environment, draft in zip(environments, command.environments, strict=True)
            for selection in draft.equipment
        )
        return AthleteOnboardingResult(
            athlete=athlete,
            intake_observation=observation,
            environments=environments,
            equipment_availability=availability,
        )


def list_onboarding_equipment(session: Session) -> tuple[OnboardingEquipmentOption, ...]:
    return tuple(
        OnboardingEquipmentOption(
            equipment_id=item.id,
            name=item.name,
            category=item.category,
            capabilities=item.capabilities,
        )
        for item in DomainRepository(session).list_equipment()
    )
