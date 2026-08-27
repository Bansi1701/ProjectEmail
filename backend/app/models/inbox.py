"""Inbox and Message.

For the MVP these live in Postgres rather than Redis. Redis is the right long-term home
for messages — native TTL, cheap writes, no vacuum pressure — but at MVP volume it is a
service to run for no gain. See docs/ADR 0003.

Expiry is enforced two ways on purpose:
  1. Reads always filter on `expires_at`, so an expired message is never returned even if
     the sweeper has not run. Correctness does not depend on a background job.
  2. A periodic sweep deletes expired rows, so the table does not grow forever.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Inbox(Base, TimestampMixin):
    __tablename__ = "inboxes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # The full address, e.g. "k3f9x2mq8bn1@temp-domain.xyz".
    address: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)

    # HMAC of the possession token. Knowing the address must NOT be enough to read the
    # inbox — the address is handed to third parties as the whole point of the product.
    # See docs/SECURITY.md section 2.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    messages: Mapped[list[Message]] = relationship(
        back_populates="inbox", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (Index("ix_inboxes_expires_at", "expires_at"),)

    def __repr__(self) -> str:
        return f"<Inbox {self.address}>"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    inbox_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inboxes.id", ondelete="CASCADE"), nullable=False
    )

    sender: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str] = mapped_column(String(998), nullable=False, default="")

    text_body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Already sanitized by app.services.sanitize before it lands here. Still rendered
    # inside a sandboxed iframe on a separate origin — both layers, always.
    html_body: Mapped[str | None] = mapped_column(Text)

    # Surfaced so the UI can offer one-click copy without opening the message.
    otp: Mapped[str | None] = mapped_column(String(16))
    verification_link: Mapped[str | None] = mapped_column(Text)

    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    inbox: Mapped[Inbox] = relationship(back_populates="messages")

    __table_args__ = (
        # The hot read: "messages for this inbox, newest first, not expired".
        Index("ix_messages_inbox_received", "inbox_id", "received_at"),
        Index("ix_messages_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<Message {self.subject[:40]!r} from {self.sender}>"
