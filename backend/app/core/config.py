"""Application settings, loaded from environment. See .env.example."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    secret_key: str

    database_url: str
    # Neon runs DDL unreliably through PgBouncer, so migrations should use the direct
    # (unpooled) endpoint. Falls back to database_url when unset.
    migration_database_url: str = ""
    redis_url: str

    # Inbox behaviour
    inbox_ttl_seconds: int = Field(default=3600, ge=600, le=3600)
    max_messages_per_inbox: int = 50
    # 12 bytes -> 96 bits of entropy. Minimum 8 (64 bits) per docs/SECURITY.md section 2.
    address_entropy_bytes: int = Field(default=12, ge=8)

    # Email HTML MUST render on a different origin than the app. See SECURITY.md section 1.
    # app_origin accepts a comma-separated list: the GitHub Pages site and the app's own
    # domain are different origins, and both need to pass CORS.
    app_origin: str
    sandbox_origin: str

    @property
    def cors_origins(self) -> list[str]:
        """Allowed browser origins, in the order given."""
        return [o.strip() for o in self.app_origin.split(",") if o.strip()]

    # Binds all interfaces because it runs inside a container; the published port is
    # what actually controls exposure. Never expose this directly to the internet.
    smtp_listen_host: str = "0.0.0.0"  # noqa: S104
    smtp_listen_port: int = 1025
    max_message_size_bytes: int = 10 * 1024 * 1024

    rate_limit_inbox_create: str = "10/minute"
    rate_limit_inbox_read: str = "60/minute"

    sentry_dsn: str = ""
    turnstile_secret_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
