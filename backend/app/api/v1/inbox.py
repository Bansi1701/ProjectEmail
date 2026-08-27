"""Inbox endpoints: create, read, and the live SSE stream."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.db import get_session
from app.models import Inbox
from app.schemas.inbox import InboxCreated, MessageDetail, MessageSummary
from app.services import inbox as inbox_service
from app.services.events import broker

router = APIRouter(prefix="/inbox", tags=["inbox"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# Below any sane proxy idle timeout. Without periodic traffic an intermediary will close
# a quiet SSE connection, and the user waiting on an OTP silently stops receiving events.
_KEEPALIVE_SECONDS = 15


@router.post("", response_model=InboxCreated, status_code=status.HTTP_201_CREATED)
async def create_inbox(session: SessionDep) -> InboxCreated:
    """Create a disposable inbox.

    The token is returned exactly once. It is required for every subsequent read — the
    address alone is not a credential, because handing the address to a third party is
    the entire point of the product. See docs/SECURITY.md section 2.
    """
    try:
        created, token = await inbox_service.create_inbox(session)
    except inbox_service.NoActiveDomainError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "no domain available") from None

    return InboxCreated(
        id=created.id, address=created.address, token=token, expires_at=created.expires_at
    )


@router.get("/{inbox_id}/messages", response_model=list[MessageSummary])
async def list_messages(
    inbox_id: uuid.UUID, token: Annotated[str, Query()], session: SessionDep
) -> list[MessageSummary]:
    inbox = await _authenticate(session, inbox_id, token)
    messages = await inbox_service.list_messages(session, inbox.id)
    return [MessageSummary.model_validate(m) for m in messages]


@router.get("/{inbox_id}/messages/{message_id}", response_model=MessageDetail)
async def get_message(
    inbox_id: uuid.UUID,
    message_id: uuid.UUID,
    token: Annotated[str, Query()],
    session: SessionDep,
) -> MessageDetail:
    inbox = await _authenticate(session, inbox_id, token)
    for message in await inbox_service.list_messages(session, inbox.id):
        if message.id == message_id:
            return MessageDetail.model_validate(message)
    raise HTTPException(status.HTTP_404_NOT_FOUND, "message not found")


@router.delete("/{inbox_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inbox(
    inbox_id: uuid.UUID, token: Annotated[str, Query()], session: SessionDep
) -> Response:
    """Immediately erase an inbox after verifying its possession token."""
    inbox = await _authenticate(session, inbox_id, token)
    await inbox_service.delete_inbox(session, inbox)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{inbox_id}/stream")
async def stream(
    inbox_id: uuid.UUID, token: Annotated[str, Query()], session: SessionDep
) -> EventSourceResponse:
    """Live message stream.

    SSE rather than WebSockets: the flow is one-way, EventSource reconnects on its own,
    and there is no protocol upgrade to shepherd through proxies.
    See docs/adr/0002-sse-over-websockets.md.

    The token travels as a query parameter because EventSource cannot set headers.
    """
    inbox = await _authenticate(session, inbox_id, token)
    return EventSourceResponse(_events(str(inbox.id)))


async def _events(inbox_id: str) -> AsyncIterator[dict[str, str]]:
    async with broker.subscribe(f"inbox:{inbox_id}") as queue:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=_KEEPALIVE_SECONDS)
            except TimeoutError:
                # A comment frame. Keeps intermediaries from closing an idle connection
                # and gives the client evidence the stream is still alive.
                yield {"event": "ping", "data": ""}
                continue
            yield {"event": "message", "data": json.dumps(event)}


async def _authenticate(session: AsyncSession, inbox_id: uuid.UUID, token: str) -> Inbox:
    try:
        return await inbox_service.authenticate(session, inbox_id, token)
    except inbox_service.InboxNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "inbox not found") from None
