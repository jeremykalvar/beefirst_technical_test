from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence, TypedDict

import psycopg
from psycopg.rows import tuple_row
from psycopg.types.json import Json

from app.domain.ports.outbox_repository import OutboxRepositoryPort


@dataclass
class OutboxMessage:
    id: str
    topic: str
    payload: dict
    attempts: int


# class Payload(TypedDict):
#     topic: str
#     payload: dict
#     status: str


class PgOutboxRepository(OutboxRepositoryPort):
    """
    Postgres implementation of the Outbox repo, bound to an *active async connection*.
    This class DOES NOT COMMIT; the caller (UoW / worker) controls transactions.
    """

    def __init__(self, conn: psycopg.AsyncConnection) -> None:
        self._conn = conn

    async def enqueue(
        self, *, topic: str, payload: dict, idempotency_key: str | None = None
    ) -> str:
        """
        Minimal enqueue
        """
        sql = """
        INSERT INTO outbox (topic, payload, status)
        VALUES (%s, %s, 'pending')
        RETURNING id
        """
        async with self._conn.cursor() as cur:
            await cur.execute(sql, (topic, Json(payload)))
            row = await cur.fetchone()
            return str(row[0])

    async def fetch_ready_for_dispatch(self, limit: int = 10) -> list[OutboxMessage]:
        """
        Grab up to `limit` messages that are ready to be dispatched.

        - We select rows that are pending AND available_at <= now()
        - We lock them with FOR UPDATE SKIP LOCKED so multiple workers can run safely
        - Caller should process them within the same transaction
        """
        sql = """
        SELECT id, topic, payload, attempts
        FROM outbox
        WHERE status = 'pending' AND available_at <= now()
        ORDER BY created_at
        LIMIT %s
        FOR UPDATE SKIP LOCKED
        """
        async with self._conn.cursor(row_factory=tuple_row) as cur:
            await cur.execute(sql, (limit,))
            rows: Sequence[tuple] = await cur.fetchall()

        messages: list[OutboxMessage] = []
        for id_, topic, payload, attempts in rows:
            messages.append(
                OutboxMessage(
                    id=str(id_),
                    topic=str(topic),
                    payload=payload or {},
                    attempts=int(attempts or 0),
                )
            )
        return messages

    async def mark_dispatched(self, message_id: str) -> None:
        sql = """
        UPDATE outbox
        SET status = 'dispatched',
            updated_at = now(),
            last_error = NULL
        WHERE id = %s
        """
        async with self._conn.cursor() as cur:
            await cur.execute(sql, (message_id,))

    async def mark_failed(
        self,
        message_id: str,
        *,
        error: str,
        retry_in_seconds: int,
    ) -> None:
        """
        Record failure details, increment attempts, and schedule a retry by pushing
        available_at forward by `retry_in_seconds`.
        """
        # Compute next time in UTC. (DB uses timestamptz; now() is UTC in our container.)
        next_time = datetime.now(timezone.utc) + timedelta(seconds=retry_in_seconds)

        sql = """
        UPDATE outbox
        SET attempts   = attempts + 1,
            last_error = %s,
            updated_at = now(),
            available_at = %s
        WHERE id = %s
        """
        async with self._conn.cursor() as cur:
            await cur.execute(sql, (error[:1000], next_time, message_id))
