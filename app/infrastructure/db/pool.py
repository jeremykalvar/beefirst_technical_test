from __future__ import annotations

from typing import Optional

from psycopg_pool import AsyncConnectionPool

from app.settings import get_settings

_pool: Optional[AsyncConnectionPool] = None


def get_pool() -> AsyncConnectionPool:
    """
    Return a singleton AsyncConnectionPool (not yet opened).

    We lazily create the pool the first time this is called, but we do NOT open it here.
    Call `await open_pool()` once at application startup (via FastAPI lifespan) to
    actually open the pool; then `get_pool()` can be used anywhere to retrieve it.
    """
    global _pool
    if _pool is None:
        dsn = get_settings().database_url
        _pool = AsyncConnectionPool(
            dsn,
            min_size=1,
            max_size=10,
            timeout=5,
        )
    return _pool


async def open_pool() -> AsyncConnectionPool:
    """
    Open the global pool. Safe to call multiple times; only opens once.
    """
    pool = get_pool()
    await pool.open()
    return pool


async def close_pool() -> None:
    """
    Close and clear the global pool if it was created.
    """
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
