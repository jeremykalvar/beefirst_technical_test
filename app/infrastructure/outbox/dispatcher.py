from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable

from psycopg import AsyncCursor
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger("app.infrastructure.outbox.dispatcher")


@dataclass(frozen=True)
class RetryPolicy:
    base: int = 2  # base delay (seconds)
    max_delay: int = 60  # cap (seconds)

    def compute_delay(self, attempts: int) -> int:
        # attempts is the *current* number of attempts already made
        # next delay = min(max_delay, base * 2**(attempts))
        delay = self.base * (2**attempts)
        return delay if delay < self.max_delay else self.max_delay


class OutboxDispatcher:
    """
    Polls the outbox table, claims due rows, dispatches them, and marks
    them as dispatched or reschedules for retry on failure.
    """

    def __init__(
        self,
        *,
        pool: AsyncConnectionPool,
        email_adapter,
        batch_size: int = 10,
        poll_interval: float = 1.0,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.pool = pool
        self.email_adapter = email_adapter
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.retry_policy = retry_policy or RetryPolicy()

    async def run_forever(self) -> None:
        logger.info(
            "outbox dispatcher started",
            extra={"batch_size": self.batch_size, "poll_interval": self.poll_interval},
        )
        while True:
            processed = await self._process_once()
            # simple throttle: if nothing to do, sleep a bit
            if processed == 0:
                import asyncio

                await asyncio.sleep(self.poll_interval)

    async def _process_once(self) -> int:
        """
        Single iteration:
        - claim up to batch_size due rows into 'processing'
        - for each, try to dispatch
        - mark dispatched or reschedule for retry
        Returns number of rows it attempted to process (claimed count).
        """
        # Claim
        batch = await self._claim_due_batch(self.batch_size)
        if not batch:
            return 0

        logger.info("claimed messages", extra={"count": len(batch)})

        # Process each message (commit per message)
        for msg in batch:
            msg_id = msg["id"]
            topic = msg["topic"]
            attempts = msg["attempts"]
            logger.info(
                "processing message",
                extra={"id": msg_id, "topic": topic, "attempts": attempts},
            )
            try:
                await self._dispatch(topic, msg["payload"])
            except Exception as e:  # noqa: BLE001
                # schedule retry
                new_attempts = attempts + 1
                delay = self.retry_policy.compute_delay(attempts)
                logger.warning(
                    "dispatch failed; scheduling retry",
                    extra={
                        "id": msg_id,
                        "topic": topic,
                        "attempts": new_attempts,
                        "retry_in_s": delay,
                    },
                )
                await self._mark_failed(msg_id, new_attempts, delay)
            else:
                await self._mark_dispatched(msg_id)

        return len(batch)

    async def _dispatch(self, topic: str, payload: dict[str, Any]) -> None:
        """
        Route by topic. For now we only support 'user.verification_code'.
        """
        if topic == "user.verification_code":
            to = payload["to"]
            subject = payload["subject"]
            body = payload["body"]
            await self.email_adapter.send(to=to, subject=subject, body=body)
            return

        # Unknown topic -> treated as failure to trigger retry path
        raise RuntimeError(f"unknown topic: {topic}")

    async def _claim_due_batch(self, limit: int) -> list[dict[str, Any]]:
        """
        Atomically move up to `limit` due 'pending' rows into 'processing'
        and return them.
        """
        sql = """
        WITH claimed AS (
            SELECT id
            FROM outbox
            WHERE status = 'pending'
              AND COALESCE(next_attempt_at, NOW()) <= NOW()
            ORDER BY created_at
            FOR UPDATE SKIP LOCKED
            LIMIT %s
        ),
        updated AS (
            UPDATE outbox o
            SET status = 'processing', updated_at = NOW()
            FROM claimed c
            WHERE o.id = c.id
            RETURNING o.id, o.topic, o.payload, o.attempts
        )
        SELECT id, topic, payload, attempts
        FROM updated
        ORDER BY id;
        """
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:  # type: AsyncCursor
                    await cur.execute(sql, (limit,))
                    rows = await cur.fetchall()

        batch: list[dict[str, Any]] = []
        for r in rows or ():
            batch.append(
                {
                    "id": r[0],
                    "topic": r[1],
                    "payload": r[2],
                    "attempts": r[3],
                }
            )
        return batch

    async def _mark_dispatched(self, msg_id: int) -> None:
        sql = """
        UPDATE outbox
        SET status = 'dispatched',
            updated_at = NOW()
        WHERE id = %s;
        """
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    await cur.execute(sql, (msg_id,))

    async def _mark_failed(
        self, msg_id: int, attempts: int, delay_seconds: int
    ) -> None:
        """
        Move message back to 'pending', bump attempts, and set a next_attempt_at in the future.
        """
        sql = """
        UPDATE outbox
        SET status = 'pending',
            attempts = %s,
            next_attempt_at = NOW() + make_interval(secs => %s),
            updated_at = NOW()
        WHERE id = %s;
        """
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    await cur.execute(sql, (attempts, delay_seconds, msg_id))
