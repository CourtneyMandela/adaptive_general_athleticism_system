from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from agas_domain import (
    Account,
    AccountRole,
    AccountRoleAssignment,
    AccountRoleStatus,
    AthleteOwnership,
    Confidence,
    Environment,
    EquipmentAvailability,
    Observation,
    ObservationSource,
    Provenance,
)
from agas_domain.models import VersionedRecord
from agas_domain.persistence.repository import DomainRepository
from agas_seed_data import SeedCatalogImporter, TravelScenarioSeed, load_seed_catalog
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from agas_api.database import database_session
from agas_api.initial_planning_preparation import InitialPlanningPreparationProjector
from agas_api.settings import Settings, get_settings

DEMO_FIXTURE_VERSION = "local-onboarding-demo@1.0.0"
DEMO_ATHLETE_SUBJECT = "local-browser"
DEMO_REVIEWER_SUBJECT = "local-reviewer"
DEMO_ASSESSMENT_REVIEWER_SUBJECT = "local-assessment-reviewer"


class LocalDemoBootstrapError(RuntimeError):
    """Raised when a local demo would be unsafe or collide with persisted history."""


class LocalDemoBootstrapResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fixture_version: str
    catalog_version: str
    catalog_created: bool
    created_records: dict[str, int]
    athlete_id: UUID
    athlete_access_token: str
    reviewer_access_token: str
    reviewer_role_assignment_id: UUID
    assessment_reviewer_access_token: str
    assessment_reviewer_role_assignment_id: UUID
    planning_status: str
    athlete_path: str
    reviewer_path: str


def bootstrap_local_demo(
    session: Session,
    *,
    settings: Settings,
    bootstrapped_at: datetime | None = None,
) -> LocalDemoBootstrapResult:
    """Create an idempotent, non-production profile at an honest planning boundary."""

    _require_local_development(settings)
    instant = bootstrapped_at or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("demo bootstrap time must include a timezone")

    repository = DomainRepository(session)
    catalog = load_seed_catalog()
    scenario = catalog.travel_scenario
    created: dict[str, int] = {
        "accounts": 0,
        "athletes": 0,
        "ownerships": 0,
        "role_assignments": 0,
        "observations": 0,
        "environments": 0,
        "equipment_availability": 0,
    }
    try:
        catalog_result = SeedCatalogImporter(repository).import_catalog(
            catalog, imported_at=instant
        )
        athlete_account, account_created = _ensure_account(
            repository,
            issuer=settings.development_auth_issuer,
            subject=DEMO_ATHLETE_SUBJECT,
            created_at=instant,
        )
        created["accounts"] += int(account_created)
        reviewer_account, reviewer_created = _ensure_account(
            repository,
            issuer=settings.development_auth_issuer,
            subject=DEMO_REVIEWER_SUBJECT,
            created_at=instant,
        )
        created["accounts"] += int(reviewer_created)
        assessment_reviewer_account, assessment_reviewer_created = _ensure_account(
            repository,
            issuer=settings.development_auth_issuer,
            subject=DEMO_ASSESSMENT_REVIEWER_SUBJECT,
            created_at=instant,
        )
        created["accounts"] += int(assessment_reviewer_created)
        session.flush()

        created["athletes"] += int(
            _ensure_exact(
                label="synthetic demo athlete",
                expected=scenario.athlete,
                getter=repository.get_athlete,
                adder=repository.add_athlete,
            )
        )
        session.flush()

        ownership = repository.get_athlete_ownership(scenario.athlete.id)
        if ownership is None:
            ownership = AthleteOwnership(
                id=_fixture_id("athlete-ownership"),
                created_at=instant,
                account_id=athlete_account.id,
                athlete_id=scenario.athlete.id,
                granted_at=instant,
                grant_method="local-demo-bootstrap",
                rule_version=DEMO_FIXTURE_VERSION,
            )
            repository.add_athlete_ownership(ownership)
            created["ownerships"] += 1
        elif ownership.account_id != athlete_account.id:
            raise LocalDemoBootstrapError(
                "synthetic demo athlete already belongs to a different account"
            )

        role_assignment, role_created = _ensure_reviewer_role(
            repository,
            account=reviewer_account,
            assigned_at=instant,
            role=AccountRole.PLANNING_REVIEWER,
        )
        created["role_assignments"] += int(role_created)
        assessment_role_assignment, assessment_role_created = _ensure_reviewer_role(
            repository,
            account=assessment_reviewer_account,
            assigned_at=instant,
            role=AccountRole.ASSESSMENT_REVIEWER,
        )
        created["role_assignments"] += int(assessment_role_created)

        observation = _demo_observation(scenario)
        created["observations"] += int(
            _ensure_exact(
                label="synthetic demo observation",
                expected=observation,
                getter=repository.get_observation,
                adder=repository.add_observation,
            )
        )
        session.flush()

        environments = _demo_environments(scenario)
        for environment in environments:
            created["environments"] += int(
                _ensure_exact(
                    label="synthetic demo environment",
                    expected=environment,
                    getter=repository.get_environment,
                    adder=repository.add_environment,
                )
            )
        session.flush()

        for availability in _demo_equipment_availability(observation, environments, scenario):
            created["equipment_availability"] += int(
                _ensure_exact(
                    label="synthetic demo equipment availability",
                    expected=availability,
                    getter=repository.get_equipment_availability,
                    adder=repository.add_equipment_availability,
                )
            )
        session.flush()

        planning = InitialPlanningPreparationProjector(session).project(
            scenario.athlete.id, instant
        )
        session.commit()
    except Exception:
        session.rollback()
        raise

    return LocalDemoBootstrapResult(
        fixture_version=DEMO_FIXTURE_VERSION,
        catalog_version=catalog.manifest.catalog_version,
        catalog_created=catalog_result.created,
        created_records=created,
        athlete_id=scenario.athlete.id,
        athlete_access_token=f"dev.{DEMO_ATHLETE_SUBJECT}",
        reviewer_access_token=f"dev.{DEMO_REVIEWER_SUBJECT}",
        reviewer_role_assignment_id=role_assignment.id,
        assessment_reviewer_access_token=f"dev.{DEMO_ASSESSMENT_REVIEWER_SUBJECT}",
        assessment_reviewer_role_assignment_id=assessment_role_assignment.id,
        planning_status=planning.status,
        athlete_path=f"/?athleteId={scenario.athlete.id}",
        reviewer_path="/review/queue",
    )


def _require_local_development(settings: Settings) -> None:
    if settings.environment.casefold() in {"production", "prod"}:
        raise LocalDemoBootstrapError("local demo bootstrap is disabled in production")
    if settings.auth_mode != "development":
        raise LocalDemoBootstrapError("local demo bootstrap requires development authentication")


def _fixture_id(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"agas:{DEMO_FIXTURE_VERSION}:{name}")


def _ensure_account(
    repository: DomainRepository,
    *,
    issuer: str,
    subject: str,
    created_at: datetime,
) -> tuple[Account, bool]:
    existing = repository.get_account_by_identity(issuer, subject)
    if existing is not None:
        return existing, False
    account = Account(
        id=_fixture_id(f"account:{issuer}:{subject}"),
        created_at=created_at,
        issuer=issuer,
        subject=subject,
    )
    repository.add_account(account)
    return account, True


def _ensure_reviewer_role(
    repository: DomainRepository,
    *,
    account: Account,
    assigned_at: datetime,
    role: AccountRole,
) -> tuple[AccountRoleAssignment, bool]:
    current = repository.get_current_account_role_assignment(account.id, role)
    if current is not None and current.status is AccountRoleStatus.ACTIVE:
        return current, False
    if current is not None:
        raise LocalDemoBootstrapError(
            f"local {role.value} role is revoked; use identity_admin to grant it explicitly"
        )
    sequence_number = 1
    assignment_fixture_name = (
        f"reviewer-role:{account.id}:{sequence_number}"
        if role is AccountRole.PLANNING_REVIEWER
        else f"reviewer-role:{role.value}:{account.id}:{sequence_number}"
    )
    rationale = (
        "Enable the explicit local planning-review workflow."
        if role is AccountRole.PLANNING_REVIEWER
        else "Enable the explicit local assessment-governance inspection workflow."
    )
    assignment = AccountRoleAssignment(
        id=_fixture_id(assignment_fixture_name),
        created_at=assigned_at,
        account_id=account.id,
        role=role,
        status=AccountRoleStatus.ACTIVE,
        sequence_number=sequence_number,
        supersedes_assignment_id=None,
        assigned_at=assigned_at,
        assigned_by="local-demo-bootstrap",
        rationale=rationale,
        rule_version=DEMO_FIXTURE_VERSION,
    )
    repository.add_account_role_assignment(assignment)
    return assignment, True


def _ensure_exact[Record: VersionedRecord](
    *,
    label: str,
    expected: Record,
    getter: Callable[[UUID], Record | None],
    adder: Callable[[Record], None],
) -> bool:
    existing = getter(expected.id)
    if existing is None:
        adder(expected)
        return True
    if existing != expected:
        raise LocalDemoBootstrapError(
            f"persisted {label} {expected.id} differs from fixture content"
        )
    return False


def _demo_observation(scenario: TravelScenarioSeed) -> Observation:
    athlete = scenario.athlete
    environments = (scenario.home, scenario.travel)
    return Observation(
        id=_fixture_id("onboarding-observation"),
        created_at=athlete.created_at,
        athlete_id=athlete.id,
        observed_at=athlete.created_at,
        observation_type="synthetic_local_demo_profile_environment_report",
        measurement={
            "display_name": athlete.display_name,
            "goals": list(athlete.goals),
            "available_weekdays": list(scenario.available_weekdays),
            "environments": [
                {
                    "name": environment.name,
                    "floor_area_m2": environment.floor_area_m2,
                    "max_noise_level": environment.max_noise_level.value,
                    "outdoor_access": environment.outdoor_access,
                    "equipment_ids": [str(item) for item in environment.equipment_ids],
                }
                for environment in environments
            ],
        },
        source=ObservationSource.USER_REPORT,
        reliability=Confidence.MODERATE,
        context={
            "fixture_version": DEMO_FIXTURE_VERSION,
            "scenario_version": scenario.scenario_version,
            "synthetic": True,
            "operational_training_authority": False,
        },
        provenance=Provenance(
            recorded_by="repository-owned synthetic fixture",
            source_system="agas-local-demo",
            ingestion_method="deterministic-demo-bootstrap",
            external_reference=f"synthetic-travel-scenario@{scenario.scenario_version}",
        ),
    )


def _demo_environments(scenario: TravelScenarioSeed) -> tuple[Environment, Environment]:
    athlete = scenario.athlete
    home = Environment(
        id=_fixture_id("environment:home"),
        created_at=athlete.created_at,
        athlete_id=athlete.id,
        name=scenario.home.name,
        space_constraints={"floor_area_m2": scenario.home.floor_area_m2},
        max_noise_level=scenario.home.max_noise_level,
        outdoor_access=scenario.home.outdoor_access,
    )
    travel = Environment(
        id=_fixture_id("environment:travel"),
        created_at=athlete.created_at,
        athlete_id=athlete.id,
        name=scenario.travel.name,
        space_constraints={"floor_area_m2": scenario.travel.floor_area_m2},
        max_noise_level=scenario.travel.max_noise_level,
        outdoor_access=scenario.travel.outdoor_access,
    )
    return home, travel


def _demo_equipment_availability(
    observation: Observation,
    environments: tuple[Environment, Environment],
    scenario: TravelScenarioSeed,
) -> tuple[EquipmentAvailability, ...]:
    availability = []
    for environment, source in zip(environments, (scenario.home, scenario.travel), strict=True):
        for equipment_id in source.equipment_ids:
            availability.append(
                EquipmentAvailability(
                    id=_fixture_id(f"availability:{environment.id}:{equipment_id}"),
                    created_at=observation.created_at,
                    environment_id=environment.id,
                    equipment_id=equipment_id,
                    source_observation_id=observation.id,
                    is_available=True,
                    effective_from=observation.observed_at,
                    reason=(
                        "Synthetic local demo report; not a scientific claim or exercise "
                        "equivalence decision."
                    ),
                )
            )
    return tuple(availability)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create local demo identity and onboarding state without training rules."
    )
    parser.add_argument("command", choices=("bootstrap",))
    arguments = parser.parse_args()
    if arguments.command != "bootstrap":
        parser.error("unsupported demo command")
    try:
        with database_session() as session:
            result = bootstrap_local_demo(session, settings=get_settings())
    except (LocalDemoBootstrapError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result.model_dump(mode="json"), sort_keys=True))


if __name__ == "__main__":
    main()
