from __future__ import annotations

from typing import Any, Optional, Type

import psycopg
from psycopg_pool import AsyncConnectionPool

from app.domain.ports.unit_of_work import UnitOfWorkPort
from app.infrastructure.db.users_repo import PgUserRepository
from app.infrastructure.db.outbox_repo import PgOutboxRepository


class PgUnitOfWork(UnitOfWorkPort):
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool
        self._conn_cm: Optional[Any] = None
        self._conn: Optional[psycopg.AsyncConnection] = None
        self._committed: bool = False
        self.db_users: PgUserRepository
        self.outbox: PgOutboxRepository

    async def __aenter__(self) -> "PgUnitOfWork":
        self._conn_cm = self._pool.connection()
        self._conn = await self._conn_cm.__aenter__()
        self.db_users = PgUserRepository(self._conn)
        self.outbox = PgOutboxRepository(self._conn)
        self._committed = False
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> None:
        try:
            if self._conn:
                if exc_value or not self._committed:
                    try:
                        await self._conn.rollback()
                    except Exception:
                        pass
        finally:
            if self._conn_cm:
                await self._conn_cm.__aexit__(exc_type, exc_value, traceback)
            self._conn = None
            self._conn_cm = None
            self._committed = False

    async def commit(self) -> None:
        if not self._conn:
            raise RuntimeError("No connection available to commit")
        await self._conn.commit()
        self._committed = True

    async def rollback(self) -> None:
        if self._conn:
            await self._conn.rollback()
        self._committed = False
