from collections.abc import Iterator

import pytest
from agas_api.identity import AuthenticatedPrincipal, authenticated_principal_dependency
from agas_api.main import app
from agas_domain.persistence.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

TEST_PRINCIPAL = AuthenticatedPrincipal(
    issuer="urn:agas:test-suite",
    subject="test-suite-account",
    authentication_method="test-bypass",
    test_bypass=True,
)


@pytest.fixture(autouse=True)
def authenticated_test_principal() -> Iterator[None]:
    app.dependency_overrides[authenticated_principal_dependency] = lambda: TEST_PRINCIPAL
    try:
        yield
    finally:
        app.dependency_overrides.pop(authenticated_principal_dependency, None)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as database_session:
        yield database_session
    Base.metadata.drop_all(engine)
    engine.dispose()
