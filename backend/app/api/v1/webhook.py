"""Inbound mail webhook.

Cloudflare Email Routing receives SMTP on port 25 for the catch-all address and an Email
Worker forwards the raw message here over HTTPS. That is what lets the API run on a host
with no inbound SMTP of its own. See docs/DEPLOYMENT.md.
"""

from __future__ import annotations

import hmac
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.schemas.inbox import InboundEmail
from app.services import inbox as inbox_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/inbound", status_code=status.HTTP_202_ACCEPTED)
async def inbound(
    payload: InboundEmail,
    session: Annotated[AsyncSession, Depends(get_session)],
    x_webhook_secret: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    """Accept one inbound message.

    Always answers 202, even when the address has no live inbox. A 404 would tell a
    prober which addresses exist, and the sender would retry mail we deliberately dropped.
    """
    settings = get_settings()
    if not settings.inbound_webhook_secret:
        # Refuse rather than run unauthenticated — an open endpoint here lets anyone
        # inject arbitrary messages into any inbox.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "webhook not configured")

    if not x_webhook_secret or not hmac.compare_digest(
        x_webhook_secret, settings.inbound_webhook_secret
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad secret")

    message = await inbox_service.deliver(session, payload.to, payload.raw.encode())
    if message is None:
        logger.info("dropped mail for %s (no live inbox or cap reached)", payload.to)
        return {"status": "dropped"}
    return {"status": "delivered"}
