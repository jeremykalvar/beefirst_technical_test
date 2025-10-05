from __future__ import annotations

from typing import Optional

from redis.asyncio import Redis

from app.settings import get_settings

_client: Optional[Redis] = None


def get_redis() -> Redis:
    """
    Lazy singleton Redis client using REDIS_URL from settings.
    decode_responses=True -> we get/put str, not bytes.
    """
    global _client
    if _client is None:
        url = get_settings().redis_url
        _client = Redis.from_url(url, encoding="utf-8", decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
