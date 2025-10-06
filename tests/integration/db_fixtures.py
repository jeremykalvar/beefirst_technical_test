import asyncio
import time
from contextlib import asynccontextmanager

import pytest_asyncio
from psycopg_pool import AsyncConnectionPool

from app.infrastructure.db.pool import get_pool


class _MiniPool:
    def __init__(self, p: AsyncConnectionPool):
        self._p = p

    @asynccontextmanager
    async def connection(self):
        # use a longer timeout when borrowing a conn from the pool
        conn = await self._p.getconn(timeout=30)
        try:
            yield conn
        finally:
            await self._p.putconn(conn)


async def _wait_pool_ready(p: AsyncConnectionPool, timeout: float = 30.0) -> None:
    """Retry simple SELECT until Postgres accepts connections."""
    deadline = time.monotonic() + timeout
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            conn = await p.getconn(timeout=1)
            try:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1;")
                    await cur.fetchone()
                return
            finally:
                await p.putconn(conn)
        except Exception as e:
            last_exc = e
            await asyncio.sleep(0.5)
    # if we’re here, we never managed to connect
    if last_exc:
        raise last_exc
    raise TimeoutError("database not ready")


@pytest_asyncio.fixture(scope="session")
async def pool() -> _MiniPool:
    p = get_pool()
    # open the pool and wait until DB is responsive
    if getattr(p, "open", None):
        await p.open()
    p.timeout = 30
    await _wait_pool_ready(p, timeout=30)
    try:
        yield _MiniPool(p)
    finally:
        await p.close()


@pytest_asyncio.fixture
async def truncate_outbox(pool: _MiniPool):
    # before each test
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute("TRUNCATE outbox RESTART IDENTITY;")
    yield
    # after each test
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute("TRUNCATE outbox RESTART IDENTITY;")
