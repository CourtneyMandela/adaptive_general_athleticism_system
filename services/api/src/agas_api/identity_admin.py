from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from uuid import UUID

from agas_domain import (
    Account,
    AccountRole,
    AccountRoleAssignment,
    AccountRoleStatus,
    AthleteOwnership,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from sqlalchemy.orm import Session

from agas_api.database import database_session
from agas_api.settings import get_settings

OWNERSHIP_RULE_VERSION = "account-athlete-ownership@1.0.0"
ROLE_ASSIGNMENT_RULE_VERSION = "account-role-assignment@1.0.0"


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


def set_account_role(
    session: Session,
    *,
    issuer: str,
    subject: str,
    role: AccountRole,
    status: AccountRoleStatus,
    assigned_at: datetime,
    rationale: str,
) -> tuple[Account, AccountRoleAssignment, bool, bool]:
    """Append a local role grant or revocation without exposing role self-service."""

    repository = DomainRepository(session)
    account = repository.get_account_by_identity(issuer, subject)
    account_created = account is None
    if account is None:
        if status is AccountRoleStatus.REVOKED:
            raise DomainIntegrityError("cannot revoke a role from an unregistered account")
        account = Account(created_at=assigned_at, issuer=issuer, subject=subject)
        repository.add_account(account)
        session.flush()
    current = repository.get_current_account_role_assignment(account.id, role)
    if current is not None and current.status is status:
        return account, current, account_created, False
    assignment = AccountRoleAssignment(
        created_at=assigned_at,
        account_id=account.id,
        role=role,
        status=status,
        sequence_number=1 if current is None else current.sequence_number + 1,
        supersedes_assignment_id=current.id if current else None,
        assigned_at=assigned_at,
        assigned_by="local-operator-cli",
        rationale=rationale,
        rule_version=ROLE_ASSIGNMENT_RULE_VERSION,
    )
    repository.add_account_role_assignment(assignment)
    session.commit()
    return account, assignment, account_created, True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage local-development account ownership without a public claim endpoint."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    grant_parser = subparsers.add_parser("grant", help="Grant one fixture athlete to an account")
    grant_parser.add_argument("--athlete-id", type=UUID, required=True)
    grant_parser.add_argument("--subject", default="local-browser")
    grant_parser.add_argument("--issuer", default=get_settings().development_auth_issuer)
    for command, help_text in (
        ("grant-role", "Grant an administrative role to an account"),
        ("revoke-role", "Revoke an administrative role from an account"),
    ):
        role_parser = subparsers.add_parser(command, help=help_text)
        role_parser.add_argument("--subject", required=True)
        role_parser.add_argument("--issuer", default=get_settings().development_auth_issuer)
        role_parser.add_argument(
            "--role",
            choices=tuple(item.value for item in AccountRole),
            default=AccountRole.PLANNING_REVIEWER.value,
        )
        role_parser.add_argument("--rationale", required=True)
    arguments = parser.parse_args()

    if arguments.command in {"grant-role", "revoke-role"}:
        role_status = (
            AccountRoleStatus.ACTIVE
            if arguments.command == "grant-role"
            else AccountRoleStatus.REVOKED
        )
        try:
            with database_session() as session:
                account, assignment, account_created, changed = set_account_role(
                    session,
                    issuer=arguments.issuer,
                    subject=arguments.subject,
                    role=AccountRole(arguments.role),
                    status=role_status,
                    assigned_at=datetime.now(UTC),
                    rationale=arguments.rationale,
                )
        except DomainIntegrityError as error:
            parser.error(str(error))
        print(
            json.dumps(
                {
                    "account_created": account_created,
                    "account_id": str(account.id),
                    "assignment_changed": changed,
                    "assignment_id": str(assignment.id),
                    "role": assignment.role.value,
                    "status": assignment.status.value,
                },
                sort_keys=True,
            )
        )
        return
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
