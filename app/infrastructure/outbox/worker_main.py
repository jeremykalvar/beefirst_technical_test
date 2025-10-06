from __future__ import annotations

import asyncio
import signal
from contextlib import suppress
import logging

from app.logging import setup_logging
from app.settings import get_settings
from app.infrastructure.db.pool import get_pool, close_pool
from app.infrastructure.outbox.dispatcher import OutboxDispatcher, RetryPolicy
from app.infrastructure.email.http_smtp_adapter import HttpSmtpEmailAdapter

logger = logging.getLogger(__name__)


async def _run() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    pool = get_pool()
    if getattr(pool, "closed", True):
        await pool.open()
    logger.info("worker: pool opened")

    email = HttpSmtpEmailAdapter(base_url=settings.smtp_base_url)
    dispatcher = OutboxDispatcher(
        pool=pool,
        email_adapter=email,
        batch_size=10,
        poll_interval=1.0,
        retry_policy=RetryPolicy(base=2, max_delay=300),
    )

    stop = asyncio.Event()

    def _on_signal(*_: object) -> None:
        logger.info("worker: stop signal received")
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, _on_signal)

    worker_task = asyncio.create_task(dispatcher.run_forever())
    logger.info("worker: started run_forever loop")

    await stop.wait()

    worker_task.cancel()
    with suppress(asyncio.CancelledError):
        await worker_task

    await email.aclose()
    await close_pool()
    logger.info("worker: stopped cleanly")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
