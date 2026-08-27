"""Alembic environment — async, and Neon-aware.

Reuses app.core.db.normalize_database_url so migrations connect exactly the way the
application does. Without that, a Neon URL with `?sslmode=require` fails here with a
confusing asyncpg TypeError even though the app itself runs fine.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import get_settings
from app.core.db import normalize_database_url
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

_settings = get_settings()
# Prefer the direct endpoint for DDL; PgBouncer transaction mode is not reliable for it.
_url, _connect_args = normalize_database_url(
    _settings.migration_database_url or _settings.database_url
)
config.set_main_option("sqlalchemy.url", _url)


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting — useful for reviewing a migration."""
    context.configure(
        url=_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Without these, autogenerate misses column type and server-default changes.
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # One-shot: no pooling for a migration run.
        connect_args=_connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
