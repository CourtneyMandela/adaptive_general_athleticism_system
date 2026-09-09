from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Literal
from uuid import UUID

from agas_domain import Confidence, Observation, ObservationSource, Provenance
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agas_api.identity import AuthenticatedPrincipal

DATE_OF_BIRTH_OBSERVATION_TYPE = "athlete_date_of_birth_report"
DATE_OF_BIRTH_RULE_VERSION = "athlete-date-of-birth-report@1.0.0"


class DateOfBirthReportCommand(BaseModel):
    """An attested current report; corrections append rather than mutate identity history."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    report_id: UUID
    date_of_birth: date
    reported_at: datetime
    date_of_birth_confirmed: Literal[True]

    @field_validator("reported_at")
    @classmethod
    def require_aware_reported_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reported_at must include a timezone")
        return value


class AthleteDemographicsProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    athlete_id: UUID
    as_of: datetime
    date_of_birth: date | None
    age_years: int | None
    source_observation_id: UUID | None
    source_kind: Literal["reported_observation", "legacy_profile", "unknown"]
    report_count: int
    message: str
    projection_version: str = "athlete-demographics-projection@1.0.0"


class DateOfBirthReportResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: UUID
    demographics: AthleteDemographicsProjection
    created: bool
    rule_version: str = DATE_OF_BIRTH_RULE_VERSION


class AthleteDemographicsNotFoundError(LookupError):
    pass


class AthleteDemographicsConflictError(RuntimeError):
    pass


class AthleteDemographicsValidationError(ValueError):
    pass


class FloorAgeApplicability(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["applicable", "not_applicable", "unknown"]
    age_years: int | None
    reason: str


def age_on(date_of_birth: date, on_date: date) -> int:
    return (
        on_date.year
        - date_of_birth.year
        - ((on_date.month, on_date.day) < (date_of_birth.month, date_of_birth.day))
    )


def project_athlete_demographics(
    session: Session, athlete_id: UUID, as_of: datetime | None = None
) -> AthleteDemographicsProjection:
    repository = DomainRepository(session)
    athlete = repository.get_athlete(athlete_id)
    if athlete is None:
        raise AthleteDemographicsNotFoundError("athlete does not exist")
    instant = as_of or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise AthleteDemographicsValidationError("demographics time must include a timezone")

    reports = repository.list_observations(
        athlete_id, observation_type=DATE_OF_BIRTH_OBSERVATION_TYPE
    )
    effective_reports = tuple(report for report in reports if report.observed_at <= instant)
    if effective_reports:
        current = effective_reports[0]
        reported_date = _date_of_birth_from_observation(current)
        return AthleteDemographicsProjection(
            athlete_id=athlete.id,
            as_of=instant,
            date_of_birth=reported_date,
            age_years=age_on(reported_date, instant.date()),
            source_observation_id=current.id,
            source_kind="reported_observation",
            report_count=len(effective_reports),
            message=(
                "Current age is derived from the latest append-only date-of-birth report. "
                "Earlier reports remain in history."
            ),
        )
    if athlete.date_of_birth is not None and athlete.created_at <= instant:
        return AthleteDemographicsProjection(
            athlete_id=athlete.id,
            as_of=instant,
            date_of_birth=athlete.date_of_birth,
            age_years=age_on(athlete.date_of_birth, instant.date()),
            source_observation_id=None,
            source_kind="legacy_profile",
            report_count=0,
            message=(
                "Current age uses the legacy profile value. Submit a report to establish "
                "append-only provenance for future planning."
            ),
        )
    return AthleteDemographicsProjection(
        athlete_id=athlete.id,
        as_of=instant,
        date_of_birth=None,
        age_years=None,
        source_observation_id=None,
        source_kind="unknown",
        report_count=0,
        message=(
            "Date of birth has not been reported. Age-bounded planning authorities must fail "
            "closed until it is known."
        ),
    )


def evaluate_floor_age_applicability(
    minimum_age_years: int | None,
    maximum_age_years: int | None,
    demographics: AthleteDemographicsProjection,
) -> FloorAgeApplicability:
    if minimum_age_years is None and maximum_age_years is None:
        return FloorAgeApplicability(
            status="applicable",
            age_years=demographics.age_years,
            reason="This floor has no structured age restriction.",
        )
    if demographics.age_years is None:
        return FloorAgeApplicability(
            status="unknown",
            age_years=None,
            reason="The athlete's age is unknown for an age-bounded competency floor.",
        )
    if minimum_age_years is not None and demographics.age_years < minimum_age_years:
        return FloorAgeApplicability(
            status="not_applicable",
            age_years=demographics.age_years,
            reason=f"The athlete is younger than the floor's minimum age of {minimum_age_years}.",
        )
    if maximum_age_years is not None and demographics.age_years > maximum_age_years:
        return FloorAgeApplicability(
            status="not_applicable",
            age_years=demographics.age_years,
            reason=f"The athlete is older than the floor's maximum age of {maximum_age_years}.",
        )
    return FloorAgeApplicability(
        status="applicable",
        age_years=demographics.age_years,
        reason="The athlete is within the floor's structured age range.",
    )


class PersistedDateOfBirthReportService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(
        self,
        athlete_id: UUID,
        command: DateOfBirthReportCommand,
        principal: AuthenticatedPrincipal,
        *,
        recorded_at: datetime | None = None,
    ) -> DateOfBirthReportResult:
        instant = recorded_at or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise AthleteDemographicsValidationError("recording time must include a timezone")
        if self.repository.get_athlete(athlete_id) is None:
            raise AthleteDemographicsNotFoundError("athlete does not exist")

        observation = self._observation(athlete_id, command, principal)
        existing = self.repository.get_observation(command.report_id)
        if existing is not None:
            if existing != observation:
                raise AthleteDemographicsConflictError(
                    "date-of-birth report identity is already occupied by different content"
                )
            return DateOfBirthReportResult(
                observation_id=existing.id,
                demographics=project_athlete_demographics(self.session, athlete_id, instant),
                created=False,
            )

        if command.reported_at > instant + timedelta(minutes=5):
            raise AthleteDemographicsValidationError("reported_at cannot be in the future")
        if command.reported_at < instant - timedelta(minutes=15):
            raise AthleteDemographicsValidationError(
                "a new date-of-birth report must be recorded as current input"
            )
        reports = self.repository.list_observations(
            athlete_id, observation_type=DATE_OF_BIRTH_OBSERVATION_TYPE
        )
        if reports and command.reported_at <= reports[0].observed_at:
            raise AthleteDemographicsConflictError(
                "a correction must postdate the current date-of-birth report"
            )
        reported_age = age_on(command.date_of_birth, command.reported_at.date())
        if reported_age < 0:
            raise AthleteDemographicsValidationError("date_of_birth cannot be in the future")
        if reported_age > 130:
            raise AthleteDemographicsValidationError("date_of_birth is outside supported bounds")

        try:
            self.repository.add_observation(observation)
            self.session.commit()
        except DomainIntegrityError as error:
            self.session.rollback()
            raise AthleteDemographicsValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise AthleteDemographicsConflictError(
                "date-of-birth report conflicts with persisted athlete history"
            ) from error
        except Exception:
            self.session.rollback()
            raise
        return DateOfBirthReportResult(
            observation_id=observation.id,
            demographics=project_athlete_demographics(self.session, athlete_id, instant),
            created=True,
        )

    @staticmethod
    def _observation(
        athlete_id: UUID,
        command: DateOfBirthReportCommand,
        principal: AuthenticatedPrincipal,
    ) -> Observation:
        return Observation(
            id=command.report_id,
            created_at=command.reported_at,
            athlete_id=athlete_id,
            observed_at=command.reported_at,
            observation_type=DATE_OF_BIRTH_OBSERVATION_TYPE,
            measurement={"date_of_birth": command.date_of_birth.isoformat()},
            source=ObservationSource.USER_REPORT,
            reliability=Confidence.HIGH,
            context={
                "rule_version": DATE_OF_BIRTH_RULE_VERSION,
                "purpose": "age-bounded planning-authority applicability",
                "correction_semantics": "latest valid report wins; earlier reports remain",
            },
            provenance=Provenance(
                recorded_by=f"{principal.issuer}:{principal.subject}",
                source_system="agas-web",
                ingestion_method="authenticated-date-of-birth-report",
            ),
        )


def _date_of_birth_from_observation(observation: Observation) -> date:
    if not isinstance(observation.measurement, dict):
        raise AthleteDemographicsValidationError(
            f"date-of-birth observation {observation.id} has invalid measurement structure"
        )
    raw_value = observation.measurement.get("date_of_birth")
    if not isinstance(raw_value, str):
        raise AthleteDemographicsValidationError(
            f"date-of-birth observation {observation.id} has no valid date"
        )
    try:
        parsed = date.fromisoformat(raw_value)
    except ValueError as error:
        raise AthleteDemographicsValidationError(
            f"date-of-birth observation {observation.id} has no valid date"
        ) from error
    return parsed
