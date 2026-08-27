"""Request/response schemas for the inbox API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InboxCreated(BaseModel):
    """Returned once, at creation. The token is never retrievable again."""

    id: uuid.UUID
    address: str
    # Possession token. Required on every read — the address alone is not a credential.
    token: str
    expires_at: datetime


class MessageSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender: str
    subject: str
    otp: str | None
    verification_link: str | None
    received_at: datetime


class MessageDetail(MessageSummary):
    text_body: str
    # Sanitized, but still only ever rendered inside a sandboxed iframe on a separate
    # origin. See docs/SECURITY.md section 1.
    html_body: str | None


class InboundEmail(BaseModel):
    """Payload posted by the Cloudflare Email Worker.

    Deliberately minimal: the worker forwards the raw RFC 5322 message and lets our
    parser do the work, so parsing logic lives in one place and is unit-tested.
    """

    to: str
    sender: str
    raw: str
