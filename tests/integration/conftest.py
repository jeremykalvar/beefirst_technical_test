# tests/integration/conftest.py
import pytest_asyncio
from redis.asyncio import Redis


@pytest_asyncio.fixture
async def redis_client():
    r = Redis.from_url("redis://redis:6379/0", encoding="utf-8", decode_responses=True)
    try:
        yield r
    finally:
        await r.aclose()
