from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from agas_api import __version__
from agas_api.database import database_session
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
    allow_methods=["GET"],
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
