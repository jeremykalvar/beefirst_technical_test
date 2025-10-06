from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from typing import Any, Dict, List, TypedDict

import psycopg
from psycopg_pool import AsyncConnectionPool

from app.domain.ports.email_port import EmailPort
from app.infrastructure.db.outbox_repo import PgOutboxRepository

logger = logging.getLogger(__name__)


class Payload(TypedDict, total=False):
    to: str
    subject: str
    body: str
    idempotency_key: str | None


class RetryPolicy:
    """
    Exponential backoff with a cap.
    attempts=0 -> base * 2^0,
    attempts=1 -> base * 2^1, ...
    Capped to max_delay seconds.
    """

    def __init__(self, base: int = 2, max_delay: int = 300) -> None:
        self.base = base
        self.max_delay = max_delay

    def next_delay(self, attempts: int) -> int:
        delay = self.base * (2**attempts)
        return min(delay, self.max_delay)


@dataclass
class OutboxDispatcher:
    pool: AsyncConnectionPool
    email_adapter: EmailPort
    batch_size: int = 10
    poll_interval: float = 1.0
    retry_policy: RetryPolicy = RetryPolicy()

    async def run_forever(self) -> None:
        logger.info(
            "outbox dispatcher started",
            extra={"batch_size": self.batch_size, "poll_interval": self.poll_interval},
        )
        try:
            while True:
                processed = await self._process_once()
                if processed == 0:
                    logger.debug(
                        "no due messages; sleeping", extra={"sleep": self.poll_interval}
                    )
                    await asyncio.sleep(self.poll_interval)
        except asyncio.CancelledError:
            logger.info("outbox dispatcher cancelled; shutting down")
            raise

    async def _process_once(self) -> int:
        # 1) claim
        async with self.pool.connection() as conn:
            async with conn.transaction():
                batch = await self._claim_due_batch(conn)

        if not batch:
            return 0

        logger.info("claimed messages", extra={"count": len(batch)})

        # 2) process
        processed = 0
        for msg in batch:
            msg_id: str = msg["id"]
            topic: str = msg["topic"]
            attempts: int = int(msg["attempts"] or 0)

            logger.info(
                "processing message",
                extra={"id": msg_id, "topic": topic, "attempts": attempts},
            )
            try:
                await self._handle(topic, msg["payload"])
            except Exception as e:
                delay = self.retry_policy.next_delay(attempts)
                logger.warning(
                    "dispatch failed; scheduling retry",
                    extra={
                        "id": msg_id,
                        "topic": topic,
                        "attempts": attempts + 1,
                        "retry_in_s": delay,
                    },
                )
                async with self.pool.connection() as conn:
                    async with conn.transaction():
                        repo = PgOutboxRepository(conn)
                        await repo.mark_failed(
                            msg_id, error=repr(e), retry_in_seconds=delay
                        )
            else:
                logger.info(
                    "dispatch ok; marking dispatched",
                    extra={"id": msg_id, "topic": topic},
                )
                async with self.pool.connection() as conn:
                    async with conn.transaction():
                        repo = PgOutboxRepository(conn)
                        await repo.mark_dispatched(msg_id)

            processed += 1

        return processed

    async def _claim_due_batch(
        self, conn: psycopg.AsyncConnection
    ) -> List[Dict[str, Any]]:
        """
        Atomically claim up to `batch_size` messages that are due:
          - status='pending'
          - COALESCE(next_attempt_at, now()) <= now()
        Flip them to status='processing' and return their data.

        Uses SKIP LOCKED so multiple workers don't fight over the same rows.
        """
        sql = """
            WITH due AS (
                SELECT id
                FROM outbox
                WHERE status = 'pending'
                AND (next_attempt_at IS NULL OR next_attempt_at <= NOW())
                ORDER BY created_at
                FOR UPDATE SKIP LOCKED
                LIMIT %s
            )
            UPDATE outbox o
            SET status = 'processing',
                updated_at = NOW()
            FROM due
            WHERE o.id = due.id
            RETURNING o.id, o.topic, o.payload, o.attempts;
            """

        async with conn.cursor() as cur:
            await cur.execute(sql, (self.batch_size,))
            rows = await cur.fetchall()

        # psycopg adapts jsonb -> dict automatically
        return [
            {"id": r[0], "topic": r[1], "payload": r[2], "attempts": r[3]} for r in rows
        ]

    async def _handle(self, topic: str, payload: Dict[str, Any]) -> None:
        """
        Route by topic.
        Add new topics here as you extend the system.
        """
        if topic == "user.verification_code":
            await self._send_verification_email(payload)  # type: ignore[arg-type]
            return

        raise RuntimeError(f"Unknown topic: {topic!r}")

    async def _send_verification_email(self, payload: Payload) -> None:
        """
        Expected payload:
          {
            "to": "...",
            "subject": "...",
            "body": "...",
            "idempotency_key": "..."   # optional
          }
        """
        await self.email_adapter.send(
            to=payload["to"],
            subject=payload["subject"],
            body=payload["body"],
            idempotency_key=payload.get("idempotency_key"),
        )
