from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, NoReturn, Protocol
from uuid import UUID

from agas_domain import AccountRole, AccountRoleStatus
from agas_domain.persistence.models import (
    BlockPlanRecord,
    BlockReviewRecord,
    LongRangeStrategyRecord,
    SessionExecutionRecord,
    WeeklyPlanRecord,
)
from agas_domain.persistence.repository import DomainRepository
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient, decode
from jwt.exceptions import PyJWKClientConnectionError, PyJWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from agas_api.database import database_session_dependency
from agas_api.settings import Settings, get_settings

DEVELOPMENT_SUBJECT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,99}$")
ALLOWED_EXTERNAL_JWT_ALGORITHMS = frozenset({"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"})


class IdentityAuthenticationError(ValueError):
    pass


class IdentityAuthenticationUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    issuer: str
    subject: str
    authentication_method: str
    test_bypass: bool = False


class TokenVerifier(Protocol):
    def verify(self, token: str) -> AuthenticatedPrincipal: ...


class DevelopmentBearerVerifier:
    """Resolve a local identity selector that must never be enabled in production."""

    token_prefix = "dev."

    def __init__(self, issuer: str) -> None:
        self.issuer = issuer

    def verify(self, token: str) -> AuthenticatedPrincipal:
        if not token.startswith(self.token_prefix):
            raise IdentityAuthenticationError("development bearer token must start with dev.")
        subject = token.removeprefix(self.token_prefix)
        if DEVELOPMENT_SUBJECT_PATTERN.fullmatch(subject) is None:
            raise IdentityAuthenticationError("development bearer subject is invalid")
        return AuthenticatedPrincipal(
            issuer=self.issuer,
            subject=subject,
            authentication_method="development-bearer",
        )


class ExternalJWTVerifier:
    """Verify one explicitly configured asymmetric JWT resource-server contract."""

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str,
        algorithms: tuple[str, ...],
        leeway_seconds: int,
        jwks_timeout_seconds: float,
        jwks_cache_seconds: int,
        jwks_client: PyJWKClient | None = None,
    ) -> None:
        if not algorithms or any(
            algorithm not in ALLOWED_EXTERNAL_JWT_ALGORITHMS for algorithm in algorithms
        ):
            raise ValueError("external JWT algorithms must use the asymmetric allow-list")
        self.issuer = issuer
        self.audience = audience
        self.algorithms = algorithms
        self.leeway_seconds = leeway_seconds
        self.jwks_client = jwks_client or PyJWKClient(
            jwks_url,
            cache_keys=False,
            cache_jwk_set=True,
            lifespan=jwks_cache_seconds,
            timeout=jwks_timeout_seconds,
        )

    def verify(self, token: str) -> AuthenticatedPrincipal:
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            claims = decode(
                token,
                signing_key,
                algorithms=list(self.algorithms),
                audience=self.audience,
                issuer=self.issuer,
                leeway=self.leeway_seconds,
                options={"require": ["iss", "aud", "exp", "iat", "sub"]},
            )
        except PyJWKClientConnectionError as error:
            raise IdentityAuthenticationUnavailableError(
                "external signing keys are temporarily unavailable"
            ) from error
        except PyJWTError as error:
            raise IdentityAuthenticationError("external bearer token is invalid") from error

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise IdentityAuthenticationError("external bearer token is invalid")
        return AuthenticatedPrincipal(
            issuer=self.issuer,
            subject=subject.strip(),
            authentication_method="external-jwt",
        )


def _token_verifier(settings: Settings) -> TokenVerifier:
    if settings.auth_mode == "development":
        return DevelopmentBearerVerifier(settings.development_auth_issuer)
    if (
        settings.external_auth_issuer is None
        or settings.external_auth_jwks_url is None
        or not settings.external_auth_audience
    ):
        raise IdentityAuthenticationUnavailableError(
            "external token verification is not configured"
        )
    return ExternalJWTVerifier(
        issuer=str(settings.external_auth_issuer),
        audience=settings.external_auth_audience,
        jwks_url=str(settings.external_auth_jwks_url),
        algorithms=settings.external_auth_algorithms,
        leeway_seconds=settings.external_auth_leeway_seconds,
        jwks_timeout_seconds=settings.external_auth_jwks_timeout_seconds,
        jwks_cache_seconds=settings.external_auth_jwks_cache_seconds,
    )


def authenticated_principal_dependency(
    authorization: Annotated[str | None, Header()] = None,
) -> AuthenticatedPrincipal:
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="bearer authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.casefold() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="valid bearer authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return _token_verifier(get_settings()).verify(token)
    except IdentityAuthenticationError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    except IdentityAuthenticationUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error


class OwnershipAuthorizer:
    """Resolve persisted aggregates to an athlete and enforce its immutable owner."""

    def __init__(self, session: Session, principal: AuthenticatedPrincipal) -> None:
        self.session = session
        self.repository = DomainRepository(session)
        self.principal = principal

    def require_athlete(self, athlete_id: UUID) -> None:
        if self.principal.test_bypass:
            return
        if self.repository.get_athlete(athlete_id) is None:
            self._not_found("athlete")
        self._require_owner(athlete_id, "athlete")

    def require_strategy(self, strategy_id: UUID) -> None:
        self._require_aggregate(
            self.session.scalar(
                select(LongRangeStrategyRecord.athlete_id).where(
                    LongRangeStrategyRecord.id == strategy_id
                )
            ),
            "long-range strategy",
        )

    def require_block(self, block_id: UUID) -> None:
        self._require_aggregate(
            self.session.scalar(
                select(BlockPlanRecord.athlete_id).where(BlockPlanRecord.id == block_id)
            ),
            "block plan",
        )

    def require_block_review(self, review_id: UUID) -> None:
        self._require_aggregate(
            self.session.scalar(
                select(BlockReviewRecord.athlete_id).where(BlockReviewRecord.id == review_id)
            ),
            "block review",
        )

    def require_weekly_plan(self, weekly_plan_id: UUID) -> None:
        self._require_aggregate(
            self.session.scalar(
                select(WeeklyPlanRecord.athlete_id).where(WeeklyPlanRecord.id == weekly_plan_id)
            ),
            "weekly plan",
        )

    def require_session_execution(self, execution_id: UUID) -> None:
        self._require_aggregate(
            self.session.scalar(
                select(SessionExecutionRecord.athlete_id).where(
                    SessionExecutionRecord.id == execution_id
                )
            ),
            "session execution",
        )

    def _require_aggregate(self, athlete_id: UUID | None, resource_name: str) -> None:
        if self.principal.test_bypass:
            return
        if athlete_id is None:
            self._not_found(resource_name)
        self._require_owner(athlete_id, resource_name)

    def _require_owner(self, athlete_id: UUID, resource_name: str) -> None:
        account = self.repository.get_account_by_identity(
            self.principal.issuer, self.principal.subject
        )
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="authenticated account is not registered",
                headers={"WWW-Authenticate": "Bearer"},
            )
        ownership = self.repository.get_athlete_ownership(athlete_id)
        if ownership is None or ownership.account_id != account.id:
            self._not_found(resource_name)

    @staticmethod
    def _not_found(resource_name: str) -> NoReturn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_name} does not exist",
        )


def ownership_authorizer_dependency(
    session: Annotated[Session, Depends(database_session_dependency)],
    principal: Annotated[AuthenticatedPrincipal, Depends(authenticated_principal_dependency)],
) -> OwnershipAuthorizer:
    return OwnershipAuthorizer(session, principal)


@dataclass(frozen=True, slots=True)
class AuthorizedRole:
    """The exact current assignment that authorized an operator request."""

    account_id: UUID
    assignment_id: UUID
    role: AccountRole
    assigned_at: datetime


class RoleAuthorizer:
    """Enforce current append-only account-role assignments for operator resources."""

    def __init__(self, session: Session, principal: AuthenticatedPrincipal) -> None:
        self.repository = DomainRepository(session)
        self.principal = principal

    def require_role(self, role: AccountRole) -> AuthorizedRole:
        if self.principal.test_bypass:
            return AuthorizedRole(
                account_id=UUID(int=0),
                assignment_id=UUID(int=0),
                role=role,
                assigned_at=datetime.min.replace(tzinfo=UTC),
            )
        account = self.repository.get_account_by_identity(
            self.principal.issuer, self.principal.subject
        )
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="authenticated account is not registered",
                headers={"WWW-Authenticate": "Bearer"},
            )
        assignment = self.repository.get_current_account_role_assignment(account.id, role)
        if assignment is None or assignment.status is not AccountRoleStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"active {role.value} role required",
            )
        return AuthorizedRole(
            account_id=account.id,
            assignment_id=assignment.id,
            role=assignment.role,
            assigned_at=assignment.assigned_at,
        )


def role_authorizer_dependency(
    session: Annotated[Session, Depends(database_session_dependency)],
    principal: Annotated[AuthenticatedPrincipal, Depends(authenticated_principal_dependency)],
) -> RoleAuthorizer:
    return RoleAuthorizer(session, principal)


def planning_reviewer_dependency(
    role_authorizer: Annotated[RoleAuthorizer, Depends(role_authorizer_dependency)],
) -> AuthorizedRole:
    """Authorize before operator request bodies reach their application handlers."""

    return role_authorizer.require_role(AccountRole.PLANNING_REVIEWER)


def assessment_reviewer_dependency(
    role_authorizer: Annotated[RoleAuthorizer, Depends(role_authorizer_dependency)],
) -> AuthorizedRole:
    """Authorize access to scientific assessment-governance projections."""

    return role_authorizer.require_role(AccountRole.ASSESSMENT_REVIEWER)
