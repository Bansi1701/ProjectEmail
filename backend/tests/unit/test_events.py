"""Event broker tests.

The cleanup and backpressure cases matter most: a leaked queue is a slow memory leak,
and an unbounded one is a fast one.
"""

import asyncio

import pytest

from app.services.events import EventBroker


async def test_subscriber_receives_published_event() -> None:
    b = EventBroker()
    async with b.subscribe("inbox:1") as q:
        await b.publish("inbox:1", {"id": "m1"})
        assert (await asyncio.wait_for(q.get(), timeout=1)) == {"id": "m1"}


async def test_publish_reaches_every_subscriber() -> None:
    b = EventBroker()
    async with b.subscribe("inbox:1") as q1, b.subscribe("inbox:1") as q2:
        assert await b.publish("inbox:1", {"id": "m1"}) == 2
        assert await q1.get() == {"id": "m1"}
        assert await q2.get() == {"id": "m1"}


async def test_channels_are_isolated() -> None:
    """A message for one inbox must never reach another — this is a privacy boundary."""
    b = EventBroker()
    async with b.subscribe("inbox:1") as q1, b.subscribe("inbox:2") as q2:
        await b.publish("inbox:1", {"id": "m1"})
        assert await q1.get() == {"id": "m1"}
        assert q2.empty()


async def test_unsubscribe_on_context_exit() -> None:
    b = EventBroker()
    async with b.subscribe("inbox:1"):
        assert b.subscriber_count("inbox:1") == 1
    assert b.subscriber_count("inbox:1") == 0
    assert b.total_subscribers == 0


async def test_unsubscribe_even_when_the_body_raises() -> None:
    """An SSE client disconnecting raises inside the generator. The queue must still go."""
    b = EventBroker()
    with pytest.raises(RuntimeError):
        async with b.subscribe("inbox:1"):
            raise RuntimeError("client disconnected")
    assert b.total_subscribers == 0


async def test_publish_to_nobody_is_harmless() -> None:
    b = EventBroker()
    assert await b.publish("inbox:nobody", {"id": "m1"}) == 0


async def test_slow_subscriber_does_not_block_publish() -> None:
    """A saturated queue drops events rather than stalling mail delivery."""
    b = EventBroker()
    async with b.subscribe("inbox:1") as q:
        for i in range(100):
            await asyncio.wait_for(b.publish("inbox:1", {"id": i}), timeout=1)
        assert q.full()
        assert q.qsize() == 32
