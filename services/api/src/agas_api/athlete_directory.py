from __future__ import annotations

from datetime import datetime
from uuid import UUID

from agas_domain.persistence.repository import DomainRepository
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from agas_api.identity import AuthenticatedPrincipal

ATHLETE_DIRECTORY_VERSION = "account-athlete-directory@1.0.0"


class OwnedEnvironmentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    environment_id: UUID
    name: str


class OwnedAthleteSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    athlete_id: UUID
    display_name: str
    profile_created_at: datetime
    goals: tuple[str, ...]
    environments: tuple[OwnedEnvironmentSummary, ...]
    ownership_granted_at: datetime
    ownership_rule_version: str


class OwnedAthleteDirectoryProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    projection_version: str = ATHLETE_DIRECTORY_VERSION
    athletes: tuple[OwnedAthleteSummary, ...]


def project_owned_athlete_directory(
    session: Session, principal: AuthenticatedPrincipal
) -> OwnedAthleteDirectoryProjection:
    """List only profiles owned by the exact authenticated account.

    An authenticated identity without a registered account has an empty directory so the
    onboarding screen can create its first account, athlete, and ownership atomically.
    """

    repository = DomainRepository(session)
    account = repository.get_account_by_identity(principal.issuer, principal.subject)
    if account is None:
        return OwnedAthleteDirectoryProjection(athletes=())

    summaries: list[OwnedAthleteSummary] = []
    for ownership in repository.list_athlete_ownerships_for_account(account.id):
        athlete = repository.get_athlete(ownership.athlete_id)
        if athlete is None:
            raise RuntimeError("owned athlete does not exist")
        summaries.append(
            OwnedAthleteSummary(
                athlete_id=athlete.id,
                display_name=athlete.display_name,
                profile_created_at=athlete.created_at,
                goals=athlete.goals,
                environments=tuple(
                    OwnedEnvironmentSummary(environment_id=item.id, name=item.name)
                    for item in repository.list_environments(athlete.id)
                ),
                ownership_granted_at=ownership.granted_at,
                ownership_rule_version=ownership.rule_version,
            )
        )
    return OwnedAthleteDirectoryProjection(athletes=tuple(summaries))
