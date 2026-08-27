"""FastAPI application entrypoint."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import v1
from app.core.config import get_settings
from app.core.db import check_connection, get_engine
from app.core.migrate import upgrade_to_head
from app.workers.expiry import run_expiry_sweeper

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if settings.run_migrations_on_startup:
        await upgrade_to_head()
    # Touch the database on boot. On Neon this also wakes a suspended compute, so the
    # first real request does not pay the cold start.
    await check_connection()

    sweeper_stop = asyncio.Event()
    sweeper = asyncio.create_task(
        run_expiry_sweeper(sweeper_stop, settings.expiry_sweep_interval_seconds),
        name="expiry-sweeper",
    )
    try:
        yield
    finally:
        sweeper_stop.set()
        await sweeper
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

    Failing liveness on a Neon cold start would get a healthy container killed and
    create a restart loop. Dependency health belongs on the readiness endpoint.
    """
    return {"status": "ok"}


@app.get("/health/ready", tags=["ops"])
async def readiness() -> dict[str, object]:
    """Readiness — reports dependency health without failing the request."""
    db_ok = await check_connection()
    return {"status": "ok" if db_ok else "degraded", "database": "up" if db_ok else "down"}


app.include_router(v1.router)
