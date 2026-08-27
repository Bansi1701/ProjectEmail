"""Database engine and session management.

Works against plain Postgres (local Docker) and Neon (serverless) without code
changes — point DATABASE_URL at either.

Three Neon-specific gotchas are handled here, because each one produces a confusing
failure if you hit it unprepared:

1. **libpq-only query params.** Neon's dashboard hands you a URL ending in
   `?sslmode=require&channel_binding=require`. Those are libpq parameters. asyncpg
   is not libpq and raises `TypeError: connect() got an unexpected keyword argument
   'sslmode'`. We strip them and translate to asyncpg's `ssl` connect arg.

2. **PgBouncer and prepared statements.** Neon's pooled endpoint (host contains
   `-pooler`) runs PgBouncer in transaction mode, where prepared statements are not
   safe — you get `DuplicatePreparedStatementError` or `InvalidSQLStatementNameError`
   under concurrency. Both statement caches must be disabled on that endpoint.

3. **Scale to zero.** Neon suspends an idle compute and the first query afterwards
   hits a cold start. Pooled connections held across a suspend are dead, so
   `pool_pre_ping` is required — without it the first request after idle fails.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

# Recognised by libpq, meaningless to asyncpg. Stripped from the URL and translated.
_LIBPQ_ONLY_PARAMS = frozenset(
    {"sslmode", "channel_binding", "target_session_attrs", "options", "application_name"}
)


def normalize_database_url(url: str) -> tuple[str, dict[str, Any]]:
    """Split a Postgres URL into an asyncpg-safe URL plus connect_args.

    Accepts what Neon, Supabase or a local container actually give you, including
    the `postgresql://` and `postgres://` prefixes, and returns a URL the asyncpg
    dialect will not choke on.

    Returns:
        (url, connect_args) ready for create_async_engine.
    """
    parts = urlsplit(url)

    scheme = parts.scheme
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"

    query = dict(parse_qsl(parts.query))
    connect_args: dict[str, Any] = {}

    # sslmode -> asyncpg's ssl argument. Neon always requires TLS.
    sslmode = query.get("sslmode")
    if sslmode in ("require", "verify-ca", "verify-full"):
        connect_args["ssl"] = "require"
    elif sslmode in ("disable", "allow", "prefer"):
        pass  # asyncpg negotiates TLS on its own; no explicit arg needed.

    remaining = {k: v for k, v in query.items() if k not in _LIBPQ_ONLY_PARAMS}
    clean = urlunsplit((scheme, parts.netloc, parts.path, urlencode(remaining), parts.fragment))

    host = parts.hostname or ""

    if is_neon(host):
        # Neon terminates TLS at the proxy and requires it even when the URL omits sslmode.
        connect_args.setdefault("ssl", "require")

        if "-pooler" in host:
            # PgBouncer transaction mode: prepared statements are not safe here.
            # Both caches must go — one belongs to asyncpg, one to SQLAlchemy's dialect.
            connect_args["statement_cache_size"] = 0
            connect_args["prepared_statement_cache_size"] = 0

    return clean, connect_args


def is_neon(host: str) -> bool:
    return host.endswith(".neon.tech")


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    url, connect_args = normalize_database_url(settings.database_url)
    neon = is_neon(urlsplit(url).hostname or "")

    return create_async_engine(
        url,
        connect_args=connect_args,
        echo=settings.environment == "development",
        # Required on Neon: a suspended compute kills pooled connections, and without
        # a pre-ping the first request after idle fails instead of reconnecting.
        pool_pre_ping=True,
        # Neon's own pooler fronts the database, so a large local pool buys nothing
        # and just holds connections open against the quota.
        pool_size=5 if neon else 10,
        max_overflow=5 if neon else 20,
        # Recycle below Neon's idle timeout so we never hand out a dead connection.
        pool_recycle=300 if neon else 1800,
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,  # Objects stay usable after commit, inside a request.
        autoflush=False,
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency. Rolls back on exception, always closes."""
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_connection() -> bool:
    """Used by /health. Cheap round trip that also warms a suspended Neon compute."""
    from sqlalchemy import text

    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
