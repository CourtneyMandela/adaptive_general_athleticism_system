from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from uuid import UUID

from agas_domain import Account, AthleteOwnership
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from sqlalchemy.orm import Session

from agas_api.database import database_session
from agas_api.settings import get_settings

OWNERSHIP_RULE_VERSION = "account-athlete-ownership@1.0.0"


def grant_athlete_ownership(
    session: Session,
    *,
    athlete_id: UUID,
    issuer: str,
    subject: str,
    granted_at: datetime,
) -> tuple[Account, AthleteOwnership, bool]:
    """Grant a fixture athlete to one local account without exposing a claim API."""

    repository = DomainRepository(session)
    if repository.get_athlete(athlete_id) is None:
        raise DomainIntegrityError("athlete does not exist")
    account = repository.get_account_by_identity(issuer, subject)
    account_created = account is None
    if account is None:
        account = Account(
            created_at=granted_at,
            issuer=issuer,
            subject=subject,
        )
        repository.add_account(account)
        session.flush()
    existing = repository.get_athlete_ownership(athlete_id)
    if existing is not None:
        if existing.account_id != account.id:
            raise DomainIntegrityError("athlete already belongs to another account")
        return account, existing, False
    ownership = AthleteOwnership(
        created_at=granted_at,
        account_id=account.id,
        athlete_id=athlete_id,
        granted_at=granted_at,
        grant_method="local-operator-cli",
        rule_version=OWNERSHIP_RULE_VERSION,
    )
    repository.add_athlete_ownership(ownership)
    session.commit()
    return account, ownership, account_created


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage local-development account ownership without a public claim endpoint."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    grant_parser = subparsers.add_parser("grant", help="Grant one fixture athlete to an account")
    grant_parser.add_argument("--athlete-id", type=UUID, required=True)
    grant_parser.add_argument("--subject", default="local-browser")
    grant_parser.add_argument("--issuer", default=get_settings().development_auth_issuer)
    arguments = parser.parse_args()

    if arguments.command != "grant":
        parser.error("unsupported identity administration command")
    try:
        with database_session() as session:
            account, ownership, account_created = grant_athlete_ownership(
                session,
                athlete_id=arguments.athlete_id,
                issuer=arguments.issuer,
                subject=arguments.subject,
                granted_at=datetime.now(UTC),
            )
    except DomainIntegrityError as error:
        parser.error(str(error))
    print(
        json.dumps(
            {
                "account_created": account_created,
                "account_id": str(account.id),
                "athlete_id": str(ownership.athlete_id),
                "ownership_id": str(ownership.id),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
