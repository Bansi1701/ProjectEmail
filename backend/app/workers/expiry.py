"""Periodic physical deletion for expired inbox rows."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.core.db import get_sessionmaker
from app.services import inbox as inbox_service

logger = logging.getLogger(__name__)

SweepOperation = Callable[[], Awaitable[int]]


async def sweep_expired_once() -> int:
    """Run one expiry pass in its own database session."""
    async with get_sessionmaker()() as session:
        return await inbox_service.sweep_expired(session)


async def run_expiry_sweeper(
    stop_event: asyncio.Event,
    interval_seconds: float,
    *,
    sweep_once: SweepOperation = sweep_expired_once,
) -> None:
    """Delete expired rows until shutdown, without taking the API down on failure.

    Reads enforce ``expires_at`` independently, so a failed pass is an operations issue,
    not a privacy-boundary bypass. The next interval retries automatically.
    """
    while not stop_event.is_set():
        try:
            deleted = await sweep_once()
        except Exception:
            logger.exception("expiry sweep failed")
        else:
            if deleted:
                logger.info("deleted %d expired inboxes", deleted)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except TimeoutError:
            continue
