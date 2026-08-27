"""Inbox lifecycle and message delivery."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.mail import otp as otp_extractor
from app.mail import parser
from app.models import Domain, DomainStatus, Inbox, Message
from app.services import addresses, sanitize
from app.services.events import broker


async def create_inbox(session: AsyncSession) -> tuple[Inbox, str]:
    """Create an inbox on an active domain. Returns the inbox and its plaintext token."""
    settings = get_settings()

    domain = (
        await session.execute(select(Domain).where(Domain.status == DomainStatus.ACTIVE).limit(1))
    ).scalar_one_or_none()
    if domain is None:
        raise NoActiveDomainError("no active domain in the pool")

    local_part = addresses.generate_local_part(settings.address_entropy_bytes)
    token = addresses.issue_possession_token()

    inbox = Inbox(
        address=f"{local_part}@{domain.name}",
        token_hash=addresses.hash_token(token, settings.secret_key),
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.inbox_ttl_seconds),
    )
    session.add(inbox)
    await session.flush()
    return inbox, token


async def authenticate(session: AsyncSession, inbox_id: uuid.UUID, token: str) -> Inbox:
    """Resolve an inbox, verifying the possession token.

    Expired inboxes are treated as missing. Reads filter on expires_at so correctness
    never depends on the sweeper having run.
    """
    settings = get_settings()
    inbox = (
        await session.execute(
            select(Inbox).where(Inbox.id == inbox_id, Inbox.expires_at > datetime.now(UTC))
        )
    ).scalar_one_or_none()

    if inbox is None:
        raise InboxNotFoundError(str(inbox_id))
    if not addresses.verify_token(token, inbox.token_hash, settings.secret_key):
        # Same error as a missing inbox on purpose — distinguishing them would let an
        # attacker enumerate which inboxes exist.
        raise InboxNotFoundError(str(inbox_id))
    return inbox


async def deliver(session: AsyncSession, to_address: str, raw: bytes) -> Message | None:
    """Parse, sanitize and store an inbound message, then notify open connections.

    Returns None when no live inbox owns the address. Mail for an address nobody is
    watching is dropped without being stored — that is what stops a temp-mail service
    from becoming a spam archive.
    """
    settings = get_settings()

    inbox = (
        await session.execute(
            select(Inbox).where(
                Inbox.address == to_address.lower(),
                Inbox.expires_at > datetime.now(UTC),
            )
        )
    ).scalar_one_or_none()
    if inbox is None:
        return None

    existing = (
        (await session.execute(select(Message).where(Message.inbox_id == inbox.id))).scalars().all()
    )
    if len(existing) >= settings.max_messages_per_inbox:
        # Cap rather than queue. An attacker mailbombing an address should not be able to
        # grow our storage without bound.
        return None

    parsed = parser.parse(raw)
    html = sanitize.sanitize_email_html(parsed.html_body) if parsed.html_body else None

    # Search the text body first — HTML bodies are full of markup that produces
    # false-positive digit runs.
    haystack = parsed.text_body or ""
    message = Message(
        inbox_id=inbox.id,
        sender=parsed.sender,
        subject=parsed.subject,
        text_body=parsed.text_body,
        html_body=html,
        otp=otp_extractor.extract_otp(haystack),
        verification_link=otp_extractor.extract_verification_link(haystack),
        received_at=parsed.received_at,
        expires_at=inbox.expires_at,
    )
    session.add(message)
    await session.flush()

    # Commit before publishing: a client that reacts by fetching the message must not
    # race an uncommitted write and get an empty list.
    await session.commit()

    await broker.publish(
        f"inbox:{inbox.id}",
        {
            "id": str(message.id),
            "sender": message.sender,
            "subject": message.subject,
            "otp": message.otp,
            "verificationLink": message.verification_link,
            "receivedAt": message.received_at.isoformat(),
        },
    )
    return message


async def list_messages(session: AsyncSession, inbox_id: uuid.UUID) -> list[Message]:
    result = await session.execute(
        select(Message)
        .where(Message.inbox_id == inbox_id, Message.expires_at > datetime.now(UTC))
        .order_by(Message.received_at.desc())
    )
    return list(result.scalars().all())


async def delete_inbox(session: AsyncSession, inbox: Inbox) -> None:
    """Immediately erase an authenticated inbox and all of its messages."""
    await session.delete(inbox)
    # Commit inside the service so a successful 204 means the erasure is durable, rather
    # than depending on request-dependency cleanup after the response is constructed.
    await session.commit()


async def sweep_expired(session: AsyncSession) -> int:
    """Delete expired inboxes and their messages.

    Reads already filter on expires_at, so this is housekeeping rather than correctness —
    it keeps the tables from growing forever. Redis would do this natively; on Postgres
    it is a periodic job. See docs/adr/0003-no-redis-for-mvp.md.
    """
    result = await session.execute(delete(Inbox).where(Inbox.expires_at <= datetime.now(UTC)))
    await session.commit()
    # CursorResult carries rowcount; the base Result protocol does not.
    return cast("CursorResult[Any]", result).rowcount or 0


class NoActiveDomainError(RuntimeError):
    """The domain pool has no active domain to hand out."""


class InboxNotFoundError(LookupError):
    """No such inbox, or the token did not match. Deliberately indistinguishable."""
