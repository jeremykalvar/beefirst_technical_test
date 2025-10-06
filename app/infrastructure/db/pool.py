from __future__ import annotations

from typing import Optional
from psycopg_pool import AsyncConnectionPool
from app.settings import get_settings

_pool: Optional[AsyncConnectionPool] = None


def _add_connect_timeout(dsn: str, seconds: int = 3) -> str:
    if "connect_timeout=" in dsn:
        return dsn
    sep = "&" if "?" in dsn else "?"
    return f"{dsn}{sep}connect_timeout={seconds}"


def get_pool() -> AsyncConnectionPool:
    """
    Create (if needed) and return the global pool WITHOUT opening it.
    No deprecation warning because we pass open=False.
    """
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(
            get_settings().database_url,
            min_size=1,
            max_size=10,
            timeout=5,
            open=False,  # created closed; caller decides when to open
        )
    return _pool


async def open_pool() -> AsyncConnectionPool:
    pool = get_pool()
    await pool.open()
    return pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
