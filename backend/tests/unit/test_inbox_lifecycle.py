"""Inbox erasure tests."""

import uuid
from unittest.mock import AsyncMock, Mock

from fastapi import status
from pytest import MonkeyPatch
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import inbox as inbox_api
from app.models import Inbox
from app.services import inbox as inbox_service


async def test_service_delete_is_committed_before_success() -> None:
    session = AsyncMock(spec=AsyncSession)
    inbox = Mock(spec=Inbox)

    await inbox_service.delete_inbox(session, inbox)

    session.delete.assert_awaited_once_with(inbox)
    session.commit.assert_awaited_once_with()


async def test_delete_route_authenticates_then_erases(monkeypatch: MonkeyPatch) -> None:
    session = AsyncMock(spec=AsyncSession)
    inbox = Mock(spec=Inbox)
    inbox_id = uuid.uuid4()
    authenticate = AsyncMock(return_value=inbox)
    erase = AsyncMock()
    monkeypatch.setattr(inbox_api, "_authenticate", authenticate)
    monkeypatch.setattr(inbox_api.inbox_service, "delete_inbox", erase)

    response = await inbox_api.delete_inbox(inbox_id, "possession-token", session)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    authenticate.assert_awaited_once_with(session, inbox_id, "possession-token")
    erase.assert_awaited_once_with(session, inbox)
