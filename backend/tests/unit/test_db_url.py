"""Tests for Neon/Postgres URL normalization.

Each case here corresponds to a real failure mode. The Neon ones in particular fail
at connect time with errors that do not obviously point at the URL.
"""

from app.core.db import is_neon, normalize_database_url


def test_local_docker_url_passes_through() -> None:
    url, args = normalize_database_url(
        "postgresql+asyncpg://postgres:postgres@postgres:5432/projectemail"
    )
    assert url == "postgresql+asyncpg://postgres:postgres@postgres:5432/projectemail"
    assert args == {}


def test_bare_postgresql_scheme_gets_asyncpg_driver() -> None:
    url, _ = normalize_database_url("postgresql://u:p@localhost:5432/db")
    assert url.startswith("postgresql+asyncpg://")


def test_postgres_scheme_alias_also_upgraded() -> None:
    # Heroku-style `postgres://` still shows up in the wild.
    url, _ = normalize_database_url("postgres://u:p@localhost:5432/db")
    assert url.startswith("postgresql+asyncpg://")


def test_sslmode_is_stripped_and_translated() -> None:
    """asyncpg is not libpq: `sslmode` in the URL raises TypeError at connect."""
    url, args = normalize_database_url(
        "postgresql://u:p@ep-cool-name-123.us-east-2.aws.neon.tech/neondb?sslmode=require"
    )
    assert "sslmode" not in url
    assert args["ssl"] == "require"


def test_channel_binding_is_stripped() -> None:
    """Neon's dashboard appends channel_binding; asyncpg does not accept it either."""
    url, _ = normalize_database_url(
        "postgresql://u:p@ep-x-1.us-east-2.aws.neon.tech/db?sslmode=require&channel_binding=require"
    )
    assert "channel_binding" not in url


def test_neon_requires_tls_even_without_sslmode() -> None:
    _, args = normalize_database_url("postgresql://u:p@ep-x-1.us-east-2.aws.neon.tech/db")
    assert args["ssl"] == "require"


def test_neon_pooled_endpoint_disables_statement_caches() -> None:
    """PgBouncer transaction mode + prepared statements = DuplicatePreparedStatementError."""
    _, args = normalize_database_url(
        "postgresql://u:p@ep-x-1-pooler.us-east-2.aws.neon.tech/db?sslmode=require"
    )
    assert args["statement_cache_size"] == 0
    assert args["prepared_statement_cache_size"] == 0


def test_neon_direct_endpoint_keeps_statement_cache() -> None:
    """The unpooled endpoint is a real Postgres connection — caching is a win there."""
    _, args = normalize_database_url(
        "postgresql://u:p@ep-x-1.us-east-2.aws.neon.tech/db?sslmode=require"
    )
    assert "statement_cache_size" not in args


def test_unknown_params_are_preserved() -> None:
    """Only libpq-specific params are dropped; anything asyncpg understands survives."""
    url, _ = normalize_database_url("postgresql://u:p@localhost/db?timeout=30")
    assert "timeout=30" in url


def test_is_neon_detection() -> None:
    assert is_neon("ep-cool-name-123.us-east-2.aws.neon.tech")
    assert is_neon("ep-x-pooler.eu-central-1.aws.neon.tech")
    assert not is_neon("postgres")
    assert not is_neon("db.example.com")
    # Must not match a lookalike domain.
    assert not is_neon("neon.tech.evil.com")
