from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from agas_domain import (
    AccountRole,
    AccountRoleAssignment,
    AccountRoleStatus,
)
from agas_domain.persistence.models import AthleteOwnershipRecord
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agas_api.identity import AuthenticatedPrincipal
from agas_api.settings import Settings

ACCESS_VERSION = "owner-alpha-operator-access@1.0.0"
REQUIRED_ROLES = (
    AccountRole.ASSESSMENT_REVIEWER,
    AccountRole.PLANNING_REVIEWER,
)
OwnerAlphaAccessStatus = Literal[
    "not_configured",
    "identity_not_allowlisted",
    "account_required",
    "athlete_required",
    "revoked",
    "eligible",
    "active",
]


class OwnerAlphaRoleProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: AccountRole
    status: AccountRoleStatus | None
    assignment_id: UUID | None


class OwnerAlphaAccessProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    access_version: str = ACCESS_VERSION
    status: OwnerAlphaAccessStatus
    message: str
    authenticated_issuer: str
    authenticated_subject: str
    can_activate: bool
    roles: tuple[OwnerAlphaRoleProjection, ...]


class OwnerAlphaAccessActivationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    access: OwnerAlphaAccessProjection
    activated: bool


class ActivateOwnerAlphaAccessCommand(BaseModel):
    """Require an explicit acknowledgement before app permissions are granted."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attestation: Literal[True]


class OwnerAlphaAccessError(ValueError):
    pass


class OwnerAlphaAccessService:
    """Grant prepared-workflow permissions only to one deployment-allowlisted owner."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.repository = DomainRepository(session)

    def project(self, principal: AuthenticatedPrincipal) -> OwnerAlphaAccessProjection:
        account = self.repository.get_account_by_identity(principal.issuer, principal.subject)
        roles = self._roles(account.id if account else None)
        configured_subject = self.settings.owner_alpha_operator_subject
        expected_issuer = self._expected_issuer()
        if configured_subject is None:
            status: OwnerAlphaAccessStatus = "not_configured"
            message = (
                "The deployment has not allowlisted an owner-alpha operator subject. "
                "No reviewer access can be activated."
            )
        elif principal.subject != configured_subject or principal.issuer != expected_issuer:
            status = "identity_not_allowlisted"
            message = (
                "This signed-in identity is not the deployment-allowlisted owner-alpha operator."
            )
        elif account is None:
            status = "account_required"
            message = "Create or open an athlete profile before activating operator access."
        elif not self._owns_athlete(account.id):
            status = "athlete_required"
            message = "The allowlisted account must own an athlete before activation."
        elif any(item.status is AccountRoleStatus.REVOKED for item in roles):
            status = "revoked"
            message = "A required role was revoked and cannot be self-reactivated."
        elif all(item.status is AccountRoleStatus.ACTIVE for item in roles):
            status = "active"
            message = "Owner-alpha assessment and planning review access is active."
        else:
            status = "eligible"
            message = (
                "This exact allowlisted owner account may activate the two permissions needed "
                "to review AGAS-prepared assessment and planning artifacts."
            )
        return OwnerAlphaAccessProjection(
            status=status,
            message=message,
            authenticated_issuer=principal.issuer,
            authenticated_subject=principal.subject,
            can_activate=status == "eligible",
            roles=roles,
        )

    def activate(
        self,
        principal: AuthenticatedPrincipal,
        *,
        activated_at: datetime | None = None,
    ) -> OwnerAlphaAccessActivationResult:
        before = self.project(principal)
        if before.status == "active":
            return OwnerAlphaAccessActivationResult(access=before, activated=False)
        if not before.can_activate:
            raise OwnerAlphaAccessError(before.message)
        instant = activated_at or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise OwnerAlphaAccessError("activation time must include a timezone")
        account = self.repository.get_account_by_identity(principal.issuer, principal.subject)
        if account is None:
            raise OwnerAlphaAccessError("authenticated account is not registered")
        try:
            with self.session.begin_nested():
                for role in REQUIRED_ROLES:
                    current = self.repository.get_current_account_role_assignment(account.id, role)
                    if current is not None:
                        if current.status is not AccountRoleStatus.ACTIVE:
                            raise OwnerAlphaAccessError(
                                f"revoked {role.value} role requires administrator review"
                            )
                        continue
                    self.repository.add_account_role_assignment(
                        AccountRoleAssignment(
                            created_at=instant,
                            account_id=account.id,
                            role=role,
                            status=AccountRoleStatus.ACTIVE,
                            sequence_number=1,
                            assigned_at=instant,
                            assigned_by=f"owner-alpha-activation:{principal.issuer}:{principal.subject}",
                            rationale=(
                                "Exact deployment-allowlisted owner activated provisional "
                                "review access for AGAS-prepared owner-alpha artifacts."
                            ),
                            rule_version=ACCESS_VERSION,
                        )
                    )
                self.session.flush()
            self.session.commit()
        except OwnerAlphaAccessError:
            self.session.rollback()
            raise
        except (DomainIntegrityError, IntegrityError) as error:
            self.session.rollback()
            raise OwnerAlphaAccessError(
                "operator access conflicts with persisted authorization history"
            ) from error
        return OwnerAlphaAccessActivationResult(
            access=self.project(principal),
            activated=True,
        )

    def _expected_issuer(self) -> str:
        if self.settings.auth_mode == "external":
            if self.settings.external_auth_issuer is None:
                return ""
            return str(self.settings.external_auth_issuer)
        return self.settings.development_auth_issuer

    def _roles(self, account_id: UUID | None) -> tuple[OwnerAlphaRoleProjection, ...]:
        items: list[OwnerAlphaRoleProjection] = []
        for role in REQUIRED_ROLES:
            assignment = (
                self.repository.get_current_account_role_assignment(account_id, role)
                if account_id
                else None
            )
            items.append(
                OwnerAlphaRoleProjection(
                    role=role,
                    status=assignment.status if assignment else None,
                    assignment_id=assignment.id if assignment else None,
                )
            )
        return tuple(items)

    def _owns_athlete(self, account_id: UUID) -> bool:
        return bool(
            self.session.scalar(
                select(func.count())
                .select_from(AthleteOwnershipRecord)
                .where(AthleteOwnershipRecord.account_id == account_id)
            )
        )
