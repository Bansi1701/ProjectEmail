"""Run database migrations from application startup.

Needed because Render's free plan offers no Shell and no pre-deploy hook, so there is
nowhere else to run `alembic upgrade head`.

This is a pragmatic accommodation, not a pattern to copy. With multiple instances booting
at once they would race; it is safe here only because the MVP runs a single instance with
a single worker (see docs/adr/0003-no-redis-for-mvp.md). Alembic also takes a transaction
lock, so a race would serialise rather than corrupt — but it would still be wrong.

Turn it off and migrate deliberately as soon as there is somewhere to run a command.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _upgrade_sync() -> None:
    """Blocking Alembic upgrade. Must not be called on the event loop."""
    from alembic import command
    from alembic.config import Config

    # alembic.ini sits at the backend root, one level above app/.
    ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    if not ini.exists():
        raise FileNotFoundError(f"alembic.ini not found at {ini}")

    config = Config(str(ini))
    command.upgrade(config, "head")


async def upgrade_to_head() -> bool:
    """Apply pending migrations. Returns True on success.

    Runs in a worker thread: Alembic's env.py calls asyncio.run() for the online path,
    which raises if a loop is already running on this thread. A fresh thread has none.

    A failure is logged rather than raised. The database being unmigrated is bad, but
    refusing to boot means no health endpoint and no way to diagnose it — the container
    just crash-loops.
    """
    try:
        await asyncio.to_thread(_upgrade_sync)
    except Exception:
        logger.exception("migration failed; the app is starting against an unmigrated database")
        return False
    logger.info("database migrated to head")
    return True
