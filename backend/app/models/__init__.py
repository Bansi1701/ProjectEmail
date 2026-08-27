"""Durable models. Alembic autogenerate discovers tables through these imports."""

from app.models.api_key import ApiKey
from app.models.base import Base
from app.models.domain import Domain, DomainStatus
from app.models.inbox import Inbox, Message

__all__ = ["ApiKey", "Base", "Domain", "DomainStatus", "Inbox", "Message"]
