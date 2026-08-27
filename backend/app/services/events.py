"""In-process event broker for the live inbox stream.

When mail arrives by webhook, whichever coroutine handled it publishes here, and every
SSE connection subscribed to that inbox gets it immediately.

**This works only within a single process.** With two or more workers, the webhook may
land on worker A while the user's SSE connection is held by worker B, and that user never
sees their mail — a bug that is invisible in local testing with one worker.

That is why WEB_CONCURRENCY is 1 for the MVP. On 0.1 CPU a single async worker is the
right shape anyway, and it holds thousands of idle connections without difficulty.

Crossing to multiple workers means replacing this module with Redis pub/sub (or Postgres
LISTEN/NOTIFY). The interface below is deliberately narrow so that swap stays contained.
See docs/adr/0003-no-redis-for-mvp.md.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

logger = logging.getLogger(__name__)

# How many undelivered events a single slow client may queue before we start dropping.
# A client this far behind is gone; unbounded queues would be a memory leak.
_MAX_QUEUE = 32


class EventBroker:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)

    @asynccontextmanager
    async def subscribe(self, channel: str) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
        """Subscribe for the duration of the context, cleaning up on any exit.

        The context manager matters: an SSE client that disconnects mid-stream raises
        inside the generator, and without this the queue would leak for the process's life.
        """
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=_MAX_QUEUE)
        self._subscribers[channel].add(queue)
        try:
            yield queue
        finally:
            self._subscribers[channel].discard(queue)
            if not self._subscribers[channel]:
                del self._subscribers[channel]

    async def publish(self, channel: str, event: dict[str, Any]) -> int:
        """Publish to every subscriber. Returns how many received it.

        Never blocks on a slow consumer — a full queue means that client is too far behind
        to care about, and holding up mail delivery for it would be the wrong trade.
        """
        delivered = 0
        for queue in list(self._subscribers.get(channel, ())):
            try:
                queue.put_nowait(event)
                delivered += 1
            except asyncio.QueueFull:
                logger.warning("dropping event for saturated subscriber on %s", channel)
        return delivered

    def subscriber_count(self, channel: str) -> int:
        return len(self._subscribers.get(channel, ()))

    @property
    def total_subscribers(self) -> int:
        return sum(len(s) for s in self._subscribers.values())


broker = EventBroker()
