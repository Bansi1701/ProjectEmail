"""Mail domain pool.

Domains are consumable inventory, not fixed identity: third-party sites blacklist
known temp-mail domains, so we rotate through 20-50 of them.

Critically, these are the MAIL domains only. The brand domain that carries the site
and all its SEO authority is never in this table and never receives mail — it cannot
be burned. Conflating the two would destroy accumulated search rankings on every
rotation. See docs/ARCHITECTURE.md.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class DomainStatus(enum.StrEnum):
    """Lifecycle of a mail domain.

    Rotation is a drain, not a cliff: a degrading domain stops taking new inboxes
    while existing ones keep working until they expire naturally.
    """

    WARMING = "warming"  # DNS propagating, not yet handed out
    ACTIVE = "active"  # Accepting new inboxes
    DRAINING = "draining"  # No new inboxes; existing ones still deliver
    RETIRED = "retired"  # Burned or expired; kept for history


class Domain(Base, TimestampMixin):
    __tablename__ = "domains"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(253), unique=True, nullable=False)
    status: Mapped[DomainStatus] = mapped_column(
        Enum(DomainStatus, native_enum=False, length=16),
        default=DomainStatus.WARMING,
        nullable=False,
    )

    registrar: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Health signals driving rotation.
    blacklist_hits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    messages_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Whether this domain has ever been published. We publish burned domains only —
    # publishing an active one converts its useful life from months to days.
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        # The hot path: "give me a domain for a new inbox".
        Index("ix_domains_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Domain {self.name} ({self.status})>"
