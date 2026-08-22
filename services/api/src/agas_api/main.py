from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated
from uuid import UUID

from agas_domain import BlockPlan, ClosedLoopReplanningResult
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from agas_api import __version__
from agas_api.block_creation import (
    BlockCreationConflictError,
    BlockCreationNotFoundError,
    BlockCreationValidationError,
    CreateBlockPlanCommand,
    PersistedBlockCreationService,
)
from agas_api.database import database_session, database_session_dependency
from agas_api.replanning import (
    PersistedReplanningService,
    PostBlockReplanningCommand,
    ReplanningConflictError,
    ReplanningNotFoundError,
    ReplanningValidationError,
)
from agas_api.settings import get_settings

settings = get_settings()

app = FastAPI(
    title="Adaptive General Athleticism System API",
    version=__version__,
    description="Domain-first API foundation. Training-plan generation is not implemented.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin).rstrip("/") for origin in settings.cors_origins],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@contextmanager
def _session_scope() -> Iterator[Session]:
    session = database_session()
    try:
        yield session
    finally:
        session.close()


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "agas-api", "version": __version__}


@app.get("/ready", tags=["system"])
def ready() -> dict[str, str]:
    with _session_scope() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.post(
    "/v1/block-reviews/{block_review_id}/replan",
    tags=["planning"],
    response_model=ClosedLoopReplanningResult,
    status_code=status.HTTP_201_CREATED,
)
def replan_after_block_review(
    block_review_id: UUID,
    command: PostBlockReplanningCommand,
    session: Annotated[Session, Depends(database_session_dependency)],
) -> ClosedLoopReplanningResult:
    try:
        return PersistedReplanningService(session).execute(block_review_id, command)
    except ReplanningNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ReplanningConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ReplanningValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/strategies/{strategy_id}/blocks",
    tags=["planning"],
    response_model=BlockPlan,
    status_code=status.HTTP_201_CREATED,
)
def create_block_plan(
    strategy_id: UUID,
    command: CreateBlockPlanCommand,
    session: Annotated[Session, Depends(database_session_dependency)],
) -> BlockPlan:
    try:
        return PersistedBlockCreationService(session).execute(strategy_id, command)
    except BlockCreationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except BlockCreationConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except BlockCreationValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
