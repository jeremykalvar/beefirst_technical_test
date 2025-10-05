from __future__ import annotations

from typing import Any, Optional, Type

import psycopg
from psycopg_pool import AsyncConnectionPool

from app.domain.ports.unit_of_work import UnitOfWorkPort
from app.infrastructure.db.outbox_repo import PgOutboxRepository
from app.infrastructure.db.users_repo import PgUserRepository


class PgUnitOfWork(UnitOfWorkPort):
    """
    One UoW = one DB connection + one transaction (implicit).
    We rely on psycopg’s implicit transaction: commit()/rollback() on the connection.
    """

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool
        self._conn_cm: Optional[Any] = None
        self._conn: Optional[psycopg.AsyncConnection] = None
        self._committed: bool = False

        self.db_users: PgUserRepository
        self.outbox: PgOutboxRepository

    async def __aenter__(self) -> "PgUnitOfWork":
        is_open = getattr(self._pool, "is_open", None)
        if is_open is False:
            await self._pool.open()
        elif is_open is None:
            try:
                await self._pool.open()
            except Exception:
                # If already open, some versions may raise; ignore in that case
                pass

        # Acquire a connection from the pool
        self._conn_cm = self._pool.connection()
        self._conn = await self._conn_cm.__aenter__()

        # Bind repos to this connection
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
                    await self._conn.rollback()
                # else: already committed
        finally:
            if self._conn_cm is not None:
                await self._conn_cm.__aexit__(exc_type, exc_value, traceback)
            self._conn_cm = None
            self._conn = None
            self._committed = False

    async def commit(self) -> None:
        if not self._conn:
            raise RuntimeError("Transaction not started")
        await self._conn.commit()
        self._committed = True

    async def rollback(self) -> None:
        if self._conn:
            await self._conn.rollback()
        self._committed = False
