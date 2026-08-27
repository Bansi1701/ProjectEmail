"""API keys for the public developer API (Phase 2).

Only the hash is stored. A leaked database must not yield usable keys.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ApiKey(Base, TimestampMixin):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # HMAC-SHA256 of the key. The key itself is shown once, at creation, and never stored.
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    # First few characters, so a user can identify which key is which in a list.
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)

    label: Mapped[str] = mapped_column(String(128), nullable=False)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<ApiKey {self.key_prefix}… {self.label}>"
