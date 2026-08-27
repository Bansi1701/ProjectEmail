"""FastAPI application entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.db import check_connection, get_engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Touch the database on boot. On Neon this also wakes a suspended compute, so the
    # first real request does not pay the cold start.
    await check_connection()
    yield
    await get_engine().dispose()


app = FastAPI(
    title="ProjectEmail API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    """Liveness only — deliberately does not touch the database.

    Postgres is not on the critical path: inboxes and messages live in Redis, so the
    service still delivers mail with the database down. Failing liveness on a Neon
    cold start would get the container killed for no reason.
    """
    return {"status": "ok"}


@app.get("/health/ready", tags=["ops"])
async def readiness() -> dict[str, object]:
    """Readiness — reports dependency health without failing the request."""
    db_ok = await check_connection()
    return {"status": "ok" if db_ok else "degraded", "database": "up" if db_ok else "down"}


# Routers are registered here as they land:
# app.include_router(inbox.router, prefix="/api/v1")
