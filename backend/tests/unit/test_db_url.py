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


def test_cors_origins_single() -> None:
    s = _settings(app_origin="http://localhost:3000")
    assert s.cors_origins == ["http://localhost:3000"]


def test_cors_origins_multiple_and_trimmed() -> None:
    """The Pages site and the app's own domain are different origins; both must pass."""
    s = _settings(app_origin="https://bansi1701.github.io, https://tempmail.example ")
    assert s.cors_origins == ["https://bansi1701.github.io", "https://tempmail.example"]


def test_cors_origins_ignores_empty_entries() -> None:
    s = _settings(app_origin="https://a.example,,https://b.example,")
    assert s.cors_origins == ["https://a.example", "https://b.example"]


def _settings(**overrides: str):
    from app.core.config import Settings

    base = {
        "secret_key": "x",
        "database_url": "postgresql+asyncpg://u:p@localhost/db",
        "redis_url": "redis://localhost:6379/0",
        "app_origin": "http://localhost:3000",
        "sandbox_origin": "http://localhost:8001",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]
