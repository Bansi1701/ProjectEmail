"""Expiry worker scheduling and recovery tests."""

import asyncio

from app.workers.expiry import run_expiry_sweeper


async def test_sweeper_runs_immediately_and_stops_cleanly() -> None:
    stop = asyncio.Event()
    called = asyncio.Event()
    calls = 0

    async def sweep() -> int:
        nonlocal calls
        calls += 1
        called.set()
        return 2

    task = asyncio.create_task(run_expiry_sweeper(stop, 60, sweep_once=sweep))
    await asyncio.wait_for(called.wait(), timeout=1)
    stop.set()
    await asyncio.wait_for(task, timeout=1)

    assert calls == 1


async def test_sweeper_retries_after_a_failed_pass() -> None:
    stop = asyncio.Event()
    recovered = asyncio.Event()
    calls = 0

    async def sweep() -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("database unavailable")
        recovered.set()
        return 0

    task = asyncio.create_task(run_expiry_sweeper(stop, 0.01, sweep_once=sweep))
    await asyncio.wait_for(recovered.wait(), timeout=1)
    stop.set()
    await asyncio.wait_for(task, timeout=1)

    assert calls == 2
