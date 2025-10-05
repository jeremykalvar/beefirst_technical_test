from __future__ import annotations

from typing import Any, Optional

import psycopg
from psycopg.types.json import Json

from app.domain.ports.outbox_repository import OutboxRepositoryPort


class PgOutboxRepository(OutboxRepositoryPort):
    """
    Minimal Postgres outbox implementation.
    Assumes a table like:
      outbox(id uuid default gen_random_uuid() primary key,
             topic text not null,
             payload jsonb not null,
             status text not null default 'pending',
             created_at timestamptz not null default now(),
             -- optionally: idempotency_key text unique
            )
    """

    def __init__(self, conn: psycopg.AsyncConnection) -> None:
        self._conn = conn

    async def enqueue(
        self,
        *,
        topic: str,
        payload: dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> str:
        sql = """
        INSERT INTO outbox (topic, payload, status)
        VALUES (%s, %s, 'pending')
        RETURNING id;
        """
        async with self._conn.cursor() as cur:
            await cur.execute(sql, (topic, Json(payload)))
            row = await cur.fetchone()
        return str(row[0])
